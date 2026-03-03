import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.db.models.models import RequisitionMatchTeamMemberFeedback
from tests.conftest import create_test_token

def test_submit_feedback_created(client: TestClient, db: Session):
    """Test creating new feedback."""
    payload = {
        "team_member_id": "TM001",
        "correlation_id": "CORR-20260303-1234",
        "reviewer_email": "test-client",  # Matches 'test-client' from create_test_token()
        "liked": True,
        "rating": 5,
        "comment": "Exemplary candidate"
    }
    
    response = client.post("/api/v1/requisition/match/feedback", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["action"] == "created"
    assert "feedback_id" in data
    
    # Verify in DB
    feedback = db.query(RequisitionMatchTeamMemberFeedback).filter_by(id=data["feedback_id"]).first()
    assert feedback is not None
    assert feedback.team_member_id == "TM001"
    assert feedback.liked is True
    assert feedback.rating == 5

def test_submit_feedback_updated(client: TestClient, db: Session):
    """Test updating existing feedback."""
    # First creation
    payload = {
        "team_member_id": "TM001",
        "correlation_id": "CORR-20260303-1234",
        "reviewer_email": "test-client",
        "liked": True,
        "rating": 4
    }
    client.post("/api/v1/requisition/match/feedback", json=payload)
    
    # Update
    update_payload = payload.copy()
    update_payload["liked"] = False
    update_payload["rating"] = 2
    update_payload["comment"] = "Changed my mind"
    
    response = client.post("/api/v1/requisition/match/feedback", json=update_payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "updated"
    
    # Verify in DB
    feedback = db.query(RequisitionMatchTeamMemberFeedback).filter_by(team_member_id="TM001").first()
    assert feedback.liked is False
    assert feedback.rating == 2
    assert feedback.comment == "Changed my mind"

def test_submit_feedback_email_mismatch(client: TestClient):
    """Test feedback submission with email mismatch."""
    payload = {
        "team_member_id": "TM001",
        "correlation_id": "CORR-20260303-1234",
        "reviewer_email": "wrong-email@example.com",
        "liked": True
    }
    
    response = client.post("/api/v1/requisition/match/feedback", json=payload)
    
    assert response.status_code == 403
    assert "Reviewer email must match authenticated user email" in response.json()["detail"]

def test_submit_feedback_invalid_rating(client: TestClient):
    """Test feedback with invalid rating range."""
    payload = {
        "team_member_id": "TM001",
        "correlation_id": "CORR-20260303-1234",
        "reviewer_email": "test-client",
        "liked": True,
        "rating": 6  # Invalid
    }
    
    response = client.post("/api/v1/requisition/match/feedback", json=payload)
    
    assert response.status_code == 422  # Pydantic validation error

def test_feedback_rate_limiting(client: TestClient):
    """Test rate limiting (20 req/min)."""
    payload = {
        "team_member_id": "TM_LIMIT",
        "correlation_id": "CORR-LIMIT",
        "reviewer_email": "test-client",
        "liked": True
    }
    
    # Reset rate limit store for clean test
    from app.api.routers.feedback import rate_limit_store, rate_limit_lock
    with rate_limit_lock:
        rate_limit_store.clear()

    # Submit 20 times (all should be fine)
    for _ in range(20):
        resp = client.post("/api/v1/requisition/match/feedback", json=payload)
        assert resp.status_code in [200, 201]
        
    # 21st time should be rate limited
    response = client.post("/api/v1/requisition/match/feedback", json=payload)
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json()["detail"]


def test_get_feedback_empty(client: TestClient):
    """GET returns an empty list when there is no feedback for the match."""
    corr = "CORR-EMPTY"
    team = "TM-EMPTY"
    response = client.get(f"/api/v1/requisition/match/feedback/{corr}/{team}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert isinstance(data["feedback"], list)
    assert data["feedback"] == []


def test_get_feedback_list(client: TestClient, db: Session):
    """GET returns all feedback entries for a given match."""
    corr = "CORR-20260303-1234"
    team = "TM001"

    # make sure rate limit doesn't interfere with this independent test
    from app.api.routers.feedback import rate_limit_store, rate_limit_lock
    with rate_limit_lock:
        rate_limit_store.clear()

    # create one entry via API (uses default token user)
    payload = {
        "team_member_id": team,
        "correlation_id": corr,
        "reviewer_email": "test-client",
        "liked": True,
        "rating": 3,
        "comment": "First review",
    }
    client.post("/api/v1/requisition/match/feedback", json=payload)

    # insert a second review directly into the database (different reviewer)
    from app.db.models.models import RequisitionMatchTeamMemberFeedback

    second = RequisitionMatchTeamMemberFeedback(
        team_member_id=team,
        correlation_id=corr,
        reviewer_email="other-reviewer@example.com",
        liked=False,
        rating=1,
        comment="Second review",
    )
    db.add(second)
    db.commit()

    # now fetch
    response = client.get(f"/api/v1/requisition/match/feedback/{corr}/{team}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["feedback"]) == 2

    # ensure both reviewers appear
    emails = {item["reviewer_email"] for item in data["feedback"]}
    assert emails == {"test-client", "other-reviewer@example.com"}
