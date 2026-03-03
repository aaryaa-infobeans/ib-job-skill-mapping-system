from typing import Optional, Literal
from pydantic import BaseModel, Field

class FeedbackCreate(BaseModel):
    """Schema for creating or updating candidate match feedback."""
    
    team_member_id: str = Field(..., description="The ID of the candidate being reviewed.")
    correlation_id: str = Field(..., description="The correlation ID of the requisition match.")
    reviewer_email: str = Field(..., description="The email address of the reviewer. Must match authenticated user.")
    liked: bool = Field(False, description="Whether the reviewer liked the candidate match.")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Reviewer's rating (1 to 5).")
    comment: Optional[str] = Field(None, description="Optional reviewer comment.")

class FeedbackResponse(BaseModel):
    """Standard response for feedback submission."""
    
    status: Literal["success"] = "success"
    action: Literal["created", "updated"]
    feedback_id: int


class FeedbackItem(BaseModel):
    """Representation of a single feedback record returned by the GET endpoint."""

    team_member_id: str
    correlation_id: str
    reviewer_email: str
    liked: bool
    rating: Optional[int] = None
    comment: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class FeedbackListResponse(BaseModel):
    """Response for list of feedback records."""

    status: Literal["success"] = "success"
    feedback: list[FeedbackItem]
