"""Unit tests for requisition resumption and state reconstruction logic."""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

from app.ai.resumption import resume_requisition
from app.ai.availability import calculate_requisition_window
from app.ai.audit import convert_dates_to_iso
from app.db.models.models import RequisitionRequest, RequisitionDetail, LangGraphCheckpoint


def test_calculate_requisition_window_iso_strings():
    """Test that calculate_requisition_window handles ISO date strings."""
    # Test with YYYY-MM-DD string
    start_str = "2026-05-20"
    start_date, end_date = calculate_requisition_window(start_str, 6)
    assert start_date == date(2026, 5, 20)
    assert end_date == date(2026, 5, 20) + timedelta(days=6 * 30)

    # Test with ISO datetime string
    start_dt_str = "2026-06-15T10:30:00"
    start_date, end_date = calculate_requisition_window(start_dt_str, 3)
    assert start_date == date(2026, 6, 15)
    assert end_date == date(2026, 6, 15) + timedelta(days=3 * 30)

    # Test with invalid string (should fallback to today)
    start_date, end_date = calculate_requisition_window("invalid-date", None)
    assert start_date == date.today()


def test_convert_dates_to_iso_serialization():
    """Test recursive date conversion for JSON serialization."""
    now = datetime(2026, 2, 9, 12, 0, 0)
    today = date(2026, 2, 9)
    
    input_data = {
        "dt": now,
        "d": today,
        "nested": {
            "dt_list": [now, today],
            "other": "string"
        }
    }
    
    expected = {
        "dt": now.isoformat(),
        "d": today.isoformat(),
        "nested": {
            "dt_list": [now.isoformat(), today.isoformat()],
            "other": "string"
        }
    }
    
    result = convert_dates_to_iso(input_data)
    assert result == expected


@patch("app.ai.resumption.get_checkpoints_for_request")
@patch("app.ai.resumption.RequisitionRepository")
def test_resume_requisition_cumulative_state(mock_repo_class, mock_get_checkpoints):
    """Test that resumption correctly merges states from multiple checkpoints."""
    db = MagicMock()
    request_id = "test-req-123"
    
    # Setup mock checkpoints
    cp1 = LangGraphCheckpoint(node_name="requisition_parsing", state_json={"parsed_jd": {"title": "Engineer"}})
    cp2 = LangGraphCheckpoint(node_name="skill_normalization", state_json={"normalized_skills": ["Python"]})
    mock_get_checkpoints.return_value = [cp1, cp2]
    
    # Setup mock repository and requisition
    mock_repo = mock_repo_class.return_value
    mock_req = MagicMock(spec=RequisitionRequest)
    mock_req.request_id = request_id
    mock_req.correlation_id = "corr-123"
    mock_req.detail = MagicMock(spec=RequisitionDetail)
    mock_req.detail.payload_json = {"job_description": {"title": "Engineer"}}
    mock_repo.get_requisition_by_request_id.return_value = mock_req
    
    # Mock node sequence to stop before execution for this unit test
    # Actually, we want to check the restored state. 
    # Let's mock the NODE_SEQUENCE to be empty or something we can control.
    with patch("app.ai.resumption.NODE_SEQUENCE", ["requisition_parsing", "skill_normalization"]):
        # This will trigger "already completed" logic but return the cumulative state
        state = resume_requisition(request_id, db)
        
        assert state["parsed_jd"] == {"title": "Engineer"}
        assert state["normalized_skills"] == ["Python"]
        assert "requisition_input" in state
        assert state["requisition_input"]["request_id"] == request_id


@patch("app.ai.resumption.get_checkpoints_for_request")
@patch("app.ai.resumption.RequisitionRepository")
def test_resume_requisition_reconstructs_input(mock_repo_class, mock_get_checkpoints):
    """Test that resumption reconstructs requisition_input if missing from checkpoint."""
    db = MagicMock()
    request_id = "test-req-456"
    
    # Checkpoint with lean state (no requisition_input)
    cp = LangGraphCheckpoint(node_name="requisition_parsing", state_json={"parsed_jd": {"title": "Manager"}})
    mock_get_checkpoints.return_value = [cp]
    
    # Setup mock repository
    mock_repo = mock_repo_class.return_value
    mock_req = MagicMock()
    mock_req.request_id = request_id
    mock_req.correlation_id = "corr-456"
    mock_req.detail.payload_json = {
        "job_description": {"title": "Manager"},
        "requested_team_ids": ["T1"],
        "min_availability_percentage": 60
    }
    mock_repo.get_requisition_by_request_id.return_value = mock_req
    
    with patch("app.ai.resumption.NODE_SEQUENCE", ["requisition_parsing"]):
        state = resume_requisition(request_id, db)
        
        # Verify reconstruction
        assert "requisition_input" in state
        ri = state["requisition_input"]
        assert ri["request_id"] == request_id
        assert ri["job_description"]["title"] == "Manager"
        assert ri["requested_team_ids"] == ["T1"]
        assert ri["min_availability_percentage"] == 60
        assert ri["correlation_id"] == "corr-456"
