"""Pydantic schemas for requisition requests."""

from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class PriorityEnum(str, Enum):
    """Priority enumeration."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ExperienceRange(BaseModel):
    """Experience range specification."""

    min_months: Optional[int] = Field(None, ge=0)
    max_months: Optional[int] = Field(None, ge=0)

    @field_validator("max_months")
    @classmethod
    def validate_max_greater_than_min(cls, v, info):
        """Validate max_months >= min_months."""
        if v is not None and info.data.get("min_months") is not None:
            if v < info.data["min_months"]:
                raise ValueError("max_months must be >= min_months")
        return v


class JobDescription(BaseModel):
    """Job description details."""

    client_name: str
    title: str
    role: str
    requisition_duration_month: Optional[int] = Field(None, ge=0)
    expected_start_date: Optional[date] = None
    priority: PriorityEnum
    location: List[str]
    work_mode: List[str]
    experience: Optional[ExperienceRange] = None
    mandatory_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    jd_text: str


class RequisitionMetadata(BaseModel):
    """Metadata for requisition request."""

    submitted_by: Optional[str] = None
    submitted_at: Optional[datetime] = None
    department: Optional[str] = None


class RequisitionRequest(BaseModel):
    """Request model for requisition submission."""

    request_id: str
    schema_version: str
    source_system: str
    client_name: Optional[str] = None
    job_description: JobDescription
    metadata: RequisitionMetadata


class RequisitionResponse(BaseModel):
    """Response model for requisition submission."""

    correlation_id: str
    status: str = "QUEUED_FOR_PROCESSING"
    received_at: datetime
