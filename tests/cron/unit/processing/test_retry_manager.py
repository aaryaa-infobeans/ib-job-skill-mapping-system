"""
Unit tests for RetryManager.

Tests exponential backoff, retry eligibility, successful retries, failed retries,
max retry enforcement, and batch abandonment.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.cron.processing.retry_manager import RetryManager
from app.cron.processing.error_classifier import ErrorCategory


@pytest.fixture
def mock_session():
    """Mock async database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def retry_manager(mock_session):
    """Retry manager with mocked session."""
    return RetryManager(mock_session, max_retries=3, base_delay=60)


@pytest.fixture
def mock_batch_processor():
    """Mock batch processor."""
    processor = AsyncMock()
    processor.process_batch = AsyncMock()
    return processor


@pytest.fixture
def mock_api_client():
    """Mock API client."""
    client = AsyncMock()
    client.fetch_batch_data = AsyncMock()
    return client


class TestRetryDelayCalculation:
    """Test exponential backoff delay calculation."""
    
    @pytest.mark.asyncio
    async def test_retry_delay_first_attempt(self, retry_manager):
        """First retry should use base delay (60s)."""
        delay = retry_manager.calculate_retry_delay(1)
        assert delay == 60
    
    @pytest.mark.asyncio
    async def test_retry_delay_second_attempt(self, retry_manager):
        """Second retry should double delay (120s)."""
        delay = retry_manager.calculate_retry_delay(2)
        assert delay == 120
    
    @pytest.mark.asyncio
    async def test_retry_delay_third_attempt(self, retry_manager):
        """Third retry should quadruple delay (240s)."""
        delay = retry_manager.calculate_retry_delay(3)
        assert delay == 240
    
    @pytest.mark.asyncio
    async def test_retry_delay_max_cap(self, retry_manager):
        """Delay should cap at 300 seconds."""
        delay = retry_manager.calculate_retry_delay(10)
        assert delay == 300
    
    @pytest.mark.asyncio
    async def test_retry_delay_zero_count(self, retry_manager):
        """Zero retry count should return base delay."""
        delay = retry_manager.calculate_retry_delay(0)
        assert delay == 60
    
    @pytest.mark.asyncio
    async def test_retry_delay_negative_count(self, retry_manager):
        """Negative retry count should return base delay."""
        delay = retry_manager.calculate_retry_delay(-1)
        assert delay == 60
    
    @pytest.mark.asyncio
    async def test_custom_base_delay(self, mock_session):
        """Custom base delay should be respected."""
        manager = RetryManager(mock_session, max_retries=3, base_delay=30)
        delay = manager.calculate_retry_delay(1)
        assert delay == 30


