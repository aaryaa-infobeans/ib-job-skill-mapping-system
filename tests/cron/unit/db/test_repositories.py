"""
Unit tests for database repositories.

Tests UPSERT operations, natural key conflicts, and state management.
"""

import pytest
from datetime import datetime, date
from sqlalchemy import select, MetaData, Table, Column, String, Integer, SmallInteger, Boolean, Date, DateTime, Text, ForeignKey, Numeric, CHAR
from sqlalchemy.dialects.postgresql import ENUM as SAEnum, JSON, JSONB
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.cron.db.repositories import TeamMemberRepository, BatchStateRepository
from app.cron.db.metadata import WorkTypeEnum


# Test database URL (in-memory SQLite for unit tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# Create test-compatible metadata (SQLite doesn't support JSONB)
metadata = MetaData()

# Ingestion tables
ingestion_batch_state = Table(
    "ingestion_batch_state",
    metadata,
    Column("batch_id", String(100), primary_key=True),
    Column("correlation_id", String(100), nullable=False, index=True),
    Column("status", String(20), nullable=False, index=True),
    Column("total_records", Integer, nullable=True),
    Column("processed_records", Integer, nullable=True),
    Column("failed_records", Integer, nullable=True),
    Column("started_at", DateTime, nullable=False, default=datetime.utcnow),
    Column("completed_at", DateTime, nullable=True),
    Column("error_message", Text, nullable=True),
    Column("metadata", JSON, nullable=True),  # JSON instead of JSONB for SQLite
)

ingestion_audit_log = Table(
    "ingestion_audit_log",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("batch_id", String(100), ForeignKey("ingestion_batch_state.batch_id", ondelete="CASCADE"), nullable=True),
    Column("correlation_id", String(100), nullable=False, index=True),
    Column("event_type", String(50), nullable=False),
    Column("status", String(20), nullable=False),
    Column("message", Text, nullable=False),
    Column("event_details", JSON, nullable=True),  # JSON instead of JSONB for SQLite
    Column("timestamp", DateTime, nullable=False, default=datetime.utcnow, index=True),
    Column("severity", String(20), nullable=True),
    Column("source", String(100), nullable=True),
)

# Master tables
category_master = Table(
    "category_master",
    metadata,
    Column("category_id", SmallInteger, primary_key=True, autoincrement=True),
    Column("category_name", String(100), nullable=False, unique=True),
    Column("created_at", DateTime, default=datetime.utcnow),
)

skill_master = Table(
    "skill_master",
    metadata,
    Column("skill_id", String(50), primary_key=True),
    Column("skill_name", String(100), nullable=False, unique=True),
    Column("category_id", SmallInteger, ForeignKey("category_master.category_id"), nullable=False),
    Column("created_at", DateTime, default=datetime.utcnow),
)

# Team member tables
team_member = Table(
    "team_member",
    metadata,
    Column("team_member_id", String(50), primary_key=True),
    Column("designation", String(100), nullable=True),
    Column("profile_type", String(50), nullable=True),
    Column("is_active", Boolean, default=True),
    Column("experience_in_months", Integer, nullable=True),
    Column("base_location", String(100), nullable=True),
    Column("work_type", String(20), nullable=True),  # Simplified for SQLite
    Column("profile_url", String(1024), nullable=True),
    Column("created_at", DateTime, default=datetime.utcnow),
)

team_member_allocation = Table(
    "team_member_allocation",
    metadata,
    Column("team_member_id", String(50), ForeignKey("team_member.team_member_id"), primary_key=True),
    Column("project_id", String(50), primary_key=True),
    Column("allocation_percentage", Numeric(5, 2), nullable=True),
    Column("start_date", Date, nullable=True),
    Column("end_date", Date, nullable=True),
    Column("billable", Boolean, nullable=True),
    Column("is_deleted", Boolean, default=False),
)

