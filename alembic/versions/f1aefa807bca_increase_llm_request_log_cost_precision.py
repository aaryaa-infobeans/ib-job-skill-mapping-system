"""increase llm_request_log cost precision

Revision ID: f1aefa807bca
Revises: af966df897c8
Create Date: 2026-02-05 13:04:13.539748

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1aefa807bca'
down_revision: Union[str, None] = 'af966df897c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Increase precision of cost_usd to scale=6
    op.alter_column('llm_request_log', 'cost_usd',
               existing_type=sa.Numeric(precision=10, scale=4),
               type_=sa.Numeric(precision=10, scale=6),
               existing_nullable=False)


def downgrade() -> None:
    # Revert precision of cost_usd to scale=4
    op.alter_column('llm_request_log', 'cost_usd',
               existing_type=sa.Numeric(precision=10, scale=6),
               type_=sa.Numeric(precision=10, scale=4),
               existing_nullable=False)
