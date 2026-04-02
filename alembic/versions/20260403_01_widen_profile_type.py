"""widen team_member.profile_type from VARCHAR(50) to VARCHAR(255)

Revision ID: 20260403_01
Revises: 0c7293f99a72
Create Date: 2026-04-03

Problem: profile_type VARCHAR(50) causes StringDataRightTruncationError when
the API returns designations longer than 50 characters (e.g. "Senior Vice
President, Digital Transformation Services" = 55 chars). Widening to 255
aligns it with typical designation length expectations.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260403_01'
down_revision: Union[str, None] = '0c7293f99a72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'team_member',
        'profile_type',
        existing_type=sa.String(length=50),
        type_=sa.String(length=255),
        existing_nullable=True,
    )


def downgrade() -> None:
    # WARNING: downgrade will silently truncate any profile_type values > 50 chars.
    op.alter_column(
        'team_member',
        'profile_type',
        existing_type=sa.String(length=255),
        type_=sa.String(length=50),
        existing_nullable=True,
        postgresql_using='LEFT(profile_type, 50)',
    )
