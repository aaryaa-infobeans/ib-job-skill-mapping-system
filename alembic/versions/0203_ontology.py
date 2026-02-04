"""add skill_ontology table

Revision ID: 20260203_add_skill_ontology
Revises: 20260203_add_llm_request_log
Create Date: 2026-02-03 17:22:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0203_ontology"
down_revision: Union[str, None] = "0203_llm_log"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create skill_ontology table
    op.create_table(
        "skill_ontology",
        sa.Column("core_skill", sa.String(255), nullable=False),
        sa.Column("enriched_terms", postgresql.ARRAY(sa.String(255)), nullable=True),
        sa.PrimaryKeyConstraint("core_skill"),
    )
    # Create index
    op.create_index(
        "idx_skill_ontology_core_skill",
        "skill_ontology",
        ["core_skill"],
    )


def downgrade() -> None:
    # Drop index
    op.drop_index("idx_skill_ontology_core_skill", table_name="skill_ontology")
    # Drop table
    op.drop_table("skill_ontology")
