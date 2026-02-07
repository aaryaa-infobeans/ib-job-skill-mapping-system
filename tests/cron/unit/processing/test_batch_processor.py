"""
Unit tests for BatchProcessor.

Tests transaction isolation, state management, and error handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.app.cron.processing.batch_processor import BatchProcessor


@pytest.fixture
def mock_session():
    """Create mock async session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_team_member_repo():
    """Create mock TeamMemberRepository."""
    repo = AsyncMock()
    repo.upsert_category = AsyncMock(return_value=1)
    repo.upsert_skill = AsyncMock(return_value='python')
    repo.upsert_team_member = AsyncMock(return_value='TM001')
    repo.upsert_team_member_skills = AsyncMock()
    repo.upsert_allocations = AsyncMock()
    repo.upsert_certifications = AsyncMock()
    return repo


@pytest.fixture
def mock_batch_state_repo():
    """Create mock BatchStateRepository."""
    repo = AsyncMock()
    repo.initialize_batch = AsyncMock()
    repo.update_batch_status = AsyncMock()
    repo.audit_log = AsyncMock()
    return repo


@pytest.fixture
def batch_processor(mock_session, mock_team_member_repo, mock_batch_state_repo):
    """Create BatchProcessor with mocked dependencies."""
    processor = BatchProcessor(mock_session, dry_run=False)
    processor.team_member_repo = mock_team_member_repo
    processor.batch_state_repo = mock_batch_state_repo
    return processor


@pytest.fixture
def sample_team_member():
    """Sample team member data."""
    return {
        'team_member_id': 'TM001',
        'designation': 'Senior Engineer',
        'profile_type': 'Technical',
        'team_member_status': 'active',
        'experience_in_months': 60,
        'base_location': 'Bangalore',
        'work-mode': 'HYBRID',
        'profile': 'https://example.com/profile',
        'skills': [
            {
                'skill_name': 'Python',
                'category': 'Engineering',
                'rating': 5,
                'experience_in_months': 36,
                'is_deleted': False,
                'certifications': [
                    {
                        'certification_id': 'CERT001',
                        'certificate': 'Python Professional',
                        'issuer': 'Python Institute',
                        'issued_date': '2023-01-01',
                        'valid_till': '2025-01-01'
                    }
                ]
            },
            {
                'skill_name': 'Java',
                'category': 'Engineering',
                'rating': 4,
                'experience_in_months': 24,
                'is_deleted': False,
                'certifications': []
            }
        ],
        'allocations': [
            {
                'project_id': 'P001',
                'allocation_percentage': 50.0,
                'start_date': '2024-01-01',
                'end_date': '2024-12-31',
                'billable': True,
                'is_deleted': False
            }
        ]
    }


# ===== Test process_batch =====

