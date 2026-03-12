"""add_multi_vector_embeddings

CR-EMB-002: Add multi-vector embedding columns to team_member_embeddings.

Linked Specs:
- Plan §4 | CR §3.2, §5.1 | AC-9 | R5

Schema Changes:
- Add 3 Vector(768) columns: resume_embedding, skills_embedding, certifications_embedding
- Add 3 Text columns: resume_text, skills_text, certifications_text
- Add String(100) column: embedding_model (server_default='embedding-gemma-300m')
- Add CHAR(64) column: content_hash (SHA-256)
- Add DateTime columns: resume_fetched_at, embedding_updated_at
- Add PII tracking: pii_scrubbed_at, scrubbed_at (already present — no duplicate)
- Create 3 IVFFlat indexes + 1 B-tree index on content_hash

Validation (DoD):
  alembic upgrade head
  alembic downgrade bca284b2d901
  alembic upgrade head    # idempotency — AC-9
"""

from alembic import op
import sqlalchemy as sa

# Alembic identifiers
revision = "emb002_multi_vec"
down_revision = "bca284b2d901"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name if bind is not None else "postgresql"

    # -----------------------------------------------------------------------
    # 1. New columns
    #    Vector columns must be added via raw SQL on PostgreSQL so the column
    #    type is `vector(768)`, not TEXT — TEXT columns reject vector_cosine_ops.
    #    On other dialects (SQLite in tests) fall back to TEXT.
    # -----------------------------------------------------------------------
    if dialect == "postgresql":
        # Migrate the legacy `embedding` column from vector(3072) → vector(768).
        # Existing 3072-dim vectors are cleared first; they will be re-populated
        # by `python -m app.cron.main embed --force` after the migration.
        op.execute(
            "UPDATE team_member_embeddings SET embedding = NULL "
            "WHERE embedding IS NOT NULL"
        )
        op.execute(
            "ALTER TABLE team_member_embeddings "
            "ALTER COLUMN embedding TYPE vector(768)"
        )
        op.execute(
            "ALTER TABLE team_member_embeddings "
            "ADD COLUMN IF NOT EXISTS resume_embedding vector(768)"
        )
        op.execute(
            "ALTER TABLE team_member_embeddings "
            "ADD COLUMN IF NOT EXISTS skills_embedding vector(768)"
        )
        op.execute(
            "ALTER TABLE team_member_embeddings "
            "ADD COLUMN IF NOT EXISTS certifications_embedding vector(768)"
        )
    else:
        for col in ("resume_embedding", "skills_embedding", "certifications_embedding"):
            op.add_column(
                "team_member_embeddings",
                sa.Column(col, sa.Text(), nullable=True),
            )

    op.add_column(
        "team_member_embeddings",
        sa.Column("resume_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "team_member_embeddings",
        sa.Column("skills_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "team_member_embeddings",
        sa.Column("certifications_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "team_member_embeddings",
        sa.Column(
            "embedding_model",
            sa.String(100),
            nullable=True,
            server_default="embedding-gemma-300m",
        ),
    )
    op.add_column(
        "team_member_embeddings",
        sa.Column("content_hash", sa.CHAR(64), nullable=True),
    )
    op.add_column(
        "team_member_embeddings",
        sa.Column("resume_fetched_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "team_member_embeddings",
        sa.Column("embedding_updated_at", sa.DateTime(), nullable=True),
    )

    # -----------------------------------------------------------------------
    # 2. Indexes — IVFFlat for vector columns; B-tree for content_hash
    # -----------------------------------------------------------------------
    if dialect == "postgresql":
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tme_resume_embedding
            ON team_member_embeddings
            USING ivfflat (resume_embedding vector_cosine_ops)
            WITH (lists = 10)
            """
        )
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tme_skills_embedding
            ON team_member_embeddings
            USING ivfflat (skills_embedding vector_cosine_ops)
            WITH (lists = 10)
            """
        )
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tme_certifications_embedding
            ON team_member_embeddings
            USING ivfflat (certifications_embedding vector_cosine_ops)
            WITH (lists = 10)
            """
        )

    # B-tree on content_hash (works in all dialects)
    op.create_index(
        "idx_tme_content_hash",
        "team_member_embeddings",
        ["content_hash"],
    )

    # Unique constraint on team_member_id — required for ON CONFLICT upsert.
    # The legacy table used `id` (UUID) as PK; we need team_member_id to be
    # unique so EmbeddingRepository.upsert_team_member_embeddings can use
    # ON CONFLICT (team_member_id) DO UPDATE.
    op.create_unique_constraint(
        "uq_tme_team_member_id",
        "team_member_embeddings",
        ["team_member_id"],
    )


def downgrade() -> None:
    # -----------------------------------------------------------------------
    # Drop indexes first, then columns (reverse of upgrade)
    # -----------------------------------------------------------------------
    bind = op.get_bind()
    dialect = bind.dialect.name if bind is not None else "postgresql"

    op.drop_index("idx_tme_content_hash", table_name="team_member_embeddings")

    if dialect == "postgresql":
        op.execute("DROP INDEX IF EXISTS idx_tme_certifications_embedding")
        op.execute("DROP INDEX IF EXISTS idx_tme_skills_embedding")
        op.execute("DROP INDEX IF EXISTS idx_tme_resume_embedding")
        # Restore legacy embedding column to its original vector(3072) type.
        # Existing 768-dim vectors are cleared first.
        op.execute(
            "UPDATE team_member_embeddings SET embedding = NULL "
            "WHERE embedding IS NOT NULL"
        )
        op.execute(
            "ALTER TABLE team_member_embeddings "
            "ALTER COLUMN embedding TYPE vector(3072)"
        )

    # Drop columns in reverse order
    op.drop_column("team_member_embeddings", "embedding_updated_at")
    op.drop_column("team_member_embeddings", "resume_fetched_at")
    op.drop_column("team_member_embeddings", "content_hash")
    op.drop_column("team_member_embeddings", "embedding_model")
    op.drop_column("team_member_embeddings", "certifications_text")
    op.drop_column("team_member_embeddings", "skills_text")
    op.drop_column("team_member_embeddings", "resume_text")
    op.drop_column("team_member_embeddings", "certifications_embedding")
    op.drop_column("team_member_embeddings", "skills_embedding")
    op.drop_column("team_member_embeddings", "resume_embedding")
