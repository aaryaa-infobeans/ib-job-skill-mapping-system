"""Integration tests for UPSERT idempotency validation.

Prerequisites:
--------------
1. PostgreSQL database must be running on localhost:5433
2. Database credentials configured in .env file
3. Alembic migrations applied: `alembic upgrade head`

Purpose:
--------
Validate that UPSERT operations are truly idempotent - processing the same data
multiple times should not create duplicate records in any table.

To run:
-------
pytest tests/cron/integration/test_upsert_idempotency.py -v --tb=short
"""

import pytest
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from app.cron.db.engine import create_ingestion_engine
from app.cron.db.repositories import TeamMemberRepository


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
        conn.execute(text("DELETE FROM skill_certification WHERE team_member_id LIKE 'idem-%'"))
        conn.execute(text("DELETE FROM team_member_allocation WHERE team_member_id LIKE 'idem-%'"))
        conn.execute(text("DELETE FROM team_member_skill WHERE team_member_id LIKE 'idem-%'"))
        conn.execute(text("DELETE FROM team_member WHERE team_member_id LIKE 'idem-%'"))
        conn.execute(text("DELETE FROM skill_master WHERE skill_id LIKE 'idem-%'"))
        conn.execute(text("DELETE FROM category_master WHERE category_name LIKE 'Idem%'"))
        conn.commit()
    
    yield session
    
    session.close()


@pytest.fixture
def team_member_repo(session):
    """Create TeamMemberRepository instance."""
    return TeamMemberRepository(session)


class TestCategoryIdempotency:
    """Test category UPSERT idempotency."""

    @pytest.mark.asyncio
    async def test_same_category_inserted_twice_returns_same_id(
        self, session, team_member_repo
    ):
        """Inserting the same category twice should return the same category_id."""
        # First insertion
        category_id_1 = await team_member_repo.upsert_category("Idempotency Test")
        
        # Second insertion (should not create duplicate)
        category_id_2 = await team_member_repo.upsert_category("Idempotency Test")
        
        # Should return same ID
        assert category_id_1 == category_id_2
        
        # Verify only one record exists
        count = session.execute(
            text("SELECT COUNT(*) FROM category_master WHERE category_name = 'Idempotency Test'")
        ).scalar()
        assert count == 1

    @pytest.mark.asyncio
    async def test_category_case_sensitivity(
        self, session, team_member_repo
    ):
        """Categories with different cases should create separate records."""
        category_id_1 = await team_member_repo.upsert_category("Idempotency Case")
        category_id_2 = await team_member_repo.upsert_category("idempotency case")
        
        # Different cases should create different records
        assert category_id_1 != category_id_2
        
        # Verify two records exist
        count = session.execute(
            text("SELECT COUNT(*) FROM category_master WHERE category_name LIKE 'Idem%case'")
        ).scalar()
        assert count == 2


class TestSkillIdempotency:
    """Test skill UPSERT idempotency."""

    @pytest.mark.asyncio
    async def test_same_skill_inserted_twice_returns_same_id(
        self, session, team_member_repo
    ):
        """Inserting the same skill twice should return the same skill_id."""
        category_id = await team_member_repo.upsert_category("Idempotency Skills")
        
        # First insertion
        await team_member_repo.upsert_skill("Idempotency Skill", category_id)
        
        # Second insertion
        await team_member_repo.upsert_skill("Idempotency Skill", category_id)
        
        # Verify only one record exists
        count = session.execute(
            text("SELECT COUNT(*) FROM skill_master WHERE skill_name = 'Idempotency Skill'")
        ).scalar()
        assert count == 1
        
        # Verify skill_id is correct
        skill = session.execute(
            text("SELECT skill_id FROM skill_master WHERE skill_name = 'Idempotency Skill'")
        ).fetchone()
        assert skill.skill_id == "idempotency-skill"

    @pytest.mark.asyncio
    async def test_skill_category_update_on_conflict(
        self, session, team_member_repo
    ):
        """When same skill inserted with different category, category should update."""
        category_id_1 = await team_member_repo.upsert_category("Idempotency Cat 1")
        category_id_2 = await team_member_repo.upsert_category("Idempotency Cat 2")
        
        # Insert with first category
        await team_member_repo.upsert_skill("Idem Update Skill", category_id_1)
        
        # Insert with second category (should update)
        await team_member_repo.upsert_skill("Idem Update Skill", category_id_2)
        
        # Verify only one record exists
        count = session.execute(
            text("SELECT COUNT(*) FROM skill_master WHERE skill_name = 'Idem Update Skill'")
        ).scalar()
        assert count == 1
        
        # Verify category was updated
        skill = session.execute(
            text("SELECT category_id FROM skill_master WHERE skill_name = 'Idem Update Skill'")
        ).fetchone()
        assert skill.category_id == category_id_2


