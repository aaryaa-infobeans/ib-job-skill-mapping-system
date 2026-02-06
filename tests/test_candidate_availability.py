import pytest
from pydantic import ValidationError
from src.app.ai.agents.candidate_availability import CandidateAvailabilityRequest
from datetime import date

def test_single_team_member_id():
    req = CandidateAvailabilityRequest(
        requisition_duration_month=3,
        expected_start_date=date(2026, 2, 15),
        team_member_id="EMP_8842"
    )
    assert req.team_member_ids == ["EMP_8842"]

def test_multiple_team_member_ids():
    req = CandidateAvailabilityRequest(
        requisition_duration_month=3,
        expected_start_date=date(2026, 2, 15),
        team_member_ids=["EMP_8842", "EMP_1201", "EMP_7788"]
    )
    assert req.team_member_ids == ["EMP_8842", "EMP_1201", "EMP_7788"]

def test_both_team_member_id_and_ids_merges_and_dedupes():
    req = CandidateAvailabilityRequest(
        requisition_duration_month=3,
        expected_start_date=date(2026, 2, 15),
        team_member_id="EMP_8842",
        team_member_ids=["EMP_8842", "EMP_1201", "EMP_7788", "EMP_1201"]
    )
    assert req.team_member_ids == ["EMP_8842", "EMP_1201", "EMP_7788"]

def test_trim_and_remove_empty_strings():
    req = CandidateAvailabilityRequest(
        requisition_duration_month=3,
        expected_start_date=date(2026, 2, 15),
        team_member_id="  EMP_8842  ",
        team_member_ids=["", " EMP_1201 ", "EMP_7788", " "]
    )
    assert req.team_member_ids == ["EMP_8842", "EMP_1201", "EMP_7788"]

def test_missing_team_member_id_raises():
    with pytest.raises(ValidationError):
        CandidateAvailabilityRequest(
            requisition_duration_month=3,
            expected_start_date=date(2026, 2, 15)
        )

def test_invalid_team_member_id_length():
    with pytest.raises(ValidationError):
        CandidateAvailabilityRequest(
            requisition_duration_month=3,
            expected_start_date=date(2026, 2, 15),
            team_member_id="E" * 51
        )

def test_invalid_team_member_ids_length():
    with pytest.raises(ValidationError):
        CandidateAvailabilityRequest(
            requisition_duration_month=3,
            expected_start_date=date(2026, 2, 15),
            team_member_ids=["EMP_8842", "E" * 51]
        )

def test_invalid_requisition_duration():
    with pytest.raises(ValidationError):
        CandidateAvailabilityRequest(
            requisition_duration_month=0,
            expected_start_date=date(2026, 2, 15),
            team_member_id="EMP_8842"
        )
    with pytest.raises(ValidationError):
        CandidateAvailabilityRequest(
            requisition_duration_month=61,
            expected_start_date=date(2026, 2, 15),
            team_member_id="EMP_8842"
        )

def test_invalid_expected_start_date():
    with pytest.raises(ValidationError):
        CandidateAvailabilityRequest(
            requisition_duration_month=3,
            expected_start_date="not-a-date",
            team_member_id="EMP_8842"
        )


# --- PR#2: DB Access and Availability Engine Tests ---
from src.app.ai.agents.candidate_availability import evaluate_availability, CandidateAvailabilityResult
from src.app.db.models.models import TeamMember, TeamMemberAllocation

class DummyDB:
    def __init__(self, members, allocations):
        self._members = members
        self._allocations = allocations
    def query(self, model):
        if model is TeamMember:
            return DummyQuery(self._members)
        if model is TeamMemberAllocation:
            return DummyQuery(self._allocations)
        raise NotImplementedError

class DummyQuery:
    def __init__(self, items):
        self._items = items
    def filter(self, *args):
        return self
    def all(self):
        return self._items

alloc = lambda **kwargs: TeamMemberAllocation(**kwargs)
member = lambda **kwargs: TeamMember(**kwargs)

def test_not_found_member():
    req = CandidateAvailabilityRequest(
        requisition_duration_month=3,
        expected_start_date=date(2026,2,15),
        team_member_id="EMP_XYZ"
    )
    db = DummyDB(members=[], allocations=[])
    resp = evaluate_availability(db, req)
    assert resp.results[0].reason_code == "NOT_FOUND"
    assert resp.summary.not_found_count == 1

def test_inactive_member():
    req = CandidateAvailabilityRequest(
        requisition_duration_month=3,
        expected_start_date=date(2026,2,15),
        team_member_id="EMP_1"
    )
    db = DummyDB(members=[member(team_member_id="EMP_1", is_active=False)], allocations=[])
    resp = evaluate_availability(db, req)
    assert resp.results[0].reason_code == "INACTIVE"
    assert resp.results[0].available is False
    assert resp.summary.unavailable_count == 1

