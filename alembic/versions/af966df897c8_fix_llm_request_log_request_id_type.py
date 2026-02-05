"""fix llm_request_log request_id type

Revision ID: af966df897c8
Revises: 20260204_placeholder
Create Date: 2026-02-05 13:00:15.653235

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'af966df897c8'
down_revision: Union[str, None] = '20260204_placeholder'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from sqlalchemy.dialects import postgresql

def upgrade() -> None:
    # Change request_id from UUID to VARCHAR(64)
    op.alter_column('llm_request_log', 'request_id',
               existing_type=postgresql.UUID(),
               type_=sa.String(length=64),
               existing_nullable=True,
               postgresql_using='request_id::text')


def downgrade() -> None:
    # Revert request_id from VARCHAR(64) to UUID
    op.alter_column('llm_request_log', 'request_id',
               existing_type=sa.String(length=64),
               type_=postgresql.UUID(),
               existing_nullable=True,
               postgresql_using='request_id::uuid')
