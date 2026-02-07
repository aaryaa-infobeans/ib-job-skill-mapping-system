"""
Retry manager for batch processing with exponential backoff.

Manages retry logic for failed batches with configurable max retries and
intelligent retry eligibility based on error classification.
"""

from typing import Dict, List, Any, Tuple, Optional
import structlog
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.cron.db.repositories import BatchStateRepository
from app.cron.processing.error_classifier import ErrorCategory, is_retryable
from app.cron.db.metadata import ingestion_batch_state


logger = structlog.get_logger(__name__)


class RetryManager:
    """
    Manage batch retry logic with exponential backoff.
    
    Features:
    - Exponential backoff calculation
    - Retry eligibility checks (error category + retry count)
    - Batch state transitions (FAILED → PROCESSING → SUCCESS/FAILED/ABANDONED)
    - Max retries enforcement
    - Abandoned batch marking
    """
    
    def __init__(
        self,
        session: AsyncSession,
        max_retries: int = 3,
        base_delay: int = 60
    ):
        """
        Initialize retry manager.
        
        Args:
            session: Async SQLAlchemy session for database operations
            max_retries: Maximum number of retry attempts (default: 3)
            base_delay: Base delay in seconds for exponential backoff (default: 60)
        """
        self.session = session
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.batch_state_repo = BatchStateRepository(session)
        self.logger = logger.bind(max_retries=max_retries, base_delay=base_delay)
    
    def calculate_retry_delay(self, retry_count: int) -> int:
        """
        Calculate retry delay using exponential backoff.
        
        Formula: base_delay * 2^(retry_count - 1)
        
        Examples:
            retry_count=1: 60 * 2^0 = 60 seconds
            retry_count=2: 60 * 2^1 = 120 seconds
            retry_count=3: 60 * 2^2 = 240 seconds
        
        Args:
            retry_count: Current retry attempt number (1-based)
        
        Returns:
            Delay in seconds
        
        Examples:
            >>> rm = RetryManager(session)
            >>> rm.calculate_retry_delay(1)
            60
            >>> rm.calculate_retry_delay(2)
            120
            >>> rm.calculate_retry_delay(3)
            240
        """
        if retry_count <= 0:
            return self.base_delay
        
        # Exponential backoff: base_delay * 2^(retry_count - 1)
        delay = self.base_delay * (2 ** (retry_count - 1))
        
        # Cap at 300 seconds (5 minutes)
        return min(delay, 300)
    
    async def should_retry_batch(self, batch: Dict[str, Any]) -> bool:
        """
        Determine if a batch should be retried.
        
        Criteria:
        1. Batch status is FAILED
        2. Error category is retryable (if available in metadata)
        3. Retry count < max_retries
        4. Minimum delay has passed since last attempt
        
        Args:
            batch: Batch data dict with keys:
                - batch_id
                - status
                - retry_count (from metadata)
                - error_category (from metadata)
                - completed_at (last failure timestamp)
        
        Returns:
            True if batch should be retried, False otherwise
        """
        batch_id = batch.get('batch_id')
        status = batch.get('status')
        
        # Only retry FAILED batches
        if status != 'FAILED':
            self.logger.debug(
                "Batch not eligible for retry: status not FAILED",
                batch_id=batch_id,
                status=status
            )
            return False
        
        # Check retry count
        metadata = batch.get('metadata', {})
        retry_count = metadata.get('retry_count', 0)
        
        if retry_count >= self.max_retries:
            self.logger.info(
                "Batch not eligible for retry: max retries exceeded",
                batch_id=batch_id,
                retry_count=retry_count,
                max_retries=self.max_retries
            )
            return False
        
        # Check error category (if available)
        error_category_str = metadata.get('error_category')
        if error_category_str:
            try:
                error_category = ErrorCategory(error_category_str)
                if not is_retryable(error_category):
                    self.logger.info(
                        "Batch not eligible for retry: error not retryable",
                        batch_id=batch_id,
                        error_category=error_category_str
                    )
                    return False
            except ValueError:
                # Invalid error category, allow retry
                self.logger.warning(
                    "Invalid error category in metadata, allowing retry",
                    batch_id=batch_id,
                    error_category=error_category_str
                )
        
        # Check if minimum delay has passed
        completed_at = batch.get('completed_at')
        if completed_at:
            required_delay = self.calculate_retry_delay(retry_count + 1)
            elapsed = (datetime.utcnow() - completed_at).total_seconds()
            
            if elapsed < required_delay:
                self.logger.debug(
                    "Batch not ready for retry: minimum delay not elapsed",
                    batch_id=batch_id,
                    elapsed_seconds=int(elapsed),
                    required_seconds=required_delay
                )
                return False
        
        self.logger.info(
            "Batch eligible for retry",
            batch_id=batch_id,
            retry_count=retry_count
        )
        return True
    
    async def retry_failed_batches(
        self,
        batch_processor: Any,
        api_client: Any,
        correlation_id: str
    ) -> Tuple[List[str], List[str]]:
        """
        Retry all eligible failed batches.
        
        Process:
        1. Fetch all FAILED batches
        2. Filter for retry eligibility
        3. For each eligible batch:
           - Fetch fresh data from API
           - Increment retry_count in metadata
           - Update status to PROCESSING
           - Call batch_processor.process_batch()
           - On success: status → SUCCESS
           - On failure: status → FAILED, check if should abandon
        4. Mark abandoned batches
        
        Args:
            batch_processor: BatchProcessor instance to retry batches
            api_client: API client to fetch fresh batch data
            correlation_id: Correlation ID for tracing
        
        Returns:
            Tuple of (successful_batch_ids, failed_batch_ids)
        """
        self.logger.info("Starting failed batch retry", correlation_id=correlation_id)
        
        # Fetch all FAILED batches
        failed_batches = await self.batch_state_repo.get_failed_batches(limit=100)
        
        self.logger.info(
            "Retrieved failed batches",
            count=len(failed_batches),
            correlation_id=correlation_id
        )
        
        # Filter for eligible batches
        eligible_batches = []
        for batch in failed_batches:
            if await self.should_retry_batch(batch):
                eligible_batches.append(batch)
        
        self.logger.info(
            "Filtered eligible batches for retry",
            eligible_count=len(eligible_batches),
            total_failed=len(failed_batches),
            correlation_id=correlation_id
        )
        
        successful = []
        failed = []
        
        for batch in eligible_batches:
            batch_id = batch['batch_id']
            
            try:
                # Fetch fresh data from API
                self.logger.info(
                    "Fetching fresh data for retry",
                    batch_id=batch_id,
                    correlation_id=correlation_id
                )
                
                # Get team members from API (batch_id should correspond to API payload)
                team_members = await api_client.fetch_batch_data(batch_id)
                
                # Increment retry count
                metadata = batch.get('metadata', {})
                retry_count = metadata.get('retry_count', 0) + 1
                metadata['retry_count'] = retry_count
                metadata['last_retry_at'] = datetime.utcnow().isoformat()
                
                self.logger.info(
                    "Retrying batch",
                    batch_id=batch_id,
                    retry_count=retry_count,
                    correlation_id=correlation_id
                )
                
                # Update status to PROCESSING
                await self.batch_state_repo.update_batch_status(
                    batch_id=batch_id,
                    status='PROCESSING'
                )
                
                # Retry batch processing
                success = await batch_processor.process_batch(
                    batch_id=batch_id,
                    correlation_id=correlation_id,
                    team_members=team_members,
                    metadata=metadata
                )
                
                if success:
                    successful.append(batch_id)
                    self.logger.info(
                        "Batch retry successful",
                        batch_id=batch_id,
                        retry_count=retry_count,
                        correlation_id=correlation_id
                    )
                else:
                    # Check if should abandon
                    if retry_count >= self.max_retries:
                        await self._mark_batch_abandoned(batch_id, correlation_id)
                    failed.append(batch_id)
                    
                    self.logger.warning(
                        "Batch retry failed",
                        batch_id=batch_id,
                        retry_count=retry_count,
                        will_abandon=retry_count >= self.max_retries,
                        correlation_id=correlation_id
                    )
            
            except Exception as error:
                # Increment retry count even on exception
                metadata = batch.get('metadata', {})
                retry_count = metadata.get('retry_count', 0) + 1
                
                # Check if should abandon
                if retry_count >= self.max_retries:
                    await self._mark_batch_abandoned(batch_id, correlation_id)
                
                failed.append(batch_id)
                
                self.logger.error(
                    "Batch retry error",
                    batch_id=batch_id,
                    error=str(error),
                    error_type=type(error).__name__,
                    retry_count=retry_count,
                    will_abandon=retry_count >= self.max_retries,
                    correlation_id=correlation_id
                )
        
        self.logger.info(
            "Failed batch retry completed",
            successful_count=len(successful),
            failed_count=len(failed),
            correlation_id=correlation_id
        )
        
        return successful, failed
    
    async def _mark_batch_abandoned(
        self,
        batch_id: str,
        correlation_id: str
    ) -> None:
        """
        Mark a batch as ABANDONED after max retries exceeded.
        
        Updates batch status to ABANDONED and logs audit event.
        
        Args:
            batch_id: Batch identifier
            correlation_id: Correlation ID for tracing
        """
        self.logger.warning(
            "Marking batch as ABANDONED",
            batch_id=batch_id,
            max_retries=self.max_retries,
            correlation_id=correlation_id
        )
        
        # Update status to ABANDONED
        stmt = update(ingestion_batch_state).where(
            ingestion_batch_state.c.batch_id == batch_id
        ).values(
            status='ABANDONED',
            completed_at=datetime.utcnow()
        )
        
        await self.session.execute(stmt)
        await self.session.commit()
        
        # Audit log
        await self.batch_state_repo.audit_log(
            correlation_id=correlation_id,
            event_type='BATCH_ABANDONED',
            status='ABANDONED',
            message=f'Batch {batch_id} abandoned after {self.max_retries} failed retries',
            event_details={
                'batch_id': batch_id,
                'max_retries': self.max_retries,
            },
            severity='WARNING'
        )
        
        self.logger.warning(
            "Batch marked as ABANDONED",
            batch_id=batch_id,
            correlation_id=correlation_id
        )
