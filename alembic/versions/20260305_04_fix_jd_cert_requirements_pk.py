"""fix jd_certification_requirements primary key to use id column

Revision ID: 20260305_04
Revises: 20260305_03
Create Date: 2026-03-05 10:03:00.000000

Aligns the Docker schema with production:
- Creates jd_certification_requirements_id_seq sequence
- Makes id column NOT NULL with sequence default
- Moves primary key from (jd_type, certification) to id
- Renames unique constraint to uq_jd_cert_combo (matches production)

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260305_04"
down_revision: Union[str, None] = "20260305_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create the sequence
    op.execute(
        "CREATE SEQUENCE IF NOT EXISTS jd_certification_requirements_id_seq "
        "AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1"
    )

    # 2. Backfill any NULL id values with the sequence
    op.execute(
        "UPDATE jd_certification_requirements "
        "SET id = nextval('jd_certification_requirements_id_seq') WHERE id IS NULL"
    )

    # 3. Set the default and NOT NULL
    op.execute(
        "ALTER TABLE jd_certification_requirements "
        "ALTER COLUMN id SET DEFAULT nextval('jd_certification_requirements_id_seq'::regclass)"
    )
    op.alter_column(
        "jd_certification_requirements", "id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    # 4. Own the sequence to the column
    op.execute(
        "ALTER SEQUENCE jd_certification_requirements_id_seq "
        "OWNED BY jd_certification_requirements.id"
    )

    # 5. Drop the old composite primary key on (jd_type, certification)
    op.drop_constraint(
        "jd_certification_requirements_pkey",
        "jd_certification_requirements",
        type_="primary",
    )

    # 6. Create new primary key on id
    op.create_primary_key(
        "jd_certification_requirements_pkey",
        "jd_certification_requirements",
        ["id"],
    )

    # 7. Rename the unique constraint to match production
    #    (uq_jd_cert_jd_type_certification -> uq_jd_cert_combo)
    op.drop_constraint(
        "uq_jd_cert_jd_type_certification",
        "jd_certification_requirements",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_jd_cert_combo",
        "jd_certification_requirements",
        ["jd_type", "certification"],
    )


def downgrade() -> None:
    # Reverse unique constraint rename
    op.drop_constraint(
        "uq_jd_cert_combo",
        "jd_certification_requirements",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_jd_cert_jd_type_certification",
        "jd_certification_requirements",
        ["jd_type", "certification"],
    )

    # Reverse PK change
    op.drop_constraint(
        "jd_certification_requirements_pkey",
        "jd_certification_requirements",
        type_="primary",
    )
    op.create_primary_key(
        "jd_certification_requirements_pkey",
        "jd_certification_requirements",
        ["jd_type", "certification"],
    )

    # Make id nullable again, remove default
    op.alter_column(
        "jd_certification_requirements", "id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.execute(
        "ALTER TABLE jd_certification_requirements ALTER COLUMN id DROP DEFAULT"
    )

    # Drop sequence
    op.execute("DROP SEQUENCE IF EXISTS jd_certification_requirements_id_seq")