team_member_skill = Table(
    "team_member_skill",
    metadata,
    Column("team_member_id", String(50), ForeignKey("team_member.team_member_id"), primary_key=True),
    Column("skill_id", String(50), ForeignKey("skill_master.skill_id"), primary_key=True),
    Column("rating", Integer, nullable=True),
    Column("experience_in_months", Integer, nullable=True),
    Column("is_deleted", Boolean, default=False),
)

team_member_team_member_skill_certification = Table(
    "team_member_team_member_skill_certification",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("certification_id", String(100), nullable=True),
    Column("team_member_id", String(50), nullable=False),
    Column("skill_id", String(50), nullable=False),
    Column("certificate", String(150), nullable=True),
    Column("issuer", String(100), nullable=True),
    Column("issued_date", Date, nullable=True),
    Column("valid_till", Date, nullable=True),
)


@pytest.fixture
async def engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest.fixture
async def session(engine):
    """Create test database session."""
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as sess:
        yield sess
        await sess.rollback()


@pytest.fixture
def team_member_repo(session):
    """Create TeamMemberRepository instance."""
    return TeamMemberRepository(session)


@pytest.fixture
def batch_state_repo(session):
    """Create BatchStateRepository instance."""
    return BatchStateRepository(session)


# ===== TeamMemberRepository Tests =====

class TestUpsertCategory:
    """Tests for TeamMemberRepository.upsert_category()"""
    
    @pytest.mark.asyncio
    async def test_insert_new_category(self, session, team_member_repo):
        """Test inserting a new category."""
        category_id = await team_member_repo.upsert_category("Engineering")
        await session.commit()
        
        assert isinstance(category_id, int)
        assert category_id > 0
        
        # Verify in database
        stmt = select(category_master).where(category_master.c.category_id == category_id)
        result = await session.execute(stmt)
        row = result.fetchone()
        
        assert row is not None
        assert row.category_name == "Engineering"
    
    @pytest.mark.asyncio
    async def test_upsert_duplicate_category(self, session, team_member_repo):
        """Test upserting duplicate category returns same ID."""
        category_id_1 = await team_member_repo.upsert_category("Engineering")
        await session.commit()
        
        category_id_2 = await team_member_repo.upsert_category("Engineering")
        await session.commit()
        
        assert category_id_1 == category_id_2
    
    @pytest.mark.asyncio
    async def test_upsert_category_case_sensitive(self, session, team_member_repo):
        """Test category names are case-sensitive."""
        category_id_1 = await team_member_repo.upsert_category("Engineering")
        await session.commit()
        
        category_id_2 = await team_member_repo.upsert_category("engineering")
        await session.commit()
        
        assert category_id_1 != category_id_2
    
    @pytest.mark.asyncio
    async def test_upsert_category_trims_whitespace(self, session, team_member_repo):
        """Test category names are trimmed."""
        category_id_1 = await team_member_repo.upsert_category("  Engineering  ")
        await session.commit()
        
        # Verify stored without whitespace
        stmt = select(category_master).where(category_master.c.category_id == category_id_1)
        result = await session.execute(stmt)
        row = result.fetchone()
        
        assert row.category_name == "Engineering"
    
    @pytest.mark.asyncio
    async def test_upsert_category_empty_name_raises(self, team_member_repo):
        """Test empty category name raises ValueError."""
        with pytest.raises(ValueError, match="category_name cannot be empty"):
            await team_member_repo.upsert_category("")
    
    @pytest.mark.asyncio
    async def test_upsert_category_whitespace_only_raises(self, team_member_repo):
        """Test whitespace-only category name raises ValueError."""
        with pytest.raises(ValueError, match="category_name cannot be empty"):
            await team_member_repo.upsert_category("   ")


