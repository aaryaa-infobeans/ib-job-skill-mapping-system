import logging
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.api.schemas.feedback import FeedbackCreate
from app.db.repositories.feedback_repository import FeedbackRepository
from app.db.models.models import RequisitionMatchTeamMemberFeedback

logger = logging.getLogger(__name__)

class FeedbackService:
    """Service for feedback business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = FeedbackRepository(db)

    def submit_feedback(self, feedback_data: FeedbackCreate, authenticated_email: str) -> Tuple[RequisitionMatchTeamMemberFeedback, str]:
        """
        Validates and submits feedback for a candidate match.
        """
        # Validate reviewer email matches authenticated user
        if feedback_data.reviewer_email != authenticated_email:
            logger.warning(
                f"Reviewer email mismatch: payload={feedback_data.reviewer_email}, auth={authenticated_email}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Reviewer email must match authenticated user email"
            )

        # Validate rating range (Pydantic already does this via ge/le)
        if feedback_data.rating is not None and not (1 <= feedback_data.rating <= 5):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rating must be between 1 and 5"
            )

        try:
            feedback, action = self.repo.upsert_feedback(
                team_member_id=feedback_data.team_member_id,
                correlation_id=feedback_data.correlation_id,
                reviewer_email=feedback_data.reviewer_email,
                liked=feedback_data.liked,
                rating=feedback_data.rating,
                comment=feedback_data.comment
            )
            self.db.commit()
            
            logger.info(
                f"Feedback {action} successfully",
                extra={
                    "reviewer_email": feedback_data.reviewer_email,
                    "correlation_id": feedback_data.correlation_id,
                    "team_member_id": feedback_data.team_member_id,
                    "action": action
                }
            )
            
            return feedback, action
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(
                f"Error submitting feedback: {str(e)}", 
                exc_info=True,
                extra={
                    "reviewer_email": feedback_data.reviewer_email,
                    "correlation_id": feedback_data.correlation_id,
                    "team_member_id": feedback_data.team_member_id
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An error occurred while saving feedback: {str(e)}"
            )

    def get_feedback(
        self,
        correlation_id: str,
        team_member_id: str,
    ) -> list[RequisitionMatchTeamMemberFeedback]:
        """Retrieve feedback records for a given requisition match.

        The service simply proxies to the repository; no additional business
        rules are applied at this time.
        """

        try:
            return self.repo.get_feedback(correlation_id, team_member_id)
        except Exception as e:
            logger.error(
                f"Error retrieving feedback: {str(e)}",
                exc_info=True,
                extra={
                    "correlation_id": correlation_id,
                    "team_member_id": team_member_id,
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while fetching feedback"
            )
