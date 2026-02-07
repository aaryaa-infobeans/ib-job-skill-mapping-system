"""
CLI entry point for nightly batch ingestion system.

Provides command-line interface with retry support, dry-run mode,
and comprehensive pre-run health checks.
"""

import argparse
import sys
import uuid
from typing import Optional
import structlog
from sqlalchemy.engine import Engine

from app.cron.db.engine import create_engine
from app.cron.db.migrations_check import validate_schema_version, SchemaMismatchError
from app.cron.oauth.token_client import OAuthClient
from app.cron.api.external_client import TeamDataClient
from app.cron.processing.batch_processor import BatchProcessor
from app.cron.processing.retry_manager import RetryManager
from app.cron.db.repositories import BatchStateRepository
from app.cron.utils.logging import configure_logging, set_correlation_id


logger = structlog.get_logger(__name__)


# Exit codes
EXIT_SUCCESS = 0
EXIT_PARTIAL_SUCCESS = 1
EXIT_FATAL_ERROR = 2
EXIT_SCHEMA_MISMATCH = 3
EXIT_AUTHENTICATION_FAILED = 4


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Nightly batch ingestion system for team member data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exit Codes:
  0 - SUCCESS: All batches processed successfully
  1 - PARTIAL_SUCCESS: Some batches failed
  2 - FATAL_ERROR: Fatal error preventing execution
  3 - SCHEMA_VERSION_MISMATCH: Database schema mismatch
  4 - AUTHENTICATION_FAILED: OAuth authentication failed

