"""add team_member_embeddings table

Revision ID: 20260203_add_team_member_embeddings
Revises: e8a217c84204
Create Date: 2026-02-03 17:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0203_embeddings"
down_revision: Union[str, None] = "e8a217c84204"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure pgvector extension exists
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # Create team_member_embeddings table using raw SQL
    op.execute("""
    CREATE TABLE team_member_embeddings (
        id UUID DEFAULT gen_random_uuid() NOT NULL,
        team_member_id VARCHAR(50) NOT NULL,
        embedding VECTOR(3072) NOT NULL,
        profile_text TEXT,
        metadata JSON,
        created_at TIMESTAMP DEFAULT NOW() NOT NULL,
        PRIMARY KEY (id),
        FOREIGN KEY (team_member_id) REFERENCES team_member(team_member_id)
    )
    """)
    
    # Create indexes
    op.execute(
        "CREATE INDEX idx_team_member_embeddings_team_member_id ON team_member_embeddings(team_member_id)"
    )
    op.execute(
        "CREATE INDEX idx_team_member_embeddings_created_at ON team_member_embeddings(created_at)"
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index(
        "idx_team_member_embeddings_created_at", table_name="team_member_embeddings"
    )
    op.drop_index(
        "idx_team_member_embeddings_team_member_id",
        table_name="team_member_embeddings",
    )
    # Drop table
    op.drop_table("team_member_embeddings")
