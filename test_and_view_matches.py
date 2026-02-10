#!/usr/bin/env python
"""Script to create a requisition and view the matches."""

import sys
import json
import os
from datetime import date, datetime
from sqlalchemy.orm import Session

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add src to path
sys.path.insert(0, "src")

from app.main import app
from app.db.session import SessionLocal
from app.db.models.models import RequisitionRequest, RequisitionDetail, LangGraphCheckpoint
from fastapi.testclient import TestClient

# Create test client
client = TestClient(app)

# Generate unique request ID
unique_id = datetime.now().strftime("%Y%m%d%H%M%S%f")[-6:]

# Step 1: Create a requisition
print("\n" + "="*60)
print("STEP 1: Creating a new requisition")
print("="*60)

payload = {
    "request_id": f"REQ-TEST-{unique_id}",
    "schema_version": "v1",
    "source_system": "HR_SYSTEM",
    "client_name": "LM",
    "job_description": {
        "client_name": "SMBC",
        "title": "AWS Engineer",
        "role": "Jr Cloud Engineer",
        "requisition_duration_month": 6,
        "expected_start_date": date.today().isoformat(),
        "priority": "HIGH",
        "location": ["Remote", "Pune", "Indore", "Bangalore"],
        "work_mode": ["Hybrid", "Remote", "WFO"],
        "experience": {"min_months": 24, "max_months": 240},
        "mandatory_skills": ["AWS", "Docker", "Terraform"],
        "preferred_skills": ["Docker", "AWS"],
        "certifications_required": ["AWS Solutions Architect"],
        "jd_text": "We are looking for an experienced AWS engineer to build and deploy app in the cloud. Candidates MUST have AWS Solutions Architect certification.",
    },
    "metadata": {"submitted_by": "recruiter@test.com", "department": "Engineering"},
}

response = client.post("/api/v1/jd-skill-mapping", json=payload)
print(f"\nStatus Code: {response.status_code}")
print(f"Response:\n{json.dumps(response.json(), indent=2)}")

if response.status_code == 202:
    correlation_id = response.json()["correlation_id"]
    print(f"\n✅ Requisition created successfully!")
    print(f"Correlation ID: {correlation_id}")

    # Step 2: Get matches
    print("\n" + "="*60)
    print("STEP 2: Fetching matches for the requisition")
    print("="*60)

    matches_response = client.get(f"/api/v1/jd-skill-mapping/{correlation_id}/matches")
    print(f"\nStatus Code: {matches_response.status_code}")
    
    matches_data = matches_response.json()
    print(f"\nMatches Response:")
    print(json.dumps(matches_data, indent=2))
    
    # Display summary
    if "total_matches" in matches_data:
        print(f"\n📊 Summary:")
        print(f"  - Total matches: {matches_data['total_matches']}")
        if "total_evaluated" in matches_data:
            print(f"  - Total candidates evaluated: {matches_data['total_evaluated']}")
        if "total_qualified" in matches_data:
            print(f"  - Total candidates qualified (FIT_SCORE_THRESHOLD): {matches_data['total_qualified']}")
            qualified_pct = (matches_data['total_qualified'] / matches_data['total_evaluated'] * 100) if matches_data['total_evaluated'] > 0 else 0
            print(f"  - Qualification rate: {qualified_pct:.1f}%")

    # Step 3: Check database
    print("\n" + "="*60)
    print("STEP 3: Database records & Checkpoint Analysis")
    print("="*60)

    db: Session = SessionLocal()
    try:
        # Get requisition
        req = db.query(RequisitionRequest).filter(
            RequisitionRequest.correlation_id == correlation_id
        ).first()

        if req:
            print(f"\nRequisition Record:")
            print(f"  - ID: {req.id}")
            print(f"  - Request ID: {req.request_id}")
            print(f"  - Correlation ID: {req.correlation_id}")
            print(f"  - Status: {req.status}")
            print(f"  - Received At: {req.received_at}")
            print(f"  - Client: {req.client_name}")

            # Get requisition detail
            detail = db.query(RequisitionDetail).filter(
                RequisitionDetail.requisition_request_id == req.id
            ).first()

            if detail:
                print(f"\nRequisition Detail:")
                print(f"  - ID: {detail.id}")
                print(f"  - Payload Hash: {detail.payload_hash}")

            # Step 4: Check LLM Request Logs
            from app.db.models.models import LLMRequestLog
            llm_logs = db.query(LLMRequestLog).filter(
                LLMRequestLog.request_id == req.request_id
            ).all()

            if llm_logs:
                print(f"\n📜 LLM Request Logs: {len(llm_logs)}")
                for log in llm_logs:
                    print(f"  - Agent: {log.agent_name}")
                    print(f"    Prompt: {log.prompt_name}")
                    print(f"    Tokens: {log.total_tokens} (P: {log.prompt_tokens}, C: {log.completion_tokens})")
                    print(f"    Cost: ${log.cost_usd:.6f}")
            else:
                print("\n📜 LLM Request Logs: None found in llm_request_log table")
        else:
            print("❌ Requisition not found in database")
    finally:
        db.close()

    print("\n" + "="*60)
else:
    print(f"❌ Failed to create requisition: {response.json()}")