def test_billable_overlap_blocks():
    req = CandidateAvailabilityRequest(
        requisition_duration_month=3,
        expected_start_date=date(2026,2,15),
        team_member_id="EMP_2"
    )
    db = DummyDB(
        members=[member(team_member_id="EMP_2", is_active=True)],
        allocations=[alloc(team_member_id="EMP_2", project_id="PRJ_1", allocation_percentage=50, start_date=date(2026,1,10), end_date=date(2026,3,1), billable=True, is_deleted=False)]
    )
    resp = evaluate_availability(db, req)
    assert resp.results[0].reason_code == "BILLABLE_OVERLAP"
    assert resp.results[0].conflicts
    assert resp.summary.unavailable_count == 1

def test_billable_ended_before_start_available():
    req = CandidateAvailabilityRequest(
        requisition_duration_month=3,
        expected_start_date=date(2026,2,15),
        team_member_id="EMP_3"
    )
    db = DummyDB(
        members=[member(team_member_id="EMP_3", is_active=True)],
        allocations=[alloc(team_member_id="EMP_3", project_id="PRJ_2", allocation_percentage=100, start_date=date(2025,12,1), end_date=date(2026,2,1), billable=True, is_deleted=False)]
    )
    resp = evaluate_availability(db, req)
    assert resp.results[0].reason_code == "AVAILABLE"
    assert not resp.results[0].conflicts
    assert resp.summary.available_count == 1

def test_non_billable_overlap_available():
    req = CandidateAvailabilityRequest(
        requisition_duration_month=3,
        expected_start_date=date(2026,2,15),
        team_member_id="EMP_4"
    )
    db = DummyDB(
        members=[member(team_member_id="EMP_4", is_active=True)],
        allocations=[alloc(team_member_id="EMP_4", project_id="PRJ_3", allocation_percentage=100, start_date=date(2026,2,1), end_date=date(2026,4,1), billable=False, is_deleted=False)]
    )
    resp = evaluate_availability(db, req)
    assert resp.results[0].reason_code == "AVAILABLE"
    assert not resp.results[0].conflicts
    assert resp.summary.available_count == 1

def test_null_end_date_ongoing_billable_not_available():
    req = CandidateAvailabilityRequest(
        requisition_duration_month=3,
        expected_start_date=date(2026,2,15),
        team_member_id="EMP_5"
    )
    db = DummyDB(
        members=[member(team_member_id="EMP_5", is_active=True)],
        allocations=[alloc(team_member_id="EMP_5", project_id="PRJ_4", allocation_percentage=100, start_date=date(2026,2,1), end_date=None, billable=True, is_deleted=False)]
    )
    resp = evaluate_availability(db, req)
    assert resp.results[0].reason_code == "BILLABLE_OVERLAP"
    assert resp.results[0].conflicts
    assert resp.summary.unavailable_count == 1

def test_multiple_ids_order_and_dedupe():
    req = CandidateAvailabilityRequest(
        requisition_duration_month=3,
        expected_start_date=date(2026,2,15),
        team_member_id="EMP_6",
        team_member_ids=["EMP_6", "EMP_7", "EMP_8", "EMP_7"]
    )
    db = DummyDB(
        members=[
            member(team_member_id="EMP_6", is_active=True),
            member(team_member_id="EMP_7", is_active=True),
            member(team_member_id="EMP_8", is_active=False),
        ],
        allocations=[]
    )
    resp = evaluate_availability(db, req)
    assert [r.team_member_id for r in resp.results] == ["EMP_6", "EMP_7", "EMP_8"]
    assert resp.results[2].reason_code == "INACTIVE"
    assert resp.summary.unavailable_count == 1
    assert resp.summary.requested == 3

def test_soft_deleted_allocation_ignored():
    req = CandidateAvailabilityRequest(
        requisition_duration_month=3,
        expected_start_date=date(2026,2,15),
        team_member_id="EMP_9"
    )
    db = DummyDB(
        members=[member(team_member_id="EMP_9", is_active=True)],
        allocations=[alloc(team_member_id="EMP_9", project_id="PRJ_5", allocation_percentage=100, start_date=date(2026,2,1), end_date=None, billable=True, is_deleted=True)]
    )
    resp = evaluate_availability(db, req)
    assert resp.results[0].reason_code == "AVAILABLE"
    assert not resp.results[0].conflicts
    assert resp.summary.available_count == 1
