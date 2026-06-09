"""Add pg_bm25 (ParadeDB) index on team_member_embeddings for true BM25 keyword search.

Revision ID: 20260519_01
Revises: 20260403_01
Create Date: 2026-05-19

Creates a BM25 inverted index over skills_text, certifications_text, and profile_text
on team_member_embeddings. Enables true Okapi BM25 retrieval via the pg_search extension
(ParadeDB) as the keyword path in hybrid search — replacing ts_rank TF-only scoring.
"""
from alembic import op

revision = '20260519_01'
down_revision = '20260403_01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_search;")
    op.execute("""
        CREATE INDEX idx_tme_bm25 ON team_member_embeddings
        USING bm25 (id, skills_text, certifications_text, profile_text)
        WITH (key_field='id');
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_tme_bm25;")
    op.execute("DROP EXTENSION IF EXISTS pg_search;")
