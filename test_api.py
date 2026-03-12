#!/usr/bin/env python3
"""Test the JD Skill Mapping API with proper authentication."""

import requests
import jwt
from datetime import datetime, timedelta, timezone
import json

# Configuration
BASE_URL = "http://127.0.0.1:8001"
SECRET_KEY = "test-secret-key-for-testing"
ALGORITHM = "HS256"

def generate_token():
    """Generate a valid JWT token."""
    payload = {
        "sub": "test-client",
        "client_id": "test-client",
        "exp": datetime.now(timezone.utc) + timedelta(days=365)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def test_health():
    """Test the health endpoint (no auth required)."""
    print_section("TEST 1: Health Check (No Authentication)")
    print("Endpoint: GET /health\n")
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response:\n{json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_submit_requisition(token):
    """Test submitting a job requisition (auth required)."""
    print_section("TEST 2: Submit Job Requisition (JWT Authentication)")
    print("Endpoint: POST /api/v1/jd-skill-mapping/\n")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "request_id": "REQ-2026-000145",
        "schema_version": "1.1",
        "source_system": "EAGLE_v1",
        "client_name": "DNC",
        "metadata": {
            "submitted_by": "Aarya",
            "submitted_at": "2026-02-19",
            "department": "Engineering"
        },
        "job_description": {
            "client_name": "DNC",
            "title": "Senior Backend Engineer",
            "role": "Backend Engineer",
            "requisition_duration_month": 3,
            "expected_start_date": "2026-02-15",
            "priority": "HIGH",
            "location": ["Bangalore", "Pune"],
            "work_mode": ["wfh"],
            "experience": {
                "min_months": 48,
                "max_months": 60
            },
            "mandatory_skills": [
                "Python",
                "Django",
                "REST API",
                "AWS",
                "PostgreSQL"
            ],
            "preferred_skills": [
                "Docker",
                "Kubernetes"
            ],
            "jd_text": "Looking for a Senior Backend Engineer with strong backend experience in Python, Django, REST APIs, AWS, and PostgreSQL."
        }
    }
    
    print(f"Request Payload:\n{json.dumps(payload, indent=2)}\n")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/jd-skill-mapping/",
            headers=headers,
            json=payload
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response:\n{json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 202:
            correlation_id = response.json().get("correlation_id")
            print(f"\n✅ Requisition Submitted Successfully!")
            print(f"📋 Correlation ID: {correlation_id}")
            return True, correlation_id
        else:
            print(f"\n❌ Request failed with status {response.status_code}")
            return False, None
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False, None

def test_get_matches(token, correlation_id):
    """Test getting matches for a requisition (auth required)."""
    print_section("TEST 3: Get Matches for Requisition (JWT Authentication)")
    print(f"Endpoint: GET /api/v1/jd-skill-mapping/{correlation_id}/matches\n")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/jd-skill-mapping/{correlation_id}/matches",
            headers=headers
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response:\n{json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            result = response.json()
            match_count = len(result.get("matches", []))
            print(f"\n✅ Retrieved {match_count} matches")
            return True
        else:
            print(f"\n❌ Request failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("  IB Job Skill Mapping System - API Test")
    print("=" * 80)
    
    # Generate token
    print("\n🔑 Generating JWT Token...")
    token = generate_token()
    print(f"✅ Token Generated:\n{token}\n")
    print("Token Details:")
    print(f"  - Algorithm: {ALGORITHM}")
    print(f"  - Valid for: 365 days")
    print(f"  - Length: {len(token)} characters")
    
    # Test 1: Health Check
    if not test_health():
        print("\n❌ Health check failed!")
        return
    
    # Test 2: Submit Requisition
    success, correlation_id = test_submit_requisition(token)
    
    if not success:
        print_section("Testing Complete - Some Tests Failed ❌")
        print("")
        return
    
    # Test 3: Get Matches
    import time
    print("\nWaiting 2 seconds for background processing...")
    time.sleep(2)
    
    matches_success = test_get_matches(token, correlation_id)
    
    if matches_success:
        print_section("Testing Complete - All Tests Passed! ✅")
        print(f"\n📚 Next Steps:")
        print(f"  1. View Swagger UI: {BASE_URL}/docs")
        print(f"  2. Fix SpaCy dependency: pip install spacy && python -m spacy download en_core_web_sm")
        print(f"  3. See E2E_VALIDATION_GUIDE.md for more tests")
    else:
        print_section("Testing Complete - Some Tests Failed ❌")
    
    print("")

if __name__ == "__main__":
    main()
