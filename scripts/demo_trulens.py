"""Demo script for TruLens observability."""

import uuid
import json
import logging
import sys
import os

# Add src to sys.path
sys.path.append(os.path.join(os.getcwd(), "src"))

from app.db.session import SessionLocal
from app.ai.graph_executor import execute_graph_with_audit
from app.services.trulens_service import trulens_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_demo():
    print("🚀 Starting TruLens Demo...")
    
    db = SessionLocal()
    request_id = str(uuid.uuid4())
    correlation_id = f"demo-{request_id[:8]}"
    
    # 1. Ensure prerequisite records exist
    from app.db.models.models import AuthClient, RequisitionStatusMaster, RequisitionRequest
    
    # Check if a client exists, create one if not
    client = db.query(AuthClient).first()
    if not client:
        client = AuthClient(
            client_name="Demo Client",
            client_code="DEMO",
            client_secret_hash="hash",
            is_active=True
        )
        db.add(client)
        db.flush()
    
    # Ensure status 1 exists
    status = db.query(RequisitionStatusMaster).filter_by(status_id=1).first()
    if not status:
        status = RequisitionStatusMaster(status_id=1, status_key="PENDING", status_message="Pending processing")
        db.add(status)
        db.flush()
        
    # 2. Create requisition record
    dummy_req = RequisitionRequest(
        request_id=request_id,
        correlation_id=correlation_id,
        auth_client_id=client.id,
        status=1, # PENDING
        client_name="InfoBeans"
    )
    db.add(dummy_req)
    db.commit()
    
    initial_state = {
        "requisition_input": {
            "request_id": request_id,
            "job_description": {
                "title": "Python Developer",
                "role": "Software Engineer",
                "client_name": "InfoBeans", # Required
                "location": ["Pune", "Remote"], # Required
                "work_mode": ["Hybrid"], # Required
                "jd_text": "Looking for a Python Developer with experience in AWS and Generative AI. Must have 3+ years of experience.",
                "mandatory_skills": ["Python"],
                "preferred_skills": ["AWS", "GenAI"],
                "experience": {"min_months": 36}
            },
            "correlation_id": correlation_id
        }
    }
    
    try:
        print(f"📝 Executing graph for Request ID: {request_id}")
        final_state = execute_graph_with_audit(initial_state, request_id, db)
        
        print("\n✅ Execution Completed!")
        print(f"Total Evaluated: {final_state.get('total_evaluated', 0)}")
        print(f"Total Qualified: {final_state.get('total_qualified', 0)}")
        
        # Show TruLens Stats
        print("\n📊 TruLens Trace Summary:")
        tru = trulens_service.tru
        try:
            records_df, feedbacks = tru.get_records_and_feedback(app_ids=["IB-Skill-Match-Graph"])
            if not records_df.empty:
                last_record = records_df.iloc[-1]
                print(f"Record ID: {last_record.record_id}")
                print(f"App ID: {last_record.app_id}")
                print(f"Input: {str(last_record.main_input)[:100]}...")
                print(f"Output: {str(last_record.main_output)[:100]}...")
            else:
                print("⚠️ No TruLens records found in the database yet.")
        except Exception as e:
            print(f"⚠️ Could not retrieve TruLens records: {e}")
            print("Check the TruLens dashboard for the full trace.")
            
            # Show node latencies from our custom tracing
            print("\n⏱️ Node Latencies (from custom tracing):")
            node_metadata = final_state.get("node_metadata", {})
            for node, meta in node_metadata.items():
                print(f"  - {node}: {meta.get('latency', 0):.4f}s")
        else:
            print("❌ No TruLens records found. Instrumentation might have failed.")

    except Exception as e:
        logger.error(f"Demo failed: {str(e)}", exc_info=True)
    finally:
        db.close()

if __name__ == "__main__":
    run_demo()
