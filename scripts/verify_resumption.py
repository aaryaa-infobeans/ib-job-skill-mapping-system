"""Verification script for requisition resumption."""

import os
import sys
import json
from datetime import datetime, timedelta

# Add src to python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from app.db.session import SessionLocal
from app.db.models.models import RequisitionRequest, RequisitionDetail, LangGraphCheckpoint
from app.ai.resumption import resume_requisition
import logging

# Configure logging to see node outputs
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def setup_test_data(db):
    """Set up a stuck requisition in the database."""
    request_id = f"TEST-RESUME-{int(datetime.utcnow().timestamp())}"
    correlation_id = f"CORR-{request_id}"
    
    # 1. Create requisition in PROCESSING status (2)
    # Set received_at to 1 hour ago to ensure it's "stuck"
    requisition = RequisitionRequest(
        request_id=request_id,
        auth_client_id=1,
        status=2,
        client_name="TestClient",
        correlation_id=correlation_id,
        received_at=datetime.utcnow() - timedelta(hours=1)
    )
    db.add(requisition)
    db.flush()
    
    # 2. Create detail
    detail = RequisitionDetail(
        requisition_request_id=requisition.id,
        payload_json={
            "job_description": {
                "title": "Python Developer",
                "jd_text": "We need a Python developer with FastAPI experience.",
                "mandatory_skills": ["Python"]
            }
        },
        payload_hash=f"hash-{request_id}"
    )
    db.add(detail)
    db.flush()
    
    # 3. Create a checkpoint for Stage 1 (requisition_parsing)
    # This simulates that it successfully completed stage 1 but stuck before stage 2
    state = {
        "requisition_input": {
            "request_id": request_id,
            "job_description": detail.payload_json["job_description"],
            "correlation_id": correlation_id
        },
        "parsed_jd": {
            "normalized_title": "Python Developer",
            "normalized_role": "Engineer",
            "extracted_mandatory_skills": ["Python", "FastAPI"],
            "extracted_preferred_skills": [],
            "location": [],
            "experience": {"min_months": 0, "max_months": None}
        },
        "token_metrics": {},
        "llm_call_logs": [],
        "cumulative_tokens": 0,
        "cumulative_cost_usd": 0.0,
        "correlation_id": correlation_id
    }
    
    checkpoint = LangGraphCheckpoint(
        request_id=request_id,
        node_name="requisition_parsing",
        state_json=state,
        created_at=datetime.utcnow() - timedelta(minutes=50)
    )
    db.add(checkpoint)
    db.commit()
    
    return request_id

def verify():
    db = SessionLocal()
    try:
        print("--- Setting up test data ---")
        request_id = setup_test_data(db)
        print(f"Created stuck requisition: {request_id}")
        
        print("\n--- Running Resumption Logic ---")
        # Instead of running the cron script, we call resume_requisition directly
        # or we could run the cron script if we wanted to test the detection too.
        # Let's test detection first by calling get_stuck_requisitions in the main loop logic
        
        from app.db.repositories.requisition_repository import RequisitionRepository
        repo = RequisitionRepository(db)
        stuck_reqs = repo.get_stuck_requisitions(timeout_minutes=30)
        
        found = any(req.request_id == request_id for req in stuck_reqs)
        if found:
            print(f"SUCCESS: Requisition {request_id} detected as stuck.")
        else:
            print(f"FAILURE: Requisition {request_id} NOT detected as stuck.")
            return

        # Now resume it
        result = resume_requisition(request_id, db)
        
        if result and result.get("final_results") is not None:
            print(f"SUCCESS: Requisition {request_id} resumed and completed.")
            print(f"Results: {len(result['final_results'])} matches found.")
        else:
            print(f"FAILURE: Requisition {request_id} failed to complete.")
            if result and result.get("error_message"):
                print(f"Error: {result['error_message']}")
                
        # Final check in DB
        final_req = repo.get_requisition_by_request_id(request_id)
        if final_req.status == 4: # COMPLETED
            print(f"SUCCESS: DB Status is COMPLETED (4).")
        else:
            print(f"FAILURE: DB Status is {final_req.status}.")
            
    finally:
        db.close()

if __name__ == "__main__":
    verify()