class TestUpsertSkill:
    """Tests for TeamMemberRepository.upsert_skill()"""
    
    @pytest.mark.asyncio
    async def test_insert_new_skill(self, session, team_member_repo):
        """Test inserting a new skill."""
        category_id = await team_member_repo.upsert_category("Engineering")
        await session.commit()
        
        skill_id = await team_member_repo.upsert_skill("Python", category_id)
        await session.commit()
        
        assert skill_id == "python"
        
        # Verify in database
        stmt = select(skill_master).where(skill_master.c.skill_id == skill_id)
        result = await session.execute(stmt)
        row = result.fetchone()
        
        assert row is not None
        assert row.skill_name == "Python"
        assert row.category_id == category_id
    
    @pytest.mark.asyncio
    async def test_upsert_skill_generates_id_from_name(self, session, team_member_repo):
        """Test skill_id is generated from skill_name."""
        category_id = await team_member_repo.upsert_category("Engineering")
        await session.commit()
        
        skill_id = await team_member_repo.upsert_skill("Machine Learning", category_id)
        await session.commit()
        
        assert skill_id == "machine-learning"
    
    @pytest.mark.asyncio
    async def test_upsert_skill_special_characters(self, session, team_member_repo):
        """Test skill_id generation handles special characters."""
        category_id = await team_member_repo.upsert_category("Engineering")
        await session.commit()
        
        skill_id = await team_member_repo.upsert_skill("C++", category_id)
        await session.commit()
        
        assert skill_id == "c"  # Special characters removed
    
    @pytest.mark.asyncio
    async def test_upsert_skill_updates_category(self, session, team_member_repo):
        """Test upserting existing skill updates category_id."""
        category_id_1 = await team_member_repo.upsert_category("Engineering")
        await session.commit()
        
        skill_id_1 = await team_member_repo.upsert_skill("Python", category_id_1)
        await session.commit()
        
        category_id_2 = await team_member_repo.upsert_category("Data Science")
        await session.commit()
        
        skill_id_2 = await team_member_repo.upsert_skill("Python", category_id_2)
        await session.commit()
        
        assert skill_id_1 == skill_id_2
        
        # Verify category updated
        stmt = select(skill_master).where(skill_master.c.skill_id == skill_id_2)
        result = await session.execute(stmt)
        row = result.fetchone()
        
        assert row.category_id == category_id_2
    
    @pytest.mark.asyncio
    async def test_upsert_skill_empty_name_raises(self, session, team_member_repo):
        """Test empty skill name raises ValueError."""
        category_id = await team_member_repo.upsert_category("Engineering")
        await session.commit()
        
        with pytest.raises(ValueError, match="skill_name cannot be empty"):
            await team_member_repo.upsert_skill("", category_id)
    
    @pytest.mark.asyncio
    async def test_upsert_skill_truncates_long_id(self, session, team_member_repo):
        """Test skill_id is truncated to 50 chars."""
        category_id = await team_member_repo.upsert_category("Engineering")
        await session.commit()
        
        long_name = "A" * 100
        skill_id = await team_member_repo.upsert_skill(long_name, category_id)
        await session.commit()
        
        assert len(skill_id) == 50


