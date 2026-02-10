import requests
import json

url = "http://localhost:8004/api/v1/team-members/skill-availability/bulk-upsert"
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LWNsaWVudCIsImNsaWVudF9pZCI6InRlc3QtY2xpZW50IiwiZXhwIjoxODAyMTk2NjM4fQ.bEB5VPwuG6DoplMPmjsjSCFa8-kjVM3mXnI4E4RoC1A",
    "Content-Type": "application/json"
}

# Small test payload with just 1 team member
data = {
    "metadata": {
        "batch_id": "test-batch-001",
        "timestamp": "2026-02-09T18:00:00Z",
        "total_records": 1,
        "source_system": "test"
    },
    "team_members": [
        {
            "team_member_id": "TM001",
            "designation": "Software Engineer",
            "profile_type": "Technical",
            "is_active": True,
            "experience_in_months": 36,
            "base_location": "Bangalore",
            "work_type": "hybrid",
            "skills": [
                {
                    "skill_id": "SKILL001",
                    "skill_name": "Python",
                    "rating": 4
                }
            ],
            "allocations": [
                {
                    "project_id": "PROJ001",
                    "allocation_percentage": 80,
                    "start_date": "2026-01-01"
                }
            ]
        }
    ]
}

try:
    print("Sending request...")
    response = requests.post(url, headers=headers, json=data, timeout=30)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
