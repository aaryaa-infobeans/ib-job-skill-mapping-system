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
    "client_name": "Test Corp",
    "job_description": {
        "client_name": "Test Corp",
        "title": "Senior Python Developer",
        "role": "Backend Developer",
        "requisition_duration_month": 6,
        "expected_start_date": date.today().isoformat(),
        "priority": "HIGH",
        "location": ["Bangalore"],
        "work_mode": ["Hybrid", "Remote", "WFO"],
        "experience": {"min_months": 36, "max_months": 60},
        "mandatory_skills": ["Python", "FastAPI", "PostgreSQL", "PHP"],
        "preferred_skills": ["Docker", "Kubernetes"],
        "jd_text": "We are looking for an experienced Python developer with strong backend expertise...",
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

            # Get LangGraph checkpoints
            checkpoints = db.query(LangGraphCheckpoint).filter(
                LangGraphCheckpoint.request_id == req.request_id
            ).all()

            print(f"\n🔍 LangGraph Checkpoints: {len(checkpoints)}")
            if checkpoints:
                # Display checkpoint info with token tracking
                total_tokens = 0
                total_cost = 0.0
                
                for i, cp in enumerate(checkpoints, 1):
                    print(f"\n  Checkpoint {i}: {cp.node_name}")
                    print(f"    - ID: {cp.id}")
                    
                    if cp.token_count is not None:
                        print(f"    - Token Count: {cp.token_count:,}")
                        total_tokens += cp.token_count
                    else:
                        print(f"    - Token Count: None (awaiting integration)")
                    
                    # Show state keys
                    if cp.state_json and isinstance(cp.state_json, dict):
                        state_keys = list(cp.state_json.keys())
                        print(f"    - State Keys: {state_keys}")
                        
                        # Display relevant metrics
                        if "candidate_count" in cp.state_json:
                            print(f"    - Candidates: {cp.state_json['candidate_count']}")
                        if "total_evaluated" in cp.state_json:
                            print(f"    - Total Evaluated: {cp.state_json['total_evaluated']}")
                        if "total_qualified" in cp.state_json:
                            print(f"    - Total Qualified: {cp.state_json['total_qualified']}")
                
                if total_tokens > 0:
                    # Calculate cost from tokens (GPT-4: $0.03 per 1M input tokens, $0.06 per 1M output tokens)
                    # Assuming roughly 50% input, 50% output
                    estimated_cost = (total_tokens / 2) / 1_000_000 * 0.03 + (total_tokens / 2) / 1_000_000 * 0.06
                    print(f"\n📊 Token & Cost Summary:")
                    print(f"  - Total Tokens Used: {total_tokens:,}")
                    print(f"  - Estimated Cost: ${estimated_cost:.6f} (${estimated_cost*100:.4f}¢)")
                    print(f"  - Cost per Candidate Explanation: ${estimated_cost/2 if total_tokens > 0 else 0:.6f}")
                    print(f"  - Model: GPT-4 (input: $0.03/1M, output: $0.06/1M)")
                else:
                    print(f"\n⚠️  Token Tracking Status:")
                    print(f"  - Tokens not yet captured")
                    print(f"  - Note: Non-LLM nodes (jd_parsing, skill_normalization, matching_scoring) don't consume tokens")
                    print(f"  - LLM explanations are tracked in explanation_generation checkpoint")
            else:
                print("  (No checkpoints found - processing may not have started yet)")
        else:
            print("❌ Requisition not found in database")
    finally:
        db.close()

    print("\n" + "="*60)
else:
    print(f"❌ Failed to create requisition: {response.json()}")
