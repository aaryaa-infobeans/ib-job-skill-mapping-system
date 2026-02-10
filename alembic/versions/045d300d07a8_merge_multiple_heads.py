"""merge multiple heads

Revision ID: 045d300d07a8
Revises: 9c18630a6317, ba97cf8e4fdf
Create Date: 2026-02-10 14:47:09.331108

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '045d300d07a8'
down_revision: Union[str, None] = ('9c18630a6317', 'ba97cf8e4fdf')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
