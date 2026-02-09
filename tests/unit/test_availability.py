"""Unit tests for availability evaluation logic."""

from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.availability import (
    calculate_availability,
    calculate_requisition_window,
    evaluate_availability,
    get_overlapping_allocations,
)
from app.db.base import Base
from app.db.models import TeamMember, TeamMemberAllocation


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Create test database session."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_calculate_requisition_window_with_dates():
    """Test requisition window calculation with provided dates."""
    start = date(2026, 3, 1)
    duration = 6
    
    start_date, end_date = calculate_requisition_window(start, duration)
    
    assert start_date == start
    assert end_date == start + timedelta(days=6 * 30)


def test_calculate_requisition_window_defaults():
    """Test requisition window calculation with default values."""
    start_date, end_date = calculate_requisition_window(None, None)
    
    assert start_date == date.today()
    assert end_date == date.today() + timedelta(days=6 * 30)


def test_calculate_requisition_window_iso_strings():
    """Test requisition window calculation with ISO strings."""
    # Test with YYYY-MM-DD string
    start_str = "2026-05-20"
    start_date, end_date = calculate_requisition_window(start_str, 6)
    assert start_date == date(2026, 5, 20)
    assert end_date == date(2026, 5, 20) + timedelta(days=6 * 30)

    # Test with ISO datetime string
    start_dt_str = "2026-06-15T10:30:00"
    start_date, end_date = calculate_requisition_window(start_dt_str, 3)
    assert start_date == date(2026, 6, 15)
    assert end_date == date(2026, 6, 15) + timedelta(days=3 * 30)

    # Test with invalid string (should fallback to today)
    start_date, end_date = calculate_requisition_window("invalid-date", None)
    assert start_date == date.today()


def test_get_overlapping_allocations_no_overlap(db_session):
    """Test getting allocations with no overlaps."""
    # Create team member
    member = TeamMember(
        team_member_id="tm-001",
        designation="Senior Developer",
        experience_in_months=60,
    )
    db_session.add(member)
    
    # Create allocation outside requisition window
    allocation = TeamMemberAllocation(
        team_member_id="tm-001",
        project_id="PROJECT-A",
        allocation_percentage=50.0,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 6, 30),
    )
    db_session.add(allocation)
    db_session.commit()
    
    # Query for allocations in different window
    allocations = get_overlapping_allocations(
        db_session,
        "tm-001",
        date(2026, 7, 1),
        date(2026, 12, 31),
    )
    
    assert len(allocations) == 0


def test_get_overlapping_allocations_with_overlap(db_session):
    """Test getting allocations with overlaps."""
    member = TeamMember(
        team_member_id="tm-002",
        designation="Developer",
        experience_in_months=48,
    )
    db_session.add(member)
    
    # Create overlapping allocations
    alloc1 = TeamMemberAllocation(
        team_member_id="tm-002",
        project_id="PROJECT-B",
        allocation_percentage=40.0,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 30),
    )
    alloc2 = TeamMemberAllocation(
        team_member_id="tm-002",
        project_id="PROJECT-C",
        allocation_percentage=30.0,
        start_date=date(2026, 3, 1),
        end_date=date(2026, 9, 30),
    )
    db_session.add_all([alloc1, alloc2])
    db_session.commit()
    
    # Query for allocations overlapping with requisition window
    allocations = get_overlapping_allocations(
        db_session,
        "tm-002",
        date(2026, 3, 1),
        date(2026, 9, 1),
    )
    
    assert len(allocations) == 2


def test_get_overlapping_allocations_excludes_deleted(db_session):
    """Test that deleted allocations are excluded."""
    member = TeamMember(
        team_member_id="tm-003",
        designation="Engineer",
        experience_in_months=36,
    )
    db_session.add(member)
    
    alloc1 = TeamMemberAllocation(
        team_member_id="tm-003",
        project_id="PROJECT-D",
        allocation_percentage=50.0,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_deleted=False,
    )
    alloc2 = TeamMemberAllocation(
        team_member_id="tm-003",
        project_id="PROJECT-E",
        allocation_percentage=25.0,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_deleted=True,
    )
    db_session.add_all([alloc1, alloc2])
    db_session.commit()
    
    allocations = get_overlapping_allocations(
        db_session,
        "tm-003",
        date(2026, 6, 1),
        date(2026, 12, 1),
    )
    
    assert len(allocations) == 1
    assert allocations[0].project_id == "PROJECT-D"


def test_calculate_availability_fully_available(db_session):
    """Test availability calculation for fully available member."""
    member = TeamMember(
        team_member_id="tm-004",
        designation="Senior Engineer",
        experience_in_months=72,
    )
    db_session.add(member)
    db_session.commit()
    
    is_available, available_capacity, total_allocation = calculate_availability(
        db_session,
        "tm-004",
        date(2026, 6, 1),
        date(2026, 12, 1),
    )
    
    assert is_available is True
    assert available_capacity == 100.0
    assert total_allocation == 0.0


def test_calculate_availability_partially_allocated(db_session):
    """Test availability calculation for partially allocated member."""
    member = TeamMember(
        team_member_id="tm-005",
        designation="Developer",
        experience_in_months=60,
    )
    db_session.add(member)
    
    allocation = TeamMemberAllocation(
        team_member_id="tm-005",
        project_id="PROJECT-F",
        allocation_percentage=60.0,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    db_session.add(allocation)
    db_session.commit()
    
    is_available, available_capacity, total_allocation = calculate_availability(
        db_session,
        "tm-005",
        date(2026, 6, 1),
        date(2026, 12, 1),
    )
    
    assert is_available is True
    assert available_capacity == 40.0
    assert total_allocation == 60.0


def test_calculate_availability_over_threshold(db_session):
    """Test availability calculation for over-allocated member."""
    member = TeamMember(
        team_member_id="tm-006",
        designation="Tech Lead",
        experience_in_months=48,
    )
    db_session.add(member)
    
    alloc1 = TeamMemberAllocation(
        team_member_id="tm-006",
        project_id="PROJECT-G",
        allocation_percentage=50.0,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    alloc2 = TeamMemberAllocation(
        team_member_id="tm-006",
        project_id="PROJECT-H",
        allocation_percentage=40.0,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    db_session.add_all([alloc1, alloc2])
    db_session.commit()
    
    is_available, available_capacity, total_allocation = calculate_availability(
        db_session,
        "tm-006",
        date(2026, 6, 1),
        date(2026, 12, 1),
        threshold_percentage=80.0,
    )
    
    assert is_available is False
    assert available_capacity == 10.0
    assert total_allocation == 90.0


def test_evaluate_availability_full_integration(db_session):
    """Test full availability evaluation integration."""
    member = TeamMember(
        team_member_id="tm-007",
        designation="Junior Developer",
        experience_in_months=36,
    )
    db_session.add(member)
    
    allocation = TeamMemberAllocation(
        team_member_id="tm-007",
        project_id="PROJECT-I",
        allocation_percentage=70.0,
        start_date=date(2026, 3, 1),
        end_date=date(2026, 9, 30),
    )
    db_session.add(allocation)
    db_session.commit()
    
    result = evaluate_availability(
        db_session,
        "tm-007",
        date(2026, 6, 1),
        6,
        threshold_percentage=80.0,
    )
    
    assert result["is_available"] is True
    assert result["available_capacity"] == 30.0
    assert result["total_allocation"] == 70.0
    assert result["requisition_window"][0] == date(2026, 6, 1)
