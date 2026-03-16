"""fix pii audit entity id type

Revision ID: 0c7293f99a72
Revises: emb002_multi_vec
Create Date: 2026-03-13 18:45:27.617690

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0c7293f99a72'
down_revision: Union[str, None] = 'emb002_multi_vec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Change entity_id from BIGINT to VARCHAR(100)
    op.alter_column('pii_scrub_audit', 'entity_id',
               existing_type=sa.BigInteger(),
               type_=sa.String(length=100),
               existing_nullable=True)


def downgrade() -> None:
    # Revert entity_id from VARCHAR(100) to BIGINT
    # Note: This may fail if there are non-numeric strings in the column
    op.alter_column('pii_scrub_audit', 'entity_id',
               existing_type=sa.String(length=100),
               type_=sa.BigInteger(),
               existing_nullable=True,
               postgresql_using='entity_id::bigint')