class TestRetryEligibility:
    """Test retry eligibility logic."""
    
    @pytest.mark.asyncio
    async def test_failed_batch_eligible(self, retry_manager):
        """FAILED batch with retry count < max should be eligible."""
        batch = {
            'batch_id': 'batch-1',
            'status': 'FAILED',
            'metadata': {'retry_count': 0},
            'completed_at': datetime.utcnow() - timedelta(seconds=120)
        }
        
        eligible = await retry_manager.should_retry_batch(batch)
        assert eligible is True
    
    @pytest.mark.asyncio
    async def test_success_batch_not_eligible(self, retry_manager):
        """SUCCESS batch should not be eligible."""
        batch = {
            'batch_id': 'batch-1',
            'status': 'SUCCESS',
            'metadata': {'retry_count': 0}
        }
        
        eligible = await retry_manager.should_retry_batch(batch)
        assert eligible is False
    
    @pytest.mark.asyncio
    async def test_processing_batch_not_eligible(self, retry_manager):
        """PROCESSING batch should not be eligible."""
        batch = {
            'batch_id': 'batch-1',
            'status': 'PROCESSING',
            'metadata': {'retry_count': 0}
        }
        
        eligible = await retry_manager.should_retry_batch(batch)
        assert eligible is False
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, retry_manager):
        """Batch with retry_count >= max_retries should not be eligible."""
        batch = {
            'batch_id': 'batch-1',
            'status': 'FAILED',
            'metadata': {'retry_count': 3},
            'completed_at': datetime.utcnow() - timedelta(seconds=120)
        }
        
        eligible = await retry_manager.should_retry_batch(batch)
        assert eligible is False
    
    @pytest.mark.asyncio
    async def test_non_retryable_error_category(self, retry_manager):
        """Batch with non-retryable error category should not be eligible."""
        batch = {
            'batch_id': 'batch-1',
            'status': 'FAILED',
            'metadata': {
                'retry_count': 1,
                'error_category': ErrorCategory.AUTHENTICATION_ERROR.value
            },
            'completed_at': datetime.utcnow() - timedelta(seconds=120)
        }
        
        eligible = await retry_manager.should_retry_batch(batch)
        assert eligible is False
    
    @pytest.mark.asyncio
    async def test_retryable_error_category(self, retry_manager):
        """Batch with retryable error category should be eligible."""
        batch = {
            'batch_id': 'batch-1',
            'status': 'FAILED',
            'metadata': {
                'retry_count': 1,
                'error_category': ErrorCategory.NETWORK_ERROR.value
            },
            'completed_at': datetime.utcnow() - timedelta(seconds=120)
        }
        
        eligible = await retry_manager.should_retry_batch(batch)
        assert eligible is True
    
    @pytest.mark.asyncio
    async def test_minimum_delay_not_elapsed(self, retry_manager):
        """Batch should not be eligible if minimum delay hasn't passed."""
        batch = {
            'batch_id': 'batch-1',
            'status': 'FAILED',
            'metadata': {'retry_count': 1},
            'completed_at': datetime.utcnow() - timedelta(seconds=30)  # Only 30s elapsed, need 120s
        }
        
        eligible = await retry_manager.should_retry_batch(batch)
        assert eligible is False
    
    @pytest.mark.asyncio
    async def test_minimum_delay_elapsed(self, retry_manager):
        """Batch should be eligible if minimum delay has passed."""
        batch = {
            'batch_id': 'batch-1',
            'status': 'FAILED',
            'metadata': {'retry_count': 1},
            'completed_at': datetime.utcnow() - timedelta(seconds=130)  # 130s elapsed, need 120s
        }
        
        eligible = await retry_manager.should_retry_batch(batch)
        assert eligible is True
    
    @pytest.mark.asyncio
    async def test_no_completed_at_timestamp(self, retry_manager):
        """Batch without completed_at should be eligible (no delay check)."""
        batch = {
            'batch_id': 'batch-1',
            'status': 'FAILED',
            'metadata': {'retry_count': 0},
            'completed_at': None
        }
        
        eligible = await retry_manager.should_retry_batch(batch)
        assert eligible is True
    
    @pytest.mark.asyncio
    async def test_invalid_error_category_allows_retry(self, retry_manager):
        """Invalid error category should allow retry."""
        batch = {
            'batch_id': 'batch-1',
            'status': 'FAILED',
            'metadata': {
                'retry_count': 1,
                'error_category': 'invalid_category'
            },
            'completed_at': datetime.utcnow() - timedelta(seconds=120)
        }
        
        eligible = await retry_manager.should_retry_batch(batch)
        assert eligible is True


