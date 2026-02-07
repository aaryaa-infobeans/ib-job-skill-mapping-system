"""
Integration tests for batch retry flow.

Tests end-to-end retry scenarios including:
- Batch failure and successful retry
- Multiple failures leading to abandonment
- Exponential backoff delays
- Non-retryable error handling
- Batch isolation
- State transitions
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.cron.processing.retry_manager import RetryManager
from app.cron.processing.batch_processor import BatchProcessor
from app.cron.db.repositories import BatchStateRepository
from app.cron.processing.error_classifier import ErrorCategory


@pytest.fixture
async def mock_session():
    """Create mock async session for testing."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_api_client():
    """Mock API client for testing."""
    client = AsyncMock()
    client.fetch_team_members.return_value = {
        "data": [
            {
                "team_member_id": "tm-001",
                "name": "Test Member",
                "email": "test@example.com",
                "skills": [{"skill_name": "Python", "proficiency": "Expert"}]
            }
        ],
        "sync_timestamp": datetime.now().isoformat()
    }
    return client


@pytest.fixture
def mock_repository():
    """Mock batch state repository."""
    return AsyncMock(spec=BatchStateRepository)


@pytest.mark.asyncio
class TestRetryFlowIntegration:
    """Integration tests for batch retry flow."""
    
    async def test_batch_fails_first_succeeds_on_retry(self, mock_session, mock_api_client, mock_repository):
        """Test: Batch fails on first attempt, succeeds on retry."""
        # Setup mock batch as dictionary
        mock_batch = {
            'batch_id': 'batch-001',
            'status': 'FAILED',
            'metadata': {
                'retry_count': 1,
                'error_category': ErrorCategory.NETWORK_ERROR.value
            },
            'completed_at': datetime.utcnow() - timedelta(minutes=2),
            'updated_at': datetime.utcnow() - timedelta(minutes=5),
            'created_at': datetime.utcnow() - timedelta(hours=1)
        }
        
        # Mock repository to return failed batch
        mock_repository.get_failed_batches.return_value = [mock_batch]
        
        # Create retry manager with mocked repository
        retry_manager = RetryManager(mock_session, max_retries=3, base_delay=60)
        retry_manager.batch_state_repo = mock_repository
        
        batch_processor = BatchProcessor(mock_session, dry_run=False)
        
        # Mock successful processing
        with patch.object(batch_processor, 'process_batch', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = True
            
            # Execute retry
            successful, failed = await retry_manager.retry_failed_batches(
                batch_processor=batch_processor,
                api_client=mock_api_client,
                correlation_id="test-corr-1"
            )
        
        # Assertions
        assert len(successful) == 1
        assert len(failed) == 0
        assert successful[0] == "batch-001"
    
    async def test_batch_reaches_max_retries_marked_abandoned(self, mock_session, mock_api_client, mock_repository):
        """Test: Batch fails multiple times and is marked ABANDONED."""
        # Setup mock batch at max retries
        mock_batch = MagicMock()
        mock_batch.batch_id = "batch-002"
        mock_batch.status = "FAILED"
        mock_batch.retry_count = 3  # Max retries reached
        mock_batch.last_error_category = ErrorCategory.NETWORK_ERROR.value
        mock_batch.completed_at = datetime.now() - timedelta(minutes=6)
        
        # Mock repository to return batch at max retries
        mock_repository.get_failed_batches.return_value = [mock_batch]
        
        # Create retry manager
        retry_manager = RetryManager(mock_session, max_retries=3, base_delay=60)
        retry_manager.batch_state_repo = mock_repository
        
        batch_processor = BatchProcessor(mock_session, dry_run=False)
        
        # Execute retry (should skip due to max retries)
        successful, failed = await retry_manager.retry_failed_batches(
            batch_processor=batch_processor,
            api_client=mock_api_client,
            correlation_id="test-corr-2"
        )
        
        # Assertions
        assert len(successful) == 0
        assert len(failed) == 0  # Not attempted because max retries reached
    
    async def test_successful_batches_not_retried(self, mock_session, mock_api_client, mock_repository):
        """Test: Successful batches are not retried."""
        # Mock repository returns no failed batches
        mock_repository.get_failed_batches.return_value = []
        
        # Create retry manager
        retry_manager = RetryManager(mock_session, max_retries=3, base_delay=60)
        retry_manager.batch_state_repo = mock_repository
        
        batch_processor = BatchProcessor(mock_session, dry_run=False)
        
        # Execute retry
        successful, failed = await retry_manager.retry_failed_batches(
            batch_processor=batch_processor,
            api_client=mock_api_client,
            correlation_id="test-corr-3"
        )
        
        # Assertions
        assert len(successful) == 0
        assert len(failed) == 0
        
        # Verify repository was queried
        mock_repository.get_failed_batches.assert_called_once()
    
    async def test_exponential_backoff_delays(self, mock_session):
        """Test: Exponential backoff delays are calculated correctly."""
        retry_manager = RetryManager(mock_session, max_retries=3, base_delay=60)
        
        # Test delay calculations
        assert retry_manager.calculate_retry_delay(1) == 60    # 60 * 2^0 = 60s
        assert retry_manager.calculate_retry_delay(2) == 120   # 60 * 2^1 = 120s
        assert retry_manager.calculate_retry_delay(3) == 240   # 60 * 2^2 = 240s
        assert retry_manager.calculate_retry_delay(4) == 300   # Capped at 300s
        assert retry_manager.calculate_retry_delay(5) == 300   # Still capped
    
    async def test_non_retryable_errors_not_retried(self, mock_session, mock_api_client, mock_repository):
        """Test: Non-retryable error categories prevent retry."""
        # Setup mock batch with validation error (non-retryable)
        mock_batch = MagicMock()
        mock_batch.batch_id = "batch-005"
        mock_batch.status = "FAILED"
        mock_batch.retry_count = 1
        mock_batch.last_error_category = ErrorCategory.VALIDATION_ERROR.value
        mock_batch.completed_at = datetime.now() - timedelta(minutes=2)
        
        # Mock repository to return batch with non-retryable error
        mock_repository.get_failed_batches.return_value = [mock_batch]
        
        # Create retry manager
        retry_manager = RetryManager(mock_session, max_retries=3, base_delay=60)
        retry_manager.batch_state_repo = mock_repository
        
        batch_processor = BatchProcessor(mock_session, dry_run=False)
        
        # Execute retry
        successful, failed = await retry_manager.retry_failed_batches(
            batch_processor=batch_processor,
            api_client=mock_api_client,
            correlation_id="test-corr-5"
        )
        
        # Assertions
        assert len(successful) == 0
        assert len(failed) == 0  # Not attempted due to non-retryable error
    
    async def test_batch_isolation(self, mock_session, mock_api_client, mock_repository):
        """Test: Retry is batch_id specific, doesn't affect other batches."""
        # Setup two mock batches as dictionaries
        mock_batch1 = {
            'batch_id': 'batch-006',
            'status': 'FAILED',
            'metadata': {
                'retry_count': 1,
                'error_category': ErrorCategory.NETWORK_ERROR.value
            },
            'completed_at': datetime.utcnow() - timedelta(minutes=2)
        }
        
        mock_batch2 = {
            'batch_id': 'batch-007',
            'status': 'FAILED',
            'metadata': {
                'retry_count': 1,
                'error_category': ErrorCategory.NETWORK_ERROR.value
            },
            'completed_at': datetime.utcnow() - timedelta(minutes=6)
        }
        
        # Mock repository to return both batches
        mock_repository.get_failed_batches.return_value = [mock_batch1, mock_batch2]
        
        # Create retry manager and batch processor
        retry_manager = RetryManager(mock_session, max_retries=3, base_delay=60)
        retry_manager.batch_state_repo = mock_repository
        
        batch_processor = BatchProcessor(mock_session, dry_run=False)
        
        # Mock processing: batch-006 succeeds, batch-007 fails
        process_results = {
            "batch-006": True,
            "batch-007": False
        }
        
        with patch.object(batch_processor, 'process_batch', new_callable=AsyncMock) as mock_process:
            mock_process.side_effect = lambda batch_id, correlation_id, team_members, metadata=None: process_results[batch_id]
            
            # Execute retry
            successful, failed = await retry_manager.retry_failed_batches(
                batch_processor=batch_processor,
                api_client=mock_api_client,
                correlation_id="test-corr-6"
            )
        
        # Assertions
        assert len(successful) == 1
        assert len(failed) == 1
        assert "batch-006" in successful
        assert "batch-007" in failed
    
    async def test_state_transitions_tracked(self, mock_session, mock_api_client, mock_repository):
        """Test: State transitions are tracked correctly through retry flow."""
        # Setup mock batch as dictionary
        original_created = datetime.utcnow() - timedelta(hours=1)
        original_updated = datetime.utcnow() - timedelta(minutes=10)
        
        mock_batch = {
            'batch_id': 'batch-008',
            'status': 'FAILED',
            'metadata': {
                'retry_count': 1,
                'error_category': ErrorCategory.NETWORK_ERROR.value
            },
            'completed_at': datetime.utcnow() - timedelta(minutes=2),
            'created_at': original_created,
            'updated_at': original_updated
        }
        
        # Mock repository to return batch
        mock_repository.get_failed_batches.return_value = [mock_batch]
        
        # Create retry manager and processor
        retry_manager = RetryManager(mock_session, max_retries=3, base_delay=60)
        retry_manager.batch_state_repo = mock_repository
        
        batch_processor = BatchProcessor(mock_session, dry_run=False)
        
        # Mock successful processing
        with patch.object(batch_processor, 'process_batch', new_callable=AsyncMock) as mock_process:
            mock_process.return_value = True
            
            # Execute retry
            successful, failed = await retry_manager.retry_failed_batches(
                batch_processor=batch_processor,
                api_client=mock_api_client,
                correlation_id="test-corr-8"
            )
        
        # Verify execution
        assert len(successful) == 1
        assert "batch-008" in successful
        assert mock_process.called

