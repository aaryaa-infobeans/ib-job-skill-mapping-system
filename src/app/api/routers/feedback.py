import logging
import threading
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import verify_token
from app.api.schemas.feedback import (
    FeedbackCreate,
    FeedbackResponse,
    FeedbackListResponse,
    FeedbackItem,
)
from app.db.session import get_db
from app.services.feedback_service import FeedbackService

router = APIRouter(prefix="/requisition/match", tags=["feedback"])
logger = logging.getLogger(__name__)

# In-memory rate limiter store
# Keys are reviewer emails, values are lists of timestamps
# Note: In a distributed system, this should be handled by Redis or similar.
rate_limit_store: Dict[str, List[datetime]] = defaultdict(list)
rate_limit_lock = threading.Lock()

def check_rate_limit(reviewer_email: str) -> bool:
    """
    Check if the reviewer has exceeded the rate limit (20 requests/min).
    """
    with rate_limit_lock:
        now = datetime.utcnow()
        one_minute_ago = now - timedelta(minutes=1)
        
        # Filter out timestamps older than one minute
        rate_limit_store[reviewer_email] = [
            ts for ts in rate_limit_store[reviewer_email] if ts > one_minute_ago
        ]
        
        if len(rate_limit_store[reviewer_email]) >= 20:
            return False
            
        rate_limit_store[reviewer_email].append(now)
        return True

@router.post("/feedback", response_model=FeedbackResponse)
async def submit_match_feedback(
    feedback_data: FeedbackCreate,
    response: Response,
    db: Session = Depends(get_db),
    token: dict = Depends(verify_token),
):
    """
    Submit or update feedback for a candidate match.
    
    Requirements:
    - Authenticated user
    - reviewer_email in payload must match authenticated user's email (from token sub/email claim)
    - Rate limit: 20 requests/min per reviewer
    """
    # Extract authenticated email (typically in 'sub' or 'email' claim)
    authenticated_email = token.get("sub") or token.get("email")
    
    if not authenticated_email:
        logger.error("Authentication token missing email/sub claim")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User identity could not be verified from token"
        )

    # Apply rate limiting
    if not check_rate_limit(authenticated_email):
        logger.warning(
            f"Rate limit exceeded for reviewer: {authenticated_email}",
            extra={"reviewer_email": authenticated_email}
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Maximum 20 feedback submissions per minute allowed."
        )

    service = FeedbackService(db)
    feedback, action = service.submit_feedback(feedback_data, authenticated_email)
    
    # Set appropriate status code based on action
    if action == "created":
        response.status_code = status.HTTP_201_CREATED
    else:
        response.status_code = status.HTTP_200_OK
        
    return FeedbackResponse(
        status="success",
        action=action,
        feedback_id=feedback.id
    )


@router.get(
    "/feedback/{correlation_id}/{team_member_id}",
    response_model=FeedbackListResponse,
)
async def get_match_feedback(
    correlation_id: str,
    team_member_id: str,
    db: Session = Depends(get_db),
    token: dict = Depends(verify_token),
):
    """Retrieve previously submitted feedback for a specific requisition match.

    Authentication is required but no authorization checks are performed; the
    endpoint is intended to be used by tooling or UI components to display
    existing comments/ratings.  An empty list is returned if no feedback has
    been recorded yet.
    """

    # ensure caller has identity (we don't care what it is)
    authenticated_email = token.get("sub") or token.get("email")
    if not authenticated_email:
        logger.error("Authentication token missing email/sub claim for GET feedback")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User identity could not be verified from token"
        )

    service = FeedbackService(db)
    records = service.get_feedback(correlation_id, team_member_id)

    # convert to schema objects
    items = []
    for r in records:
        items.append(
            FeedbackItem(
                team_member_id=r.team_member_id,
                correlation_id=r.correlation_id,
                reviewer_email=r.reviewer_email,
                liked=r.liked,
                rating=r.rating,
                comment=r.comment,
                created_at=r.created_at.isoformat() if r.created_at else None,
                updated_at=r.updated_at.isoformat() if r.updated_at else None,
            )
        )

    return FeedbackListResponse(status="success", feedback=items)
