"""Integration tests for batch processing with real PostgreSQL database.

Prerequisites:
--------------
1. PostgreSQL database must be running on localhost:5433
2. Database credentials must be configured in .env file:
   - DB_HOST=localhost
   - DB_PORT=5433
   - DB_NAME=ib_job_skill_mapping
   - DB_USER=postgres
   - DB_PASSWORD=<your_password>
3. Alembic migrations must be applied: `alembic upgrade head`

To run these tests:
------------------
pytest tests/cron/integration/test_batch_processing.py -v --tb=short

Expected: All 10 test scenarios pass in < 60 seconds
"""

import pytest
from datetime import datetime
from sqlalchemy import text, select
from sqlalchemy.orm import sessionmaker
from app.cron.db.engine import create_ingestion_engine
from app.cron.db.repositories import TeamMemberRepository, BatchStateRepository
from app.cron.processing.batch_processor import BatchProcessor


@pytest.fixture(scope="module")
def integration_engine():
    """Create real database engine for integration tests."""
    engine = create_ingestion_engine(validate_schema=False)
    yield engine
    engine.dispose()


@pytest.fixture
def session(integration_engine):
    """Create database session for each test with cleanup."""
    Session = sessionmaker(bind=integration_engine)
    session = Session()
    
    # Clean up test data before each test
    with integration_engine.begin() as conn:
        # Delete in reverse order of foreign key dependencies
        conn.execute(text("DELETE FROM team_member_team_member_skill_certification WHERE team_member_id LIKE 'test-%'"))
        conn.execute(text("DELETE FROM team_member_allocation WHERE team_member_id LIKE 'test-%'"))
        conn.execute(text("DELETE FROM team_member_skill WHERE team_member_id LIKE 'test-%'"))
        conn.execute(text("DELETE FROM team_member WHERE team_member_id LIKE 'test-%'"))
        conn.execute(text("DELETE FROM skill_master WHERE skill_id LIKE 'test-%'"))
        conn.execute(text("DELETE FROM category_master WHERE category_name LIKE 'Test%'"))
        conn.execute(text("DELETE FROM ingestion_audit_log WHERE correlation_id LIKE 'test-%'"))
        conn.execute(text("DELETE FROM ingestion_batch_state WHERE batch_id LIKE 'test-%'"))
        conn.commit()
    
    yield session
    
    session.close()


@pytest.fixture
def team_member_repo(session):
    """Create TeamMemberRepository instance."""
    return TeamMemberRepository(session)


@pytest.fixture
def batch_state_repo(session):
    """Create BatchStateRepository instance."""
    return BatchStateRepository(session)


@pytest.fixture
def batch_processor(team_member_repo, batch_state_repo):
    """Create BatchProcessor instance."""
    return BatchProcessor(team_member_repo, batch_state_repo)


