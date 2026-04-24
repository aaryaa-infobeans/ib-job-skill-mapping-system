"""Tests for TruLens integration."""

import pytest
import uuid
from sqlalchemy.orm import Session
from app.ai.graph_executor import execute_graph_with_audit
from app.db.session import SessionLocal
from app.evaluation.feedback import get_feedback_functions
from app.services.trulens_service import trulens_service

def test_feedback_functions_initialization():
    """Verify that feedback functions can be initialized."""
    feedbacks = get_feedback_functions()
    # It might be empty if API keys are missing in test env, but should not crash
    assert isinstance(feedbacks, list)
    if feedbacks:
        for f in feedbacks:
            assert hasattr(f, "name")
            print(f"Initialized feedback: {f.name}")

@pytest.mark.asyncio
def test_trulens_tracing_e2e():
    """
    End-to-end test to verify TruLens tracing during graph execution.
    Note: This requires a working database and LLM API keys.
    """
    db = SessionLocal()
    request_id = str(uuid.uuid4())
    correlation_id = f"test-trulens-{request_id[:8]}"
    
    initial_state = {
        "requisition_input": {
            "request_id": request_id,
            "job_description": {
                "title": "Senior Python Developer",
                "role": "Backend Engineer",
                "jd_text": "We are looking for a Senior Python Developer with 5+ years of experience in FastAPI and AWS. Experience with LangGraph and TruLens is a plus.",
                "mandatory_skills": ["Python", "FastAPI"],
                "preferred_skills": ["AWS", "LangGraph"],
                "experience": {"min_months": 60}
            },
            "correlation_id": correlation_id
        }
    }
    
    try:
        # Execute graph
        final_state = execute_graph_with_audit(initial_state, request_id, db)
        
        # Verify state
        assert final_state is not None
        assert "final_results" in final_state
        
        # Verify TruLens session has records
        tru = trulens_service.tru
        records, _ = tru.get_records_and_feedback(app_ids=["IB-Skill-Match-Graph"])
        
        assert len(records) > 0
        print(f"TruLens captured {len(records)} records for this run.")
        
        # Check if feedback scores are being processed (might be async/pending)
        # We just check if the app is registered
        apps = tru.get_apps()
        assert any(app['app_id'] == "IB-Skill-Match-Graph" for app in apps)
        
    finally:
        db.close()

if __name__ == "__main__":
    # Manual test run
    test_feedback_functions_initialization()
    # test_trulens_tracing_e2e() # Skip by default if no DB/API keys
