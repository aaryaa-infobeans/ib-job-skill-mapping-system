"""Tests for TruLens integration."""

import sys
import json
import uuid
import hashlib
from datetime import datetime
import pytest
from unittest.mock import MagicMock, patch
import numpy as np

# 1. Import third-party libraries to monkeypatch them BEFORE importing application code
import openai
import groq
from trulens.core.feedback.endpoint import Endpoint
from trulens.core.utils.pace import Pace

# 2. Define the mock function for Endpoint.run_in_pace
def mock_run_in_pace(self, func, *args, **kwargs):
    """Mock Endpoint.run_in_pace to directly return pre-baked feedback responses."""
    messages = kwargs.get("messages") or (args[0] if len(args) > 0 and isinstance(args[0], list) else None)
    prompt = kwargs.get("prompt") or (args[0] if len(args) > 0 and isinstance(args[0], str) else None)
    response_format = kwargs.get("response_format")
    
    prompt_text = ""
    if messages:
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                prompt_text += f"\n{content}"
    elif prompt:
        prompt_text = prompt
        
    prompt_lower = prompt_text.lower()
    
    # Determine the string output content based on prompt
    if "groundedness" in prompt_lower or "criteria" in prompt_lower or "supporting_evidence" in prompt_lower:
        res_content = json.dumps({
            "criteria": "The candidate matches the experience requirements and has most of the mandatory skills.",
            "supporting_evidence": "Candidate has 5+ years of experience and is a High match.",
            "score": 3
        })
    elif "relevance" in prompt_lower or "relevant" in prompt_lower:
        if "json" in prompt_lower:
            res_content = json.dumps({
                "reasons": "Highly relevant to the query.",
                "score": 3
            })
        else:
            res_content = "RELEVANCE: 3"
    else:
        res_content = "3"

    if response_format is not None:
        try:
            return response_format.model_validate_json(res_content)
        except Exception:
            try:
                return response_format()
            except Exception:
                pass
    return res_content

def mock_chat_completions_create(*args, **kwargs):
    # Retrieve messages/model
    messages = kwargs.get("messages", [])
    model = kwargs.get("model", "unknown")
    
    # Combine message contents to inspect the prompt
    prompt_text = ""
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            prompt_text += f"\n{content}"
            
    prompt_lower = prompt_text.lower()
    
    # Check semantic validation
    if "data quality validator" in prompt_lower or "validate this requisition data" in prompt_lower:
        res_content = json.dumps({
            "is_valid": True,
            "validation_errors": []
        })
    # Check requisition parsing
    elif "expert talent matcher and hr analyst" in prompt_lower or "parse this job description" in prompt_lower:
        res_content = json.dumps({
            "normalized_title": "Senior Python Developer",
            "normalized_role": "Backend Engineer",
            "level": "SENIOR",
            "mandatory_skills": ["Python", "FastAPI"],
            "preferred_skills": ["AWS", "LangGraph"],
            "experience": {
                "min_months": 60,
                "max_months": None
            },
            "certifications": ["AWS Certified Developer"]
        })
    # Check skill normalization
    elif "skill normalization and ontology expansion" in prompt_lower or "normalize these skills" in prompt_lower:
        res_content = json.dumps({
            "mandatory": [
                {"raw": "Python", "canonical": "Python", "enriched": ["FastAPI", "Django"]},
                {"raw": "FastAPI", "canonical": "FastAPI", "enriched": ["FastAPI"]}
            ],
            "preferred": [
                {"raw": "AWS", "canonical": "Amazon Web Services", "enriched": ["Cloud"]},
                {"raw": "LangGraph", "canonical": "LangGraph", "enriched": ["Agent"]}
            ],
            "certifications": [
                {"raw": "AWS Certified Developer", "canonical": "AWS Certified Developer - Associate", "enriched": []}
            ]
        })
    # Check candidate explanation
    elif "expert recruiter" in prompt_lower or "detailed_explanation" in prompt_lower or "strengths" in prompt_lower or "fit_analysis" in prompt_lower:
        res_content = json.dumps({
            "summary": "This candidate is a high match for the role, showing strong experience in Python and FastAPI.",
            "fit_analysis": "The candidate matches the experience requirements and has most of the mandatory skills.",
            "recommendation": "Highly recommended to proceed to technical interview.",
            "strengths": ["Python expertise", "FastAPI experience"],
            "gaps": ["Missing LangGraph experience"]
        })
    else:
        res_content = "3"
        
    # Build mock completion structure
    mock_message = MagicMock()
    mock_message.content = res_content
    
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 100
    mock_usage.completion_tokens = 50
    mock_usage.total_tokens = 150
    
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_completion.usage = mock_usage
    mock_completion.model = model
    return mock_completion

# Apply monkeypatches immediately at the module level
Endpoint.run_in_pace = mock_run_in_pace
openai.resources.chat.completions.Completions.create = mock_chat_completions_create
groq.resources.chat.completions.Completions.create = mock_chat_completions_create
Pace.mark = lambda *args, **kwargs: 0.0
Pace.amark = lambda *args, **kwargs: 0.0

# Mock responses.parse
def mock_responses_parse(*args, **kwargs):
    raise TypeError("Responses.parse() got an unexpected keyword argument 'seed'")
import openai.resources.responses.responses
openai.resources.responses.responses.Responses.parse = mock_responses_parse

# 3. Now import application modules and mock embeddings
from app.ai.graph_executor import execute_graph_with_audit
from app.db.session import SessionLocal
from app.evaluation.feedback import get_feedback_functions
from app.services.trulens_service import trulens_service
from app.db.models.models import (
    RequisitionRequest as RequisitionRequestModel,
    RequisitionDetail,
    AuthClient,
    LangGraphCheckpoint,
    LLMRequestLog
)
from app.ai.utils.gemma_embedding import GemmaEmbeddingAgent
from app.ai.utils.embedding import EmbeddingAgent

