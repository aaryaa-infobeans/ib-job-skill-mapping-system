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
from dotenv import load_dotenv as _load_dotenv
_load_dotenv()  # populate os.environ from .env so PII config and other os.getenv() callers work
from sqlalchemy.engine import Engine
from sqlalchemy import text

from app.cron.db.engine import create_ingestion_engine
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

    # CR-EMB-002: subcommands (TASK-EMB-034)
    subparsers = parser.add_subparsers(dest="subcommand")

    embed_parser = subparsers.add_parser(
        "embed",
        help="Run embedding phase only (does not re-ingest team data)",
    )
    embed_parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Re-embed all members even if content hash unchanged",
    )

    ingest_embed_parser = subparsers.add_parser(
        "ingest-embed",
        help="Run ingest phase then embed phase (separate transactions)",
    )
    ingest_embed_parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Re-embed all members after ingestion",
    )

    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Run ingest phase only — fetch and persist team member data, skip embedding",
    )
    ingest_parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Re-ingest all members regardless of existing batch state",
    )

    embed_member_parser = subparsers.add_parser(
        "embed-member",
        help="Re-run embedding for a single team member (by team_member_id)",
    )
    embed_member_parser.add_argument(
        "--member-id",
        required=True,
        metavar="TEAM_MEMBER_ID",
        help="team_member_id of the record to re-embed",
    )
    embed_member_parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Re-embed even if content hash unchanged",
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
            conn.execute(text("SELECT 1"))
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
    
    Fetches all batches from the external API and processes them sequentially.
    
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
        # Fetch first batch to get total batch count
        first_payload = await api_client.fetch_team_members(page=1)
        
        if not first_payload:
            logger.warning(
                "No data received from API",
                correlation_id=correlation_id
            )
            return EXIT_SUCCESS
        
        # Extract pagination metadata
        metadata = first_payload.get("metadata", {})
        total_batches = metadata.get("total_batches", 1)
        first_batch_number = metadata.get("batch_number", 1)

        logger.info(
            "Discovered batch pagination",
            correlation_id=correlation_id,
            total_batches=total_batches
        )

        # Process first batch
        successful, failed = await batch_processor.process_all_batches(first_payload)
        all_successful = list(successful)
        all_failed = list(failed)

        # Track seen batch_numbers to detect API cycling (source API bug where
        # total_batches > actual unique batches and batch_number resets mid-run).
        seen_batch_numbers = {first_batch_number}

        # Fetch and process remaining batches
        for page in range(2, total_batches + 1):
            logger.info(
                "Fetching next batch",
                correlation_id=correlation_id,
                page=page,
                total_batches=total_batches
            )

            try:
                payload = await api_client.fetch_team_members(page=page)

                if payload:
                    page_batch_number = payload.get("metadata", {}).get("batch_number")
                    if page_batch_number in seen_batch_numbers:
                        logger.warning(
                            "API cycling detected: batch_number already seen, stopping early",
                            correlation_id=correlation_id,
                            page=page,
                            batch_number=page_batch_number,
                            unique_batches_fetched=len(seen_batch_numbers),
                        )
                        break
                    seen_batch_numbers.add(page_batch_number)

                    successful, failed = await batch_processor.process_all_batches(payload)
                    all_successful.extend(successful)
                    all_failed.extend(failed)
                else:
                    logger.warning(
                        "Empty payload received",
                        correlation_id=correlation_id,
                        page=page
                    )

            except Exception as error:
                logger.error(
                    "Failed to fetch/process batch",
                    correlation_id=correlation_id,
                    page=page,
                    error=str(error)
                )
                all_failed.append(f"page_{page}")
        
        logger.info(
            "Batch ingestion completed",
            correlation_id=correlation_id,
            successful_count=len(all_successful),
            failed_count=len(all_failed),
            total_batches=total_batches,
            dry_run=dry_run
        )
        
        if all_failed:
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
        engine = create_ingestion_engine()
        
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
        log_level=args.log_level,
        subcommand=getattr(args, "subcommand", None),
    )

    # CR-EMB-002: embed / ingest-embed / ingest subcommands
    if getattr(args, "subcommand", None) == "embed":
        return _run_embed_phase(args, correlation_id)
    if getattr(args, "subcommand", None) == "ingest-embed":
        return _run_ingest_embed(args, correlation_id)
    if getattr(args, "subcommand", None) == "ingest":
        return _run_ingest_phase(args, correlation_id)
    if getattr(args, "subcommand", None) == "embed-member":
        return _run_embed_member(args, correlation_id)

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




# ---------------------------------------------------------------------------
# CR-EMB-002: embed phase helpers (TASK-EMB-034)
# ---------------------------------------------------------------------------


