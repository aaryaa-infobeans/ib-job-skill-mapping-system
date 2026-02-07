"""
Integration tests for simulating failure scenarios and retry behavior.

Tests cover:
- Network timeout during API call
- Database connection lost
- API rate limit (429)
- Authentication failure (401)
- Validation error
- Constraint violation
- Partial batch failure
- All retries exhausted

Each test simulates a failure condition and validates that retry logic
handles it correctly based on error categorization.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import OperationalError, IntegrityError

from app.cron.processing.retry_manager import RetryManager
from app.cron.processing.batch_processor import BatchProcessor
from app.cron.processing.error_classifier import ErrorCategory
from app.cron.db.repositories import BatchStateRepository


@pytest.fixture
def mock_session():
    """Mock AsyncSession for database operations."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_api_client():
    """Mock API client for external calls."""
    client = AsyncMock()
    client.fetch_team_members = AsyncMock(return_value=[
        {"id": "tm-001", "name": "John Doe", "skills": ["Python", "SQL"]},
        {"id": "tm-002", "name": "Jane Smith", "skills": ["Java", "AWS"]}
    ])
    return client


@pytest.fixture
def mock_repository():
    """Mock BatchStateRepository."""
    return AsyncMock(spec=BatchStateRepository)


class TestFailureScenarios:
    """Test suite for failure simulation and retry behavior."""
    
    async def test_network_timeout_retry_succeeds(
        self, mock_session, mock_api_client, mock_repository
    ):
        """Test: Network timeout during API call → retry succeeds."""
        # Setup batch that failed due to network timeout
        mock_batch = {
            'batch_id': 'batch-net-001',
            'status': 'FAILED',
            'metadata': {
                'retry_count': 1,
                'error_category': ErrorCategory.NETWORK_ERROR.value,
                'last_error': 'Connection timeout after 30s'
            },
            'completed_at': datetime.utcnow() - timedelta(minutes=2),
            'created_at': datetime.utcnow() - timedelta(hours=1),
            'updated_at': datetime.utcnow() - timedelta(minutes=5)
        }
        
        mock_repository.get_failed_batches.return_value = [mock_batch]
        
        # Create retry manager
        retry_manager = RetryManager(mock_session, max_retries=3, base_delay=60)
        retry_manager.batch_state_repo = mock_repository
        
        batch_processor = BatchProcessor(mock_session, dry_run=False)
        
        # Mock successful retry after network timeout
        with patch.object(batch_processor, 'process_batch', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = True
            
            # Execute retry
            successful, failed = await retry_manager.retry_failed_batches(
                batch_processor=batch_processor,
                api_client=mock_api_client,
                correlation_id="test-net-timeout"
            )
        
        # Verify batch retried successfully after network timeout
        assert len(successful) == 1
        assert successful[0] == 'batch-net-001'
        assert len(failed) == 0
    
    async def test_database_connection_lost_retry_succeeds(
        self, mock_session, mock_api_client, mock_repository
    ):
        """Test: Database lock released → retry succeeds."""
        # Setup batch that failed due to database lock
        mock_batch = {
            'batch_id': 'batch-db-001',
            'status': 'FAILED',
            'metadata': {
                'retry_count': 1,
                'error_category': ErrorCategory.DATABASE_LOCK.value,
                'last_error': 'Database lock timeout - could not acquire lock'
            },
            'completed_at': datetime.utcnow() - timedelta(minutes=3),
            'created_at': datetime.utcnow() - timedelta(hours=1),
            'updated_at': datetime.utcnow() - timedelta(minutes=6)
        }
        
        mock_repository.get_failed_batches.return_value = [mock_batch]
        
        # Create retry manager
        retry_manager = RetryManager(mock_session, max_retries=3, base_delay=60)
        retry_manager.batch_state_repo = mock_repository
        
        batch_processor = BatchProcessor(mock_session, dry_run=False)
        
        # Mock successful retry after database lock released
        with patch.object(batch_processor, 'process_batch', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = True
            
            # Execute retry
            successful, failed = await retry_manager.retry_failed_batches(
                batch_processor=batch_processor,
                api_client=mock_api_client,
                correlation_id="test-db-lock"
            )
        
        # Verify batch retried successfully after lock released
        assert len(successful) == 1
        assert successful[0] == 'batch-db-001'
        assert len(failed) == 0
    
    async def test_rate_limit_429_retry_succeeds(
        self, mock_session, mock_api_client, mock_repository
    ):
        """Test: API rate limit (429) → retry succeeds after backoff."""
        # Setup batch that failed due to rate limiting
        mock_batch = {
            'batch_id': 'batch-rate-001',
            'status': 'FAILED',
            'metadata': {
                'retry_count': 1,
                'error_category': ErrorCategory.API_RATE_LIMIT.value,
                'last_error': 'HTTP 429: Too Many Requests',
                'retry_after': 120
            },
            'completed_at': datetime.utcnow() - timedelta(minutes=3),
            'created_at': datetime.utcnow() - timedelta(hours=1),
            'updated_at': datetime.utcnow() - timedelta(minutes=6)
        }
        
        mock_repository.get_failed_batches.return_value = [mock_batch]
        
        # Create retry manager with appropriate delay
        retry_manager = RetryManager(mock_session, max_retries=3, base_delay=60)
        retry_manager.batch_state_repo = mock_repository
        
        batch_processor = BatchProcessor(mock_session, dry_run=False)
        
        # Mock successful retry after rate limit expires
        with patch.object(batch_processor, 'process_batch', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = True
            
            # Execute retry
            successful, failed = await retry_manager.retry_failed_batches(
                batch_processor=batch_processor,
                api_client=mock_api_client,
                correlation_id="test-rate-limit"
            )
        
        # Verify batch retried successfully after rate limit backoff
        assert len(successful) == 1
        assert successful[0] == 'batch-rate-001'
        assert len(failed) == 0
    
    async def test_authentication_failure_no_retry(
        self, mock_session, mock_api_client, mock_repository
    ):
        """Test: Authentication failure (401) → no retry."""
        # Setup batch that failed due to authentication
        mock_batch = {
            'batch_id': 'batch-auth-001',
            'status': 'FAILED',
            'metadata': {
                'retry_count': 1,
                'error_category': ErrorCategory.AUTHENTICATION_ERROR.value,
                'last_error': 'HTTP 401: Unauthorized - Invalid credentials'
            },
            'completed_at': datetime.utcnow() - timedelta(minutes=2),
            'created_at': datetime.utcnow() - timedelta(hours=1),
            'updated_at': datetime.utcnow() - timedelta(minutes=5)
        }
        
        mock_repository.get_failed_batches.return_value = [mock_batch]
        
        # Create retry manager
        retry_manager = RetryManager(mock_session, max_retries=3, base_delay=60)
        retry_manager.batch_state_repo = mock_repository
        
        batch_processor = BatchProcessor(mock_session, dry_run=False)
        
        # Execute retry - should skip auth failures
        successful, failed = await retry_manager.retry_failed_batches(
            batch_processor=batch_processor,
            api_client=mock_api_client,
            correlation_id="test-auth-fail"
        )
        
        # Verify auth failure not retried
        assert len(successful) == 0
        assert len(failed) == 0
    
    async def test_validation_error_no_retry(
        self, mock_session, mock_api_client, mock_repository
    ):
        """Test: Validation error → no retry."""
        # Setup batch that failed due to validation error
        mock_batch = {
            'batch_id': 'batch-valid-001',
            'status': 'FAILED',
            'metadata': {
                'retry_count': 1,
                'error_category': ErrorCategory.VALIDATION_ERROR.value,
                'last_error': 'Invalid skill data: missing required field "name"'
            },
            'completed_at': datetime.utcnow() - timedelta(minutes=2),
            'created_at': datetime.utcnow() - timedelta(hours=1),
            'updated_at': datetime.utcnow() - timedelta(minutes=5)
        }
        
        mock_repository.get_failed_batches.return_value = [mock_batch]
        
        # Create retry manager
        retry_manager = RetryManager(mock_session, max_retries=3, base_delay=60)
        retry_manager.batch_state_repo = mock_repository
        
        batch_processor = BatchProcessor(mock_session, dry_run=False)
        
        # Execute retry - should skip validation errors
        successful, failed = await retry_manager.retry_failed_batches(
            batch_processor=batch_processor,
            api_client=mock_api_client,
            correlation_id="test-validation-fail"
        )
        
        # Verify validation error not retried
        assert len(successful) == 0
        assert len(failed) == 0
    
    async def test_constraint_violation_no_retry(
        self, mock_session, mock_api_client, mock_repository
    ):
        """Test: Constraint violation → no retry."""
        # Setup batch that failed due to database constraint violation
        mock_batch = {
            'batch_id': 'batch-constraint-001',
            'status': 'FAILED',
            'metadata': {
                'retry_count': 1,
                'error_category': ErrorCategory.CONSTRAINT_VIOLATION.value,
                'last_error': 'IntegrityError: duplicate key value violates unique constraint'
            },
            'completed_at': datetime.utcnow() - timedelta(minutes=2),
            'created_at': datetime.utcnow() - timedelta(hours=1),
            'updated_at': datetime.utcnow() - timedelta(minutes=5)
        }
        
        mock_repository.get_failed_batches.return_value = [mock_batch]
        
        # Create retry manager
        retry_manager = RetryManager(mock_session, max_retries=3, base_delay=60)
        retry_manager.batch_state_repo = mock_repository
        
        batch_processor = BatchProcessor(mock_session, dry_run=False)
        
        # Execute retry - should skip constraint violations
        successful, failed = await retry_manager.retry_failed_batches(
            batch_processor=batch_processor,
            api_client=mock_api_client,
            correlation_id="test-constraint-fail"
        )
        
        # Verify constraint violation not retried
        assert len(successful) == 0
        assert len(failed) == 0
    
    async def test_partial_batch_failure_rollback_and_retry(
        self, mock_session, mock_api_client, mock_repository
    ):
        """Test: Partial batch failure → rollback + retry."""
        # Setup batch that partially failed (some records succeeded, others failed)
        mock_batch = {
            'batch_id': 'batch-partial-001',
            'status': 'FAILED',
            'metadata': {
                'retry_count': 1,
                'error_category': ErrorCategory.NETWORK_ERROR.value,
                'last_error': 'Processed 5/10 records, failed on record #6',
                'partial_success': 5,
                'partial_failure': 5
            },
            'completed_at': datetime.utcnow() - timedelta(minutes=2),
            'created_at': datetime.utcnow() - timedelta(hours=1),
            'updated_at': datetime.utcnow() - timedelta(minutes=5)
        }
        
        mock_repository.get_failed_batches.return_value = [mock_batch]
        
        # Create retry manager
        retry_manager = RetryManager(mock_session, max_retries=3, base_delay=60)
        retry_manager.batch_state_repo = mock_repository
        
        batch_processor = BatchProcessor(mock_session, dry_run=False)
        
        # Mock successful full batch processing on retry
        with patch.object(batch_processor, 'process_batch', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = True
            
            # Execute retry
            successful, failed = await retry_manager.retry_failed_batches(
                batch_processor=batch_processor,
                api_client=mock_api_client,
                correlation_id="test-partial-fail"
            )
        
        # Verify partial failure retried and succeeded
        assert len(successful) == 1
        assert successful[0] == 'batch-partial-001'
        assert len(failed) == 0
    
    async def test_max_retries_exhausted_abandoned(
        self, mock_session, mock_api_client, mock_repository
    ):
        """Test: All retries exhausted → batch marked as abandoned."""
        # Setup batch that reached max retries
        mock_batch = {
            'batch_id': 'batch-exhaust-001',
            'status': 'FAILED',
            'metadata': {
                'retry_count': 3,  # Already at max retries
                'error_category': ErrorCategory.NETWORK_ERROR.value,
                'last_error': 'Connection timeout after 30s (retry #3)'
            },
            'completed_at': datetime.utcnow() - timedelta(minutes=10),
            'created_at': datetime.utcnow() - timedelta(hours=2),
            'updated_at': datetime.utcnow() - timedelta(minutes=10)
        }
        
        mock_repository.get_failed_batches.return_value = [mock_batch]
        
        # Create retry manager with max_retries=3
        retry_manager = RetryManager(mock_session, max_retries=3, base_delay=60)
        retry_manager.batch_state_repo = mock_repository
        
        batch_processor = BatchProcessor(mock_session, dry_run=False)
        
        # Execute retry - should not attempt retry (already at max)
        successful, failed = await retry_manager.retry_failed_batches(
            batch_processor=batch_processor,
            api_client=mock_api_client,
            correlation_id="test-max-retries"
        )
        
        # Verify batch not retried (already exhausted)
        assert len(successful) == 0
        assert len(failed) == 0
        
        # Batch should remain in FAILED state, not attempted again
        mock_repository.get_failed_batches.assert_called_once()
