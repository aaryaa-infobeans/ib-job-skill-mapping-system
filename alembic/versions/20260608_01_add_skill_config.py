"""Add skill_config table and seed keyword data

Replaces FRONTEND_KEYWORDS / BACKEND_KEYWORDS / BACKEND_AI_INDICATORS /
SKILL_GROUP_* environment variables. Update rows here to change keyword
lists at runtime without a redeploy.

Revision ID: 20260608_01
Revises: 20260604_01
Create Date: 2026-06-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260608_01"
down_revision: str = "20260604_01"
branch_labels = None
depends_on = None

_SEED_ROWS = [
    # family — used for skill-family penalty detection
    ("family", "frontend",    ["react","angular","vue","html","css","javascript","js","frontend","ui","ux"]),
    ("family", "backend",     ["python","java","scala","sql","node","backend","api","spark","snowflake","kafka","ai","ml"]),
    ("family", "backend_ai",  ["backend","ai","ml","data","python","spark","sql","snowflake"]),
    # group — used for skill-group matching / fallback text search
    ("group",  "python",      ["python","django","flask","fastapi","pandas","numpy","scikit-learn","pytorch","tensorflow"]),
    ("group",  "javascript",  ["javascript","js","typescript","ts","react","node","next.js","angular","vue","html","css"]),
    ("group",  "sql",         ["sql","postgresql","postgres","mysql","sql server","snowflake","oracle","db2"]),
    ("group",  "big_data",    ["spark","pyspark","hadoop","kafka","databricks"]),
    ("group",  "ai_ml",       ["machine learning","ai","ml","nlp","llm","genai","deep learning","computer vision"]),
    ("group",  "cloud",       ["aws","azure","gcp","docker","kubernetes","terraform"]),
]


def upgrade() -> None:
    skill_config = op.create_table(
        "skill_config",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("config_type", sa.String(20), nullable=False),
        sa.Column("config_key", sa.String(50), nullable=False),
        sa.Column(
            "keywords",
            postgresql.ARRAY(sa.Text),
            nullable=False,
            server_default="{}",
        ),
        sa.UniqueConstraint("config_type", "config_key", name="uq_skill_config_type_key"),
    )
    op.create_index("ix_skill_config_type", "skill_config", ["config_type"])

    op.bulk_insert(
        skill_config,
        [{"config_type": t, "config_key": k, "keywords": kws} for t, k, kws in _SEED_ROWS],
    )


def downgrade() -> None:
    op.drop_index("ix_skill_config_type", table_name="skill_config")
    op.drop_table("skill_config")
