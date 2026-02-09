"""placeholder_migration_keep_in_sync

Revision ID: 20260204_placeholder
Revises: 0203_jd_certs
Create Date: 2026-02-04 15:30:00.000000

This migration is a placeholder to mark the current head of the migration chain.
All required tables (skill_ontology, jd_certification_requirements) are already
created by migrations 0203_ontology and 0203_jd_certs respectively.
Seed data files can now be loaded.

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260204_placeholder"
down_revision: Union[str, None] = "20260204_add_id_to_cert_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This migration is a placeholder - all tables already exist
    # created by previous migrations: 0203_ontology and 0203_jd_certs
    pass


def downgrade() -> None:
    # No changes to rollback
    pass