class TestProcessBatch:
    """Tests for BatchProcessor.process_batch()"""
    
    @pytest.mark.asyncio
    async def test_successful_batch_processing(
        self,
        batch_processor,
        mock_session,
        mock_batch_state_repo,
        sample_team_member
    ):
        """Test successful processing of a batch."""
        batch_id = 'BATCH001'
        correlation_id = 'CORR001'
        team_members = [sample_team_member]
        
        result = await batch_processor.process_batch(
            batch_id=batch_id,
            correlation_id=correlation_id,
            team_members=team_members
        )
        
        assert result is True
        
        # Verify batch state transitions
        mock_batch_state_repo.initialize_batch.assert_called_once_with(
            batch_id=batch_id,
            correlation_id=correlation_id,
            total_records=1,
            metadata={}
        )
        
        # Verify PROCESSING status update
        assert mock_batch_state_repo.update_batch_status.call_count == 2
        first_call = mock_batch_state_repo.update_batch_status.call_args_list[0]
        assert first_call[1]['batch_id'] == batch_id
        assert first_call[1]['status'] == 'PROCESSING'
        
        # Verify SUCCESS status update
        second_call = mock_batch_state_repo.update_batch_status.call_args_list[1]
        assert second_call[1]['batch_id'] == batch_id
        assert second_call[1]['status'] == 'SUCCESS'
        assert second_call[1]['processed_records'] == 1
        assert second_call[1]['failed_records'] == 0
        
        # Verify transaction committed
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_batch_processing_with_multiple_members(
        self,
        batch_processor,
        mock_session,
        sample_team_member
    ):
        """Test processing batch with multiple team members."""
        team_members = [
            {**sample_team_member, 'team_member_id': 'TM001'},
            {**sample_team_member, 'team_member_id': 'TM002'},
            {**sample_team_member, 'team_member_id': 'TM003'}
        ]
        
        result = await batch_processor.process_batch(
            batch_id='BATCH001',
            correlation_id='CORR001',
            team_members=team_members
        )
        
        assert result is True
        
        # Verify all team members processed
        assert batch_processor.team_member_repo.upsert_team_member.call_count == 3
        
        # Verify transaction committed once
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_batch_processing_empty_batch(
        self,
        batch_processor,
        mock_session,
        mock_batch_state_repo
    ):
        """Test processing empty batch."""
        result = await batch_processor.process_batch(
            batch_id='BATCH001',
            correlation_id='CORR001',
            team_members=[]
        )
        
        assert result is True
        
        # Verify SUCCESS with 0 processed records
        success_call = mock_batch_state_repo.update_batch_status.call_args_list[1]
        assert success_call[1]['processed_records'] == 0
        
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_batch_processing_with_metadata(
        self,
        batch_processor,
        mock_batch_state_repo,
        sample_team_member
    ):
        """Test processing batch with metadata."""
        metadata = {'source': 'external_api', 'version': '1.0'}
        
        result = await batch_processor.process_batch(
            batch_id='BATCH001',
            correlation_id='CORR001',
            team_members=[sample_team_member],
            metadata=metadata
        )
        
        assert result is True
        
        # Verify metadata passed to initialize_batch
        mock_batch_state_repo.initialize_batch.assert_called_once()
        call_kwargs = mock_batch_state_repo.initialize_batch.call_args[1]
        assert call_kwargs['metadata'] == metadata
    
    @pytest.mark.asyncio
    async def test_batch_processing_rollback_on_error(
        self,
        batch_processor,
        mock_session,
        mock_batch_state_repo,
        sample_team_member
    ):
        """Test transaction rollback on processing error."""
        # Simulate error during team member processing
        batch_processor.team_member_repo.upsert_team_member.side_effect = \
            ValueError("Invalid data")
        
        with pytest.raises(ValueError, match="Invalid data"):
            await batch_processor.process_batch(
                batch_id='BATCH001',
                correlation_id='CORR001',
                team_members=[sample_team_member]
            )
        
        # Verify rollback called
        mock_session.rollback.assert_called()
        
        # Verify batch marked as failed (in separate transaction)
        assert mock_batch_state_repo.update_batch_status.call_count >= 2
        
        # Verify commit NOT called for main transaction
        assert mock_session.commit.call_count <= 1  # Only for _mark_batch_failed
    
    @pytest.mark.asyncio
    async def test_dry_run_mode(
        self,
        mock_session,
        mock_team_member_repo,
        mock_batch_state_repo,
        sample_team_member
    ):
        """Test dry run mode rolls back changes."""
        processor = BatchProcessor(mock_session, dry_run=True)
        processor.team_member_repo = mock_team_member_repo
        processor.batch_state_repo = mock_batch_state_repo
        
        result = await processor.process_batch(
            batch_id='BATCH001',
            correlation_id='CORR001',
            team_members=[sample_team_member]
        )
        
        assert result is True
        
        # Verify processing occurred
        mock_team_member_repo.upsert_team_member.assert_called_once()
        
        # Verify rollback called (not commit)
        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()


# ===== Test process_all_batches =====

