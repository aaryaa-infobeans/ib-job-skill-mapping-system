"""Matches router."""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import verify_token
from app.ai.results_cache import get_results
from app.db.repositories.requisition_repository import RequisitionRepository
from app.db.session import get_db, SessionLocal

router = APIRouter(prefix="/jd-skill-mapping", tags=["matches"])

async def background_resumption(request_id: str):
    """Background task to resume processing."""
    db = SessionLocal()
    try:
        from app.ai.resumption import resume_requisition
        resume_requisition(request_id, db)
    finally:
        db.close()

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
    error_message: Optional[str] = None
    validation_errors: Optional[List[str]] = None


@router.get("/{correlation_id}/matches", response_model=MatchesResponse)
async def get_matches(
    correlation_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    token: dict = Depends(verify_token),
):
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
    cached_data = get_results(correlation_id)
    
    if cached_data is None:
        # Results not in cache, check if requisition is already finished in DB
        if requisition.status == 4:  # COMPLETED
            from app.db.models.models import LangGraphCheckpoint
            from app.ai.results_cache import store_results
            
            # Attempt to recover results from checkpoint
            checkpoint = db.query(LangGraphCheckpoint).filter(
                LangGraphCheckpoint.request_id == requisition.request_id,
                LangGraphCheckpoint.node_name == "result_aggregation"
            ).first()
            
            if checkpoint and checkpoint.state_json and "final_results" in checkpoint.state_json:
                final_results = checkpoint.state_json["final_results"]
                metrics = checkpoint.state_json.get("metrics", {})
                
                # Re-populate cache for subsequent requests
                store_results(correlation_id, final_results, metrics)
                cached_data = {"results": final_results, "metrics": metrics}
            else:
                # No results checkpoint found - return completed with zero matches
                return MatchesResponse(
                    correlation_id=correlation_id,
                    status="COMPLETED",
                    total_matches=0,
                    matches=[],
                )
        elif requisition.status == 5:  # FAILED
            from app.db.models.models import LangGraphCheckpoint
            
            # Retrieve error message from checkpoint
            error_checkpoint = db.query(LangGraphCheckpoint).filter(
                LangGraphCheckpoint.request_id == requisition.request_id
            ).order_by(LangGraphCheckpoint.created_at.desc()).first()
            
            error_message = None
            validation_errors = None
            
            if error_checkpoint and error_checkpoint.state_json:
                error_message = error_checkpoint.state_json.get("error_message")
                
                # Extract validation errors if stored as a list in state
                validation_errors = error_checkpoint.state_json.get("validation_errors")
                
                # Fallback: Parse from error_message if not in state
                if not validation_errors and error_message and error_message.startswith("VALIDATION_FAILED:"):
                    error_text = error_message.replace("VALIDATION_FAILED: ", "")
                    validation_errors = [e.strip() for e in error_text.split(";") if e.strip()]
            
            return MatchesResponse(
                correlation_id=correlation_id,
                status="FAILED",
                total_matches=0,
                matches=[],
                error_message=error_message,
                validation_errors=validation_errors,
            )
        else:
            # Requisition is still being processed
            # CHECK FOR STUCK REQUISITION
            # If processing for more than 5 minutes and no results in cache, trigger resumption
            if requisition.received_at:
                processing_time = datetime.utcnow() - requisition.received_at
                if processing_time > timedelta(minutes=5):
                    from app.ai.audit import get_checkpoints_for_request
                    checkpoints = get_checkpoints_for_request(db, requisition.request_id)
                    
                    # Only resume if we have some checkpoints but not COMPLETED
                    if checkpoints:
                        # Check if we already tried to resume recently (e.g. within last 2 minutes)
                        # We can use the last checkpoint's creation time to avoid spamming resumption
                        last_cp_time = checkpoints[-1].created_at if checkpoints else requisition.received_at
                        if datetime.utcnow() - last_cp_time > timedelta(minutes=2):
                            background_tasks.add_task(background_resumption, requisition.request_id)
            
            return MatchesResponse(
                correlation_id=correlation_id,
                status="PROCESSING",
                total_matches=0,
                matches=[],
            )
    
    final_results = cached_data.get("results", [])
    cached_metrics = cached_data.get("metrics", {})
    
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
    
    # Get metrics from cache
    metrics = None
    if cached_metrics:
        metrics = MatchesMetrics(
            total_evaluated=cached_metrics.get("total_evaluated"),
            total_qualified=cached_metrics.get("total_qualified"),
            token_count=cached_metrics.get("token_count"),
            cost_usd=round(cached_metrics.get("cost_usd", 0.0), 4) if cached_metrics.get("cost_usd") is not None else None,
        )
        # Calculate qualification rate if possible
        if metrics.total_evaluated and metrics.total_evaluated > 0:
            rate = (metrics.total_qualified or 0) / metrics.total_evaluated
            metrics.qualification_rate = round(rate, 2)
    
    return MatchesResponse(
        correlation_id=correlation_id,
        status="COMPLETED",
        total_matches=len(matches),
        matches=matches,
        metrics=metrics if any(getattr(metrics, f, None) is not None for f in metrics.__fields__) else None,
    )

