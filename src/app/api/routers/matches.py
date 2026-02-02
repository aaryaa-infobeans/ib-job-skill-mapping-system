"""Matches router."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.ai.results_cache import get_results
from app.db.repositories.requisition_repository import RequisitionRepository
from app.db.session import get_db

router = APIRouter(prefix="/jd-skill-mapping", tags=["matches"])


class MatchResult(BaseModel):
    """Individual match result."""

    team_member_id: str
    profile_score: float
    fit_level: str
    availability_match: bool
    explanation: List[str]


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

    Returns the ranked list of candidates with scores and explanations.
    """
    repo = RequisitionRepository(db)

    # Verify requisition exists
    requisition = repo.get_requisition_by_correlation_id(correlation_id)
    if not requisition:
        raise HTTPException(status_code=404, detail="Requisition not found")

    # Retrieve results from cache
    final_results = get_results(correlation_id)
    
    if final_results is None:
        # Results not yet available - still processing
        return MatchesResponse(
            correlation_id=correlation_id,
            status="PROCESSING",
            total_matches=0,
            matches=[],
        )
    
    # Format results for response
    matches = [
        MatchResult(
            team_member_id=result["team_member_id"],
            profile_score=result["profile_score"],
            fit_level=result["fit_level"],
            availability_match=result["availability_match"],
            explanation=result["explanation"],
        )
        for result in final_results
    ]
    
    return MatchesResponse(
        correlation_id=correlation_id,
        status="COMPLETED",
        total_matches=len(matches),
        matches=matches,
    )

