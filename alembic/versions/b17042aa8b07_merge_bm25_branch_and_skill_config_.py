"""merge bm25 branch and skill_config branch

Revision ID: b17042aa8b07
Revises: 20260519_01, 20260608_01
Create Date: 2026-06-08 10:49:36.003446

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b17042aa8b07'
down_revision: Union[str, None] = ('20260519_01', '20260608_01')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