class TestRetryFailedBatches:
    """Test retry_failed_batches method."""
    
    @pytest.mark.asyncio
    async def test_successful_retry(self, retry_manager, mock_batch_processor, mock_api_client):
        """Successful retry should update batch status and return success."""
        # Mock get_failed_batches
        failed_batch = {
            'batch_id': 'batch-1',
            'status': 'FAILED',
            'correlation_id': 'corr-1',
            'metadata': {'retry_count': 0},
            'completed_at': datetime.utcnow() - timedelta(seconds=120)
        }
        
        retry_manager.batch_state_repo.get_failed_batches = AsyncMock(return_value=[failed_batch])
        retry_manager.batch_state_repo.update_batch_status = AsyncMock()
        retry_manager.batch_state_repo.audit_log = AsyncMock()
        
        # Mock API client
        mock_api_client.fetch_batch_data.return_value = [{'team_member_id': 'tm-1'}]
        
        # Mock batch processor success
        mock_batch_processor.process_batch.return_value = True
        
        successful, failed = await retry_manager.retry_failed_batches(
            batch_processor=mock_batch_processor,
            api_client=mock_api_client,
            correlation_id='retry-corr-1'
        )
        
        assert len(successful) == 1
        assert 'batch-1' in successful
        assert len(failed) == 0
        
        # Verify batch processor called
        mock_batch_processor.process_batch.assert_called_once()
        call_args = mock_batch_processor.process_batch.call_args
        assert call_args[1]['batch_id'] == 'batch-1'
        assert call_args[1]['metadata']['retry_count'] == 1
    
    @pytest.mark.asyncio
    async def test_failed_retry_not_abandoned(self, retry_manager, mock_batch_processor, mock_api_client):
        """Failed retry with retries remaining should not abandon."""
        failed_batch = {
            'batch_id': 'batch-1',
            'status': 'FAILED',
            'correlation_id': 'corr-1',
            'metadata': {'retry_count': 1},
            'completed_at': datetime.utcnow() - timedelta(seconds=120)
        }
        
        retry_manager.batch_state_repo.get_failed_batches = AsyncMock(return_value=[failed_batch])
        retry_manager.batch_state_repo.update_batch_status = AsyncMock()
        retry_manager.batch_state_repo.audit_log = AsyncMock()
        
        mock_api_client.fetch_batch_data.return_value = [{'team_member_id': 'tm-1'}]
        mock_batch_processor.process_batch.return_value = False
        
        successful, failed = await retry_manager.retry_failed_batches(
            batch_processor=mock_batch_processor,
            api_client=mock_api_client,
            correlation_id='retry-corr-1'
        )
        
        assert len(successful) == 0
        assert len(failed) == 1
        assert 'batch-1' in failed
        
        # Should not mark as abandoned (retry_count 2 < max_retries 3)
        retry_manager.session.execute.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_failed_retry_max_retries_abandoned(self, retry_manager, mock_batch_processor, mock_api_client):
        """Failed retry at max retries should mark batch as ABANDONED."""
        failed_batch = {
            'batch_id': 'batch-1',
            'status': 'FAILED',
            'correlation_id': 'corr-1',
            'metadata': {'retry_count': 2},  # Next attempt will be 3rd (max)
            'completed_at': datetime.utcnow() - timedelta(seconds=240)
        }
        
        retry_manager.batch_state_repo.get_failed_batches = AsyncMock(return_value=[failed_batch])
        retry_manager.batch_state_repo.update_batch_status = AsyncMock()
        retry_manager.batch_state_repo.audit_log = AsyncMock()
        
        mock_api_client.fetch_batch_data.return_value = [{'team_member_id': 'tm-1'}]
        mock_batch_processor.process_batch.return_value = False
        
        successful, failed = await retry_manager.retry_failed_batches(
            batch_processor=mock_batch_processor,
            api_client=mock_api_client,
            correlation_id='retry-corr-1'
        )
        
        assert len(successful) == 0
        assert len(failed) == 1
        
        # Should mark as abandoned (retry_count 3 >= max_retries 3)
        retry_manager.session.execute.assert_called_once()
        retry_manager.session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_exception_during_retry(self, retry_manager, mock_batch_processor, mock_api_client):
        """Exception during retry should handle gracefully and mark abandoned if max retries."""
        failed_batch = {
            'batch_id': 'batch-1',
            'status': 'FAILED',
            'correlation_id': 'corr-1',
            'metadata': {'retry_count': 2},
            'completed_at': datetime.utcnow() - timedelta(seconds=240)
        }
        
        retry_manager.batch_state_repo.get_failed_batches = AsyncMock(return_value=[failed_batch])
        retry_manager.batch_state_repo.update_batch_status = AsyncMock()
        retry_manager.batch_state_repo.audit_log = AsyncMock()
        
        mock_api_client.fetch_batch_data.side_effect = Exception("API error")
        
        successful, failed = await retry_manager.retry_failed_batches(
            batch_processor=mock_batch_processor,
            api_client=mock_api_client,
            correlation_id='retry-corr-1'
        )
        
        assert len(successful) == 0
        assert len(failed) == 1
        
        # Should mark as abandoned due to max retries
        retry_manager.session.execute.assert_called_once()
        retry_manager.session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_no_failed_batches(self, retry_manager, mock_batch_processor, mock_api_client):
        """No failed batches should return empty results."""
        retry_manager.batch_state_repo.get_failed_batches = AsyncMock(return_value=[])
        
        successful, failed = await retry_manager.retry_failed_batches(
            batch_processor=mock_batch_processor,
            api_client=mock_api_client,
            correlation_id='retry-corr-1'
        )
        
        assert len(successful) == 0
        assert len(failed) == 0
        
        # Should not call API or processor
        mock_api_client.fetch_batch_data.assert_not_called()
        mock_batch_processor.process_batch.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_no_eligible_batches(self, retry_manager, mock_batch_processor, mock_api_client):
        """Failed batches with no eligible retries should not be processed."""
        # Batch with max retries exceeded
        failed_batch = {
            'batch_id': 'batch-1',
            'status': 'FAILED',
            'correlation_id': 'corr-1',
            'metadata': {'retry_count': 3},
            'completed_at': datetime.utcnow() - timedelta(seconds=120)
        }
        
        retry_manager.batch_state_repo.get_failed_batches = AsyncMock(return_value=[failed_batch])
        
        successful, failed = await retry_manager.retry_failed_batches(
            batch_processor=mock_batch_processor,
            api_client=mock_api_client,
            correlation_id='retry-corr-1'
        )
        
        assert len(successful) == 0
        assert len(failed) == 0
        
        # Should not call API or processor
        mock_api_client.fetch_batch_data.assert_not_called()
        mock_batch_processor.process_batch.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_multiple_batches_mixed_results(self, retry_manager, mock_batch_processor, mock_api_client):
        """Multiple batches with mixed success/failure results."""
        failed_batches = [
            {
                'batch_id': 'batch-1',
                'status': 'FAILED',
                'correlation_id': 'corr-1',
                'metadata': {'retry_count': 0},
                'completed_at': datetime.utcnow() - timedelta(seconds=120)
            },
            {
                'batch_id': 'batch-2',
                'status': 'FAILED',
                'correlation_id': 'corr-2',
                'metadata': {'retry_count': 1},
                'completed_at': datetime.utcnow() - timedelta(seconds=130)
            }
        ]
        
        retry_manager.batch_state_repo.get_failed_batches = AsyncMock(return_value=failed_batches)
        retry_manager.batch_state_repo.update_batch_status = AsyncMock()
        retry_manager.batch_state_repo.audit_log = AsyncMock()
        
        mock_api_client.fetch_batch_data.return_value = [{'team_member_id': 'tm-1'}]
        
        # First batch succeeds, second fails
        mock_batch_processor.process_batch.side_effect = [True, False]
        
        successful, failed = await retry_manager.retry_failed_batches(
            batch_processor=mock_batch_processor,
            api_client=mock_api_client,
            correlation_id='retry-corr-1'
        )
        
        assert len(successful) == 1
        assert 'batch-1' in successful
        assert len(failed) == 1
        assert 'batch-2' in failed


