"""add llm_request_log table

Revision ID: 20260203_add_llm_request_log
Revises: 20260203_add_team_member_embeddings
Create Date: 2026-02-03 17:21:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0203_llm_log"
down_revision: Union[str, None] = "0203_embeddings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create llm_request_log table
    op.create_table(
        "llm_request_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.func.gen_random_uuid(),
            nullable=False,
        ),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_name", sa.String(255), nullable=False),
        sa.Column("prompt_name", sa.String(255), nullable=False),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # Create indexes
    op.create_index(
        "idx_llm_request_log_request_id_created_at",
        "llm_request_log",
        ["request_id", "created_at"],
    )
    op.create_index(
        "idx_llm_request_log_agent_name",
        "llm_request_log",
        ["agent_name"],
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_llm_request_log_agent_name", table_name="llm_request_log")
    op.drop_index(
        "idx_llm_request_log_request_id_created_at", table_name="llm_request_log"
    )
    # Drop table
    op.drop_table("llm_request_log")
