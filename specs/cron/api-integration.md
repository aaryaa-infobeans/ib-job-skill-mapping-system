# API Integration - Nightly Batch Ingestion Service

**Version:** 1.0  
**Date:** 2026-02-06  
**Status:** Draft  
**Owner:** Platform Engineering

---

## 1. Overview

This document defines the integration strategy for consuming the external Team Member Skill & Availability API using OAuth 2.0 Client Credentials grant. The integration includes token management, API client implementation, error handling, and retry logic.

---

## 2. OAuth 2.0 Authentication Flow

### 2.1 Client Credentials Grant (RFC 6749 Section 4.4)

```mermaid
sequenceDiagram
    participant SERVICE as Ingestion Service
    participant AUTH as OAuth 2.0 Server
    participant API as External API
    
    SERVICE->>AUTH: POST /oauth/token<br/>grant_type=client_credentials<br/>client_id=xxx<br/>client_secret=yyy<br/>scope=read:team-data
    AUTH->>AUTH: Validate credentials
    AUTH-->>SERVICE: 200 OK<br/>{access_token, expires_in, token_type}
    
    SERVICE->>SERVICE: Cache token with expiry
    
    SERVICE->>API: GET /api/v1/team-members/skill-availability<br/>Authorization: Bearer {access_token}
    API->>API: Validate token
    API-->>SERVICE: 200 OK<br/>{batch data}
    
    Note over SERVICE: Token expires after 3600s
    
    SERVICE->>AUTH: POST /oauth/token (refresh)
    AUTH-->>SERVICE: 200 OK<br/>{new access_token}
```

### 2.2 Token Endpoint Configuration

```python
# OAuth 2.0 Token Endpoint
OAUTH_TOKEN_URL = "https://external-system.example.com/oauth/token"

# Request Parameters
{
    "grant_type": "client_credentials",
    "client_id": "<from-env>",
    "client_secret": "<from-vault>",
    "scope": "read:team-data"
}

# Response Format
{
    "access_token": "eyJhbGciOiJSUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 3600,  # seconds
    "scope": "read:team-data"
}
```

---

## 3. OAuth Client Implementation

### 3.1 Token Manager Class

**File:** `src/external_api/oauth_client.py`

```python
"""OAuth 2.0 client for external API authentication."""

import time
from datetime import datetime, timedelta
from typing import Optional
import requests
from requests.auth import HTTPBasicAuth

from src.app.settings import settings


class OAuthTokenError(Exception):
    """Raised when OAuth token acquisition fails."""
    pass


class OAuthClient:
    """
    OAuth 2.0 Client Credentials grant implementation.
    
    Features:
    - Token caching with expiry tracking
    - Automatic token refresh
    - Thread-safe token access
    - Retry logic for transient failures
    """
    
    def __init__(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        scope: str = "read:team-data"
    ):
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._buffer_seconds = 60  # Refresh 60s before expiry
    
    def get_access_token(self, force_refresh: bool = False) -> str:
        """
        Get valid access token, refreshing if necessary.
        
        Args:
            force_refresh: Force token refresh even if not expired
            
        Returns:
            Valid access token
            
        Raises:
            OAuthTokenError: If token acquisition fails
        """
        if force_refresh or self._is_token_expired():
            self._refresh_token()
        
        if not self._access_token:
            raise OAuthTokenError("No access token available")
        
        return self._access_token
    
    def _is_token_expired(self) -> bool:
        """Check if current token is expired or about to expire."""
        if not self._access_token or not self._token_expires_at:
            return True
        
        # Consider token expired if within buffer period
        return datetime.utcnow() >= (self._token_expires_at - timedelta(seconds=self._buffer_seconds))
    
    def _refresh_token(self) -> None:
        """
        Request new access token from OAuth server.
        
        Raises:
            OAuthTokenError: If token request fails
        """
        payload = {
            "grant_type": "client_credentials",
            "scope": self.scope
        }
        
        try:
            response = requests.post(
                self.token_url,
                data=payload,
                auth=HTTPBasicAuth(self.client_id, self.client_secret),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10
            )
            
            response.raise_for_status()
            
            token_data = response.json()
            self._access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)
            self._token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            print(f"✓ OAuth token acquired (expires in {expires_in}s)")
            
        except requests.RequestException as e:
            raise OAuthTokenError(f"Failed to acquire OAuth token: {e}")
        except KeyError:
            raise OAuthTokenError("Invalid token response format (missing access_token)")
    
    def revoke_token(self) -> None:
        """Clear cached token (logout)."""
        self._access_token = None
        self._token_expires_at = None


# Singleton instance
_oauth_client: Optional[OAuthClient] = None


def get_oauth_client() -> OAuthClient:
    """Get or create OAuth client singleton."""
    global _oauth_client
    
    if _oauth_client is None:
        _oauth_client = OAuthClient(
            token_url=settings.oauth_token_url,
            client_id=settings.oauth_client_id,
            client_secret=settings.oauth_client_secret,
            scope=settings.oauth_scope
        )
    
    return _oauth_client
```

