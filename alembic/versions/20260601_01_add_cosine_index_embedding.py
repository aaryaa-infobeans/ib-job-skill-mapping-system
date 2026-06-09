"""add cosine ivfflat index on team_member_embeddings.embedding

The multi-vector migration (emb002) created cosine indexes for resume_embedding,
skills_embedding, and certifications_embedding but left the main embedding column
(used for full-JD similarity) without a vector index. The retrieval SQL also
incorrectly used <-> (L2) instead of <=> (cosine) for all distance calculations,
meaning the three existing cosine indexes were never used.

This migration:
  1. Adds an IVFFlat cosine index on the main embedding column so full-JD
     similarity queries hit an index instead of doing a full table scan.

The SQL operator change (<-> → <=>) is handled in code (rag_retrieval.py).

Revision ID: 20260601_01
Revises: emb002_multi_vec
"""

from alembic import op

revision = "20260601_01"
down_revision = "emb002_multi_vec"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_tme_embedding_cosine
        ON team_member_embeddings
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 10)
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("DROP INDEX IF EXISTS idx_tme_embedding_cosine")
