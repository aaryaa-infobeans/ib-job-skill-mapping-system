"""Database engine factory for ingestion service."""

from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
from app.cron.config import settings
from app.cron.db.migrations_check import validate_schema_version
from app.cron.utils.logging import get_correlation_id
import structlog

logger = structlog.get_logger(__name__)

# Global engine instance (singleton pattern)
_engine: Optional[Engine] = None


def create_ingestion_engine(
    validate_schema: bool = True,
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_pre_ping: bool = True,
    pool_recycle: int = 3600,
) -> Engine:
    """
    Create SQLAlchemy engine for ingestion service with connection pooling.

    Args:
        validate_schema: If True, validate schema version before returning engine
        pool_size: Number of connections to maintain in the pool (default: 5)
        max_overflow: Max connections above pool_size (default: 10)
        pool_pre_ping: Test connections before using (default: True)
        pool_recycle: Recycle connections after N seconds (default: 3600)

    Returns:
        Configured SQLAlchemy Engine instance

    Raises:
        SchemaMismatchError: If schema validation fails
        RuntimeError: If engine creation fails
    """
    correlation_id = get_correlation_id()

    try:
        logger.info(
            "Creating ingestion database engine",
            correlation_id=correlation_id,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=pool_pre_ping,
            pool_recycle=pool_recycle,
        )

        engine = create_engine(
            settings.database_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=pool_pre_ping,
            pool_recycle=pool_recycle,
            echo=False,  # Set to True for SQL logging
        )

        logger.info(
            "Database engine created successfully",
            correlation_id=correlation_id,
        )

        # Validate schema version if requested
        if validate_schema:
            validate_schema_version(engine, strict=True)
            logger.info(
                "Schema validation passed",
                correlation_id=correlation_id,
            )

        return engine

    except Exception as e:
        logger.error(
            "Failed to create database engine",
            correlation_id=correlation_id,
            error=str(e),
        )
        raise RuntimeError(f"Failed to create database engine: {e}") from e


def get_engine(recreate: bool = False) -> Engine:
    """
    Get or create the global ingestion database engine (singleton).

    Args:
        recreate: If True, dispose existing engine and create new one

    Returns:
        SQLAlchemy Engine instance
    """
    global _engine

    if recreate and _engine is not None:
        logger.info("Disposing existing engine")
        _engine.dispose()
        _engine = None

    if _engine is None:
        _engine = create_ingestion_engine()

    return _engine


def test_connection(engine: Optional[Engine] = None) -> bool:
    """
    Test database connection by executing a simple query.

    Args:
        engine: SQLAlchemy engine to test. If None, uses global engine.

    Returns:
        True if connection successful, False otherwise
    """
    correlation_id = get_correlation_id()

    if engine is None:
        engine = get_engine()

    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            value = result.scalar()

            if value == 1:
                logger.info(
                    "Database connection test successful",
                    correlation_id=correlation_id,
                )
                return True

            logger.warning(
                "Database connection test returned unexpected value",
                correlation_id=correlation_id,
                value=value,
            )
            return False

    except Exception as e:
        logger.error(
            "Database connection test failed",
            correlation_id=correlation_id,
            error=str(e),
        )
        return False


def dispose_engine() -> None:
    """Dispose the global database engine and clean up connections."""
    global _engine

    if _engine is not None:
        correlation_id = get_correlation_id()
        logger.info(
            "Disposing database engine",
            correlation_id=correlation_id,
        )
        _engine.dispose()
        _engine = None