### 3.2 Environment Configuration

```bash
# .env file (never commit to git)
OAUTH_TOKEN_URL=https://external-system.example.com/oauth/token
OAUTH_CLIENT_ID=ib-ingestion-service
OAUTH_CLIENT_SECRET=<vault-managed-secret>
OAUTH_SCOPE=read:team-data
```

---

## 4. External API Client

### 4.1 API Client Class

**File:** `src/external_api/team_data_client.py`

```python
"""Client for external team member skill & availability API."""

import uuid
from typing import Dict, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.external_api.oauth_client import get_oauth_client, OAuthTokenError
from src.app.settings import settings


class ExternalAPIError(Exception):
    """Base exception for external API errors."""
    pass


class TeamDataClient:
    """
    HTTP client for fetching team member data from external system.
    
    Features:
    - Automatic OAuth token management
    - Retry logic with exponential backoff
    - Correlation ID tracking
    - Timeout handling
    """
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.oauth_client = get_oauth_client()
        
        # Configure session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            backoff_factor=2  # 1s, 2s, 4s
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def fetch_all_batches(self, correlation_id: Optional[str] = None) -> Dict:
        """
        Fetch all batches of team member data.
        
        Args:
            correlation_id: Optional correlation ID for tracking
            
        Returns:
            Complete payload with metadata and team_members[]
            
        Raises:
            ExternalAPIError: If API request fails
        """
        if correlation_id is None:
            correlation_id = f"INGEST-{uuid.uuid4().hex[:12]}"
        
        endpoint = f"{self.base_url}/api/v1/team-members/skill-availability/bulk-upsert"
        
        try:
            # Get fresh token
            access_token = self.oauth_client.get_access_token()
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Correlation-ID": correlation_id,
                "Accept": "application/json"
            }
            
            print(f"Fetching team data from {endpoint}")
            print(f"Correlation ID: {correlation_id}")
            
            response = self.session.get(
                endpoint,
                headers=headers,
                timeout=self.timeout
            )
            
            # Handle 401 - token may have expired mid-request
            if response.status_code == 401:
                print("Token expired, refreshing...")
                access_token = self.oauth_client.get_access_token(force_refresh=True)
                headers["Authorization"] = f"Bearer {access_token}"
                response = self.session.get(endpoint, headers=headers, timeout=self.timeout)
            
            response.raise_for_status()
            
            payload = response.json()
            
            print(f"✓ Fetched {payload['metadata']['total_batches']} batches")
            print(f"  Total records: {payload['metadata']['total_records']}")
            
            return payload
            
        except OAuthTokenError as e:
            raise ExternalAPIError(f"OAuth authentication failed: {e}")
        except requests.Timeout:
            raise ExternalAPIError(f"Request timed out after {self.timeout}s")
        except requests.HTTPError as e:
            raise ExternalAPIError(f"HTTP error {e.response.status_code}: {e.response.text}")
        except requests.RequestException as e:
            raise ExternalAPIError(f"Request failed: {e}")
        except ValueError:
            raise ExternalAPIError("Invalid JSON response from API")
    
    def fetch_batch_by_id(self, batch_id: str, correlation_id: Optional[str] = None) -> Dict:
        """
        Fetch specific batch by batch_id (for retry scenarios).
        
        Args:
            batch_id: Batch identifier to fetch
            correlation_id: Optional correlation ID for tracking
            
        Returns:
            Batch payload
            
        Raises:
            ExternalAPIError: If API request fails
        """
        if correlation_id is None:
            correlation_id = f"RETRY-{uuid.uuid4().hex[:12]}"
        
        endpoint = f"{self.base_url}/api/v1/team-members/skill-availability/bulk-upsert"
        params = {"batch_id": batch_id}
        
        try:
            access_token = self.oauth_client.get_access_token()
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Correlation-ID": correlation_id,
                "X-Batch-ID": batch_id,
                "Accept": "application/json"
            }
            
            print(f"Fetching batch {batch_id}")
            
            response = self.session.get(
                endpoint,
                params=params,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 401:
                access_token = self.oauth_client.get_access_token(force_refresh=True)
                headers["Authorization"] = f"Bearer {access_token}"
                response = self.session.get(endpoint, params=params, headers=headers, timeout=self.timeout)
            
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            raise ExternalAPIError(f"Failed to fetch batch {batch_id}: {e}")


def get_team_data_client() -> TeamDataClient:
    """Get configured team data API client."""
    return TeamDataClient(
        base_url=settings.external_api_base_url,
        timeout=settings.external_api_timeout
    )
```

