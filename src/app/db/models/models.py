"""Database models for the job skill mapping system."""

from pgvector.sqlalchemy import Vector

import enum
from datetime import datetime
from sqlalchemy import (
    Boolean,
    CHAR,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    JSON,
    Numeric,
    SmallInteger,
    String,
    Text,
    text,
)
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship

from app.db.base import Base


class WorkTypeEnum(enum.Enum):
    """Work type enumeration."""

    wfo = "wfo"
    wfh = "wfh"
    hybrid = "hybrid"


class AuthClient(Base):
    """Client applications authorized to access the system."""

    __tablename__ = "auth_clients"

    id = Column(SmallInteger, primary_key=True, autoincrement=True)
    client_name = Column(String(100), nullable=False)
    client_code = Column(String(50), nullable=False, unique=True)
    client_secret_hash = Column(String(255), nullable=False)
    auth_type = Column(String(10), nullable=False, default="OAUTH")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    access_tokens = relationship("AuthAccessToken", back_populates="client")
    requisition_requests = relationship("RequisitionRequest", back_populates="client")


class AuthAccessToken(Base):
    """Access tokens issued to clients."""

    __tablename__ = "auth_access_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    auth_client_id = Column(SmallInteger, ForeignKey("auth_clients.id"), nullable=False)
    access_token = Column(String(255), nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, nullable=False, default=False)
    issued_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    client = relationship("AuthClient", back_populates="access_tokens")


class RequisitionStatusMaster(Base):
    """Master table for requisition request statuses."""

    __tablename__ = "requisition_status_master"

    status_id = Column(SmallInteger, primary_key=True)
    status_key = Column(String(40), nullable=False, unique=True)
    status_message = Column(String(255), nullable=False)

    # Relationships
    requisition_requests = relationship("RequisitionRequest", back_populates="status_ref")


class RequisitionRequest(Base):
    """Metadata for each incoming requisition request."""

    __tablename__ = "requisition_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(64), nullable=False, unique=True)
    auth_client_id = Column(SmallInteger, ForeignKey("auth_clients.id"), nullable=False)
    status = Column(SmallInteger, ForeignKey("requisition_status_master.status_id"), nullable=False)
    client_name = Column(String(100), nullable=False)
    correlation_id = Column(String(100), nullable=True)
    received_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    client = relationship("AuthClient", back_populates="requisition_requests")
    status_ref = relationship("RequisitionStatusMaster", back_populates="requisition_requests")
    detail = relationship("RequisitionDetail", back_populates="request", uselist=False)
    checkpoints = relationship("LangGraphCheckpoint", back_populates="request")


