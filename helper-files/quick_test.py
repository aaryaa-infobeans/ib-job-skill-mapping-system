#!/usr/bin/env python3
"""Quick test to submit a requisition and check if SpaCy works."""

import requests
import jwt
from datetime import datetime, timedelta, timezone
import json
import time

BASE_URL = "http://127.0.0.1:9000"
SECRET_KEY = "test-secret-key-for-testing"

# Generate token
payload = {
    "sub": "test-client",
    "client_id": "test-client",
    "exp": datetime.now(timezone.utc) + timedelta(days=365)
}
token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

print(f"Token: {token}\n")

# Submit requisition
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

requisition = {
    "request_id": f"REQ-TEST-{int(time.time())}",
    "schema_version": "1.1",
    "source_system": "TEST",
    "client_name": "Test Client",
    "metadata": {
        "submitted_by": "Test User",
        "submitted_at": datetime.now(timezone.utc).isoformat() + "Z",
        "department": "Testing"
    },
    "job_description": {
        "client_name": "Test Client",
        "title": "Senior Python Developer",
        "role": "Software Engineer",
        "requisition_duration_month": 6,
        "expected_start_date": "2026-03-01",
        "priority": "HIGH",
        "location": ["Remote"],
        "work_mode": ["wfh"],
        "experience": {
            "min_months": 36,
            "max_months": 60
        },
        "mandatory_skills": ["Python", "FastAPI", "PostgreSQL"],
        "preferred_skills": ["Docker", "AWS"],
        "jd_text": "Looking for a senior Python developer with FastAPI experience."
    }
}

print("Submitting requisition...")
response = requests.post(
    f"{BASE_URL}/api/v1/jd-skill-mapping/",
    headers=headers,
    json=requisition
)

print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}\n")

if response.status_code == 202:
    correlation_id = response.json()["correlation_id"]
    print(f"Correlation ID: {correlation_id}")
    print("Waiting 3 seconds for processing...")
    time.sleep(3)
    
    # Check matches
    print("\nChecking matches...")
    matches_response = requests.get(
        f"{BASE_URL}/api/v1/jd-skill-mapping/{correlation_id}/matches",
        headers=headers
    )
    
    print(f"Status: {matches_response.status_code}")
    result = matches_response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    
    if "error_message" in result:
        print(f"\n❌ ERROR: {result['error_message']}")
    else:
        print(f"\n✅ SUCCESS: Retrieved {len(result.get('matches', []))} matches")