class TestTeamMemberIdempotency:
    """Test team member UPSERT idempotency."""

    @pytest.mark.asyncio
    async def test_same_team_member_inserted_twice_updates_data(
        self, session, team_member_repo
    ):
        """Inserting same team member twice should update data, not create duplicate."""
        member_data_v1 = {
            "team_member_id": "idem-tm-001",
            "name": "Test Member V1",
            "email": "test@v1.com",
            "work_type": "wfh",
            "is_active": True
        }
        
        member_data_v2 = {
            "team_member_id": "idem-tm-001",
            "name": "Test Member V2 Updated",
            "email": "test@v2.com",
            "work_type": "hybrid",
            "is_active": False
        }
        
        # First insertion
        await team_member_repo.upsert_team_member(member_data_v1)
        
        # Second insertion (should update)
        await team_member_repo.upsert_team_member(member_data_v2)
        
        # Verify only one record exists
        count = session.execute(
            text("SELECT COUNT(*) FROM team_member WHERE team_member_id = 'idem-tm-001'")
        ).scalar()
        assert count == 1
        
        # Verify data was updated
        member = session.execute(
            text("SELECT * FROM team_member WHERE team_member_id = 'idem-tm-001'")
        ).fetchone()
        assert member.name == "Test Member V2 Updated"
        assert member.email == "test@v2.com"
        assert member.work_type == "hybrid"
        assert member.is_active is False


class TestTeamMemberSkillIdempotency:
    """Test team member skill junction table idempotency."""

    @pytest.mark.asyncio
    async def test_same_skill_for_team_member_twice_updates_data(
        self, session, team_member_repo
    ):
        """Same skill assigned to team member twice should update, not duplicate."""
        category_id = await team_member_repo.upsert_category("Idempotency TM Skills")
        await team_member_repo.upsert_skill("Idem TM Skill", category_id)
        
        member_data = {
            "team_member_id": "idem-tm-002",
            "name": "Skill Test Member",
            "email": "skills@test.com",
            "work_type": "wfo",
            "is_active": True
        }
        await team_member_repo.upsert_team_member(member_data)
        
        skills_v1 = [{
            "skill_id": "idem-tm-skill",
            "rating": 3.5,
            "experience_in_months": 12,
            "is_deleted": False
        }]
        
        skills_v2 = [{
            "skill_id": "idem-tm-skill",
            "rating": 4.5,
            "experience_in_months": 24,
            "is_deleted": False
        }]
        
        # First assignment
        await team_member_repo.upsert_team_member_skills("idem-tm-002", skills_v1, category_id)
        
        # Second assignment (should update)
        await team_member_repo.upsert_team_member_skills("idem-tm-002", skills_v2, category_id)
        
        # Verify only one record exists
        count = session.execute(
            text("SELECT COUNT(*) FROM team_member_skill WHERE team_member_id = 'idem-tm-002' AND skill_id = 'idem-tm-skill'")
        ).scalar()
        assert count == 1
        
        # Verify data was updated
        skill = session.execute(
            text("SELECT * FROM team_member_skill WHERE team_member_id = 'idem-tm-002' AND skill_id = 'idem-tm-skill'")
        ).fetchone()
        assert skill.rating == 4.5
        assert skill.experience_in_months == 24

    @pytest.mark.asyncio
    async def test_soft_delete_flag_toggling(
        self, session, team_member_repo
    ):
        """Soft delete flag should toggle on subsequent UPSERTs."""
        category_id = await team_member_repo.upsert_category("Idempotency Soft Delete")
        await team_member_repo.upsert_skill("Idem Soft Skill", category_id)
        
        member_data = {
            "team_member_id": "idem-tm-003",
            "name": "Soft Delete Test",
            "email": "soft@test.com",
            "work_type": "wfh",
            "is_active": True
        }
        await team_member_repo.upsert_team_member(member_data)
        
        # First: not deleted
        skills_active = [{
            "skill_id": "idem-soft-skill",
            "rating": 4.0,
            "experience_in_months": 18,
            "is_deleted": False
        }]
        await team_member_repo.upsert_team_member_skills("idem-tm-003", skills_active, category_id)
        
        skill = session.execute(
            text("SELECT is_deleted FROM team_member_skill WHERE team_member_id = 'idem-tm-003'")
        ).fetchone()
        assert skill.is_deleted is False
        
        # Second: soft deleted
        skills_deleted = [{
            "skill_id": "idem-soft-skill",
            "rating": 4.0,
            "experience_in_months": 18,
            "is_deleted": True
        }]
        await team_member_repo.upsert_team_member_skills("idem-tm-003", skills_deleted, category_id)
        
        skill = session.execute(
            text("SELECT is_deleted FROM team_member_skill WHERE team_member_id = 'idem-tm-003'")
        ).fetchone()
        assert skill.is_deleted is True


