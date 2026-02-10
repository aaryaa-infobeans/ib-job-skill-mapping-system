"""Database metadata definitions for ingestion service."""

from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    SmallInteger,
    String,
    Table,
    Text,
    Date,
    Enum as SAEnum,
    CHAR,
    JSON,
)
from sqlalchemy.dialects.postgresql import JSONB
from app.db.models.models import WorkTypeEnum

# Metadata object for ingestion tables
metadata = MetaData()

# ===== Ingestion Tables =====

ingestion_batch_state = Table(
    "ingestion_batch_state",
    metadata,
    Column("batch_id", String(100), primary_key=True, nullable=False),
    Column("correlation_id", String(100), nullable=False, index=True),
    Column("status", String(20), nullable=False, index=True),
    Column("total_records", Integer, nullable=True),
    Column("processed_records", Integer, nullable=True),
    Column("failed_records", Integer, nullable=True),
    Column("started_at", DateTime, nullable=False, default=datetime.utcnow),
    Column("completed_at", DateTime, nullable=True),
    Column("error_message", Text, nullable=True),
    Column("metadata", JSONB, nullable=True),
)

ingestion_audit_log = Table(
    "ingestion_audit_log",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True, nullable=False),
    Column("batch_id", String(100), ForeignKey("ingestion_batch_state.batch_id", ondelete="CASCADE"), nullable=False, index=True),
    Column("correlation_id", String(100), nullable=False, index=True),
    Column("event_type", String(50), nullable=False),
    Column("event_details", JSONB, nullable=True),
    Column("timestamp", DateTime, nullable=False, default=datetime.utcnow, index=True),
    Column("severity", String(20), nullable=True),
    Column("source", String(100), nullable=True),
)

# ===== Existing Tables (Referenced from src.app.db.models.models) =====
# These are imported for query construction and relationships

# Auth tables
auth_clients = Table(
    "auth_clients",
    metadata,
    Column("id", SmallInteger, primary_key=True, autoincrement=True),
    Column("client_name", String(100), nullable=False),
    Column("client_code", String(50), nullable=False, unique=True),
    Column("client_secret_hash", String(255), nullable=False),
    Column("auth_type", String(10), nullable=False, default="OAUTH"),
    Column("is_active", Boolean, nullable=False, default=True),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
    extend_existing=True,
)

# Master tables
category_master = Table(
    "category_master",
    metadata,
    Column("category_id", SmallInteger, primary_key=True),
    Column("category_name", String(100), nullable=False, unique=True),
    Column("created_at", DateTime),
    extend_existing=True,
)

skill_master = Table(
    "skill_master",
    metadata,
    Column("skill_id", String(50), primary_key=True),
    Column("skill_name", String(100), nullable=False, unique=True),
    Column("category_id", SmallInteger, ForeignKey("category_master.category_id"), nullable=False),
    Column("created_at", DateTime, default=datetime.utcnow),
    extend_existing=True,
)

# Team member tables
team_member = Table(
    "team_member",
    metadata,
    Column("team_member_id", String(50), primary_key=True),
    Column("designation", String(100), nullable=True),
    Column("profile_type", String(50), nullable=True),
    Column("is_active", Boolean, default=True),
    Column("experience_in_months", Integer, nullable=True),
    Column("base_location", String(100), nullable=True),
    Column("work_type", SAEnum(WorkTypeEnum, name="work_type_enum"), nullable=True),
    Column("profile_url", String(1024), nullable=True),
    Column("created_at", DateTime, default=datetime.utcnow),
    extend_existing=True,
)

team_member_allocation = Table(
    "team_member_allocation",
    metadata,
    Column("team_member_id", String(50), ForeignKey("team_member.team_member_id"), primary_key=True),
    Column("project_id", String(50), primary_key=True),
    Column("allocation_percentage", Numeric(5, 2), nullable=True),
    Column("start_date", Date, nullable=True),
    Column("end_date", Date, nullable=True),
    Column("billable", Boolean, nullable=True),
    Column("is_deleted", Boolean, default=False),
    extend_existing=True,
)

team_member_skill = Table(
    "team_member_skill",
    metadata,
    Column("team_member_id", String(50), ForeignKey("team_member.team_member_id"), primary_key=True),
    Column("skill_id", String(50), ForeignKey("skill_master.skill_id"), primary_key=True),
    Column("rating", Integer, nullable=True),
    Column("experience_in_months", Integer, nullable=True),
    Column("is_deleted", Boolean, default=False),
    extend_existing=True,
)

skill_certification = Table(
    "skill_certification",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("certification_id", String(100), nullable=True),
    Column("team_member_id", String(50), nullable=False),
    Column("skill_id", String(50), nullable=False),
    Column("certificate", String(150), nullable=True),
    Column("issuer", String(100), nullable=True),
    Column("issued_date", Date, nullable=True),
    Column("valid_till", Date, nullable=True),
    extend_existing=True,
)

# Requisition tables
requisition_status_master = Table(
    "requisition_status_master",
    metadata,
    Column("status_id", SmallInteger, primary_key=True),
    Column("status_key", String(40), nullable=False, unique=True),
    Column("status_message", String(255), nullable=False),
    extend_existing=True,
)

requisition_requests = Table(
    "requisition_requests",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("request_id", String(64), nullable=False, unique=True),
    Column("auth_client_id", SmallInteger, ForeignKey("auth_clients.id"), nullable=False),
    Column("status", SmallInteger, ForeignKey("requisition_status_master.status_id"), nullable=False),
    Column("client_name", String(100), nullable=False),
    Column("correlation_id", String(100), nullable=True),
    Column("received_at", DateTime, nullable=False, default=datetime.utcnow),
    Column("completed_at", DateTime, nullable=True),
    extend_existing=True,
)

requisition_detail = Table(
    "requisition_detail",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("requisition_request_id", Integer, ForeignKey("requisition_requests.id"), nullable=False, unique=True),
    Column("payload_json", JSON, nullable=False),
    Column("payload_hash", CHAR(64), nullable=False, unique=True),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
    extend_existing=True,
)

# LangGraph table
langgraph_checkpoints = Table(
    "langgraph_checkpoints",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("request_id", String(64), ForeignKey("requisition_requests.request_id"), nullable=False),
    Column("node_name", String(50), nullable=False),
    Column("state_json", JSON, nullable=False),
    Column("token_count", Integer, nullable=True),
    Column("created_at", DateTime, nullable=False, default=datetime.utcnow),
    extend_existing=True,
)

# Export for convenience
__all__ = [
    "metadata",
    # Ingestion tables
    "ingestion_batch_state",
    "ingestion_audit_log",
    # Master tables
    "category_master",
    "skill_master",
    # Team member tables
    "team_member",
    "team_member_allocation",
    "team_member_skill",
    "skill_certification",
    # Auth tables
    "auth_clients",
    # Requisition tables
    "requisition_status_master",
    "requisition_requests",
    "requisition_detail",
    # LangGraph tables
    "langgraph_checkpoints",
]
