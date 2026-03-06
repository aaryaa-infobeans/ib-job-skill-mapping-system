"""add status and error_message columns to llm_request_log

Revision ID: 20260305_02
Revises: 20260305_01
Create Date: 2026-03-05 10:01:00.000000

Aligns the Docker schema with production:
- Adds status VARCHAR(50) NOT NULL DEFAULT 'SUCCESS'
- Adds error_message TEXT nullable

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260305_02"
down_revision: Union[str, None] = "20260305_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "llm_request_log",
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="SUCCESS",
        ),
    )
    op.add_column(
        "llm_request_log",
        sa.Column("error_message", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("llm_request_log", "error_message")
    op.drop_column("llm_request_log", "status")