class TestProcessAllBatches:
    """Tests for BatchProcessor.process_all_batches()"""
    
    @pytest.mark.asyncio
    async def test_process_multiple_batches(
        self,
        batch_processor,
        sample_team_member
    ):
        """Test processing multiple batches."""
        payload = {
            'metadata': {'correlation_id': 'CORR001'},
            'batches': [
                {
                    'batch_id': 'BATCH001',
                    'team_members': [sample_team_member]
                },
                {
                    'batch_id': 'BATCH002',
                    'team_members': [sample_team_member]
                }
            ]
        }
        
        successful, failed = await batch_processor.process_all_batches(payload)
        
        assert len(successful) == 2
        assert len(failed) == 0
        assert 'BATCH001' in successful
        assert 'BATCH002' in successful
    
    @pytest.mark.asyncio
    async def test_process_batches_with_failures(
        self,
        batch_processor,
        sample_team_member
    ):
        """Test processing batches where some fail."""
        payload = {
            'metadata': {'correlation_id': 'CORR001'},
            'batches': [
                {
                    'batch_id': 'BATCH001',
                    'team_members': [sample_team_member]
                },
                {
                    'batch_id': 'BATCH002',
                    'team_members': [sample_team_member]
                }
            ]
        }
        
        # Simulate error for second batch
        call_count = 0
        original_process_batch = batch_processor.process_batch
        
        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise ValueError("Processing error")
            return await original_process_batch(*args, **kwargs)
        
        batch_processor.process_batch = AsyncMock(side_effect=side_effect)
        
        successful, failed = await batch_processor.process_all_batches(payload)
        
        assert len(successful) == 1
        assert len(failed) == 1
        assert 'BATCH001' in successful
        assert 'BATCH002' in failed
    
    @pytest.mark.asyncio
    async def test_process_batches_skips_missing_batch_id(
        self,
        batch_processor,
        sample_team_member
    ):
        """Test processing skips batches without batch_id."""
        payload = {
            'metadata': {'correlation_id': 'CORR001'},
            'batches': [
                {
                    'batch_id': 'BATCH001',
                    'team_members': [sample_team_member]
                },
                {
                    # Missing batch_id
                    'team_members': [sample_team_member]
                },
                {
                    'batch_id': 'BATCH003',
                    'team_members': [sample_team_member]
                }
            ]
        }
        
        successful, failed = await batch_processor.process_all_batches(payload)
        
        assert len(successful) == 2
        assert len(failed) == 0
        assert 'BATCH001' in successful
        assert 'BATCH003' in successful
    
    @pytest.mark.asyncio
    async def test_process_empty_batches_list(
        self,
        batch_processor
    ):
        """Test processing payload with empty batches list."""
        payload = {
            'metadata': {'correlation_id': 'CORR001'},
            'batches': []
        }
        
        successful, failed = await batch_processor.process_all_batches(payload)
        
        assert len(successful) == 0
        assert len(failed) == 0


# ===== Test _process_team_member =====

class TestProcessTeamMember:
    """Tests for BatchProcessor._process_team_member()"""
    
    @pytest.mark.asyncio
    async def test_process_team_member_with_all_data(
        self,
        batch_processor,
        mock_team_member_repo,
        sample_team_member
    ):
        """Test processing team member with complete data."""
        await batch_processor._process_team_member(sample_team_member)
        
        # Verify category upserted
        mock_team_member_repo.upsert_category.assert_called_once_with('Engineering')
        
        # Verify team member upserted
        mock_team_member_repo.upsert_team_member.assert_called_once_with(
            sample_team_member
        )
        
        # Verify skills upserted
        mock_team_member_repo.upsert_team_member_skills.assert_called_once()
        skills_call = mock_team_member_repo.upsert_team_member_skills.call_args[1]
        assert skills_call['team_member_id'] == 'TM001'
        assert len(skills_call['skills']) == 2
        
        # Verify allocations upserted
        mock_team_member_repo.upsert_allocations.assert_called_once()
        alloc_call = mock_team_member_repo.upsert_allocations.call_args[1]
        assert alloc_call['team_member_id'] == 'TM001'
        assert len(alloc_call['allocations']) == 1
        
        # Verify certifications upserted
        mock_team_member_repo.upsert_certifications.assert_called_once()
        cert_call = mock_team_member_repo.upsert_certifications.call_args[1]
        assert cert_call['team_member_id'] == 'TM001'
        assert len(cert_call['certifications']) == 1
    
    @pytest.mark.asyncio
    async def test_process_team_member_without_skills(
        self,
        batch_processor,
        mock_team_member_repo
    ):
        """Test processing team member without skills."""
        member_data = {
            'team_member_id': 'TM001',
            'designation': 'Engineer',
            'skills': [],
            'allocations': []
        }
        
        await batch_processor._process_team_member(member_data)
        
        # Verify default category used
        mock_team_member_repo.upsert_category.assert_called_once_with('Uncategorized')
        
        # Verify team member upserted
        mock_team_member_repo.upsert_team_member.assert_called_once()
        
        # Verify skills NOT upserted (empty list)
        mock_team_member_repo.upsert_team_member_skills.assert_not_called()
        
        # Verify allocations NOT upserted (empty list)
        mock_team_member_repo.upsert_allocations.assert_not_called()
        
        # Verify certifications NOT upserted (no skills)
        mock_team_member_repo.upsert_certifications.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_team_member_missing_id_raises(
        self,
        batch_processor
    ):
        """Test processing team member without team_member_id raises error."""
        member_data = {
            'designation': 'Engineer',
            'skills': []
        }
        
        with pytest.raises(ValueError, match="team_member_id is required"):
            await batch_processor._process_team_member(member_data)
    
    @pytest.mark.asyncio
    async def test_process_team_member_with_certifications_from_multiple_skills(
        self,
        batch_processor,
        mock_team_member_repo
    ):
        """Test certifications extracted from multiple skills."""
        member_data = {
            'team_member_id': 'TM001',
            'skills': [
                {
                    'skill_name': 'Python',
                    'category': 'Engineering',
                    'certifications': [
                        {'certification_id': 'CERT001', 'certificate': 'Python Pro'}
                    ]
                },
                {
                    'skill_name': 'Java',
                    'category': 'Engineering',
                    'certifications': [
                        {'certification_id': 'CERT002', 'certificate': 'Java Expert'}
                    ]
                }
            ],
            'allocations': []
        }
        
        await batch_processor._process_team_member(member_data)
        
        # Verify certifications called with both certs
        mock_team_member_repo.upsert_certifications.assert_called_once()
        cert_call = mock_team_member_repo.upsert_certifications.call_args[1]
        assert len(cert_call['certifications']) == 2
        
        # Verify skill_name added to certifications
        cert_list = cert_call['certifications']
        assert cert_list[0]['skill_name'] == 'Python'
        assert cert_list[1]['skill_name'] == 'Java'


