"""Matches router."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.repositories.requisition_repository import RequisitionRepository
from app.db.session import get_db

router = APIRouter(prefix="/jd-skill-mapping", tags=["matches"])


class MatchResult(BaseModel):
    """Individual match result."""

    team_member_id: str
    full_name: str
    match_score: float
    matched_skills: List[str]
    missing_skills: List[str]
    explanation: str


class MatchesResponse(BaseModel):
    """Response model for matches endpoint."""

    correlation_id: str
    status: str
    total_matches: int
    matches: List[MatchResult]


@router.get("/{correlation_id}/matches", response_model=MatchesResponse)
async def get_matches(correlation_id: str, db: Session = Depends(get_db)):
    """
    Get match results for a requisition.

    This is a stub endpoint that returns a placeholder structure.
    """
    repo = RequisitionRepository(db)

    # Verify requisition exists
    requisition = repo.get_requisition_by_correlation_id(correlation_id)
    if not requisition:
        raise HTTPException(status_code=404, detail="Requisition not found")

    # Return stub response with valid structure
    return MatchesResponse(
        correlation_id=correlation_id,
        status="PROCESSING",
        total_matches=0,
        matches=[],
    )