---

## 5. API Request/Response Formats

### 5.1 Request Headers

```http
GET /api/v1/team-members/skill-availability/bulk-upsert HTTP/1.1
Host: external-system.example.com
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
X-Correlation-ID: INGEST-20260206-abc123
Accept: application/json
User-Agent: ib-ingestion-service/1.0
```

### 5.2 Success Response (200 OK)

```json
{
  "metadata": {
    "batch_id": "BATCH-2026-02-06-001",
    "timestamp": "2026-02-06T02:00:00Z",
    "total_records": 150,
    "batch_number": 1,
    "total_batches": 3,
    "records_in_batch": 50,
    "source_system": "HRIS",
    "schema_version": "1.0",
    "status": {
      "code": 200,
      "key": "SUCCESS",
      "message": "Batch data retrieved successfully"
    }
  },
  "team_members": [...]
}
```

### 5.3 Error Responses

#### 401 Unauthorized

```json
{
  "error": "invalid_token",
  "error_description": "The access token expired"
}
```

**Action:** Refresh token and retry

#### 429 Too Many Requests

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
Content-Type: application/json

{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Retry after 60 seconds"
}
```

**Action:** Wait `Retry-After` seconds, then retry

#### 500 Internal Server Error

```json
{
  "error": "internal_error",
  "message": "Unexpected error occurred",
  "request_id": "req-abc123"
}
```

**Action:** Retry with exponential backoff (max 3 attempts)

#### 503 Service Unavailable

```http
HTTP/1.1 503 Service Unavailable
Content-Type: application/json

{
  "error": "service_unavailable",
  "message": "Service temporarily unavailable"
}
```

**Action:** Retry after delay, fail batch if persistent

---

## 6. Error Handling Strategy

### 6.1 Error Classification

```python
class ErrorClassifier:
    """Classify API errors into retryable vs. fatal."""
    
    RETRYABLE_STATUS_CODES = {401, 429, 500, 502, 503, 504}
    FATAL_STATUS_CODES = {400, 403, 404}
    
    @staticmethod
    def is_retryable(status_code: int) -> bool:
        """Determine if error is retryable."""
        return status_code in ErrorClassifier.RETRYABLE_STATUS_CODES
    
    @staticmethod
    def get_retry_delay(attempt: int, base_delay: int = 60) -> int:
        """Calculate exponential backoff delay."""
        return base_delay * (2 ** (attempt - 1))  # 60s, 120s, 240s