class TestAllocationIdempotency:
    """Test team member allocation idempotency."""

    @pytest.mark.asyncio
    async def test_same_allocation_twice_updates_data(
        self, session, team_member_repo
    ):
        """Same allocation inserted twice should update, not create duplicate."""
        member_data = {
            "team_member_id": "idem-tm-004",
            "name": "Allocation Test",
            "email": "alloc@test.com",
            "work_type": "hybrid",
            "is_active": True
        }
        await team_member_repo.upsert_team_member(member_data)
        
        allocations_v1 = [{
            "project_name": "Idem Project Alpha",
            "allocation_percentage": 50,
            "is_billable": True
        }]
        
        allocations_v2 = [{
            "project_name": "Idem Project Alpha",
            "allocation_percentage": 80,
            "is_billable": False
        }]
        
        # First allocation
        await team_member_repo.upsert_allocations("idem-tm-004", allocations_v1)
        
        # Second allocation (should update)
        await team_member_repo.upsert_allocations("idem-tm-004", allocations_v2)
        
        # Verify only one record exists
        count = session.execute(
            text("SELECT COUNT(*) FROM team_member_allocation WHERE team_member_id = 'idem-tm-004'")
        ).scalar()
        assert count == 1
        
        # Verify data was updated
        allocation = session.execute(
            text("SELECT * FROM team_member_allocation WHERE team_member_id = 'idem-tm-004'")
        ).fetchone()
        assert allocation.allocation_percentage == 80
        assert allocation.is_billable is False


class TestCertificationIdempotency:
    """Test skill certification idempotency."""

    @pytest.mark.asyncio
    async def test_same_certification_twice_no_duplicates(
        self, session, team_member_repo
    ):
        """Same certification inserted twice should not create duplicates."""
        category_id = await team_member_repo.upsert_category("Idempotency Certs")
        await team_member_repo.upsert_skill("Idem Cert Skill", category_id)
        
        member_data = {
            "team_member_id": "idem-tm-005",
            "name": "Cert Test",
            "email": "cert@test.com",
            "work_type": "wfo",
            "is_active": True
        }
        await team_member_repo.upsert_team_member(member_data)
        
        certifications = [{
            "certification_name": "Idem Certification Alpha"
        }]
        
        # First insertion
        await team_member_repo.upsert_certifications("idem-tm-005", certifications, category_id)
        
        # Second insertion (should not duplicate)
        await team_member_repo.upsert_certifications("idem-tm-005", certifications, category_id)
        
        # Verify only one record exists
        count = session.execute(
            text("SELECT COUNT(*) FROM skill_certification WHERE team_member_id = 'idem-tm-005' AND certification_name = 'Idem Certification Alpha'")
        ).scalar()
        assert count == 1