Examples:
  # Normal ingestion
  python -m app.cron.main
  
  # Retry failed batches
  python -m app.cron.main --retry-failed
  
  # Dry run mode
  python -m app.cron.main --dry-run --log-level DEBUG
        """
    )
    
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Retry failed batches only (do not fetch new data)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode (validate without committing changes)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    return parser.parse_args()


def pre_run_checks(engine: Engine, oauth_client: OAuthClient, correlation_id: str) -> bool:
    """
    Execute pre-flight health checks.
    
    Checks:
    1. Database connection
    2. Schema version validation
    3. OAuth authentication
    
    Args:
        engine: SQLAlchemy engine
        oauth_client: OAuth client for authentication
        correlation_id: Correlation ID for tracing
    
    Returns:
        True if all checks pass, False otherwise
    
    Raises:
        SchemaMismatchError: If schema version doesn't match
        Exception: For other critical errors
    """
    logger.info("Starting pre-run health checks", correlation_id=correlation_id)
    
    # Check 1: Database connection
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info(
            "Database connection check passed",
            correlation_id=correlation_id
        )
    except Exception as error:
        logger.error(
            "Database connection check failed",
            correlation_id=correlation_id,
            error=str(error)
        )
        raise
    
    # Check 2: Schema version
    try:
        validate_schema_version(engine)
        logger.info(
            "Schema version check passed",
            correlation_id=correlation_id
        )
    except SchemaMismatchError as error:
        logger.error(
            "Schema version mismatch",
            correlation_id=correlation_id,
            error=str(error)
        )
        raise
    
    # Check 3: OAuth authentication
    try:
        token = oauth_client.get_access_token()
        if not token:
            raise ValueError("Failed to obtain access token")
        logger.info(
            "OAuth authentication check passed",
            correlation_id=correlation_id
        )
    except Exception as error:
        logger.error(
            "OAuth authentication check failed",
            correlation_id=correlation_id,
            error=str(error)
        )
        raise
    
    logger.info(
        "All pre-run checks passed",
        correlation_id=correlation_id
    )
    return True


async def run_ingestion(
    api_client: TeamDataClient,
    batch_processor: BatchProcessor,
    correlation_id: str,
    dry_run: bool = False
) -> int:
    """
    Run new batch ingestion from external API.
    
    Args:
        api_client: Team data API client
        batch_processor: Batch processor instance
        correlation_id: Correlation ID for tracing
        dry_run: If True, validate without committing
    
    Returns:
        Exit code (0=success, 1=partial success, 2=fatal error)
    """
    logger.info(
        "Starting new batch ingestion",
        correlation_id=correlation_id,
        dry_run=dry_run
    )
    
    try:
        # Fetch team member data from API
        payload = await api_client.fetch_team_members()
        
        if not payload:
            logger.warning(
                "No data received from API",
                correlation_id=correlation_id
            )
            return EXIT_SUCCESS
        
        # Process all batches
        successful, failed = await batch_processor.process_all_batches(payload)
        
        logger.info(
            "Batch ingestion completed",
            correlation_id=correlation_id,
            successful_count=len(successful),
            failed_count=len(failed),
            dry_run=dry_run
        )
        
        if failed:
            return EXIT_PARTIAL_SUCCESS
        
        return EXIT_SUCCESS
    
    except Exception as error:
        logger.error(
            "Fatal error during ingestion",
            correlation_id=correlation_id,
            error=str(error),
            error_type=type(error).__name__
        )
        return EXIT_FATAL_ERROR


async def run_retry(
    retry_manager: RetryManager,
    batch_processor: BatchProcessor,
    api_client: TeamDataClient,
    correlation_id: str
) -> int:
    """
    Retry failed batches.
    
    Args:
        retry_manager: Retry manager instance
        batch_processor: Batch processor instance
        api_client: API client for fetching fresh data
        correlation_id: Correlation ID for tracing
    
    Returns:
        Exit code (0=success, 1=partial success, 2=fatal error)
    """
    logger.info(
        "Starting failed batch retry",
        correlation_id=correlation_id
    )
    
    try:
        # Retry all eligible failed batches
        successful, failed = await retry_manager.retry_failed_batches(
            batch_processor=batch_processor,
            api_client=api_client,
            correlation_id=correlation_id
        )
        
        logger.info(
            "Batch retry completed",
            correlation_id=correlation_id,
            successful_count=len(successful),
            failed_count=len(failed)
        )
        
        if failed:
            return EXIT_PARTIAL_SUCCESS
        
        return EXIT_SUCCESS
    
    except Exception as error:
        logger.error(
            "Fatal error during retry",
            correlation_id=correlation_id,
            error=str(error),
            error_type=type(error).__name__
        )
        return EXIT_FATAL_ERROR


async def main_async(args: argparse.Namespace, correlation_id: str) -> int:
    """
    Main async execution logic.
    
    Args:
        args: Parsed command line arguments
        correlation_id: Correlation ID for tracing
    
    Returns:
        Exit code
    """
    engine: Optional[Engine] = None
    
    try:
        # Create database engine
        engine = create_engine()
        
        # Initialize OAuth client
        oauth_client = OAuthClient()
        
        # Pre-run checks
        try:
            pre_run_checks(engine, oauth_client, correlation_id)
        except SchemaMismatchError:
            return EXIT_SCHEMA_MISMATCH
        except Exception as error:
            if "auth" in str(error).lower():
                return EXIT_AUTHENTICATION_FAILED
            return EXIT_FATAL_ERROR
        
        # Initialize API client
        api_client = TeamDataClient(oauth_client=oauth_client)
        
        # Create async session and components
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        
        async_engine = create_async_engine(
            engine.url.render_as_string(hide_password=False).replace("postgresql://", "postgresql+asyncpg://"),
            echo=False
        )
        
        async_session_maker = sessionmaker(
            async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        async with async_session_maker() as session:
            batch_processor = BatchProcessor(session, dry_run=args.dry_run)
            
            if args.retry_failed:
                # Retry mode
                retry_manager = RetryManager(session, max_retries=3, base_delay=60)
                exit_code = await run_retry(
                    retry_manager=retry_manager,
                    batch_processor=batch_processor,
                    api_client=api_client,
                    correlation_id=correlation_id
                )
            else:
                # Normal ingestion mode
                exit_code = await run_ingestion(
                    api_client=api_client,
                    batch_processor=batch_processor,
                    correlation_id=correlation_id,
                    dry_run=args.dry_run
                )
        
        await async_engine.dispose()
        
        return exit_code
    
    finally:
        if engine:
            engine.dispose()


def main() -> int:
    """
    Main entry point for CLI.
    
    Returns:
        Exit code
    """
    # Parse arguments
    args = parse_args()
    
    # Configure logging
    configure_logging(log_level=args.log_level)
    
    # Generate correlation ID
    correlation_id = str(uuid.uuid4())
    set_correlation_id(correlation_id)
    
    logger.info(
        "Batch ingestion system starting",
        correlation_id=correlation_id,
        retry_mode=args.retry_failed,
        dry_run=args.dry_run,
        log_level=args.log_level
    )
    
    # Run async main
    import asyncio
    try:
        exit_code = asyncio.run(main_async(args, correlation_id))
    except KeyboardInterrupt:
        logger.warning(
            "Interrupted by user",
            correlation_id=correlation_id
        )
        exit_code = EXIT_FATAL_ERROR
    except Exception as error:
        logger.error(
            "Unexpected error",
            correlation_id=correlation_id,
            error=str(error),
            error_type=type(error).__name__
        )
        exit_code = EXIT_FATAL_ERROR
    
    logger.info(
        "Batch ingestion system exiting",
        correlation_id=correlation_id,
        exit_code=exit_code
    )
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
