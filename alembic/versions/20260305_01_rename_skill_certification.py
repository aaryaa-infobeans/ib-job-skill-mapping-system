"""rename skill_certification to team_member_skill_certification

Revision ID: 20260305_01
Revises: 937cc5c69c28
Create Date: 2026-03-05 10:00:00.000000

Aligns the Docker schema with production:
- Renames table skill_certification -> team_member_skill_certification
- Keeps the existing skill_certification_id_seq and re-owns it to the renamed table

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260305_01"
down_revision: Union[str, None] = "937cc5c69c28"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename the table
    op.rename_table("skill_certification", "team_member_skill_certification")

    # Create sequence (matches production backup) and wire it to the id column
    op.execute(
        "CREATE SEQUENCE IF NOT EXISTS skill_certification_id_seq "
        "AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1"
    )
    op.execute(
        "ALTER SEQUENCE skill_certification_id_seq "
        "OWNED BY team_member_skill_certification.id"
    )
    op.execute(
        "ALTER TABLE team_member_skill_certification "
        "ALTER COLUMN id SET DEFAULT nextval('skill_certification_id_seq'::regclass)"
    )


def downgrade() -> None:
    # Remove sequence default
    op.execute(
        "ALTER TABLE team_member_skill_certification "
        "ALTER COLUMN id DROP DEFAULT"
    )
    op.execute("DROP SEQUENCE IF EXISTS skill_certification_id_seq")

    # Rename back
    op.rename_table("team_member_skill_certification", "skill_certification")