# ===== Test _mark_batch_failed =====

class TestMarkBatchFailed:
    """Tests for BatchProcessor._mark_batch_failed()"""
    
    @pytest.mark.asyncio
    async def test_mark_batch_failed_updates_status(
        self,
        batch_processor,
        mock_session,
        mock_batch_state_repo
    ):
        """Test marking batch as failed."""
        await batch_processor._mark_batch_failed(
            batch_id='BATCH001',
            correlation_id='CORR001',
            error_message='Database connection lost'
        )
        
        # Verify status updated to FAILED
        mock_batch_state_repo.update_batch_status.assert_called_once_with(
            batch_id='BATCH001',
            status='FAILED',
            error_message='Database connection lost'
        )
        
        # Verify commit called (separate transaction)
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_mark_batch_failed_swallows_exception(
        self,
        batch_processor,
        mock_batch_state_repo
    ):
        """Test marking batch as failed swallows exceptions."""
        # Simulate error during status update
        mock_batch_state_repo.update_batch_status.side_effect = \
            Exception("Status update failed")
        
        # Should not raise exception
        await batch_processor._mark_batch_failed(
            batch_id='BATCH001',
            correlation_id='CORR001',
            error_message='Original error'
        )
        
        # Exception logged but not raised


# ===== Test Transaction Isolation =====

class TestTransactionIsolation:
    """Tests for transaction isolation guarantees."""
    
    @pytest.mark.asyncio
    async def test_transaction_isolation_on_partial_failure(
        self,
        batch_processor,
        mock_session,
        mock_team_member_repo,
        sample_team_member
    ):
        """Test transaction rollback on partial batch failure."""
        team_members = [
            {**sample_team_member, 'team_member_id': 'TM001'},
            {**sample_team_member, 'team_member_id': 'TM002'},
            {**sample_team_member, 'team_member_id': 'TM003'}
        ]
        
        # Simulate error on third member
        call_count = 0
        
        async def side_effect(member_data):
            nonlocal call_count
            call_count += 1
            if call_count == 3:
                raise ValueError("Validation error")
        
        mock_team_member_repo.upsert_team_member.side_effect = side_effect
        
        with pytest.raises(ValueError):
            await batch_processor.process_batch(
                batch_id='BATCH001',
                correlation_id='CORR001',
                team_members=team_members
            )
        
        # Verify rollback called
        mock_session.rollback.assert_called()
        
        # Verify first two members processed before failure
        assert mock_team_member_repo.upsert_team_member.call_count == 3
    
    @pytest.mark.asyncio
    async def test_state_transitions_on_error(
        self,
        batch_processor,
        mock_batch_state_repo,
        sample_team_member
    ):
        """Test state transitions during error scenarios."""
        # Simulate error during processing
        batch_processor.team_member_repo.upsert_team_member.side_effect = \
            Exception("Processing error")
        
        with pytest.raises(Exception):
            await batch_processor.process_batch(
                batch_id='BATCH001',
                correlation_id='CORR001',
                team_members=[sample_team_member]
            )
        
        # Verify state transitions:
        # 1. initialize_batch (PENDING)
        # 2. update_batch_status (PROCESSING)
        # 3. update_batch_status (FAILED) - in _mark_batch_failed
        
        assert mock_batch_state_repo.initialize_batch.call_count == 1
        assert mock_batch_state_repo.update_batch_status.call_count >= 2
        
        # Last call should be FAILED status
        last_call = mock_batch_state_repo.update_batch_status.call_args_list[-1]
        assert last_call[1]['status'] == 'FAILED'
