from typing import List, Optional, Any
from pydantic import BaseModel, Field, model_validator, field_validator, ConfigDict
from datetime import date

class CandidateAvailabilityRequest(BaseModel):
    requisition_duration_month: int = Field(..., ge=1, le=60)
    expected_start_date: date
    team_member_id: Optional[str] = Field(None, min_length=1, max_length=50)
    team_member_ids: Optional[List[str]] = None

    model_config = ConfigDict(extra='forbid')

    @model_validator(mode='before')
    @classmethod
    def normalize_team_member_ids(cls, values: Any) -> Any:
        if not isinstance(values, dict):
            return values
            
        member_id = values.get('team_member_id')
        member_ids = values.get('team_member_ids')
        result = []
        if member_id:
            result.append(str(member_id).strip())
        if member_ids and isinstance(member_ids, list):
            for mid in member_ids:
                if mid:
                    result.append(str(mid).strip())
        
        seen = set()
        normalized = []
        for mid in result:
            if mid and mid not in seen:
                seen.add(mid)
                normalized.append(mid)
        
        if not normalized:
            # We check this in a refined way or allow it if it's being populated
            pass
            
        values['team_member_ids'] = normalized
        return values

    @field_validator('team_member_ids')
    @classmethod
    def validate_member_ids_list(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one team_member_id must be provided')
        for mid in v:
            if not isinstance(mid, str) or len(mid) > 50:
                raise ValueError(f'Invalid team_member_id: {mid}. Must be string and max length 50.')
        return v

class AllocationConflict(BaseModel):
    project_id: str
    allocation_percentage: float
    start_date: Optional[date]
    end_date: Optional[date]
    billable: bool

class CandidateAvailabilityResult(BaseModel):
    team_member_id: str
    available: bool
    reason_code: str
    reason: str
    conflicts: List[AllocationConflict]

class CandidateAvailabilitySummary(BaseModel):
    requested: int
    available_count: int
    unavailable_count: int
    not_found_count: int


class CandidateAvailabilityResponse(BaseModel):
    request_id: str
    expected_start_date: date
    expected_end_date: date
    requisition_duration_month: int
    results: List[CandidateAvailabilityResult]
    summary: CandidateAvailabilitySummary
    errors: List[Any]

    model_config = ConfigDict(extra='forbid')

# --- DB Access and Availability Engine ---
from sqlalchemy.orm import Session
from app.db.models.models import TeamMember, TeamMemberAllocation
from uuid import uuid4
from typing import List
from dateutil.relativedelta import relativedelta

def get_team_members(db: Session, team_member_ids: List[str]) -> List[TeamMember]:
    return db.query(TeamMember).filter(TeamMember.team_member_id.in_(team_member_ids)).all()

def get_allocations(db: Session, team_member_ids: List[str], window_start, window_end) -> List[TeamMemberAllocation]:
    # Only billable, not soft-deleted, overlapping allocations
    return db.query(TeamMemberAllocation).filter(
        TeamMemberAllocation.team_member_id.in_(team_member_ids),
        TeamMemberAllocation.is_deleted == False,
        TeamMemberAllocation.billable == True,
        # Overlap logic:
        ((TeamMemberAllocation.start_date == None) | (TeamMemberAllocation.start_date <= window_end)),
        ((TeamMemberAllocation.end_date == None) | (TeamMemberAllocation.end_date >= window_start)),
    ).all()

def calculate_window(expected_start_date, requisition_duration_month):
    window_start = expected_start_date
    window_end = expected_start_date + relativedelta(months=requisition_duration_month)
    return window_start, window_end

def evaluate_availability(
    db: Session, req: CandidateAvailabilityRequest
) -> CandidateAvailabilityResponse:
    request_id = str(uuid4())
    team_member_ids = req.team_member_ids
    window_start, window_end = calculate_window(req.expected_start_date, req.requisition_duration_month)
    members = get_team_members(db, team_member_ids)
    member_map = {m.team_member_id: m for m in members}
    allocations = get_allocations(db, team_member_ids, window_start, window_end)
    alloc_map = {}
    for alloc in allocations:
        alloc_map.setdefault(alloc.team_member_id, []).append(alloc)
    results = []
    available_count = 0
    unavailable_count = 0
    not_found_count = 0
    for tm_id in team_member_ids:
        member = member_map.get(tm_id)
        if not member:
            results.append(CandidateAvailabilityResult(
                team_member_id=tm_id,
                available=False,
                reason_code="NOT_FOUND",
                reason="Team member not found.",
                conflicts=[]
            ))
            not_found_count += 1
            continue
        if not member.is_active:
            results.append(CandidateAvailabilityResult(
                team_member_id=tm_id,
                available=False,
                reason_code="INACTIVE",
                reason="Team member is inactive.",
                conflicts=[]
            ))
            unavailable_count += 1
            continue
        conflicts = []
        for alloc in alloc_map.get(tm_id, []):
            conflicts.append(AllocationConflict(
                project_id=alloc.project_id,
                allocation_percentage=float(alloc.allocation_percentage or 0),
                start_date=alloc.start_date,
                end_date=alloc.end_date,
                billable=alloc.billable,
            ))
        if conflicts:
            results.append(CandidateAvailabilityResult(
                team_member_id=tm_id,
                available=False,
                reason_code="BILLABLE_OVERLAP",
                reason="Conflicting billable allocations overlap requested window.",
                conflicts=conflicts
            ))
            unavailable_count += 1
        else:
            results.append(CandidateAvailabilityResult(
                team_member_id=tm_id,
                available=True,
                reason_code="AVAILABLE",
                reason="No conflicting billable allocations found in requested window.",
                conflicts=[]
            ))
            available_count += 1
    summary = CandidateAvailabilitySummary(
        requested=len(team_member_ids),
        available_count=available_count,
        unavailable_count=unavailable_count,
        not_found_count=not_found_count,
    )
    return CandidateAvailabilityResponse(
        request_id=request_id,
        expected_start_date=req.expected_start_date,
        expected_end_date=window_end,
        requisition_duration_month=req.requisition_duration_month,
        results=results,
        summary=summary,
        errors=[],
    )
