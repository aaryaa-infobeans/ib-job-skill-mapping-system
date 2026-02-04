"""Matches router."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.ai.results_cache import get_results
from app.db.repositories.requisition_repository import RequisitionRepository
from app.db.session import get_db

router = APIRouter(prefix="/jd-skill-mapping", tags=["matches"])


class MatchResult(BaseModel):
    """Individual match result with detailed explanation."""

    team_member_id: str
    profile_score: float
    fit_level: str
    availability_match: bool
    explanation: List[str]
    detailed_breakdown: Optional[dict] = None


class MatchesMetrics(BaseModel):
    """Metrics about the matching process."""
    
    total_evaluated: Optional[int] = None
    total_qualified: Optional[int] = None
    qualification_rate: Optional[float] = None
    token_count: Optional[int] = None
    cost_usd: Optional[float] = None


class MatchesResponse(BaseModel):
    """Response model for matches endpoint."""

    correlation_id: str
    status: str
    total_matches: int
    matches: List[MatchResult]
    metrics: Optional[MatchesMetrics] = None


@router.get("/{correlation_id}/matches", response_model=MatchesResponse)
async def get_matches(correlation_id: str, db: Session = Depends(get_db)):
    """
    Get match results for a requisition.

    Returns the ranked list of candidates with scores and explanations.
    Includes metrics about evaluation and qualification rates (FIT_SCORE_THRESHOLD filtering).
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
            detailed_breakdown=result.get("detailed_breakdown"),
        )
        for result in final_results
    ]
    
    # Get metrics from cache if available
    # Try to retrieve metrics from results_cache - this would be populated by the workflow
    metrics = MatchesMetrics()
    
    return MatchesResponse(
        correlation_id=correlation_id,
        status="COMPLETED",
        total_matches=len(matches),
        matches=matches,
        metrics=metrics if any(getattr(metrics, f, None) is not None for f in metrics.__fields__) else None,
    )

