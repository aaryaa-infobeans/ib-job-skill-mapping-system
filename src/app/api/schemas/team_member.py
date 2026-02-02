"""Pydantic schemas for team member skill availability."""

from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class TeamMemberStatus(str, Enum):
    """Team member status enumeration."""

    active = "active"
    inactive = "inactive"
    terminated = "terminated"


class StatusInfo(BaseModel):
    """Status information."""

    code: int
    key: str
    message: str


class BatchMetadata(BaseModel):
    """Metadata for bulk upsert batch."""

    batch_id: str = Field(..., description="Unique identifier for the sync batch")
    timestamp: datetime = Field(..., description="Timestamp of batch creation in ISO 8601 format")
    total_records: int = Field(..., description="Total number of records across all batches")
    batch_number: int = Field(..., description="Current batch number")
    total_batches: int = Field(..., description="Total number of batches")
    records_in_batch: int = Field(..., description="Number of records in this batch")
    source_system: str = Field(..., description="Source system name")
    schema_version: str = Field(..., description="Schema version")
    status: StatusInfo


class AllocationDetails(BaseModel):
    """Project allocation details for a team member."""

    project_id: str
    allocation_percentage: Optional[float] = Field(None, ge=0, le=100)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    billable: Optional[bool] = None
    is_deleted: bool = False


class CertificationDetails(BaseModel):
    """Certification details for a skill."""

    certification_id: Optional[str] = None
    certificate: Optional[str] = None
    issuer: Optional[str] = None
    issued_date: Optional[date] = None
    valid_till: Optional[date] = None


class SkillDetails(BaseModel):
    """Skill details for a team member."""

    skill_id: str
    skill_name: str
    rating: Optional[int] = Field(None, ge=1, le=10)
    experience_in_months: Optional[int] = Field(None, ge=0)
    category: Optional[str] = None
    certifications: Optional[List[CertificationDetails]] = None
    is_deleted: bool = False


class TeamMemberData(BaseModel):
    """Team member data for bulk upsert."""

    team_member_id: str
    team_member_status: TeamMemberStatus
    experience_in_months: int = Field(..., ge=0)
    full_name: str
    designation: Optional[str] = None
    profile_type: Optional[str] = None
    base_location: Optional[str] = None
    work_type: Optional[str] = None
    profile_url: Optional[str] = None
    allocations: Optional[List[AllocationDetails]] = None
    skills: Optional[List[SkillDetails]] = None


class BulkUpsertRequest(BaseModel):
    """Request model for bulk upsert of team member skill availability."""

    metadata: BatchMetadata
    team_members: List[TeamMemberData]


class UpsertSummary(BaseModel):
    """Summary of upsert operation."""

    records_received: int
    team_members_inserted: int
    team_members_updated: int
    skills_inserted: int
    skills_updated: int
    allocations_inserted: int
    allocations_updated: int
    records_failed: int
    batch_id: str
    processed_at: datetime


class BulkUpsertResponse(BaseModel):
    """Response model for bulk upsert operation."""

    status: str = "ACCEPTED"
    message: str
    summary: UpsertSummary
