"""Test configuration and fixtures."""

import os
import pytest
import sqlalchemy.pool
import time
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# --- Apply Global Mocks to prevent all network LLM calls during imports or tests ---
import json
import numpy as np
from unittest.mock import MagicMock
import openai
import groq
from trulens.core.feedback.endpoint import Endpoint
from trulens.core.utils.pace import Pace

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
    """Mock LLM completions to return valid mock data for nodes."""
    messages = kwargs.get("messages", [])
    model = kwargs.get("model", "unknown")
    prompt_text = ""
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            prompt_text += f"\n{content}"
            
    prompt_lower = prompt_text.lower()
    
    if "data quality validator" in prompt_lower or "validate this requisition data" in prompt_lower:
        res_content = json.dumps({
            "is_valid": True,
            "validation_errors": []
        })
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

# Apply monkeypatches immediately
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

from app.db.base import Base
from app.db.session import get_db
from app.main import app

# ----------------------------------------------------------------------------------

# Import all models to ensure they are registered with Base.metadata
from app.db.models import models as _  # noqa: F401

# Test JWT secret key (must match what app uses in test environment)
TEST_JWT_SECRET = "test-secret-key-for-testing"

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=sqlalchemy.pool.StaticPool,  # Share same connection for in-memory DB
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    # Set JWT secret key for test environment
    os.environ["JWT_SECRET_KEY"] = TEST_JWT_SECRET
    
    yield
    
    # Cleanup
    if "JWT_SECRET_KEY" in os.environ:
        del os.environ["JWT_SECRET_KEY"]


def create_test_token(client_id: str = "test-client"):
    """Create a test JWT token using the test secret key."""
    payload = {
        "sub": client_id,
        "client_id": client_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    # Use same secret key as test environment
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture
def db():
    """Database fixture that creates tables before each test."""
    Base.metadata.create_all(bind=engine)
    db_session = TestingSessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    """Test client fixture with database override and auth token."""
    app.dependency_overrides[get_db] = override_get_db
    try:
        test_client = TestClient(app)
        # Add default auth token to all requests
        token = create_test_token()
        test_client.headers = {**test_client.headers, "Authorization": f"Bearer {token}"}
        yield test_client
    finally:
        app.dependency_overrides.clear()


def pytest_sessionfinish(session, exitstatus):
    """Force exit to prevent hanging on background thread cleanup."""
    os._exit(exitstatus)

