"""Add id fields to certification tables

Revision ID: 20260204_add_id_to_cert_tables
Revises: 0203_jd_certs
Create Date: 2026-02-04 15:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260204_add_id_to_cert_tables"
down_revision: Union[str, None] = "0203_jd_certs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add id column to skill_ontology
    op.add_column(
        "skill_ontology",
        sa.Column("id", sa.Integer(), nullable=True, autoincrement=True),
    )
    
    # Create a unique constraint on core_skill if it doesn't exist
    op.create_unique_constraint(
        "uq_skill_ontology_core_skill",
        "skill_ontology",
        ["core_skill"],
    )
    
    # Add id column to jd_certification_requirements
    op.add_column(
        "jd_certification_requirements",
        sa.Column("id", sa.Integer(), nullable=True, autoincrement=True),
    )
    
    # Create a unique constraint on jd_type, certification
    op.create_unique_constraint(
        "uq_jd_cert_jd_type_certification",
        "jd_certification_requirements",
        ["jd_type", "certification"],
    )


def downgrade() -> None:
    # Drop unique constraint from jd_certification_requirements
    op.drop_constraint(
        "uq_jd_cert_jd_type_certification",
        "jd_certification_requirements",
        type_="unique",
    )
    
    # Drop id column from jd_certification_requirements
    op.drop_column("jd_certification_requirements", "id")
    
    # Drop unique constraint from skill_ontology
    op.drop_constraint(
        "uq_skill_ontology_core_skill",
        "skill_ontology",
        type_="unique",
    )
    
    # Drop id column from skill_ontology
    op.drop_column("skill_ontology", "id")
