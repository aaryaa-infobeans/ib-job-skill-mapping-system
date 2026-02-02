"""Integration tests for requisition endpoints."""

from datetime import date


def test_create_requisition_success(client, db):
    """Test successful requisition creation."""
    payload = {
        "request_id": "REQ-001",
        "schema_version": "v1",
        "source_system": "HR_SYSTEM",
        "client_name": "Acme Corp",
        "job_description": {
            "client_name": "Acme Corp",
            "title": "Senior Python Developer",
            "role": "Backend Developer",
            "requisition_duration_month": 6,
            "expected_start_date": date.today().isoformat(),
            "priority": "HIGH",
            "location": ["Bangalore", "Remote"],
            "work_mode": ["Hybrid", "Remote"],
            "experience": {"min_months": 36, "max_months": 60},
            "mandatory_skills": ["Python", "FastAPI", "PostgreSQL"],
            "preferred_skills": ["Docker", "Kubernetes"],
            "jd_text": "We are looking for an experienced Python developer...",
        },
        "metadata": {"submitted_by": "recruiter@acme.com", "department": "Engineering"},
    }

    response = client.post("/api/v1/jd-skill-mapping", json=payload)

    assert response.status_code == 202
    data = response.json()
    assert "correlation_id" in data
    assert data["status"] == "QUEUED_FOR_PROCESSING"
    assert "received_at" in data


def test_create_requisition_duplicate(client, db):
    """Test duplicate request_id handling."""
    payload = {
        "request_id": "REQ-002",
        "schema_version": "v1",
        "source_system": "HR_SYSTEM",
        "job_description": {
            "client_name": "Test Corp",
            "title": "Developer",
            "role": "Developer",
            "priority": "MEDIUM",
            "location": ["Mumbai"],
            "work_mode": ["On-site"],
            "jd_text": "Test job description",
        },
        "metadata": {},
    }

    # First request should succeed
    response1 = client.post("/api/v1/jd-skill-mapping", json=payload)
    assert response1.status_code == 202

    # Second request with same request_id should fail
    response2 = client.post("/api/v1/jd-skill-mapping", json=payload)
    assert response2.status_code == 409


def test_get_matches_not_found(client, db):
    """Test get matches for non-existent correlation_id."""
    response = client.get("/api/v1/jd-skill-mapping/INVALID-CORR-ID/matches")
    assert response.status_code == 404


def test_get_matches_stub(client, db):
    """Test get matches stub endpoint."""
    # First create a requisition
    payload = {
        "request_id": "REQ-003",
        "schema_version": "v1",
        "source_system": "HR_SYSTEM",
        "job_description": {
            "client_name": "Test Corp",
            "title": "Developer",
            "role": "Developer",
            "priority": "MEDIUM",
            "location": ["Mumbai"],
            "work_mode": ["On-site"],
            "jd_text": "Test job description",
        },
        "metadata": {},
    }

    create_response = client.post("/api/v1/jd-skill-mapping", json=payload)
    assert create_response.status_code == 202
    correlation_id = create_response.json()["correlation_id"]

    # Get matches (stub)
    matches_response = client.get(f"/api/v1/jd-skill-mapping/{correlation_id}/matches")
    assert matches_response.status_code == 200
    data = matches_response.json()
    assert data["correlation_id"] == correlation_id
    assert data["status"] == "PROCESSING"
    assert data["total_matches"] == 0
    assert data["matches"] == []


def test_requisition_validation_error(client, db):
    """Test validation error with invalid experience range."""
    payload = {
        "request_id": "REQ-004",
        "schema_version": "v1",
        "source_system": "HR_SYSTEM",
        "job_description": {
            "client_name": "Test Corp",
            "title": "Developer",
            "role": "Developer",
            "priority": "MEDIUM",
            "location": ["Mumbai"],
            "work_mode": ["On-site"],
            "experience": {"min_months": 60, "max_months": 36},  # Invalid range
            "jd_text": "Test job description",
        },
        "metadata": {},
    }

    response = client.post("/api/v1/jd-skill-mapping", json=payload)
    assert response.status_code == 422  # Validation error
