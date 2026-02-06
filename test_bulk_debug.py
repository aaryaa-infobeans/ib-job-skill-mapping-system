"""Debug bulk upsert endpoint"""
import requests
import jwt
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8001"

# Generate valid token
token = jwt.encode(
    {
        "sub": "test-client",
        "client_id": "test-client",
        "exp": datetime.utcnow() + timedelta(hours=1)
    },
    "test-secret-key-for-development-only-change-in-production",
    algorithm="HS256"
)

payload = {
    "metadata": {
        "batch_id": "TEST-DEBUG-001",
        "timestamp": datetime.now().isoformat() + "Z",
        "total_records": 1,
        "batch_number": 1,
        "total_batches": 1,
        "records_in_batch": 1,
        "source_system": "Debug-Test",
        "schema_version": "1.0",
        "status": {
            "code": 200,
            "key": "SUCCESS",
            "message": "Batch submitted"
        }
    },
    "team_members": [
        {
            "team_member_id": "TM-DEBUG-001",
            "team_member_status": "active",
            "experience_in_months": 120,
            "full_name": "Debug Test",
            "designation": "Developer",
            "skills": [
                {
                    "skill_id": "SKILL-DEBUG-001",
                    "skill_name": "Python",
                    "rating": 8,
                    "experience_in_months": 96
                }
            ],
            "allocations": [
                {
                    "project_id": "PROJ-DEBUG-001",
                    "allocation_percentage": 50.0,
                    "start_date": "2026-01-01",
                    "end_date": "2026-06-30"
                }
            ]
        }
    ]
}

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

print("Testing bulk upsert endpoint...")
print(f"URL: {BASE_URL}/api/v1/team-members/skill-availability/bulk-upsert")

try:
    response = requests.post(
        f"{BASE_URL}/api/v1/team-members/skill-availability/bulk-upsert",
        json=payload,
        headers=headers,
        timeout=10
    )
    
    print(f"\nStatus: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print(f"\nResponse Text:")
    print(response.text)
    
    if response.status_code == 500:
        print("\n⚠️ Server returned 500 error - check server logs for details")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
