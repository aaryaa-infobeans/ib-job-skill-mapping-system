import requests
import json

url = "http://localhost:8004/api/v1/team-members/skill-availability/bulk-upsert"
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LWNsaWVudCIsImNsaWVudF9pZCI6InRlc3QtY2xpZW50IiwiZXhwIjoxODAyMTk2NjM4fQ.bEB5VPwuG6DoplMPmjsjSCFa8-kjVM3mXnI4E4RoC1A",
    "Content-Type": "application/json"
}

# Load the full JSON file
with open(r"C:\Users\Aarya Bhosale\Documents\ib-job-skill-mapping-system\specs-data\team-member-skill-availability-records.json", "r") as f:
    data = json.load(f)

try:
    print(f"Sending request with {len(data['team_members'])} team members...")
    response = requests.post(url, headers=headers, json=data, timeout=60)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