class TestUpsertTeamMember:
    """Tests for TeamMemberRepository.upsert_team_member()"""
    
    @pytest.mark.asyncio
    async def test_insert_new_team_member(self, session, team_member_repo):
        """Test inserting a new team member."""
        member_data = {
            'team_member_id': 'TM001',
            'designation': 'Senior Engineer',
            'profile_type': 'Technical',
            'team_member_status': 'active',
            'experience_in_months': 60,
            'base_location': 'Bangalore',
            'work-mode': 'HYBRID',
            'profile': 'https://example.com/profile',
        }
        
        team_member_id = await team_member_repo.upsert_team_member(member_data)
        await session.commit()
        
        assert team_member_id == 'TM001'
        
        # Verify in database
        stmt = select(team_member).where(team_member.c.team_member_id == team_member_id)
        result = await session.execute(stmt)
        row = result.fetchone()
        
        assert row is not None
        assert row.designation == 'Senior Engineer'
        assert row.is_active is True
        assert row.work_type == 'HYBRID'
        assert row.profile_url == 'https://example.com/profile'
    
    @pytest.mark.asyncio
    async def test_upsert_team_member_updates_existing(self, session, team_member_repo):
        """Test upserting existing team member updates fields."""
        member_data_1 = {
            'team_member_id': 'TM001',
            'designation': 'Engineer',
            'team_member_status': 'active',
        }
        
        await team_member_repo.upsert_team_member(member_data_1)
        await session.commit()
        
        member_data_2 = {
            'team_member_id': 'TM001',
            'designation': 'Senior Engineer',
            'team_member_status': 'inactive',
        }
        
        await team_member_repo.upsert_team_member(member_data_2)
        await session.commit()
        
        # Verify updated
        stmt = select(team_member).where(team_member.c.team_member_id == 'TM001')
        result = await session.execute(stmt)
        row = result.fetchone()
        
        assert row.designation == 'Senior Engineer'
        assert row.is_active is False
    
    @pytest.mark.asyncio
    async def test_upsert_team_member_maps_work_mode(self, session, team_member_repo):
        """Test work-mode is mapped to work_type enum."""
        for work_mode, expected in [('HYBRID', 'HYBRID'), ('REMOTE', 'REMOTE'), ('OFFICE', 'OFFICE'), ('invalid', None)]:
            member_data = {
                'team_member_id': f'TM-{work_mode}',
                'work-mode': work_mode,
            }
            
            await team_member_repo.upsert_team_member(member_data)
            await session.commit()
            
            stmt = select(team_member).where(team_member.c.team_member_id == f'TM-{work_mode}')
            result = await session.execute(stmt)
            row = result.fetchone()
            
            assert row.work_type == expected
    
    @pytest.mark.asyncio
    async def test_upsert_team_member_missing_id_raises(self, team_member_repo):
        """Test missing team_member_id raises ValueError."""
        member_data = {'designation': 'Engineer'}
        
        with pytest.raises(ValueError, match="team_member_id is required"):
            await team_member_repo.upsert_team_member(member_data)


class TestUpsertTeamMemberSkills:
    """Tests for TeamMemberRepository.upsert_team_member_skills()"""
    
    @pytest.mark.asyncio
    async def test_insert_team_member_skills(self, session, team_member_repo):
        """Test inserting team member skills."""
        # Setup
        category_id = await team_member_repo.upsert_category("Engineering")
        await session.commit()
        
        member_data = {'team_member_id': 'TM001'}
        await team_member_repo.upsert_team_member(member_data)
        await session.commit()
        
        skills = [
            {'skill_name': 'Python', 'rating': 5, 'experience_in_months': 36},
            {'skill_name': 'Java', 'rating': 4, 'experience_in_months': 24},
        ]
        
        await team_member_repo.upsert_team_member_skills('TM001', skills, category_id)
        await session.commit()
        
        # Verify
        stmt = select(team_member_skill).where(team_member_skill.c.team_member_id == 'TM001')
        result = await session.execute(stmt)
        rows = result.fetchall()
        
        assert len(rows) == 2
    
    @pytest.mark.asyncio
    async def test_upsert_team_member_skills_updates_existing(self, session, team_member_repo):
        """Test upserting existing skills updates rating/experience."""
        # Setup
        category_id = await team_member_repo.upsert_category("Engineering")
        await session.commit()
        
        member_data = {'team_member_id': 'TM001'}
        await team_member_repo.upsert_team_member(member_data)
        await session.commit()
        
        skills_1 = [{'skill_name': 'Python', 'rating': 3, 'experience_in_months': 12}]
        await team_member_repo.upsert_team_member_skills('TM001', skills_1, category_id)
        await session.commit()
        
        skills_2 = [{'skill_name': 'Python', 'rating': 5, 'experience_in_months': 36}]
        await team_member_repo.upsert_team_member_skills('TM001', skills_2, category_id)
        await session.commit()
        
        # Verify updated
        stmt = select(team_member_skill).where(
            team_member_skill.c.team_member_id == 'TM001',
            team_member_skill.c.skill_id == 'python'
        )
        result = await session.execute(stmt)
        row = result.fetchone()
        
        assert row.rating == 5
        assert row.experience_in_months == 36
    
    @pytest.mark.asyncio
    async def test_upsert_team_member_skills_marks_deleted(self, session, team_member_repo):
        """Test upserting skills with is_deleted flag."""
        # Setup
        category_id = await team_member_repo.upsert_category("Engineering")
        await session.commit()
        
        member_data = {'team_member_id': 'TM001'}
        await team_member_repo.upsert_team_member(member_data)
        await session.commit()
        
        skills = [{'skill_name': 'Python', 'is_deleted': True}]
        await team_member_repo.upsert_team_member_skills('TM001', skills, category_id)
        await session.commit()
        
        # Verify
        stmt = select(team_member_skill).where(
            team_member_skill.c.team_member_id == 'TM001',
            team_member_skill.c.skill_id == 'python'
        )
        result = await session.execute(stmt)
        row = result.fetchone()
        
        assert row.is_deleted is True
    
    @pytest.mark.asyncio
    async def test_upsert_team_member_skills_empty_list(self, session, team_member_repo):
        """Test empty skills list does nothing."""
        await team_member_repo.upsert_team_member_skills('TM001', [], 1)
        await session.commit()
        # Should not raise