class TestFullBatchIdempotency:
    """Test full batch processing idempotency across all tables."""

    @pytest.mark.asyncio
    async def test_full_batch_processed_twice_no_duplicates(
        self, session, team_member_repo
    ):
        """Processing complete batch twice should result in identical database state."""
        # Define complete team member data
        category_id = await team_member_repo.upsert_category("Idempotency Full Batch")
        
        await team_member_repo.upsert_skill("Idem Batch Skill 1", category_id)
        await team_member_repo.upsert_skill("Idem Batch Skill 2", category_id)
        
        member_data = {
            "team_member_id": "idem-tm-006",
            "name": "Full Batch Test",
            "email": "fullbatch@test.com",
            "work_type": "hybrid",
            "is_active": True,
            "profile_url": "https://example.com/fullbatch"
        }
        
        skills = [
            {
                "skill_id": "idem-batch-skill-1",
                "rating": 4.5,
                "experience_in_months": 30,
                "is_deleted": False
            },
            {
                "skill_id": "idem-batch-skill-2",
                "rating": 4.0,
                "experience_in_months": 24,
                "is_deleted": False
            }
        ]
        
        allocations = [
            {
                "project_name": "Idem Batch Project X",
                "allocation_percentage": 60,
                "is_billable": True
            },
            {
                "project_name": "Idem Batch Project Y",
                "allocation_percentage": 40,
                "is_billable": False
            }
        ]
        
        certifications = [
            {"certification_name": "Idem Batch Cert 1"},
            {"certification_name": "Idem Batch Cert 2"}
        ]
        
        # Process batch first time
        await team_member_repo.upsert_team_member(member_data)
        await team_member_repo.upsert_team_member_skills("idem-tm-006", skills, category_id)
        await team_member_repo.upsert_allocations("idem-tm-006", allocations)
        await team_member_repo.upsert_certifications("idem-tm-006", certifications, category_id)
        
        session.commit()
        
        # Get counts after first processing
        category_count_1 = session.execute(
            text("SELECT COUNT(*) FROM category_master WHERE category_name = 'Idempotency Full Batch'")
        ).scalar()
        skill_count_1 = session.execute(
            text("SELECT COUNT(*) FROM skill_master WHERE skill_id LIKE 'idem-batch-skill-%'")
        ).scalar()
        tm_count_1 = session.execute(
            text("SELECT COUNT(*) FROM team_member WHERE team_member_id = 'idem-tm-006'")
        ).scalar()
        tm_skill_count_1 = session.execute(
            text("SELECT COUNT(*) FROM team_member_skill WHERE team_member_id = 'idem-tm-006'")
        ).scalar()
        allocation_count_1 = session.execute(
            text("SELECT COUNT(*) FROM team_member_allocation WHERE team_member_id = 'idem-tm-006'")
        ).scalar()
        cert_count_1 = session.execute(
            text("SELECT COUNT(*) FROM skill_certification WHERE team_member_id = 'idem-tm-006'")
        ).scalar()
        
        # Process batch second time (with updated data)
        member_data["name"] = "Full Batch Test Updated"
        skills[0]["rating"] = 5.0
        allocations[0]["allocation_percentage"] = 70
        
        await team_member_repo.upsert_team_member(member_data)
        await team_member_repo.upsert_team_member_skills("idem-tm-006", skills, category_id)
        await team_member_repo.upsert_allocations("idem-tm-006", allocations)
        await team_member_repo.upsert_certifications("idem-tm-006", certifications, category_id)
        
        session.commit()
        
        # Get counts after second processing
        category_count_2 = session.execute(
            text("SELECT COUNT(*) FROM category_master WHERE category_name = 'Idempotency Full Batch'")
        ).scalar()
        skill_count_2 = session.execute(
            text("SELECT COUNT(*) FROM skill_master WHERE skill_id LIKE 'idem-batch-skill-%'")
        ).scalar()
        tm_count_2 = session.execute(
            text("SELECT COUNT(*) FROM team_member WHERE team_member_id = 'idem-tm-006'")
        ).scalar()
        tm_skill_count_2 = session.execute(
            text("SELECT COUNT(*) FROM team_member_skill WHERE team_member_id = 'idem-tm-006'")
        ).scalar()
        allocation_count_2 = session.execute(
            text("SELECT COUNT(*) FROM team_member_allocation WHERE team_member_id = 'idem-tm-006'")
        ).scalar()
        cert_count_2 = session.execute(
            text("SELECT COUNT(*) FROM skill_certification WHERE team_member_id = 'idem-tm-006'")
        ).scalar()
        
        # Verify no duplicates created
        assert category_count_1 == category_count_2 == 1
        assert skill_count_1 == skill_count_2 == 2
        assert tm_count_1 == tm_count_2 == 1
        assert tm_skill_count_1 == tm_skill_count_2 == 2
        assert allocation_count_1 == allocation_count_2 == 2
        assert cert_count_1 == cert_count_2 == 2
        
        # Verify data was updated
        updated_member = session.execute(
            text("SELECT name FROM team_member WHERE team_member_id = 'idem-tm-006'")
        ).fetchone()
        assert updated_member.name == "Full Batch Test Updated"
        
        updated_skill = session.execute(
            text("SELECT rating FROM team_member_skill WHERE team_member_id = 'idem-tm-006' AND skill_id = 'idem-batch-skill-1'")
        ).fetchone()
        assert updated_skill.rating == 5.0
        
        updated_allocation = session.execute(
            text("SELECT allocation_percentage FROM team_member_allocation WHERE team_member_id = 'idem-tm-006' AND project_name = 'Idem Batch Project X'")
        ).fetchone()
        assert updated_allocation.allocation_percentage == 70


