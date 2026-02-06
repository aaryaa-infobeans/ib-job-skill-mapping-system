"""Mock API server for integration testing OAuth and external API client."""

import json
import time
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)

# Mock tokens with expiration
MOCK_TOKENS: Dict[str, Dict[str, Any]] = {}
VALID_CLIENT_CREDENTIALS = {
    "test-client": "test-secret",
    "client-1": "secret-1",
}

# Mock team data
MOCK_TEAM_DATA = {
    "metadata": {
        "batch_id": "batch-20260206-001",
        "generated_at": "2026-02-06T10:00:00Z",
        "total_records": 5,
    },
    "team_members": [
        {
            "employee_id": "EMP001",
            "name": "Alice Johnson",
            "email": "alice@example.com",
            "location": "New York",
            "skills": [
                {"skill_id": "S001", "skill_name": "Python", "proficiency_level": "Advanced"},
                {"skill_id": "S002", "skill_name": "SQL", "proficiency_level": "Intermediate"},
            ],
            "allocations": [
                {
                    "project_id": "PRJ001",
                    "allocation_percentage": 80,
                    "start_date": "2026-01-01",
                    "end_date": "2026-06-30",
                }
            ],
            "certifications": [
                {"certification_name": "AWS Certified Developer", "issued_date": "2025-05-15"}
            ],
        },
        {
            "employee_id": "EMP002",
            "name": "Bob Smith",
            "email": "bob@example.com",
            "location": "London",
            "skills": [
                {"skill_id": "S003", "skill_name": "Java", "proficiency_level": "Advanced"},
                {"skill_id": "S004", "skill_name": "Kubernetes", "proficiency_level": "Intermediate"},
            ],
            "allocations": [
                {
                    "project_id": "PRJ002",
                    "allocation_percentage": 100,
                    "start_date": "2026-01-15",
                    "end_date": "2026-12-31",
                }
            ],
            "certifications": [],
        },
        {
            "employee_id": "EMP003",
            "name": "Carol White",
            "email": "carol@example.com",
            "location": "Mumbai",
            "skills": [
                {"skill_id": "S001", "skill_name": "Python", "proficiency_level": "Expert"},
                {"skill_id": "S005", "skill_name": "Machine Learning", "proficiency_level": "Advanced"},
            ],
            "allocations": [],
            "certifications": [
                {"certification_name": "Google Cloud Professional", "issued_date": "2024-11-20"},
                {"certification_name": "Certified Scrum Master", "issued_date": "2023-08-10"},
            ],
        },
        {
            "employee_id": "EMP004",
            "name": "David Lee",
            "email": "david@example.com",
            "location": "Singapore",
            "skills": [
                {"skill_id": "S006", "skill_name": "React", "proficiency_level": "Advanced"},
                {"skill_id": "S007", "skill_name": "TypeScript", "proficiency_level": "Intermediate"},
            ],
            "allocations": [
                {
                    "project_id": "PRJ003",
                    "allocation_percentage": 50,
                    "start_date": "2026-02-01",
                    "end_date": "2026-05-31",
                }
            ],
            "certifications": [],
        },
        {
            "employee_id": "EMP005",
            "name": "Eva Martinez",
            "email": "eva@example.com",
            "location": "Madrid",
            "skills": [
                {"skill_id": "S008", "skill_name": "DevOps", "proficiency_level": "Expert"},
                {"skill_id": "S009", "skill_name": "Terraform", "proficiency_level": "Advanced"},
            ],
            "allocations": [
                {
                    "project_id": "PRJ004",
                    "allocation_percentage": 75,
                    "start_date": "2026-01-01",
                    "end_date": "2026-03-31",
                }
            ],
            "certifications": [
                {"certification_name": "Terraform Associate", "issued_date": "2025-01-10"}
            ],
        },
    ],
}

MOCK_BATCH_DATA = {
    "batch-20260206-001": {
        "batch_id": "batch-20260206-001",
        "data": MOCK_TEAM_DATA["team_members"][:3],
    },
    "batch-20260206-002": {
        "batch_id": "batch-20260206-002",
        "data": MOCK_TEAM_DATA["team_members"][3:],
    },
}


class MockAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for mock API server."""

    def log_message(self, format: str, *args) -> None:
        """Override to use structlog."""
        logger.info("Request", method=self.command, path=self.path, message=format % args)

    def _set_response(self, status_code: int, content_type: str = "application/json"):
        """Set response headers."""
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.end_headers()

    def _send_json(self, data: Dict[str, Any], status_code: int = 200):
        """Send JSON response."""
        self._set_response(status_code)
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _send_error_json(self, error_msg: str, status_code: int):
        """Send JSON error response."""
        self._send_json({"error": error_msg}, status_code)

    def _validate_bearer_token(self) -> Optional[str]:
        """Validate Authorization header and return token."""
        auth_header = self.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        # Check if token exists and is not expired
        if token in MOCK_TOKENS:
            token_data = MOCK_TOKENS[token]
            if datetime.utcnow() < token_data["expires_at"]:
                return token
            else:
                # Token expired
                del MOCK_TOKENS[token]
                return None
        
        return None

    def do_POST(self):
        """Handle POST requests."""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == "/oauth/token":
            self._handle_oauth_token()
        else:
            self._send_error_json("Not found", 404)

    def _handle_oauth_token(self):
        """Handle OAuth token request."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        params = parse_qs(body)

        # Validate grant_type
        grant_type = params.get("grant_type", [""])[0]
        if grant_type != "client_credentials":
            self._send_error_json("Invalid grant_type", 400)
            return

        # Validate client credentials
        client_id = params.get("client_id", [""])[0]
        client_secret = params.get("client_secret", [""])[0]

        if client_id not in VALID_CLIENT_CREDENTIALS or VALID_CLIENT_CREDENTIALS[client_id] != client_secret:
            self._send_error_json("Invalid client credentials", 401)
            return

        # Generate mock token
        token = f"mock_token_{int(time.time())}"
        expires_in = 3600
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        MOCK_TOKENS[token] = {
            "client_id": client_id,
            "expires_at": expires_at,
        }

        response = {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": expires_in,
        }
        
        self._send_json(response)
        logger.info("OAuth token issued", client_id=client_id, expires_in=expires_in)

    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)
        
        # Check for error simulation query params
        query_params = parse_qs(parsed_path.query)
        simulate_error = query_params.get("simulate_error", [None])[0]
        
        if simulate_error == "401":
            self._send_error_json("Unauthorized", 401)
            return
        elif simulate_error == "429":
            self._send_error_json("Rate limit exceeded", 429)
            return
        elif simulate_error == "503":
            self._send_error_json("Service unavailable", 503)
            return

        # Validate authentication
        token = self._validate_bearer_token()
        if not token:
            self._send_error_json("Unauthorized - invalid or expired token", 401)
            return

        # Route requests
        if parsed_path.path == "/team-members":
            self._handle_team_members()
        elif parsed_path.path.startswith("/team-members/batch/"):
            batch_id = parsed_path.path.split("/")[-1]
            self._handle_batch_by_id(batch_id)
        else:
            self._send_error_json("Not found", 404)

    def _handle_team_members(self):
        """Handle team members list request."""
        self._send_json(MOCK_TEAM_DATA)
        logger.info("Team members data sent", count=len(MOCK_TEAM_DATA["team_members"]))

    def _handle_batch_by_id(self, batch_id: str):
        """Handle batch-specific request."""
        if batch_id not in MOCK_BATCH_DATA:
            self._send_error_json(f"Batch {batch_id} not found", 404)
            return
        
        batch_data = MOCK_BATCH_DATA[batch_id]
        self._send_json(batch_data)
        logger.info("Batch data sent", batch_id=batch_id, count=len(batch_data["data"]))


def run_server(port: int = 8080, host: str = "localhost"):
    """Start the mock API server."""
    server_address = (host, port)
    httpd = HTTPServer(server_address, MockAPIHandler)
    
    logger.info("Mock API server starting", host=host, port=port)
    print(f"Mock API server running on http://{host}:{port}")
    print("Press Ctrl+C to stop")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Mock API server stopping")
        print("\nServer stopped")
        httpd.server_close()


if __name__ == "__main__":
    import sys
    
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port=port)
