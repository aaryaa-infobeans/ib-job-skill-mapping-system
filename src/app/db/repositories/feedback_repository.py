from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.db.models.models import RequisitionMatchTeamMemberFeedback

class FeedbackRepository:
    """Repository for feedback data access."""

    def __init__(self, db: Session):
        self.db = db

    def upsert_feedback(
        self,
        team_member_id: str,
        correlation_id: str,
        reviewer_email: str,
        liked: bool,
        rating: Optional[int] = None,
        comment: Optional[str] = None
    ) -> Tuple[RequisitionMatchTeamMemberFeedback, str]:
        """
        Upsert feedback for a candidate match.
        
        Returns:
            tuple: (feedback_object, action) where action is "created" or "updated"
        """
        existing = (
            self.db.query(RequisitionMatchTeamMemberFeedback)
            .filter(
                and_(
                    RequisitionMatchTeamMemberFeedback.team_member_id == team_member_id,
                    RequisitionMatchTeamMemberFeedback.correlation_id == correlation_id,
                    RequisitionMatchTeamMemberFeedback.reviewer_email == reviewer_email,
                )
            )
            .first()
        )

        if existing:
            existing.liked = liked
            existing.rating = rating
            existing.comment = comment
            # No need for self.db.add(existing) if it's already in the session, 
            # but flush handles it.
            self.db.flush()
            return existing, "updated"
        else:
            new_feedback = RequisitionMatchTeamMemberFeedback(
                team_member_id=team_member_id,
                correlation_id=correlation_id,
                reviewer_email=reviewer_email,
                liked=liked,
                rating=rating,
                comment=comment,
            )
            self.db.add(new_feedback)
            self.db.flush()  # To get the ID
            return new_feedback, "created"
    def get_feedback(
        self,
        correlation_id: str,
        team_member_id: str,
    ) -> list[RequisitionMatchTeamMemberFeedback]:
        """Retrieve all feedback entries matching a given requisition match.

        This does **not** filter by reviewer, allowing callers to inspect all
        reviewers' comments for a specific match.
        """

        return (
            self.db.query(RequisitionMatchTeamMemberFeedback)
            .filter(
                and_(
                    RequisitionMatchTeamMemberFeedback.correlation_id == correlation_id,
                    RequisitionMatchTeamMemberFeedback.team_member_id == team_member_id,
                )
            )
            .all()
        )