class RequisitionDetail(Base):
    """Raw JSON payload of each requisition request."""

    __tablename__ = "requisition_detail"

    id = Column(Integer, primary_key=True, autoincrement=True)
    requisition_request_id = Column(
        Integer, ForeignKey("requisition_requests.id"), nullable=False, unique=True
    )
    # DB column is JSONB; JSON fallback for non-PG environments
    payload_json = Column(JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=False)
    payload_hash = Column(CHAR(64), nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    request = relationship("RequisitionRequest", back_populates="detail")


class CategoryMaster(Base):
    """Master table for skill categories."""

    __tablename__ = "category_master"

    category_id = Column(SmallInteger, primary_key=True, autoincrement=True)
    category_name = Column(String(100), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    skills = relationship("SkillMaster", back_populates="category")


class SkillMaster(Base):
    """Canonical dictionary of all skills."""

    __tablename__ = "skill_master"

    skill_id = Column(String(50), primary_key=True)
    skill_name = Column(String(100), nullable=False, unique=True)
    category_id = Column(SmallInteger, ForeignKey("category_master.category_id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    category = relationship("CategoryMaster", back_populates="skills")
    team_member_skills = relationship("TeamMemberSkill", back_populates="skill")


class TeamMember(Base):
    """Core profile information for each team member."""

    __tablename__ = "team_member"

    team_member_id = Column(String(50), primary_key=True)
    designation = Column(String(100), nullable=True)
    profile_type = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    experience_in_months = Column(Integer, nullable=True)
    base_location = Column(String(100), nullable=True)
    # Enum type name must match the DB type name: work_type_enum
    work_type = Column(Enum(WorkTypeEnum, name="work_type_enum"), nullable=True)
    profile_url = Column(String(1024), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    skills = relationship("TeamMemberSkill", back_populates="team_member")
    allocations = relationship("TeamMemberAllocation", back_populates="team_member")


class TeamMemberAllocation(Base):
    """Project allocation details for each team member."""

    __tablename__ = "team_member_allocation"

    team_member_id = Column(String(50), ForeignKey("team_member.team_member_id"), primary_key=True)
    project_id = Column(String(50), primary_key=True)
    allocation_percentage = Column(Numeric(5, 2), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    billable = Column(Boolean, nullable=True)
    is_deleted = Column(Boolean, default=False)

    # Relationships
    team_member = relationship("TeamMember", back_populates="allocations")


class TeamMemberSkill(Base):
    """Links team members to skills with proficiency details."""

    __tablename__ = "team_member_skill"

    team_member_id = Column(String(50), ForeignKey("team_member.team_member_id"), primary_key=True)
    skill_id = Column(String(50), ForeignKey("skill_master.skill_id"), primary_key=True)
    rating = Column(Integer, nullable=True)
    experience_in_months = Column(Integer, nullable=True)
    is_deleted = Column(Boolean, default=False)

    # Relationships
    team_member = relationship("TeamMember", back_populates="skills")
    skill = relationship("SkillMaster", back_populates="team_member_skills")
    certifications = relationship("TeamMemberSkillCertification", back_populates="team_member_skill")


class TeamMemberSkillCertification(Base):
    """Certification details for a specific team member's skill."""

    __tablename__ = "team_member_skill_certification"

    id = Column(Integer, primary_key=True, autoincrement=True)
    certification_id = Column(String(100), nullable=True)
    team_member_id = Column(String(50), nullable=False)
    skill_id = Column(String(50), nullable=False)
    certificate = Column(String(150), nullable=True)
    issuer = Column(String(100), nullable=True)
    issued_date = Column(Date, nullable=True)
    valid_till = Column(Date, nullable=True)

    # Composite foreign key
    __table_args__ = (
        ForeignKeyConstraint(
            ["team_member_id", "skill_id"],
            ["team_member_skill.team_member_id", "team_member_skill.skill_id"],
        ),
    )

    # Relationships
    team_member_skill = relationship("TeamMemberSkill", back_populates="certifications")


class LangGraphCheckpoint(Base):
    """State of the AI agent graph for auditing and debugging."""

    __tablename__ = "langgraph_checkpoints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(64), ForeignKey("requisition_requests.request_id"), nullable=False)
    node_name = Column(String(50), nullable=False)
    # DB column is JSONB; JSON fallback for non-PG environments
    state_json = Column(JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=False)
    token_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    request = relationship("RequisitionRequest", back_populates="checkpoints")


class LLMRequestLog(Base):
    """Log of all LLM requests for auditing and cost tracking."""

    __tablename__ = "llm_request_log"

    id = Column(
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )
    request_id = Column(String(64), nullable=True)
    agent_name = Column(String(255), nullable=False)
    prompt_name = Column(String(255), nullable=False)
    model = Column(String(255), nullable=False)
    prompt_tokens = Column(Integer, nullable=False)
    completion_tokens = Column(Integer, nullable=False)
    total_tokens = Column(Integer, nullable=False)
    cost_usd = Column(Numeric(precision=10, scale=6), nullable=False)
    status = Column(String(50), nullable=False, default="SUCCESS")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        sa.Index("idx_llm_request_log_agent_name", "agent_name"),
        sa.Index("idx_llm_request_log_request_id_created_at", "request_id", "created_at"),
    )


class SkillOntology(Base):
    """Enriched skill ontology for expansion and normalization."""

    __tablename__ = "skill_ontology"

    id = Column(Integer, primary_key=True, autoincrement=True)
    core_skill = Column(String(255), nullable=False, unique=True)
    enriched_terms = Column(
        JSON().with_variant(postgresql.ARRAY(String(255)), "postgresql"),
        nullable=True,
    )

    __table_args__ = (
        sa.Index("idx_skill_ontology_core_skill", "core_skill"),
    )


class RoleOntology(Base):
    """Maps canonical role names to internal profile_type codes, aliases, and enriched terms.

    canonical_role — standardised role name used as the lookup key
                     (matches normalized_role from JD parsing and jd_certification_requirements.jd_type)
    profile_type   — internal short code stored on team_member.profile_type
    aliases        — alternative names the LLM or clients may use for the same role
    enriched_terms — domain-specific concepts for semantic matching (scoped to this role only)
    """

    __tablename__ = "role_ontology"

    id = Column(Integer, primary_key=True, autoincrement=True)
    canonical_role = Column(String(100), nullable=False)
    profile_type = Column(String(100), nullable=False)
    aliases = Column(
        JSON().with_variant(postgresql.ARRAY(Text), "postgresql"),
        nullable=False,
        server_default="[]",
    )
    enriched_terms = Column(
        JSON().with_variant(postgresql.ARRAY(Text), "postgresql"),
        nullable=False,
        server_default="[]",
    )

    __table_args__ = (
        sa.Index("idx_role_ontology_canonical_role", "canonical_role", unique=True),
        sa.Index("idx_role_ontology_profile_type", "profile_type"),
    )


class TeamMemberEmbedding(Base):
    """Embeddings for team member profiles."""

    __tablename__ = "team_member_embeddings"

    # id (UUID) is the actual DB primary key — created by 0203_embeddings migration.
    # team_member_id has a unique constraint (added by emb002) for ON CONFLICT upserts.
    id = Column(
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        server_default=sa.text("gen_random_uuid()"),
    )
    team_member_id = Column(
        String(50),
        ForeignKey("team_member.team_member_id"),
        nullable=False,
    )
    # NOT NULL in DB — original migration enforced this
    embedding = Column(
        Text().with_variant(Vector(768), "postgresql"),
        nullable=False,
    )
    profile_text = Column(Text, nullable=True)
    # DB column is plain JSON (created by 0203_embeddings migration as `metadata JSON`)
    extra_metadata = Column("metadata", JSON(), nullable=True)
    # NOT NULL in DB — original migration enforced this
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=sa.text("NOW()"),
        default=datetime.utcnow,
    )

    # CR-EMB-002: Multi-vector embedding columns (Phase 1)
    resume_embedding = Column(
        Text().with_variant(Vector(768), "postgresql"), nullable=True
    )
    skills_embedding = Column(
        Text().with_variant(Vector(768), "postgresql"), nullable=True
    )
    certifications_embedding = Column(
        Text().with_variant(Vector(768), "postgresql"), nullable=True
    )
    resume_text = Column(Text, nullable=True)
    skills_text = Column(Text, nullable=True)
    certifications_text = Column(Text, nullable=True)
    embedding_model = Column(
        String(100), nullable=True, server_default="embedding-gemma-300m"
    )
    content_hash = Column(CHAR(64), nullable=True)
    resume_fetched_at = Column(DateTime, nullable=True)
    embedding_updated_at = Column(DateTime, nullable=True)
    pii_scrubbed = Column(Boolean, nullable=False, server_default="false")
    scrubbed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        sa.UniqueConstraint("team_member_id", name="uq_tme_team_member_id"),
        sa.Index("idx_team_member_embeddings_team_member_id", "team_member_id"),
        sa.Index("idx_team_member_embeddings_created_at", "created_at"),
        sa.Index("idx_tme_content_hash", "content_hash"),
        sa.Index("ix_team_member_embeddings_pii_scrubbed", "pii_scrubbed"),
        # IVFFlat vector indexes — created by raw SQL in emb002 migration
        sa.Index("idx_tme_resume_embedding", "resume_embedding", postgresql_using="ivfflat"),
        sa.Index("idx_tme_skills_embedding", "skills_embedding", postgresql_using="ivfflat"),
        sa.Index("idx_tme_certifications_embedding", "certifications_embedding", postgresql_using="ivfflat"),
    )


class RequisitionMatchTeamMemberFeedback(Base):
    """Reviewer feedback for a candidate match."""

    __tablename__ = "requisition_match_team_member_feedback"

    # DB column is BIGINT with Identity sequence
    id = Column(sa.BigInteger, primary_key=True, autoincrement=True)
    team_member_id = Column(String(50), nullable=False)
    correlation_id = Column(String(100), nullable=False)
    reviewer_email = Column(String(100), nullable=False)
    liked = Column(Boolean, nullable=False, default=False)
    rating = Column(SmallInteger, nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now())

    __table_args__ = (
        sa.UniqueConstraint("team_member_id", "correlation_id", "reviewer_email", name="uq_feedback_reviewer_match"),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="check_rating_range"),
        sa.Index("idx_feedback_correlation_id", "correlation_id"),
        sa.Index("idx_feedback_team_member_id", "team_member_id"),
    )


# ---------------------------------------------------------------------------
# Tables that exist in the DB but were previously missing from ORM models.
# Added to resolve alembic check drift (TD-002).
# ---------------------------------------------------------------------------

class JdCertificationRequirement(Base):
    """Maps job description types to required certifications."""

    __tablename__ = "jd_certification_requirements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    jd_type = Column(String(255), nullable=False)
    certification = Column(String(255), nullable=False)

    __table_args__ = (
        sa.UniqueConstraint("jd_type", "certification", name="uq_jd_cert_combo"),
        sa.Index("idx_jd_certification_jd_type", "jd_type"),
    )


class IngestionBatchState(Base):
    """Tracks the state of each profile ingestion batch."""

    __tablename__ = "ingestion_batch_state"

    batch_id = Column(String(100), primary_key=True)
    correlation_id = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)
    total_records = Column(Integer, nullable=True)
    processed_records = Column(Integer, nullable=True)
    failed_records = Column(Integer, nullable=True)
    started_at = Column(DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"))
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    extra_metadata = Column("metadata", postgresql.JSONB(), nullable=True)

    __table_args__ = (
        sa.Index("ix_ingestion_batch_state_correlation_id", "correlation_id"),
        sa.Index("ix_ingestion_batch_state_status", "status"),
    )

    audit_logs = relationship("IngestionAuditLog", back_populates="batch")


class IngestionAuditLog(Base):
    """Append-only audit log for ingestion batch events."""

    __tablename__ = "ingestion_audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(
        String(100),
        ForeignKey("ingestion_batch_state.batch_id", ondelete="CASCADE"),
        nullable=False,
    )
    correlation_id = Column(String(100), nullable=False)
    event_type = Column(String(50), nullable=False)
    event_details = Column(postgresql.JSONB(), nullable=True)
    timestamp = Column(DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"))
    severity = Column(String(20), nullable=True)
    source = Column(String(100), nullable=True)

    __table_args__ = (
        sa.Index("ix_ingestion_audit_log_batch_id", "batch_id"),
        sa.Index("ix_ingestion_audit_log_correlation_id", "correlation_id"),
        sa.Index("ix_ingestion_audit_log_timestamp", "timestamp"),
    )

    batch = relationship("IngestionBatchState", back_populates="audit_logs")


class PiiScrubAudit(Base):
    """Immutable audit log for PII scrubbing operations (NFR-PII-003).

    Partitioned by RANGE(timestamp). UPDATE/DELETE are blocked by a DB trigger.
    Composite PK (id, timestamp) is required for PostgreSQL range partitioning.
    entity_id is VARCHAR(100) after migration 0c7293f99a72.
    """

    __tablename__ = "pii_scrub_audit"

    id = Column(sa.BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(
        DateTime(timezone=True),
        primary_key=True,
        nullable=False,
        server_default=sa.text("NOW()"),
    )
    operation = Column(String(50), nullable=False)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(String(100), nullable=True)
    field_name = Column(String(100), nullable=True)
    pii_type = Column(String(50), nullable=True)
    action_taken = Column(String(50), nullable=False)
    original_value_hash = Column(String(64), nullable=True)
    scrubbed_value = Column(Text, nullable=True)
    detection_method = Column(String(50), nullable=False)
    confidence_score = Column(Numeric(5, 4), nullable=True)
    user_id = Column(sa.BigInteger, nullable=True)
    session_id = Column(String(100), nullable=True)
    extra_metadata = Column("metadata", postgresql.JSONB(), nullable=True)

    __table_args__ = (
        sa.Index("ix_pii_scrub_audit_timestamp", "timestamp"),
        sa.Index("ix_pii_scrub_audit_entity", "entity_type", "entity_id"),
        sa.Index("ix_pii_scrub_audit_operation", "operation", "timestamp"),
        {"postgresql_partition_by": "RANGE (timestamp)"},
    )