def _run_embed_phase(args, correlation_id: str) -> int:
    """
    Run the embedding phase only.
    Uses a sync SQLAlchemy session (not the async ingestion path).
    """
    from sqlalchemy.orm import Session
    from app.cron.db.engine import create_ingestion_engine
    from app.cron.embedding.mcp_client import MCPResumeClient
    from app.cron.embedding.embedding_processor import EmbeddingProcessor
    from app.ai.utils.gemma_embedding import GemmaEmbeddingAgent
    from app.settings import settings

    force = getattr(args, "force", False)
    logger.info("Starting embed phase", correlation_id=correlation_id, force=force)

    engine = create_ingestion_engine()
    try:
        with Session(engine) as db:
            mcp_client = MCPResumeClient(
                server_script=settings.mcp_gdrive_server_path,
                sa_key_path=settings.google_service_account_file,
            )
            embedding_agent = GemmaEmbeddingAgent(
                device=settings.embedding_device,
                model_name=settings.gemma_model_path or None,
            )
            processor = EmbeddingProcessor(
                db=db, mcp_client=mcp_client, embedding_agent=embedding_agent
            )
            result = processor.run(force=force)
            logger.info(
                "Embed phase complete",
                correlation_id=correlation_id,
                success=result.success_count,
                skipped=result.skip_count,
                errors=result.error_count,
            )
        if result.error_count > 0 and result.success_count == 0:
            return EXIT_FATAL_ERROR
        if result.error_count > 0:
            return EXIT_PARTIAL_SUCCESS
        return EXIT_SUCCESS
    except Exception as exc:
        logger.error(
            "Embed phase fatal error",
            correlation_id=correlation_id,
            error=str(exc),
            exc_info=True,
        )
        return EXIT_FATAL_ERROR
    finally:
        engine.dispose()


def _run_ingest_embed(args, correlation_id: str) -> int:
    """
    Run ingest phase first (committed), then embed phase (separate transaction).
    MCP crash during embed MUST NOT roll back ingestion data.
    """
    import asyncio

    # Step 1: ingest (existing async path)
    ingest_code = asyncio.run(main_async(args, correlation_id))
    if ingest_code == EXIT_FATAL_ERROR:
        logger.error(
            "Ingest phase failed; skipping embed phase",
            correlation_id=correlation_id,
        )
        return ingest_code

    # Step 2: embed (separate transaction)
    embed_code = _run_embed_phase(args, correlation_id)
    if ingest_code == EXIT_SUCCESS and embed_code == EXIT_SUCCESS:
        return EXIT_SUCCESS
    if embed_code == EXIT_FATAL_ERROR:
        return EXIT_PARTIAL_SUCCESS  # ingest succeeded; embed failed partially
    return EXIT_PARTIAL_SUCCESS

def _run_ingest_phase(args, correlation_id: str) -> int:
    """
    Run the ingest phase only — fetches team member data and persists it.
    Embedding is skipped entirely.

    Supports --force to re-ingest all members regardless of existing batch state.
    """
    import asyncio

    force = getattr(args, "force", False)
    logger.info("Starting ingest-only phase", correlation_id=correlation_id, force=force)

    try:
        exit_code = asyncio.run(main_async(args, correlation_id))
    except KeyboardInterrupt:
        logger.warning("Interrupted by user", correlation_id=correlation_id)
        exit_code = EXIT_FATAL_ERROR
    except Exception as exc:
        logger.error(
            "Ingest phase fatal error",
            correlation_id=correlation_id,
            error=str(exc),
            exc_info=True,
        )
        exit_code = EXIT_FATAL_ERROR

    logger.info(
        "Ingest-only phase complete",
        correlation_id=correlation_id,
        exit_code=exit_code,
    )
    return exit_code


def _run_embed_member(args, correlation_id: str) -> int:
    """
    Re-run the embedding pipeline for a single team member.
    Uses the same sync session path as _run_embed_phase.
    """
    from sqlalchemy.orm import Session
    from app.cron.db.engine import create_ingestion_engine
    from app.cron.embedding.mcp_client import MCPResumeClient
    from app.cron.embedding.embedding_processor import EmbeddingProcessor
    from app.ai.utils.gemma_embedding import GemmaEmbeddingAgent
    from app.settings import settings

    member_id = args.member_id
    force = getattr(args, "force", False)
    logger.info(
        "Starting single-member embed",
        correlation_id=correlation_id,
        member_id=member_id,
        force=force,
    )

    engine = create_ingestion_engine()
    try:
        with Session(engine) as db:
            mcp_client = MCPResumeClient(
                server_script=settings.mcp_gdrive_server_path,
                sa_key_path=settings.google_service_account_file,
            )
            embedding_agent = GemmaEmbeddingAgent(
                device=settings.embedding_device,
                model_name=settings.gemma_model_path or None,
            )
            processor = EmbeddingProcessor(
                db=db, mcp_client=mcp_client, embedding_agent=embedding_agent
            )
            result = processor.run_single(member_id=member_id, force=force)
            logger.info(
                "Single-member embed complete",
                correlation_id=correlation_id,
                member_id=member_id,
                success=result.success_count,
                skipped=result.skip_count,
                errors=result.error_count,
            )
        if result.error_count > 0:
            return EXIT_FATAL_ERROR
        return EXIT_SUCCESS
    except Exception as exc:
        logger.error(
            "Single-member embed fatal error",
            correlation_id=correlation_id,
            member_id=member_id,
            error=str(exc),
            exc_info=True,
        )
        return EXIT_FATAL_ERROR
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