class TestUpsertAllocations:
    """Tests for TeamMemberRepository.upsert_allocations()"""
    
    @pytest.mark.asyncio
    async def test_insert_allocations(self, session, team_member_repo):
        """Test inserting team member allocations."""
        # Setup
        member_data = {'team_member_id': 'TM001'}
        await team_member_repo.upsert_team_member(member_data)
        await session.commit()
        
        allocations = [
            {
                'project_id': 'P001',
                'allocation_percentage': 50.0,
                'start_date': date(2024, 1, 1),
                'end_date': date(2024, 12, 31),
                'billable': True,
            }
        ]
        
        await team_member_repo.upsert_allocations('TM001', allocations)
        await session.commit()
        
        # Verify
        stmt = select(team_member_allocation).where(
            team_member_allocation.c.team_member_id == 'TM001',
            team_member_allocation.c.project_id == 'P001'
        )
        result = await session.execute(stmt)
        row = result.fetchone()
        
        assert row is not None
        assert float(row.allocation_percentage) == 50.0
        assert row.billable is True
    
    @pytest.mark.asyncio
    async def test_upsert_allocations_updates_existing(self, session, team_member_repo):
        """Test upserting existing allocations updates fields."""
        # Setup
        member_data = {'team_member_id': 'TM001'}
        await team_member_repo.upsert_team_member(member_data)
        await session.commit()
        
        allocations_1 = [{'project_id': 'P001', 'allocation_percentage': 50.0}]
        await team_member_repo.upsert_allocations('TM001', allocations_1)
        await session.commit()
        
        allocations_2 = [{'project_id': 'P001', 'allocation_percentage': 75.0}]
        await team_member_repo.upsert_allocations('TM001', allocations_2)
        await session.commit()
        
        # Verify updated
        stmt = select(team_member_allocation).where(
            team_member_allocation.c.team_member_id == 'TM001',
            team_member_allocation.c.project_id == 'P001'
        )
        result = await session.execute(stmt)
        row = result.fetchone()
        
        assert float(row.allocation_percentage) == 75.0


class TestUpsertCertifications:
    """Tests for TeamMemberRepository.upsert_certifications()"""
    
    @pytest.mark.asyncio
    async def test_insert_certifications(self, session, team_member_repo):
        """Test inserting skill certifications."""
        # Setup
        category_id = await team_member_repo.upsert_category("Engineering")
        await session.commit()
        
        member_data = {'team_member_id': 'TM001'}
        await team_member_repo.upsert_team_member(member_data)
        await session.commit()
        
        certifications = [
            {
                'certification_id': 'CERT001',
                'skill_name': 'Python',
                'certificate': 'Python Professional',
                'issuer': 'Python Institute',
                'issued_date': date(2023, 1, 1),
                'valid_till': date(2025, 1, 1),
            }
        ]
        
        await team_member_repo.upsert_certifications('TM001', certifications, category_id)
        await session.commit()
        
        # Verify
        stmt = select(team_member_team_member_skill_certification).where(
            team_member_team_member_skill_certification.c.certification_id == 'CERT001'
        )
        result = await session.execute(stmt)
        row = result.fetchone()
        
        assert row is not None
        assert row.certificate == 'Python Professional'
        assert row.issuer == 'Python Institute'