```

### 6.2 Retry Logic

```python
def fetch_with_retry(client: TeamDataClient, max_attempts: int = 3) -> Dict:
    """
    Fetch data with automatic retry on transient failures.
    
    Args:
        client: Configured API client
        max_attempts: Maximum retry attempts
        
    Returns:
        API response payload
        
    Raises:
        ExternalAPIError: If all retries exhausted
    """
    for attempt in range(1, max_attempts + 1):
        try:
            return client.fetch_all_batches()
        except ExternalAPIError as e:
            if attempt == max_attempts:
                raise
            
            # Extract status code if available
            if hasattr(e, "status_code"):
                if not ErrorClassifier.is_retryable(e.status_code):
                    raise  # Don't retry fatal errors
                
                delay = ErrorClassifier.get_retry_delay(attempt)
                print(f"⚠ Attempt {attempt} failed: {e}")
                print(f"  Retrying in {delay}s...")
                time.sleep(delay)
            else:
                raise  # Non-HTTP errors are not retryable
```

---

## 7. Rate Limiting Compliance

### 7.1 Rate Limit Handling

```python
class RateLimitHandler:
    """Handle rate limit responses from external API."""
    
    @staticmethod
    def handle_429(response: requests.Response) -> int:
        """
        Extract retry delay from 429 response.
        
        Args:
            response: HTTP response with status 429
            
        Returns:
            Delay in seconds before retry
        """
        # Check Retry-After header
        retry_after = response.headers.get("Retry-After")
        
        if retry_after:
            if retry_after.isdigit():
                return int(retry_after)
            else:
                # HTTP-date format (rarely used)
                from email.utils import parsedate_to_datetime
                retry_datetime = parsedate_to_datetime(retry_after)
                delay = (retry_datetime - datetime.utcnow()).total_seconds()
                return max(0, int(delay))
        
        # Default to 60 seconds if header missing
        return 60
```

### 7.2 Client-Side Rate Limiting

```python
from time import time, sleep

class RateLimiter:
    """Client-side rate limiter to prevent excessive requests."""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = []
    
    def acquire(self) -> None:
        """Block until request can proceed within rate limit."""
        now = time()
        
        # Remove requests outside current window
        self.requests = [req_time for req_time in self.requests if now - req_time < self.window_seconds]
        
        if len(self.requests) >= self.max_requests:
            # Wait until oldest request exits window
            sleep_time = self.window_seconds - (now - self.requests[0]) + 1
            print(f"Rate limit reached, waiting {sleep_time:.1f}s")
            sleep(sleep_time)
            self.acquire()  # Re-check after sleep
        
        self.requests.append(now)
```

---

## 8. Monitoring and Observability

### 8.1 Metrics to Track

```python
class APIMetrics:
    """Track API client metrics."""
    
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_response_time_ms = 0
        self.oauth_token_refreshes = 0
        self.rate_limit_hits = 0
    
    def record_request(self, success: bool, response_time_ms: int):
        """Record request outcome."""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        self.total_response_time_ms += response_time_ms
    
    def get_summary(self) -> dict:
        """Get metrics summary."""
        return {
            "total_requests": self.total_requests,
            "success_rate": self.successful_requests / max(self.total_requests, 1),
            "avg_response_time_ms": self.total_response_time_ms / max(self.total_requests, 1),
            "oauth_refreshes": self.oauth_token_refreshes,
            "rate_limit_hits": self.rate_limit_hits
        }
```

### 8.2 Logging Requirements

```python
import logging
import json

logger = logging.getLogger("external_api")

def log_api_request(method: str, url: str, headers: dict, correlation_id: str):
    """Log outgoing API request."""
    logger.info(
        "API Request",
        extra={
            "method": method,
            "url": url,
            "correlation_id": correlation_id,
            "has_auth_header": "Authorization" in headers
        }
    )

