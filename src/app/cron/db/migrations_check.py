"""Database migration version checker for ingestion service."""

from typing import Tuple
from sqlalchemy import text
from sqlalchemy.engine import Engine
from app.cron.utils.logging import get_correlation_id
import structlog

logger = structlog.get_logger(__name__)

# Expected migration revision for ingestion service
# This represents the minimum revision that guarantees ingestion tables exist.
EXPECTED_REVISION = "ba97cf8e4fdf"
EXPECTED_REVISION_SHORT = "0002"

# Acceptable revisions (includes merge and newer revisions that contain the expected revision)
ACCEPTABLE_REVISIONS = {
    "ba97cf8e4fdf",  # Direct revision with ingestion tables
    "045d300d07a8",  # Merge revision that includes ba97cf8e4fdf
    "937cc5c69c28",  # Feedback table
    "20260305_01",   # Rename skill_certification -> team_member_skill_certification
    "20260305_02",   # Add status/error_message to llm_request_log
    "20260305_03",   # Fix skill_ontology PK to id
    "20260305_04",   # Fix jd_certification_requirements PK to id
    "20260305_05",   # Seed auth_clients with default dev client (current head)
}


class SchemaMismatchError(Exception):
    """Raised when database schema version doesn't match expected version."""

    pass


def get_migration_info(engine: Engine) -> Tuple[str, str]:
    """
    Get current Alembic migration version from database.

    Args:
        engine: SQLAlchemy engine connected to the database

    Returns:
        Tuple of (full_revision, short_version)
            full_revision: Full Alembic revision ID (e.g., "ba97cf8e4fdf")
            short_version: Short version number (e.g., "0002")

    Raises:
        RuntimeError: If alembic_version table doesn't exist
    """
    correlation_id = get_correlation_id()

    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version_num = result.scalar()

            if version_num is None:
                raise RuntimeError("No version found in alembic_version table")

            logger.info(
                "Retrieved migration info",
                correlation_id=correlation_id,
                full_revision=version_num,
            )

            # Extract short version from revision history
            # Known milestones in migration sequence:
            #   None -> e8a217c84204 (0001)
            #        -> ba97cf8e4fdf (0002, ingestion tables)
            #        -> 045d300d07a8 (0002-merge, merges ingestion + other branch)
            #        -> 937cc5c69c28 (0003, current head with feedback table)
            revision_map = {
                "e8a217c84204": "0001",
                "ba97cf8e4fdf": "0002",
                "045d300d07a8": "0002-merge",
                "937cc5c69c28": "0003",
                "20260305_01": "0004",
                "20260305_02": "0005",
                "20260305_03": "0006",
                "20260305_04": "0007",
                "20260305_05": "0008",
            }
            short_version = revision_map.get(version_num, "unknown")

            return version_num, short_version

    except Exception as e:
        logger.error(
            "Failed to get migration info",
            correlation_id=correlation_id,
            error=str(e),
        )
        raise


def validate_schema_version(engine: Engine, strict: bool = True) -> bool:
    """
    Validate that the database schema version matches expected version.

    Args:
        engine: SQLAlchemy engine connected to the database
        strict: If True, raise exception on mismatch. If False, return False.

    Returns:
        True if schema version matches, False if mismatch (when strict=False)

    Raises:
        SchemaMismatchError: If schema version doesn't match (when strict=True)
        RuntimeError: If unable to check schema version
    """
    correlation_id = get_correlation_id()

    try:
        full_revision, short_version = get_migration_info(engine)

        if full_revision in ACCEPTABLE_REVISIONS:
            logger.info(
                "Schema version validated successfully",
                correlation_id=correlation_id,
                revision=full_revision,
                short_version=short_version,
            )
            return True

        # Version mismatch
        error_msg = (
            f"Schema version mismatch: expected one of {ACCEPTABLE_REVISIONS}, "
            f"found '{full_revision}' ({short_version})"
        )

        logger.error(
            "Schema version mismatch",
            correlation_id=correlation_id,
            expected_revision=EXPECTED_REVISION,
            expected_short=EXPECTED_REVISION_SHORT,
            actual_revision=full_revision,
            actual_short=short_version,
        )

        if strict:
            raise SchemaMismatchError(error_msg)

        return False

    except SchemaMismatchError:
        raise
    except Exception as e:
        logger.error(
            "Failed to validate schema version",
            correlation_id=correlation_id,
            error=str(e),
        )
        raise RuntimeError(f"Failed to validate schema version: {e}") from e