# ===== BatchStateRepository Tests =====

class TestInitializeBatch:
    """Tests for BatchStateRepository.initialize_batch()"""
    
    @pytest.mark.asyncio
    async def test_initialize_new_batch(self, session, batch_state_repo):
        """Test initializing a new batch."""
        await batch_state_repo.initialize_batch(
            batch_id='BATCH001',
            correlation_id='CORR001',
            total_records=100,
            metadata={'source': 'external_api'}
        )
        await session.commit()
        
        # Verify batch state
        stmt = select(ingestion_batch_state).where(
            ingestion_batch_state.c.batch_id == 'BATCH001'
        )
        result = await session.execute(stmt)
        row = result.fetchone()
        
        assert row is not None
        assert row.correlation_id == 'CORR001'
        assert row.status == 'PENDING'
        assert row.total_records == 100
        assert row.processed_records == 0
        assert row.failed_records == 0
        assert row.metadata == {'source': 'external_api'}
        
        # Verify audit log
        audit_stmt = select(ingestion_audit_log).where(
            ingestion_audit_log.c.correlation_id == 'CORR001',
            ingestion_audit_log.c.event_type == 'BATCH_INITIALIZED'
        )
        audit_result = await session.execute(audit_stmt)
        audit_row = audit_result.fetchone()
        
        assert audit_row is not None
        assert audit_row.status == 'PENDING'
    
    @pytest.mark.asyncio
    async def test_initialize_batch_missing_id_raises(self, batch_state_repo):
        """Test missing batch_id raises ValueError."""
        with pytest.raises(ValueError, match="batch_id is required"):
            await batch_state_repo.initialize_batch(
                batch_id='',
                correlation_id='CORR001',
                total_records=100
            )


class TestUpdateBatchStatus:
    """Tests for BatchStateRepository.update_batch_status()"""
    
    @pytest.mark.asyncio
    async def test_update_batch_to_processing(self, session, batch_state_repo):
        """Test updating batch status to PROCESSING."""
        await batch_state_repo.initialize_batch(
            batch_id='BATCH001',
            correlation_id='CORR001',
            total_records=100
        )
        await session.commit()
        
        await batch_state_repo.update_batch_status(
            batch_id='BATCH001',
            status='PROCESSING'
        )
        await session.commit()
        
        # Verify
        stmt = select(ingestion_batch_state).where(
            ingestion_batch_state.c.batch_id == 'BATCH001'
        )
        result = await session.execute(stmt)
        row = result.fetchone()
        
        assert row.status == 'PROCESSING'
        assert row.completed_at is None  # Not yet completed
    
    @pytest.mark.asyncio
    async def test_update_batch_to_success(self, session, batch_state_repo):
        """Test updating batch status to SUCCESS."""
        await batch_state_repo.initialize_batch(
            batch_id='BATCH001',
            correlation_id='CORR001',
            total_records=100
        )
        await session.commit()
        
        await batch_state_repo.update_batch_status(
            batch_id='BATCH001',
            status='SUCCESS',
            processed_records=100,
            failed_records=0
        )
        await session.commit()
        
        # Verify
        stmt = select(ingestion_batch_state).where(
            ingestion_batch_state.c.batch_id == 'BATCH001'
        )
        result = await session.execute(stmt)
        row = result.fetchone()
        
        assert row.status == 'SUCCESS'
        assert row.processed_records == 100
        assert row.failed_records == 0
        assert row.completed_at is not None  # Completed
    
    @pytest.mark.asyncio
    async def test_update_batch_to_failed(self, session, batch_state_repo):
        """Test updating batch status to FAILED."""
        await batch_state_repo.initialize_batch(
            batch_id='BATCH001',
            correlation_id='CORR001',
            total_records=100
        )
        await session.commit()
        
        await batch_state_repo.update_batch_status(
            batch_id='BATCH001',
            status='FAILED',
            processed_records=50,
            failed_records=50,
            error_message='Database connection lost'
        )
        await session.commit()
        
        # Verify
        stmt = select(ingestion_batch_state).where(
            ingestion_batch_state.c.batch_id == 'BATCH001'
        )
        result = await session.execute(stmt)
        row = result.fetchone()
        
        assert row.status == 'FAILED'
        assert row.error_message == 'Database connection lost'
        assert row.completed_at is not None