class TestMarkBatchAbandoned:
    """Test batch abandonment marking."""
    
    @pytest.mark.asyncio
    async def test_mark_batch_abandoned(self, retry_manager):
        """Marking batch as ABANDONED should update status and log audit."""
        retry_manager.batch_state_repo.audit_log = AsyncMock()
        
        await retry_manager._mark_batch_abandoned(
            batch_id='batch-1',
            correlation_id='corr-1'
        )
        
        # Should execute UPDATE statement
        retry_manager.session.execute.assert_called_once()
        retry_manager.session.commit.assert_called_once()
        
        # Should log audit event
        retry_manager.batch_state_repo.audit_log.assert_called_once()
        call_args = retry_manager.batch_state_repo.audit_log.call_args[1]
        assert call_args['event_type'] == 'BATCH_ABANDONED'
        assert call_args['status'] == 'ABANDONED'
        assert call_args['severity'] == 'WARNING'
    
    @pytest.mark.asyncio
    async def test_abandoned_audit_details(self, retry_manager):
        """Abandoned batch audit should contain batch_id and max_retries."""
        retry_manager.batch_state_repo.audit_log = AsyncMock()
        
        await retry_manager._mark_batch_abandoned(
            batch_id='batch-1',
            correlation_id='corr-1'
        )
        
        call_args = retry_manager.batch_state_repo.audit_log.call_args[1]
        event_details = call_args['event_details']
        
        assert event_details['batch_id'] == 'batch-1'
        assert event_details['max_retries'] == 3


class TestRetryManagerConfiguration:
    """Test retry manager configuration options."""
    
    @pytest.mark.asyncio
    async def test_custom_max_retries(self, mock_session):
        """Custom max_retries should be respected."""
        manager = RetryManager(mock_session, max_retries=5, base_delay=60)
        
        batch = {
            'batch_id': 'batch-1',
            'status': 'FAILED',
            'metadata': {'retry_count': 4},
            'completed_at': datetime.utcnow() - timedelta(seconds=400)  # Enough time elapsed
        }
        
        # Should be eligible (4 < 5)
        eligible = await manager.should_retry_batch(batch)
        assert eligible is True
        
        batch['metadata']['retry_count'] = 5
        # Should not be eligible (5 >= 5)
        eligible = await manager.should_retry_batch(batch)
        assert eligible is False
    
    @pytest.mark.asyncio
    async def test_custom_base_delay_calculation(self, mock_session):
        """Custom base_delay should affect retry delay calculation."""
        manager = RetryManager(mock_session, max_retries=3, base_delay=120)
        
        delay = manager.calculate_retry_delay(1)
        assert delay == 120  # 120 * 2^0
        
        delay = manager.calculate_retry_delay(2)
        assert delay == 240  # 120 * 2^1
