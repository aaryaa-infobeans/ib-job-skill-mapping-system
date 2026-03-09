"""Alembic environment configuration.

This module is intentionally lightweight and avoids importing the full
application settings to prevent pydantic validation errors during
`alembic` CLI usage in minimally configured environments. It resolves the
database URL directly via the secrets helper or `DATABASE_URL`.
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Ensure the project src/ directory is on sys.path so `app.*` imports work
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
SRC_PATH = os.path.join(PROJECT_ROOT, "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

# Import the Base and secrets helper
from app.db.base import Base
from app.secrets import get_secret

# Import all models so they're registered with Base.metadata
import app.db.models  # noqa: F401

# this is the Alembic Config object
config = context.config


def _resolve_database_url() -> str:
    """Resolve database URL for Alembic migrations.

    Tries secrets manager keys first, then falls back to the
    `DATABASE_URL` environment variable. This mirrors the logic in
    `Settings.get_database_url` without requiring the Settings model.
    """

    db_url = get_secret("DB_URL") or get_secret("DATABASE_URL") or os.getenv(
        "DATABASE_URL"
    )

    if not db_url:
        # Fallback to connection parameters commonly used in local dev
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5433")
        name = os.getenv("DB_NAME", "ib_job_skill_mapping")
        user = os.getenv("DB_USER", "user")
        password = os.getenv("DB_PASSWORD", "password")
        db_url = f"postgresql://{user}:{password}@{host}:{port}/{name}"

    return db_url


# Set the sqlalchemy.url from resolved database URL
config.set_main_option("sqlalchemy.url", _resolve_database_url())

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