class TestGetFailedBatches:
    """Tests for BatchStateRepository.get_failed_batches()"""
    
    @pytest.mark.asyncio
    async def test_get_failed_batches(self, session, batch_state_repo):
        """Test retrieving failed batches."""
        # Create successful and failed batches
        await batch_state_repo.initialize_batch('BATCH001', 'CORR001', 100)
        await batch_state_repo.update_batch_status('BATCH001', 'SUCCESS', 100, 0)
        await session.commit()
        
        await batch_state_repo.initialize_batch('BATCH002', 'CORR002', 100)
        await batch_state_repo.update_batch_status('BATCH002', 'FAILED', 50, 50, 'Error occurred')
        await session.commit()
        
        await batch_state_repo.initialize_batch('BATCH003', 'CORR003', 100)
        await batch_state_repo.update_batch_status('BATCH003', 'FAILED', 0, 100, 'Total failure')
        await session.commit()
        
        # Retrieve failed batches
        failed_batches = await batch_state_repo.get_failed_batches()
        
        assert len(failed_batches) == 2
        batch_ids = [b['batch_id'] for b in failed_batches]
        assert 'BATCH002' in batch_ids
        assert 'BATCH003' in batch_ids
    
    @pytest.mark.asyncio
    async def test_get_failed_batches_limit(self, session, batch_state_repo):
        """Test retrieving failed batches with limit."""
        # Create 3 failed batches
        for i in range(3):
            batch_id = f'BATCH00{i+1}'
            corr_id = f'CORR00{i+1}'
            await batch_state_repo.initialize_batch(batch_id, corr_id, 100)
            await batch_state_repo.update_batch_status(batch_id, 'FAILED', 0, 100)
        await session.commit()
        
        # Retrieve with limit
        failed_batches = await batch_state_repo.get_failed_batches(limit=2)
        
        assert len(failed_batches) == 2


class TestAuditLog:
    """Tests for BatchStateRepository.audit_log()"""
    
    @pytest.mark.asyncio
    async def test_audit_log_creates_entry(self, session, batch_state_repo):
        """Test audit log creates entry."""
        await batch_state_repo.audit_log(
            correlation_id='CORR001',
            event_type='TEST_EVENT',
            status='INFO',
            message='Test message',
            event_details={'key': 'value'},
            severity='INFO',
            source='unit_test'
        )
        await session.commit()
        
        # Verify
        stmt = select(ingestion_audit_log).where(
            ingestion_audit_log.c.correlation_id == 'CORR001'
        )
        result = await session.execute(stmt)
        row = result.fetchone()
        
        assert row is not None
        assert row.event_type == 'TEST_EVENT'
        assert row.message == 'Test message'
        assert row.severity == 'INFO'
        assert row.source == 'unit_test'
    
    @pytest.mark.asyncio
    async def test_audit_log_missing_correlation_id_raises(self, batch_state_repo):
        """Test missing correlation_id raises ValueError."""
        with pytest.raises(ValueError, match="correlation_id is required"):
            await batch_state_repo.audit_log(
                correlation_id='',
                event_type='TEST_EVENT',
                status='INFO',
                message='Test message'
            )
