"""
Unit tests for main CLI entry point.

Tests argument parsing, pre-run checks, ingestion, retry, and exit codes.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
import argparse
from sqlalchemy.exc import OperationalError

from app.cron.main import (
    parse_args,
    pre_run_checks,
    run_ingestion,
    run_retry,
    main,
    main_async,
    EXIT_SUCCESS,
    EXIT_PARTIAL_SUCCESS,
    EXIT_FATAL_ERROR,
    EXIT_SCHEMA_MISMATCH,
    EXIT_AUTHENTICATION_FAILED
)
from app.cron.db.migrations_check import SchemaMismatchError


class TestArgumentParsing:
    """Test command line argument parsing."""
    
    def test_parse_args_defaults(self):
        """Default arguments should be set correctly."""
        with patch('sys.argv', ['main.py']):
            args = parse_args()
            assert args.retry_failed is False
            assert args.dry_run is False
            assert args.log_level == "INFO"
    
    def test_parse_args_retry_failed(self):
        """--retry-failed flag should be parsed."""
        with patch('sys.argv', ['main.py', '--retry-failed']):
            args = parse_args()
            assert args.retry_failed is True
    
    def test_parse_args_dry_run(self):
        """--dry-run flag should be parsed."""
        with patch('sys.argv', ['main.py', '--dry-run']):
            args = parse_args()
            assert args.dry_run is True
    
    def test_parse_args_log_level(self):
        """--log-level should accept valid levels."""
        for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
            with patch('sys.argv', ['main.py', '--log-level', level]):
                args = parse_args()
                assert args.log_level == level
    
    def test_parse_args_combined(self):
        """Combined arguments should all be parsed."""
        with patch('sys.argv', ['main.py', '--retry-failed', '--dry-run', '--log-level', 'DEBUG']):
            args = parse_args()
            assert args.retry_failed is True
            assert args.dry_run is True
            assert args.log_level == "DEBUG"


class TestPreRunChecks:
    """Test pre-flight health checks."""
    
    @pytest.fixture
    def mock_engine(self):
        """Mock database engine."""
        engine = MagicMock()
        conn = MagicMock()
        conn.execute = MagicMock()
        engine.connect = MagicMock()
        engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
        engine.connect.return_value.__exit__ = MagicMock(return_value=None)
        return engine
    
    @pytest.fixture
    def mock_oauth_client(self):
        """Mock OAuth client."""
        client = MagicMock()
        client.get_access_token = MagicMock(return_value="test-token")
        return client
    
    def test_pre_run_checks_success(self, mock_engine, mock_oauth_client):
        """All checks passing should return True."""
        with patch('app.cron.main.validate_schema_version'):
            result = pre_run_checks(mock_engine, mock_oauth_client, "corr-1")
            assert result is True
    
    def test_pre_run_checks_database_connection_failure(self, mock_engine, mock_oauth_client):
        """Database connection failure should raise exception."""
        mock_engine.connect.side_effect = OperationalError("Connection failed", None, None)
        
        with pytest.raises(OperationalError):
            pre_run_checks(mock_engine, mock_oauth_client, "corr-1")
    
    def test_pre_run_checks_schema_mismatch(self, mock_engine, mock_oauth_client):
        """Schema mismatch should raise SchemaMismatchError."""
        with patch('app.cron.main.validate_schema_version', side_effect=SchemaMismatchError("Mismatch")):
            with pytest.raises(SchemaMismatchError):
                pre_run_checks(mock_engine, mock_oauth_client, "corr-1")
    
    def test_pre_run_checks_oauth_failure(self, mock_engine, mock_oauth_client):
        """OAuth authentication failure should raise exception (STUB: always succeeds)."""
        # NOTE: Stub implementation always returns valid token
        # This test kept for compatibility but OAuth failure not possible with stub
        mock_oauth_client.get_access_token.return_value = None
        
        with patch('app.cron.main.validate_schema_version'):
            with pytest.raises(ValueError):
                pre_run_checks(mock_engine, mock_oauth_client, "corr-1")
    
    def test_pre_run_checks_oauth_exception(self, mock_engine, mock_oauth_client):
        """OAuth exception should be raised (STUB: exceptions manually mocked)."""
        # NOTE: Stub implementation doesn't raise real OAuth errors
        # This test kept for compatibility but manually mocks exceptions
        mock_oauth_client.get_access_token.side_effect = Exception("Auth error")
        
        with patch('app.cron.main.validate_schema_version'):
            with pytest.raises(Exception):
                pre_run_checks(mock_engine, mock_oauth_client, "corr-1")


class TestRunIngestion:
    """Test new batch ingestion."""
    
    @pytest.fixture
    def mock_api_client(self):
        """Mock API client."""
        client = AsyncMock()
        client.fetch_team_members = AsyncMock()
        return client
    
    @pytest.fixture
    def mock_batch_processor(self):
        """Mock batch processor."""
        processor = AsyncMock()
        processor.process_all_batches = AsyncMock()
        return processor
    
    @pytest.mark.asyncio
    async def test_run_ingestion_success(self, mock_api_client, mock_batch_processor):
        """Successful ingestion should return EXIT_SUCCESS."""
        mock_api_client.fetch_team_members.return_value = {"batches": []}
        mock_batch_processor.process_all_batches.return_value = (["batch-1"], [])
        
        exit_code = await run_ingestion(
            api_client=mock_api_client,
            batch_processor=mock_batch_processor,
            correlation_id="corr-1",
            dry_run=False
        )
        
        assert exit_code == EXIT_SUCCESS
        mock_api_client.fetch_team_members.assert_called_once()
        mock_batch_processor.process_all_batches.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_ingestion_partial_success(self, mock_api_client, mock_batch_processor):
        """Partial success (some failures) should return EXIT_PARTIAL_SUCCESS."""
        mock_api_client.fetch_team_members.return_value = {"batches": []}
        mock_batch_processor.process_all_batches.return_value = (["batch-1"], ["batch-2"])
        
        exit_code = await run_ingestion(
            api_client=mock_api_client,
            batch_processor=mock_batch_processor,
            correlation_id="corr-1",
            dry_run=False
        )
        
        assert exit_code == EXIT_PARTIAL_SUCCESS
    
    @pytest.mark.asyncio
    async def test_run_ingestion_no_data(self, mock_api_client, mock_batch_processor):
        """No data from API should return EXIT_SUCCESS."""
        mock_api_client.fetch_team_members.return_value = None
        
        exit_code = await run_ingestion(
            api_client=mock_api_client,
            batch_processor=mock_batch_processor,
            correlation_id="corr-1",
            dry_run=False
        )
        
        assert exit_code == EXIT_SUCCESS
        mock_batch_processor.process_all_batches.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_run_ingestion_fatal_error(self, mock_api_client, mock_batch_processor):
        """Fatal error should return EXIT_FATAL_ERROR."""
        mock_api_client.fetch_team_members.side_effect = Exception("API error")
        
        exit_code = await run_ingestion(
            api_client=mock_api_client,
            batch_processor=mock_batch_processor,
            correlation_id="corr-1",
            dry_run=False
        )
        
        assert exit_code == EXIT_FATAL_ERROR
    
    @pytest.mark.asyncio
    async def test_run_ingestion_dry_run(self, mock_api_client, mock_batch_processor):
        """Dry run mode should be passed through."""
        mock_api_client.fetch_team_members.return_value = {"batches": []}
        mock_batch_processor.process_all_batches.return_value = (["batch-1"], [])
        
        exit_code = await run_ingestion(
            api_client=mock_api_client,
            batch_processor=mock_batch_processor,
            correlation_id="corr-1",
            dry_run=True
        )
        
        assert exit_code == EXIT_SUCCESS


class TestRunRetry:
    """Test batch retry."""
    
    @pytest.fixture
    def mock_retry_manager(self):
        """Mock retry manager."""
        manager = AsyncMock()
        manager.retry_failed_batches = AsyncMock()
        return manager
    
    @pytest.fixture
    def mock_batch_processor(self):
        """Mock batch processor."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_api_client(self):
        """Mock API client."""
        return AsyncMock()
    
    @pytest.mark.asyncio
    async def test_run_retry_success(self, mock_retry_manager, mock_batch_processor, mock_api_client):
        """Successful retry should return EXIT_SUCCESS."""
        mock_retry_manager.retry_failed_batches.return_value = (["batch-1", "batch-2"], [])
        
        exit_code = await run_retry(
            retry_manager=mock_retry_manager,
            batch_processor=mock_batch_processor,
            api_client=mock_api_client,
            correlation_id="corr-1"
        )
        
        assert exit_code == EXIT_SUCCESS
        mock_retry_manager.retry_failed_batches.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_retry_partial_success(self, mock_retry_manager, mock_batch_processor, mock_api_client):
        """Partial retry success should return EXIT_PARTIAL_SUCCESS."""
        mock_retry_manager.retry_failed_batches.return_value = (["batch-1"], ["batch-2"])
        
        exit_code = await run_retry(
            retry_manager=mock_retry_manager,
            batch_processor=mock_batch_processor,
            api_client=mock_api_client,
            correlation_id="corr-1"
        )
        
        assert exit_code == EXIT_PARTIAL_SUCCESS
    
    @pytest.mark.asyncio
    async def test_run_retry_fatal_error(self, mock_retry_manager, mock_batch_processor, mock_api_client):
        """Fatal error during retry should return EXIT_FATAL_ERROR."""
        mock_retry_manager.retry_failed_batches.side_effect = Exception("Retry error")
        
        exit_code = await run_retry(
            retry_manager=mock_retry_manager,
            batch_processor=mock_batch_processor,
            api_client=mock_api_client,
            correlation_id="corr-1"
        )
        
        assert exit_code == EXIT_FATAL_ERROR