@pytest.fixture(scope="module", autouse=True)
def mock_llm_and_embeddings():
    """Mock embeddings cleanly and restore them on module exit to prevent pollution."""
    orig_init = GemmaEmbeddingAgent.__init__
    orig_embed_text = GemmaEmbeddingAgent.embed_text
    orig_embed_batch = GemmaEmbeddingAgent.embed_batch
    orig_emb_agent_embed_text = EmbeddingAgent.embed_text

    def mock_gemma_init(self, *args, **kwargs):
        self.tokenizer = MagicMock()
        self.tokenizer.model_max_length = 2048

    GemmaEmbeddingAgent.__init__ = mock_gemma_init
    GemmaEmbeddingAgent.embed_text = lambda self, text: np.zeros(768, dtype=np.float32)
    GemmaEmbeddingAgent.embed_batch = lambda self, texts: [np.zeros(768, dtype=np.float32) for _ in texts]
    EmbeddingAgent.embed_text = lambda self, text: np.zeros(768, dtype=np.float32)

    yield

    GemmaEmbeddingAgent.__init__ = orig_init
    GemmaEmbeddingAgent.embed_text = orig_embed_text
    GemmaEmbeddingAgent.embed_batch = orig_embed_batch
    EmbeddingAgent.embed_text = orig_emb_agent_embed_text


def test_feedback_functions_initialization():
    """Verify that feedback functions can be initialized."""
    feedbacks = get_feedback_functions()
    assert isinstance(feedbacks, list)
    if feedbacks:
        for f in feedbacks:
            assert hasattr(f, "name")
            print(f"Initialized feedback: {f.name}")

def test_trulens_tracing_e2e():
    """End-to-end test to verify TruLens tracing during graph execution."""
    db = SessionLocal()
    request_id = str(uuid.uuid4())
    correlation_id = f"test-trulens-{request_id[:8]}"
    
    initial_state = {
        "requisition_input": {
            "request_id": request_id,
            "schema_version": "1.0",
            "source_system": "TEST",
            "client_name": "Test Client",
            "job_description": {
                "client_name": "Test Client",
                "title": "Senior Python Developer",
                "role": "Backend Engineer",
                "priority": "MEDIUM",
                "location": ["Indore"],
                "work_mode": ["wfo"],
                "jd_text": "We are looking for a Senior Python Developer with 5+ years of experience in FastAPI and AWS. Experience with LangGraph and TruLens is a plus.",
                "mandatory_skills": ["Python", "FastAPI"],
                "preferred_skills": ["AWS", "LangGraph"],
                "experience": {"min_months": 60}
            },
            "metadata": {
                "submitted_by": "Test Suite",
                "department": "Engineering"
            },
            "correlation_id": correlation_id
        },
        "target_member_ids": [],
        "parsed_jd": None,
        "normalized_skills": None,
        "candidate_scores": None,
        "final_results": None,
        "error_message": None,
        "token_metrics": {},
        "llm_call_logs": [],
        "cumulative_tokens": 0,
        "cumulative_cost_usd": 0.0,
        "total_evaluated": 0,
        "total_qualified": 0,
    }
    
    req_id_to_cleanup = None
    
    try:
        # 1. Fetch or create AuthClient
        client = db.query(AuthClient).filter_by(client_code="test-client").first()
        if not client:
            client = AuthClient(
                client_name="Test Client",
                client_code="test-client",
                client_secret_hash="hash",
                auth_type="OAUTH",
                is_active=True
            )
            db.add(client)
            db.flush()
        
        # 2. Insert requisition request record
        req = RequisitionRequestModel(
            request_id=request_id,
            auth_client_id=client.id,
            status=1, # RECEIVED
            client_name="Test Client",
            correlation_id=correlation_id,
            received_at=datetime.utcnow(),
        )
        db.add(req)
        db.flush()
        req_id_to_cleanup = req.id
        
        # 3. Insert requisition detail
        payload_json = json.dumps(initial_state["requisition_input"], sort_keys=True)
        payload_hash = hashlib.sha256(payload_json.encode()).hexdigest()
        
        detail = RequisitionDetail(
            requisition_request_id=req.id,
            payload_json=initial_state["requisition_input"],
            payload_hash=payload_hash,
        )
        db.add(detail)
        db.commit()

        # Execute graph
        final_state = execute_graph_with_audit(initial_state, request_id, db)
        
        # Verify state
        assert final_state is not None
        assert "final_results" in final_state
        
        # Verify TruLens session has records
        tru = trulens_service.tru
        records, _ = tru.get_records_and_feedback()
        
        # Filter records by app_name
        app_records = records[records["app_name"] == "IB-Skill-Match-Graph"]
        assert len(app_records) > 0
        print(f"TruLens captured {len(app_records)} records for this run.")
        
        # Check if feedback scores are being processed (might be async/pending)
        apps = tru.get_apps()
        assert any(app['app_name'] == "IB-Skill-Match-Graph" for app in apps)
        
    finally:
        # Cleanup test records from database
        try:
            db.query(LangGraphCheckpoint).filter(LangGraphCheckpoint.request_id == request_id).delete()
            db.query(LLMRequestLog).filter(LLMRequestLog.request_id == request_id).delete()
            if req_id_to_cleanup:
                db.query(RequisitionDetail).filter(RequisitionDetail.requisition_request_id == req_id_to_cleanup).delete()
                db.query(RequisitionRequestModel).filter(RequisitionRequestModel.id == req_id_to_cleanup).delete()
            db.commit()
        except Exception as cleanup_err:
            print(f"Warning: Cleanup failed: {cleanup_err}")
            db.rollback()
        db.close()
