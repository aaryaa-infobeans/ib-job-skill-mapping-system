"""Test script to validate end-to-end flow."""

import requests
import json
from datetime import datetime, timedelta
from jose import jwt

# Configuration
BASE_URL = "http://127.0.0.1:8001"
SECRET_KEY = "test-secret-key-for-development-only-change-in-production"

def generate_jwt_token():
    """Generate a JWT token for testing."""
    payload = {
        "sub": "test-client",
        "client_id": "test-client",
        "scopes": ["read", "write"],
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token

def test_health():
    """Test health endpoint (no auth required)."""
    print("\n=== Testing Health Endpoint ===")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_create_requisition(token):
    """Test creating a job requisition."""
    print("\n=== Testing Create Requisition ===")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "request_id": "REQ-TEST-001",
        "schema_version": "1.1",
        "source_system": "EAGLE",
        "client_name": "EAGLE",
        "job_description": {
            "client_name": "ICC",
            "title": "Senior Software Engineer",
            "role": "Backend Developer",
            "requisition_duration_month": 12,
            "expected_start_date": "2026-03-01",
            "priority": "HIGH",
            "location": ["Pune", "Bangalore"],
            "work_mode": ["wfh", "hybrid"],
            "experience": {
                "min_months": 60,
                "max_months": 120
            },
            "mandatory_skills": ["Python", "Django", "DRF", "PostgreSQL"],
            "preferred_skills": ["AWS", "Docker", "Kubernetes"],
            "jd_text": "We are looking for a Senior Software Engineer with 5+ years of experience in Python and Django. The candidate should have strong experience with REST APIs, PostgreSQL, and cloud platforms like AWS."
        },
        "metadata": {
            "submitted_by": "Aarya",
            "submitted_at": datetime.utcnow().isoformat() + "Z",
            "department": "Open Source"
        }
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/jd-skill-mapping/",
            headers=headers,
            json=payload
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code in [200, 201]:
            return response.json().get("correlation_id")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_bulk_upsert(token):
    """Test bulk upsert of team member skills."""
    print("\n=== Testing Bulk Upsert Team Members ===")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "team_members": [
            {
                "team_member_id": "TM001",
                "name": "Rahul Sharma",
                "email": "rahul.sharma@example.com",
                "designation": "Senior Software Engineer",
                "primary_skills": ["Python", "Django", "FastAPI", "PostgreSQL"],
                "secondary_skills": ["AWS", "Docker", "Redis"],
                "total_experience_years": 7,
                "relevant_experience_years": 5
            },
            {
                "team_member_id": "TM002",
                "name": "Priya Patel",
                "email": "priya.patel@example.com",
                "designation": "Lead Engineer",
                "primary_skills": ["Python", "Django", "DRF", "MySQL"],
                "secondary_skills": ["Kubernetes", "Jenkins", "AWS"],
                "total_experience_years": 10,
                "relevant_experience_years": 8
            },
            {
                "team_member_id": "TM003",
                "name": "Amit Kumar",
                "email": "amit.kumar@example.com",
                "designation": "Software Engineer",
                "primary_skills": ["Python", "Flask", "PostgreSQL"],
                "secondary_skills": ["Docker", "Git"],
                "total_experience_years": 4,
                "relevant_experience_years": 3
            }
        ]
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/team-members/skill-availability/bulk-upsert",
            headers=headers,
            json=payload
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code in [200, 201]
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_get_matches(token, correlation_id):
    """Test retrieving matches for a requisition."""
    print("\n=== Testing Get Matches ===")
    
    if not correlation_id:
        print("❌ No correlation ID provided")
        return False
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/jd-skill-mapping/{correlation_id}/matches",
            headers=headers
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run end-to-end validation."""
    print("🚀 Starting End-to-End Validation")
    print("=" * 60)
    
    # Generate JWT token
    print("\n📝 Generating JWT Token...")
    token = generate_jwt_token()
    print(f"Token generated: {token[:50]}...")
    
    # Test 1: Health endpoint
    if not test_health():
        print("\n❌ Health check failed. Server may not be running.")
        return
    
    # Test 2: Bulk upsert team members
    if not test_bulk_upsert(token):
        print("\n❌ Bulk upsert failed.")
        return
    
    # Test 3: Create requisition
    correlation_id = test_create_requisition(token)
    if not correlation_id:
        print("\n❌ Create requisition failed.")
        return
    
    # Test 4: Get matches
    if not test_get_matches(token, correlation_id):
        print("\n❌ Get matches failed.")
        return
    
    print("\n" + "=" * 60)
    print("✅ All tests passed! End-to-end validation successful.")
    print("=" * 60)

if __name__ == "__main__":
    main()