class TestMainAsync:
    """Test main_async function."""
    
    @pytest.mark.asyncio
    @patch('app.cron.main.pre_run_checks')
    @patch('app.cron.main.OAuthClient')
    @patch('app.cron.main.create_engine')
    async def test_main_async_schema_mismatch(
        self, mock_create_engine, mock_oauth_client, mock_pre_run_checks
    ):
        """Test main_async with schema mismatch."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_pre_run_checks.side_effect = SchemaMismatchError("Schema mismatch")
        
        args = argparse.Namespace(retry_failed=False, dry_run=False, log_level='INFO')
        
        exit_code = await main_async(args, "test-corr-id")
        
        assert exit_code == EXIT_SCHEMA_MISMATCH
        mock_engine.dispose.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('app.cron.main.pre_run_checks')
    @patch('app.cron.main.OAuthClient')
    @patch('app.cron.main.create_engine')
    async def test_main_async_auth_failure(
        self, mock_create_engine, mock_oauth_client, mock_pre_run_checks
    ):
        """Test main_async with authentication failure."""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine
        mock_pre_run_checks.side_effect = Exception("auth token failed")
        
        args = argparse.Namespace(retry_failed=False, dry_run=False, log_level='INFO')
        
        exit_code = await main_async(args, "test-corr-id")
        
        assert exit_code == EXIT_AUTHENTICATION_FAILED
        mock_engine.dispose.assert_called_once()


class TestMain:
    """Test main entry point."""
    
    @patch('asyncio.run')
    @patch('app.cron.main.set_correlation_id')
    @patch('app.cron.main.configure_logging')
    @patch('sys.argv', ['main.py'])
    def test_main_success(self, mock_configure_logging, mock_set_corr_id, mock_asyncio_run):
        """Successful execution should return EXIT_SUCCESS."""
        mock_asyncio_run.return_value = EXIT_SUCCESS
        
        exit_code = main()
        
        assert exit_code == EXIT_SUCCESS
        mock_configure_logging.assert_called_once()
        mock_set_corr_id.assert_called_once()
        mock_asyncio_run.assert_called_once()
    
    @patch('asyncio.run')
    @patch('app.cron.main.set_correlation_id')
    @patch('app.cron.main.configure_logging')
    @patch('sys.argv', ['main.py', '--log-level', 'DEBUG'])
    def test_main_with_log_level(self, mock_configure_logging, mock_set_corr_id, mock_asyncio_run):
        """Log level should be passed to configure_logging."""
        mock_asyncio_run.return_value = EXIT_SUCCESS
        
        exit_code = main()
        
        mock_configure_logging.assert_called_once_with(log_level='DEBUG')
    
    @patch('asyncio.run')
    @patch('app.cron.main.set_correlation_id')
    @patch('app.cron.main.configure_logging')
    @patch('sys.argv', ['main.py'])
    def test_main_keyboard_interrupt(self, mock_configure_logging, mock_set_corr_id, mock_asyncio_run):
        """KeyboardInterrupt should return EXIT_FATAL_ERROR."""
        mock_asyncio_run.side_effect = KeyboardInterrupt()
        
        exit_code = main()
        
        assert exit_code == EXIT_FATAL_ERROR
    
    @patch('asyncio.run')
    @patch('app.cron.main.set_correlation_id')
    @patch('app.cron.main.configure_logging')
    @patch('sys.argv', ['main.py'])
    def test_main_unexpected_exception(self, mock_configure_logging, mock_set_corr_id, mock_asyncio_run):
        """Unexpected exception should return EXIT_FATAL_ERROR."""
        mock_asyncio_run.side_effect = Exception("Unexpected error")
        
        exit_code = main()
        
        assert exit_code == EXIT_FATAL_ERROR


class TestExitCodes:
    """Test exit code constants."""
    
    def test_exit_code_values(self):
        """Exit codes should have correct values."""
        assert EXIT_SUCCESS == 0
        assert EXIT_PARTIAL_SUCCESS == 1
        assert EXIT_FATAL_ERROR == 2
        assert EXIT_SCHEMA_MISMATCH == 3
        assert EXIT_AUTHENTICATION_FAILED == 4