def log_api_response(status_code: int, response_time_ms: int, correlation_id: str):
    """Log API response."""
    logger.info(
        "API Response",
        extra={
            "status_code": status_code,
            "response_time_ms": response_time_ms,
            "correlation_id": correlation_id
        }
    )
```

---

## 9. Testing Strategy

### 9.1 Unit Tests

```python
import pytest
from unittest.mock import Mock, patch
from src.external_api.oauth_client import OAuthClient

def test_oauth_client_caches_token():
    """Test that OAuth client caches token and reuses it."""
    client = OAuthClient("http://auth.example.com", "client", "secret")
    
    with patch("requests.post") as mock_post:
        mock_post.return_value.json.return_value = {
            "access_token": "token123",
            "expires_in": 3600
        }
        
        token1 = client.get_access_token()
        token2 = client.get_access_token()
        
        assert token1 == token2
        assert mock_post.call_count == 1  # Only one request

def test_oauth_client_refreshes_expired_token():
    """Test automatic token refresh on expiry."""
    client = OAuthClient("http://auth.example.com", "client", "secret")
    client._buffer_seconds = 0  # No buffer for test
    
    with patch("requests.post") as mock_post:
        mock_post.return_value.json.return_value = {
            "access_token": "token123",
            "expires_in": 1  # Expires in 1 second
        }
        
        token1 = client.get_access_token()
        time.sleep(2)  # Wait for expiry
        token2 = client.get_access_token()
        
        assert mock_post.call_count == 2  # Two requests (initial + refresh)
```

### 9.2 Integration Tests with Mock Server

```python
import pytest
from unittest.mock import Mock
import responses

@responses.activate
def test_team_data_client_fetch_all_batches():
    """Test fetching all batches from external API."""
    # Mock OAuth token endpoint
    responses.add(
        responses.POST,
        "http://auth.example.com/token",
        json={"access_token": "mock_token", "expires_in": 3600},
        status=200
    )
    
    # Mock team data endpoint
    responses.add(
        responses.GET,
        "http://api.example.com/api/v1/team-members/skill-availability/bulk-upsert",
        json={
            "metadata": {
                "batch_id": "TEST-001",
                "total_batches": 1,
                "total_records": 10
            },
            "team_members": []
        },
        status=200
    )
    
    client = TeamDataClient("http://api.example.com")
    payload = client.fetch_all_batches()
    
    assert payload["metadata"]["batch_id"] == "TEST-001"
    assert len(responses.calls) == 2  # OAuth + Data request
```

---

## 10. Security Considerations

### 10.1 Secret Management

```python
# ❌ NEVER DO THIS
client_secret = "hardcoded-secret-123"

# ✅ Use environment variables
import os
client_secret = os.getenv("OAUTH_CLIENT_SECRET")

# ✅ Use secrets manager (production)
from azure.keyvault.secrets import SecretClient
secret_client = SecretClient(vault_url, credential)
client_secret = secret_client.get_secret("oauth-client-secret").value
```

### 10.2 TLS/SSL Verification

```python
# ✅ Always verify SSL certificates in production
session.verify = True  # Default, but explicit is better

# ❌ NEVER disable verification in production
session.verify = False  # Only for local development with self-signed certs
```

### 10.3 Credential Rotation

```bash
# Procedure for rotating OAuth client credentials:
# 1. Generate new client_secret in external system
# 2. Update secret in vault/environment
# 3. Restart ingestion service (K8s will pick up new secret)
# 4. Revoke old client_secret after 24h grace period
```

---

## 11. Definition of Done

- [ ] OAuth client implemented with token caching
- [ ] External API client with retry logic
- [ ] Error classification and handling
- [ ] Rate limiting compliance
- [ ] Unit tests for OAuth client (>80% coverage)
- [ ] Integration tests with mock server
- [ ] Logging and metrics implemented
- [ ] Secret management via environment variables
- [ ] Documentation complete with examples

---

**Document Status:** Ready for Implementation  
**Next Steps:** Implement OAuth client and team data API client with comprehensive error handling
