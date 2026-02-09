"""add jd_certification_requirements table

Revision ID: 20260203_add_jd_certification_requirements
Revises: 20260203_add_skill_ontology
Create Date: 2026-02-03 17:23:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0203_jd_certs"
down_revision: Union[str, None] = "0203_ontology"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create jd_certification_requirements table
    op.create_table(
        "jd_certification_requirements",
        sa.Column("jd_type", sa.String(255), nullable=False),
        sa.Column("certification", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("jd_type", "certification"),
    )
    # Create index
    op.create_index(
        "idx_jd_certification_jd_type",
        "jd_certification_requirements",
        ["jd_type"],
    )


def downgrade() -> None:
    # Drop index
    op.drop_index(
        "idx_jd_certification_jd_type",
        table_name="jd_certification_requirements",
    )
    # Drop table
    op.drop_table("jd_certification_requirements")