class TestBatchProcessingIntegration:
    """Integration tests for end-to-end batch processing."""

    @pytest.mark.asyncio
    async def test_successful_batch_processing_end_to_end(
        self, session, batch_processor, batch_state_repo
    ):
        """Test successful batch processing with all data persisted correctly."""
        batch_id = "test-batch-001"
        correlation_id = "test-corr-001"
        
        team_members = [
            {
                "team_member_id": "test-tm-001",
                "name": "John Doe",
                "email": "john.doe@test.com",
                "work_type": "hybrid",
                "is_active": True,
                "profile_url": "https://example.com/john",
                "skills": [
                    {
                        "skill_id": "test-python",
                        "skill_name": "Python",
                        "category": "Test Programming",
                        "rating": 4.5,
                        "experience_in_months": 36,
                        "is_deleted": False,
                        "certifications": [
                            {"certification_name": "Python Certified Developer"}
                        ]
                    },
                    {
                        "skill_id": "test-java",
                        "skill_name": "Java",
                        "category": "Test Programming",
                        "rating": 4.0,
                        "experience_in_months": 24,
                        "is_deleted": False,
                        "certifications": []
                    }
                ],
                "allocations": [
                    {
                        "project_name": "Test Project A",
                        "allocation_percentage": 50,
                        "is_billable": True
                    }
                ]
            }
        ]
        
        metadata = {
            "batch_id": batch_id,
            "source": "integration_test",
            "timestamp": datetime.now().isoformat()
        }
        
        # Process the batch
        result = await batch_processor.process_batch(
            batch_id=batch_id,
            correlation_id=correlation_id,
            team_members=team_members,
            metadata=metadata
        )
        
        assert result is True
        
        # Verify batch state
        batch_state = session.execute(
            text("SELECT * FROM ingestion_batch_state WHERE batch_id = :batch_id"),
            {"batch_id": batch_id}
        ).fetchone()
        
        assert batch_state is not None
        assert batch_state.status == "SUCCESS"
        assert batch_state.total_records == 1
        assert batch_state.successful_records == 1
        assert batch_state.failed_records == 0
        assert batch_state.completed_at is not None
        
        # Verify category created
        category = session.execute(
            text("SELECT * FROM category_master WHERE category_name = :name"),
            {"name": "Test Programming"}
        ).fetchone()
        assert category is not None
        
        # Verify skills created
        skills = session.execute(
            text("SELECT * FROM skill_master WHERE skill_id IN ('test-python', 'test-java') ORDER BY skill_id")
        ).fetchall()
        assert len(skills) == 2
        assert skills[0].skill_name == "Java"
        assert skills[1].skill_name == "Python"
        
        # Verify team member created
        team_member = session.execute(
            text("SELECT * FROM team_member WHERE team_member_id = :id"),
            {"id": "test-tm-001"}
        ).fetchone()
        assert team_member is not None
        assert team_member.name == "John Doe"
        assert team_member.email == "john.doe@test.com"
        assert team_member.work_type == "hybrid"
        assert team_member.is_active is True
        
        # Verify team member skills created
        tm_skills = session.execute(
            text("SELECT * FROM team_member_skill WHERE team_member_id = :id ORDER BY skill_id"),
            {"id": "test-tm-001"}
        ).fetchall()
        assert len(tm_skills) == 2
        assert tm_skills[0].skill_id == "test-java"
        assert tm_skills[0].rating == 4.0
        assert tm_skills[1].skill_id == "test-python"
        assert tm_skills[1].rating == 4.5
        
        # Verify allocations created
        allocations = session.execute(
            text("SELECT * FROM team_member_allocation WHERE team_member_id = :id"),
            {"id": "test-tm-001"}
        ).fetchall()
        assert len(allocations) == 1
        assert allocations[0].project_name == "Test Project A"
        assert allocations[0].allocation_percentage == 50
        assert allocations[0].is_billable is True
        
        # Verify certifications created
        certifications = session.execute(
            text("SELECT * FROM team_member_team_member_skill_certification WHERE team_member_id = :id"),
            {"id": "test-tm-001"}
        ).fetchall()
        assert len(certifications) == 1
        assert certifications[0].skill_id == "test-python"
        assert certifications[0].certification_name == "Python Certified Developer"
        
        # Verify audit log entries
        audit_logs = session.execute(
            text("SELECT * FROM ingestion_audit_log WHERE correlation_id = :id ORDER BY created_at"),
            {"id": correlation_id}
        ).fetchall()
        assert len(audit_logs) >= 2  # At least BATCH_STARTED and BATCH_COMPLETED

    @pytest.mark.asyncio
    async def test_multiple_batches_processed_sequentially(
        self, session, batch_processor
    ):
        """Test processing multiple batches independently."""
        batches = [
            {
                "batch_id": "test-batch-002",
                "correlation_id": "test-corr-002",
                "team_members": [
                    {
                        "team_member_id": "test-tm-002",
                        "name": "Alice Smith",
                        "email": "alice@test.com",
                        "work_type": "wfh",
                        "is_active": True,
                        "skills": [
                            {
                                "skill_id": "test-react",
                                "skill_name": "React",
                                "category": "Test Frontend",
                                "rating": 4.8,
                                "experience_in_months": 48,
                                "is_deleted": False,
                                "certifications": []
                            }
                        ],
                        "allocations": []
                    }
                ]
            },
            {
                "batch_id": "test-batch-003",
                "correlation_id": "test-corr-003",
                "team_members": [
                    {
                        "team_member_id": "test-tm-003",
                        "name": "Bob Johnson",
                        "email": "bob@test.com",
                        "work_type": "wfo",
                        "is_active": True,
                        "skills": [
                            {
                                "skill_id": "test-nodejs",
                                "skill_name": "Node.js",
                                "category": "Test Backend",
                                "rating": 4.2,
                                "experience_in_months": 30,
                                "is_deleted": False,
                                "certifications": []
                            }
                        ],
                        "allocations": []
                    }
                ]
            }
        ]
        
        # Process batches
        for batch in batches:
            result = await batch_processor.process_batch(
                batch_id=batch["batch_id"],
                correlation_id=batch["correlation_id"],
                team_members=batch["team_members"],
                metadata={"batch_id": batch["batch_id"]}
            )
            assert result is True
        
        # Verify both batches succeeded
        batch_states = session.execute(
            text("SELECT * FROM ingestion_batch_state WHERE batch_id IN ('test-batch-002', 'test-batch-003') ORDER BY batch_id")
        ).fetchall()
        
        assert len(batch_states) == 2
        assert all(bs.status == "SUCCESS" for bs in batch_states)
        
        # Verify both team members created
        team_members = session.execute(
            text("SELECT * FROM team_member WHERE team_member_id IN ('test-tm-002', 'test-tm-003') ORDER BY team_member_id")
        ).fetchall()
        assert len(team_members) == 2

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(
        self, session, batch_processor
    ):
        """Test that transaction is rolled back when an error occurs."""
        batch_id = "test-batch-004"
        correlation_id = "test-corr-004"
        
        # Create invalid data (missing required field)
        team_members = [
            {
                "team_member_id": "test-tm-004",
                "name": "Invalid Member",
                "email": "invalid@test.com",
                "work_type": "hybrid",
                "is_active": True,
                "skills": [],
                "allocations": []
            },
            {
                # Missing team_member_id - should cause error
                "name": "Missing ID",
                "email": "missing@test.com",
                "work_type": "wfh",
                "is_active": True,
                "skills": [],
                "allocations": []
            }
        ]
        
        metadata = {"batch_id": batch_id}
        
        # Process should fail
        with pytest.raises(ValueError, match="team_member_id is required"):
            await batch_processor.process_batch(
                batch_id=batch_id,
                correlation_id=correlation_id,
                team_members=team_members,
                metadata=metadata
            )
        
        # Verify first member was NOT persisted (transaction rolled back)
        team_member = session.execute(
            text("SELECT * FROM team_member WHERE team_member_id = 'test-tm-004'")
        ).fetchone()
        assert team_member is None
        
        # Verify batch state marked as FAILED
        batch_state = session.execute(
            text("SELECT * FROM ingestion_batch_state WHERE batch_id = :batch_id"),
            {"batch_id": batch_id}
        ).fetchone()
        assert batch_state is not None
        assert batch_state.status == "FAILED"
        assert batch_state.error_message is not None

    @pytest.mark.asyncio
    async def test_idempotency_same_batch_processed_twice(
        self, session, batch_processor
    ):
        """Test that processing the same batch twice produces identical results."""
        batch_id = "test-batch-005"
        correlation_id = "test-corr-005"
        
        team_members = [
            {
                "team_member_id": "test-tm-005",
                "name": "Charlie Brown",
                "email": "charlie@test.com",
                "work_type": "hybrid",
                "is_active": True,
                "profile_url": "https://example.com/charlie",
                "skills": [
                    {
                        "skill_id": "test-sql",
                        "skill_name": "SQL",
                        "category": "Test Database",
                        "rating": 4.5,
                        "experience_in_months": 60,
                        "is_deleted": False,
                        "certifications": []
                    }
                ],
                "allocations": [
                    {
                        "project_name": "Test Project B",
                        "allocation_percentage": 100,
                        "is_billable": True
                    }
                ]
            }
        ]
        
        metadata = {"batch_id": batch_id}
        
        # Process batch first time
        result1 = await batch_processor.process_batch(
            batch_id=batch_id,
            correlation_id=correlation_id,
            team_members=team_members,
            metadata=metadata
        )
        assert result1 is True
        
        # Get counts after first processing
        category_count_1 = session.execute(
            text("SELECT COUNT(*) FROM category_master WHERE category_name = 'Test Database'")
        ).scalar()
        skill_count_1 = session.execute(
            text("SELECT COUNT(*) FROM skill_master WHERE skill_id = 'test-sql'")
        ).scalar()
        tm_count_1 = session.execute(
            text("SELECT COUNT(*) FROM team_member WHERE team_member_id = 'test-tm-005'")
        ).scalar()
        tm_skill_count_1 = session.execute(
            text("SELECT COUNT(*) FROM team_member_skill WHERE team_member_id = 'test-tm-005'")
        ).scalar()
        allocation_count_1 = session.execute(
            text("SELECT COUNT(*) FROM team_member_allocation WHERE team_member_id = 'test-tm-005'")
        ).scalar()
        
        # Update data for second processing
        team_members[0]["name"] = "Charlie Brown Updated"
        team_members[0]["skills"][0]["rating"] = 5.0
        
        # Process batch second time
        result2 = await batch_processor.process_batch(
            batch_id=batch_id + "-retry",
            correlation_id=correlation_id + "-retry",
            team_members=team_members,
            metadata={"batch_id": batch_id + "-retry"}
        )
        assert result2 is True
        
        # Get counts after second processing
        category_count_2 = session.execute(
            text("SELECT COUNT(*) FROM category_master WHERE category_name = 'Test Database'")
        ).scalar()
        skill_count_2 = session.execute(
            text("SELECT COUNT(*) FROM skill_master WHERE skill_id = 'test-sql'")
        ).scalar()
        tm_count_2 = session.execute(
            text("SELECT COUNT(*) FROM team_member WHERE team_member_id = 'test-tm-005'")
        ).scalar()
        tm_skill_count_2 = session.execute(
            text("SELECT COUNT(*) FROM team_member_skill WHERE team_member_id = 'test-tm-005'")
        ).scalar()
        allocation_count_2 = session.execute(
            text("SELECT COUNT(*) FROM team_member_allocation WHERE team_member_id = 'test-tm-005'")
        ).scalar()
        
        # Verify no duplicates created
        assert category_count_1 == category_count_2 == 1
        assert skill_count_1 == skill_count_2 == 1
        assert tm_count_1 == tm_count_2 == 1
        assert tm_skill_count_1 == tm_skill_count_2 == 1
        assert allocation_count_1 == allocation_count_2 == 1
        
        # Verify data was updated
        updated_member = session.execute(
            text("SELECT * FROM team_member WHERE team_member_id = 'test-tm-005'")
        ).fetchone()
        assert updated_member.name == "Charlie Brown Updated"
        
        updated_skill = session.execute(
            text("SELECT * FROM team_member_skill WHERE team_member_id = 'test-tm-005' AND skill_id = 'test-sql'")
        ).fetchone()
        assert updated_skill.rating == 5.0

    @pytest.mark.asyncio
    async def test_partial_data_handling(
        self, session, batch_processor
    ):
        """Test processing with minimal data (optional fields omitted)."""
        batch_id = "test-batch-006"
        correlation_id = "test-corr-006"
        
        team_members = [
            {
                "team_member_id": "test-tm-006",
                "name": "Diana Prince",
                "email": "diana@test.com",
                "work_type": "wfo",
                "is_active": True,
                # No profile_url
                "skills": [
                    {
                        "skill_id": "test-minimal",
                        "skill_name": "Minimal Skill",
                        "category": "Test Minimal",
                        "rating": 3.0,
                        "experience_in_months": 12,
                        "is_deleted": False,
                        "certifications": []  # Empty certifications
                    }
                ],
                "allocations": []  # Empty allocations
            }
        ]
        
        metadata = {"batch_id": batch_id}
        
        # Process should succeed even with minimal data
        result = await batch_processor.process_batch(
            batch_id=batch_id,
            correlation_id=correlation_id,
            team_members=team_members,
            metadata=metadata
        )
        
        assert result is True
        
        # Verify team member created with NULL profile_url
        team_member = session.execute(
            text("SELECT * FROM team_member WHERE team_member_id = 'test-tm-006'")
        ).fetchone()
        assert team_member is not None
        assert team_member.profile_url is None
        
        # Verify no allocations
        allocations = session.execute(
            text("SELECT COUNT(*) FROM team_member_allocation WHERE team_member_id = 'test-tm-006'")
        ).scalar()
        assert allocations == 0
        
        # Verify no certifications
        certifications = session.execute(
            text("SELECT COUNT(*) FROM team_member_team_member_skill_certification WHERE team_member_id = 'test-tm-006'")
        ).scalar()
        assert certifications == 0

    @pytest.mark.asyncio
    async def test_category_and_skill_creation(
        self, session, batch_processor
    ):
        """Test that categories and skills are created automatically."""
        batch_id = "test-batch-007"
        correlation_id = "test-corr-007"
        
        team_members = [
            {
                "team_member_id": "test-tm-007",
                "name": "Eve Adams",
                "email": "eve@test.com",
                "work_type": "hybrid",
                "is_active": True,
                "skills": [
                    {
                        "skill_id": "test-new-skill-1",
                        "skill_name": "Brand New Skill 1",
                        "category": "Test New Category",
                        "rating": 4.0,
                        "experience_in_months": 24,
                        "is_deleted": False,
                        "certifications": []
                    },
                    {
                        "skill_id": "test-new-skill-2",
                        "skill_name": "Brand New Skill 2",
                        "category": "Test New Category",  # Same category
                        "rating": 3.5,
                        "experience_in_months": 18,
                        "is_deleted": False,
                        "certifications": []
                    }
                ],
                "allocations": []
            }
        ]
        
        metadata = {"batch_id": batch_id}
        
        # Verify category doesn't exist before
        category_before = session.execute(
            text("SELECT COUNT(*) FROM category_master WHERE category_name = 'Test New Category'")
        ).scalar()
        assert category_before == 0
        
        # Process batch
        result = await batch_processor.process_batch(
            batch_id=batch_id,
            correlation_id=correlation_id,
            team_members=team_members,
            metadata=metadata
        )
        assert result is True
        
        # Verify category created
        category = session.execute(
            text("SELECT * FROM category_master WHERE category_name = 'Test New Category'")
        ).fetchone()
        assert category is not None
        
        # Verify both skills created with same category_id
        skills = session.execute(
            text("SELECT * FROM skill_master WHERE skill_id IN ('test-new-skill-1', 'test-new-skill-2') ORDER BY skill_id")
        ).fetchall()
        assert len(skills) == 2
        assert skills[0].category_id == category.category_id
        assert skills[1].category_id == category.category_id

    @pytest.mark.asyncio
    async def test_foreign_key_relationships(
        self, session, batch_processor
    ):
        """Test that foreign key relationships are maintained correctly."""
        batch_id = "test-batch-008"
        correlation_id = "test-corr-008"
        
        team_members = [
            {
                "team_member_id": "test-tm-008",
                "name": "Frank Miller",
                "email": "frank@test.com",
                "work_type": "wfh",
                "is_active": True,
                "skills": [
                    {
                        "skill_id": "test-fk-skill",
                        "skill_name": "FK Test Skill",
                        "category": "Test FK Category",
                        "rating": 4.0,
                        "experience_in_months": 24,
                        "is_deleted": False,
                        "certifications": [
                            {"certification_name": "FK Cert 1"},
                            {"certification_name": "FK Cert 2"}
                        ]
                    }
                ],
                "allocations": [
                    {
                        "project_name": "FK Project",
                        "allocation_percentage": 80,
                        "is_billable": True
                    }
                ]
            }
        ]
        
        metadata = {"batch_id": batch_id}
        
        # Process batch
        result = await batch_processor.process_batch(
            batch_id=batch_id,
            correlation_id=correlation_id,
            team_members=team_members,
            metadata=metadata
        )
        assert result is True
        
        # Get category_id
        category = session.execute(
            text("SELECT category_id FROM category_master WHERE category_name = 'Test FK Category'")
        ).fetchone()
        
        # Verify skill references category
        skill = session.execute(
            text("SELECT * FROM skill_master WHERE skill_id = 'test-fk-skill'")
        ).fetchone()
        assert skill.category_id == category.category_id
        
        # Verify team_member_skill references both team_member and skill
        tm_skill = session.execute(
            text("SELECT * FROM team_member_skill WHERE team_member_id = 'test-tm-008' AND skill_id = 'test-fk-skill'")
        ).fetchone()
        assert tm_skill is not None
        
        # Verify allocations reference team_member
        allocation = session.execute(
            text("SELECT * FROM team_member_allocation WHERE team_member_id = 'test-tm-008'")
        ).fetchone()
        assert allocation is not None
        
        # Verify certifications reference both team_member and skill
        certifications = session.execute(
            text("SELECT * FROM team_member_team_member_skill_certification WHERE team_member_id = 'test-tm-008' AND skill_id = 'test-fk-skill'")
        ).fetchall()
        assert len(certifications) == 2

    @pytest.mark.asyncio
    async def test_batch_state_tracking(
        self, session, batch_processor
    ):
        """Test that batch state is tracked throughout lifecycle."""
        batch_id = "test-batch-009"
        correlation_id = "test-corr-009"
        
        team_members = [
            {
                "team_member_id": "test-tm-009",
                "name": "Grace Hopper",
                "email": "grace@test.com",
                "work_type": "wfo",
                "is_active": True,
                "skills": [],
                "allocations": []
            }
        ]
        
        metadata = {
            "batch_id": batch_id,
            "source": "test_integration",
            "timestamp": datetime.now().isoformat()
        }
        
        # Process batch
        result = await batch_processor.process_batch(
            batch_id=batch_id,
            correlation_id=correlation_id,
            team_members=team_members,
            metadata=metadata
        )
        assert result is True
        
        # Verify batch state
        batch_state = session.execute(
            text("SELECT * FROM ingestion_batch_state WHERE batch_id = :batch_id"),
            {"batch_id": batch_id}
        ).fetchone()
        
        assert batch_state is not None
        assert batch_state.batch_id == batch_id
        assert batch_state.correlation_id == correlation_id
        assert batch_state.status == "SUCCESS"
        assert batch_state.total_records == 1
        assert batch_state.successful_records == 1
        assert batch_state.failed_records == 0
        assert batch_state.metadata is not None
        assert batch_state.metadata["source"] == "test_integration"
        assert batch_state.created_at is not None
        assert batch_state.completed_at is not None
        assert batch_state.error_message is None

    @pytest.mark.asyncio
    async def test_audit_log_entries(
        self, session, batch_processor
    ):
        """Test that audit log entries are created correctly."""
        batch_id = "test-batch-010"
        correlation_id = "test-corr-010"
        
        team_members = [
            {
                "team_member_id": "test-tm-010",
                "name": "Henry Ford",
                "email": "henry@test.com",
                "work_type": "hybrid",
                "is_active": True,
                "skills": [],
                "allocations": []
            }
        ]
        
        metadata = {"batch_id": batch_id}
        
        # Process batch
        result = await batch_processor.process_batch(
            batch_id=batch_id,
            correlation_id=correlation_id,
            team_members=team_members,
            metadata=metadata
        )
        assert result is True
        
        # Verify audit log entries
        audit_logs = session.execute(
            text("SELECT * FROM ingestion_audit_log WHERE correlation_id = :id ORDER BY created_at"),
            {"id": correlation_id}
        ).fetchall()
        
        assert len(audit_logs) >= 2
        
        # First entry should be batch started
        first_log = audit_logs[0]
        assert first_log.correlation_id == correlation_id
        assert first_log.batch_id == batch_id
        assert first_log.event_type in ["BATCH_STARTED", "BATCH_INITIALIZED"]
        assert first_log.created_at is not None
        
        # Last entry should be batch completed
        last_log = audit_logs[-1]
        assert last_log.correlation_id == correlation_id
        assert last_log.batch_id == batch_id
        assert last_log.event_type == "BATCH_COMPLETED"