class TestNaturalKeyRespected:
    """Test that natural keys are properly respected in UPSERT operations."""

    @pytest.mark.asyncio
    async def test_category_natural_key_category_name(
        self, session, team_member_repo
    ):
        """Category natural key (category_name) should prevent duplicates."""
        await team_member_repo.upsert_category("Idempotency Natural Key Cat")
        await team_member_repo.upsert_category("Idempotency Natural Key Cat")
        
        count = session.execute(
            text("SELECT COUNT(*) FROM category_master WHERE category_name = 'Idempotency Natural Key Cat'")
        ).scalar()
        assert count == 1

    @pytest.mark.asyncio
    async def test_skill_natural_key_skill_id(
        self, session, team_member_repo
    ):
        """Skill natural key (skill_id) should prevent duplicates."""
        category_id = await team_member_repo.upsert_category("Idempotency Natural Key")
        
        await team_member_repo.upsert_skill("Natural Key Skill", category_id)
        await team_member_repo.upsert_skill("Natural Key Skill", category_id)
        
        count = session.execute(
            text("SELECT COUNT(*) FROM skill_master WHERE skill_id = 'natural-key-skill'")
        ).scalar()
        assert count == 1

    @pytest.mark.asyncio
    async def test_team_member_natural_key_team_member_id(
        self, session, team_member_repo
    ):
        """Team member natural key (team_member_id) should prevent duplicates."""
        member_data = {
            "team_member_id": "idem-natural-key",
            "name": "Natural Key Member",
            "email": "nk@test.com",
            "work_type": "wfh",
            "is_active": True
        }
        
        await team_member_repo.upsert_team_member(member_data)
        await team_member_repo.upsert_team_member(member_data)
        
        count = session.execute(
            text("SELECT COUNT(*) FROM team_member WHERE team_member_id = 'idem-natural-key'")
        ).scalar()
        assert count == 1

    @pytest.mark.asyncio
    async def test_team_member_skill_composite_key(
        self, session, team_member_repo
    ):
        """Team member skill composite key (team_member_id, skill_id) should prevent duplicates."""
        category_id = await team_member_repo.upsert_category("Idempotency Composite")
        await team_member_repo.upsert_skill("Composite Key Skill", category_id)
        
        member_data = {
            "team_member_id": "idem-composite",
            "name": "Composite Key Test",
            "email": "comp@test.com",
            "work_type": "hybrid",
            "is_active": True
        }
        await team_member_repo.upsert_team_member(member_data)
        
        skills = [{
            "skill_id": "composite-key-skill",
            "rating": 4.0,
            "experience_in_months": 12,
            "is_deleted": False
        }]
        
        await team_member_repo.upsert_team_member_skills("idem-composite", skills, category_id)
        await team_member_repo.upsert_team_member_skills("idem-composite", skills, category_id)
        
        count = session.execute(
            text("SELECT COUNT(*) FROM team_member_skill WHERE team_member_id = 'idem-composite' AND skill_id = 'composite-key-skill'")
        ).scalar()
        assert count == 1
