"""Add role_ontology table

Maps canonical role names to internal profile_type codes, role aliases,
and domain-specific enriched terms. Mirrors the pattern of skill_ontology
but for roles rather than skills.

Revision ID: 20260604_01
Revises: 20260601_01
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260604_01"
down_revision: str = "20260601_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "role_ontology",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("canonical_role", sa.String(100), nullable=False),
        sa.Column("profile_type", sa.String(100), nullable=False),
        sa.Column(
            "aliases",
            postgresql.ARRAY(sa.Text),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "enriched_terms",
            postgresql.ARRAY(sa.Text),
            nullable=False,
            server_default="{}",
        ),
    )
    op.create_index("idx_role_ontology_canonical_role", "role_ontology", ["canonical_role"], unique=True)
    op.create_index("idx_role_ontology_profile_type", "role_ontology", ["profile_type"])


def downgrade() -> None:
    op.drop_index("idx_role_ontology_profile_type", table_name="role_ontology")
    op.drop_index("idx_role_ontology_canonical_role", table_name="role_ontology")
    op.drop_table("role_ontology")
