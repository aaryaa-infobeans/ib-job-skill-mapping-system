"""add_ingestion_tables

Revision ID: ba97cf8e4fdf
Revises: e8a217c84204
Create Date: 2026-02-06 19:23:56.247469

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'ba97cf8e4fdf'
down_revision: Union[str, None] = 'e8a217c84204'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add ingestion_batch_state and ingestion_audit_log tables."""
    
    # Create ingestion_batch_state table
    op.create_table(
        "ingestion_batch_state",
        sa.Column("batch_id", sa.String(length=100), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("total_records", sa.Integer(), nullable=True),
        sa.Column("processed_records", sa.Integer(), nullable=True),
        sa.Column("failed_records", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", JSONB, nullable=True),
        sa.PrimaryKeyConstraint("batch_id"),
    )
    
    # Create index on correlation_id for faster lookups
    op.create_index(
        "ix_ingestion_batch_state_correlation_id",
        "ingestion_batch_state",
        ["correlation_id"],
    )
    
    # Create index on status for filtering
    op.create_index(
        "ix_ingestion_batch_state_status",
        "ingestion_batch_state",
        ["status"],
    )
    
    # Create ingestion_audit_log table
    op.create_table(
        "ingestion_audit_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("batch_id", sa.String(length=100), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("event_details", JSONB, nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("severity", sa.String(length=20), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["ingestion_batch_state.batch_id"],
            ondelete="CASCADE",
        ),
    )
    
    # Create index on batch_id for faster lookups
    op.create_index(
        "ix_ingestion_audit_log_batch_id",
        "ingestion_audit_log",
        ["batch_id"],
    )
    
    # Create index on correlation_id for faster lookups
    op.create_index(
        "ix_ingestion_audit_log_correlation_id",
        "ingestion_audit_log",
        ["correlation_id"],
    )
    
    # Create index on timestamp for time-based queries
    op.create_index(
        "ix_ingestion_audit_log_timestamp",
        "ingestion_audit_log",
        ["timestamp"],
    )


def downgrade() -> None:
    """Drop ingestion tables and indexes."""
    
    # Drop indexes first
    op.drop_index("ix_ingestion_audit_log_timestamp", table_name="ingestion_audit_log")
    op.drop_index("ix_ingestion_audit_log_correlation_id", table_name="ingestion_audit_log")
    op.drop_index("ix_ingestion_audit_log_batch_id", table_name="ingestion_audit_log")
    op.drop_index("ix_ingestion_batch_state_status", table_name="ingestion_batch_state")
    op.drop_index("ix_ingestion_batch_state_correlation_id", table_name="ingestion_batch_state")
    
    # Drop tables
    op.drop_table("ingestion_audit_log")
    op.drop_table("ingestion_batch_state")
