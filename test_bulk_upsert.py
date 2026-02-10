"""Test bulk upsert endpoint with detailed error output"""

import requests
import jwt
from datetime import datetime
import traceback

BASE_URL = "http://localhost:8001"

# Generate valid token
token = jwt.encode(
    {"sub": "test-client", "client_id": "test-client"},
    "test-secret-key-for-development-only-change-in-production",
    algorithm="HS256"
)

# Minimal valid payload
payload = {
    "metadata": {
        "batch_id": "TEST-MINIMAL-2",
        "timestamp": datetime.now().isoformat() + "Z",
        "total_records": 1,
        "batch_number": 1,
        "total_batches": 1,
        "records_in_batch": 1,
        "source_system": "TEST",
        "schema_version": "1.0",
        "status": {
            "code": 200,
            "key": "SUCCESS",
            "message": "OK"
        }
    },
    "team_members": [
        {
            "team_member_id": "TM-TEST-002",
            "team_member_status": "active",
            "experience_in_months": 24,
            "full_name": "Test User Two"
        }
    ]
}

headers = {"Authorization": f"Bearer {token}"}

print("Testing bulk upsert endpoint...")
print(f"Endpoint: POST {BASE_URL}/api/v1/team-members/skill-availability/bulk-upsert")
print(f"\nPayload team members: {len(payload['team_members'])}")
print(f"Team Member ID: {payload['team_members'][0]['team_member_id']}\n")

try:
    response = requests.post(
        f"{BASE_URL}/api/v1/team-members/skill-availability/bulk-upsert",
        json=payload,
        headers=headers,
        timeout=10
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Text: {response.text}")
    
    try:
        print(f"Response JSON: {response.json()}")
    except:
        pass
    
    if response.status_code == 202:
        print("\n✅ SUCCESS")
    else:
        print("\n❌ FAILED")
        
except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()
