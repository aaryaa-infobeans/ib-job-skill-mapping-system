"""fix skill_ontology primary key to use id column

Revision ID: 20260305_03
Revises: 20260305_02
Create Date: 2026-03-05 10:02:00.000000

Aligns the Docker schema with production:
- Creates skill_ontology_id_seq sequence
- Makes id column NOT NULL with sequence default
- Moves primary key from core_skill to id
- Keeps unique constraint on core_skill (already created by 20260204_add_id_to_cert_tables)

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260305_03"
down_revision: Union[str, None] = "20260305_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create the sequence
    op.execute(
        "CREATE SEQUENCE IF NOT EXISTS skill_ontology_id_seq "
        "AS integer START WITH 1 INCREMENT BY 1 NO MINVALUE NO MAXVALUE CACHE 1"
    )

    # 2. Backfill any NULL id values with the sequence
    op.execute(
        "UPDATE skill_ontology SET id = nextval('skill_ontology_id_seq') WHERE id IS NULL"
    )

    # 3. Set the default and NOT NULL
    op.execute(
        "ALTER TABLE skill_ontology "
        "ALTER COLUMN id SET DEFAULT nextval('skill_ontology_id_seq'::regclass)"
    )
    op.alter_column("skill_ontology", "id", existing_type=sa.Integer(), nullable=False)

    # 4. Own the sequence to the column
    op.execute(
        "ALTER SEQUENCE skill_ontology_id_seq OWNED BY skill_ontology.id"
    )

    # 5. Drop the old primary key on core_skill
    op.drop_constraint("skill_ontology_pkey", "skill_ontology", type_="primary")

    # 6. Create new primary key on id
    op.create_primary_key("skill_ontology_pkey", "skill_ontology", ["id"])


def downgrade() -> None:
    # Reverse: put PK back on core_skill
    op.drop_constraint("skill_ontology_pkey", "skill_ontology", type_="primary")
    op.create_primary_key("skill_ontology_pkey", "skill_ontology", ["core_skill"])

    # Make id nullable again, remove default
    op.alter_column("skill_ontology", "id", existing_type=sa.Integer(), nullable=True)
    op.execute("ALTER TABLE skill_ontology ALTER COLUMN id DROP DEFAULT")

    # Drop sequence
    op.execute("DROP SEQUENCE IF EXISTS skill_ontology_id_seq")
