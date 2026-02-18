#!/usr/bin/env python
"""Script to create a requisition and view the matches with full authentication and detailed scoring."""

import sys
import json
import os
import time
from datetime import date, datetime
from typing import Dict, Any

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add src to path
sys.path.insert(0, "src")

from app.main import app
# API Authentication Token
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LWNsaWVudCIsImNsaWVudF9pZCI6InRlc3QtY2xpZW50IiwiZXhwIjoxODAyOTY3NTA5fQ.8PFFHEhz8Ywg51nQ68llGUVi_RXGTHam7D6LvITLT18"
headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}

# Create test client
from fastapi.testclient import TestClient
client = TestClient(app)

# Generate unique request ID
unique_id = datetime.now().strftime("%Y%m%d%H%M%S%f")[-6:]

def format_score(val):
    if not isinstance(val, (int, float)):
        return "N/A"
    # If val > 1.0, assume it's already a percentage (e.g. 56.0)
    # If val <= 1.0, assume it's a ratio (e.g. 0.56)
    if val > 1.0:
        return f"{val:.1f}%"
    return f"{val*100:.1f}%"

# Step 1: Create a requisition
print("\n" + "="*60)
print("STEP 1: Creating a new requisition (Authenticated)")
print("="*60)

payload = {
    "request_id": f"REQ-TEST-{unique_id}",
    "schema_version": "v1",
    "source_system": "HR_SYSTEM",
    "client_name": "LM",
    "job_description": {
        "client_name": "SMBC",
        "title": "Salesforce Engineer",
        "role": "Salesforce Engineer",
        "requisition_duration_month": 6,
        "expected_start_date": date.today().isoformat(),
        "priority": "HIGH",
        "location": ["Remote", "Pune", "Indore", "Bangalore"],
        "work_mode": ["Hybrid", "Remote", "WFO"],
        "experience": {"min_months": 24, "max_months": 240},
        "mandatory_skills": ["salesforce",  "Docker", "AWS"],
        "preferred_skills": ["salesforce"],
        "certifications_required": ["AWS Solutions Architect", "PHP Certified", "AI Certified"],
        "jd_text": "We are looking for an experienced Salesforce engineer to build and deploy app in the cloud. Candidates MUST have AWS Solutions Architect certification.",
    },
    "metadata": {"submitted_by": "recruiter@test.com", "department": "Engineering"},
}

response = client.post("/api/v1/jd-skill-mapping", json=payload, headers=headers)
print(f"\nStatus Code: {response.status_code}")

if response.status_code == 202:
    correlation_id = response.json()["correlation_id"]
    print(f"\n✅ Requisition created successfully!")
    print(f"Correlation ID: {correlation_id}")

    # Step 2: Poll for matches
    print("\n" + "="*60)
    print("STEP 2: Polling for matches (Asynchronous Processing)")
    print("="*60)

    max_attempts = 12
    wait_time = 5
    matches_data = {}
    
    for attempt in range(1, max_attempts + 1):
        print(f"Attempt {attempt}/{max_attempts}: Fetching results...")
        matches_response = client.get(f"/api/v1/jd-skill-mapping/{correlation_id}/matches", headers=headers)
        
        if matches_response.status_code != 200:
            print(f"❌ Error fetching matches: {matches_response.status_code}")
            break
            
        matches_data = matches_response.json()
        status = matches_data.get("status", "UNKNOWN")
        
        if status == "COMPLETED":
            print(f"✅ Processing completed!")
            break
        elif status == "FAILED":
            print(f"❌ Processing failed!")
            break
        else:
            print(f"⏳ Status: {status}. Waiting {wait_time}s...")
            time.sleep(wait_time)
    
    if matches_data.get("status") == "COMPLETED":
        # Display summary
        print(f"\n📊 Summary Metrics:")
        metrics = matches_data.get("metrics", {})
        if metrics:
            print(f"  - Total evaluated: {metrics.get('total_evaluated')}")
            print(f"  - Total qualified: {metrics.get('total_qualified')}")
            print(f"  - Qualification rate: {format_score(metrics.get('qualification_rate', 0))}")
            print(f"  - Processing Cost: ${metrics.get('cost_usd', 0.0):.4f}")

        # Display top matches
        print(f"\n🏆 Top Candidates:")
        for idx, match in enumerate(matches_data.get("matches", [])[:3]):
            print(f"\n  [{idx+1}] ID: {match['team_member_id']} | Score: {format_score(match['profile_score'])} | Fit: {match['fit_level']}")
            
            # Show Detailed Breakdown
            db = match.get("detailed_breakdown", {})
            if db:
                mr = db.get("match_reasons", {})
                print("    Breakdown:")
                print(f"      - Mandatory Skills: {format_score(mr.get('mandatory_score'))}")
                print(f"      - Preferred Skills: {format_score(mr.get('preferred_score'))}")
                print(f"      - Certifications:   {format_score(mr.get('certification_score'))}")
                print(f"      - Experience:       {format_score(mr.get('experience_score'))}")
                print(f"      - Location Match:   {'✅' if mr.get('location_matched') else '❌'}")
                print(f"      - Work Mode Match:  {'✅' if mr.get('work_mode_matched') else '❌'}")
                print(f"      - Semantic Match:   {format_score(mr.get('semantic_similarity'))}")
            
            # Show Explanation Summary
            explanations = match.get("explanation", [])
            if explanations:
                print("    Reasoning:")
                for line in explanations:
                    print(f"      {line}")

    # Step 3: Database Analysis
    print("\n" + "="*60)
    print("STEP 3: Checkpoint & Audit Analysis")
    print("="*60)

    from app.db.session import SessionLocal
    from app.db.models.models import RequisitionRequest, LLMRequestLog
    
    try:
        db_sess = SessionLocal()
        req = db_sess.query(RequisitionRequest).filter(RequisitionRequest.correlation_id == correlation_id).first()
        if req:
            logs = db_sess.query(LLMRequestLog).filter(LLMRequestLog.request_id == req.request_id).all()
            print(f"Audit Trail: Found {len(logs)} LLM calls for this request.")
            for log in logs:
                print(f"  - {log.agent_name:25} | Tokens: {log.total_tokens:5} | Status: {log.status}")
        db_sess.close()
    except Exception as e:
        print(f"Warning: Could not fetch DB audit: {e}")

else:
    print(f"❌ Failed to create requisition: {response.json()}")

print("\n" + "="*60 + "\n")
