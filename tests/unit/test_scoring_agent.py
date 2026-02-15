"""Unit tests for the new ScoringAgent."""

import pytest
from unittest.mock import MagicMock
from app.ai.utils.scoring import ScoringAgent
from app.ai.utils.models import RAGCandidate

@pytest.fixture
def scoring_agent():
    return ScoringAgent()

def test_calculate_skill_score(scoring_agent):
    """Test private skill scoring logic."""
    # All mandatory matched
    res = scoring_agent._calculate_skill_score(
        team_member_skill_ids=["PYTHON", "FASTAPI"],
        mandatory_skill_ids=["PYTHON"],
        preferred_skill_ids=["FASTAPI"]
    )
    assert res["mandatory_score"] == 1.0
    assert res["preferred_score"] == 1.0
    
    # Partial matched
    res = scoring_agent._calculate_skill_score(
        team_member_skill_ids=["PYTHON"],
        mandatory_skill_ids=["PYTHON", "FASTAPI"],
        preferred_skill_ids=["DOCKER"]
    )
    assert res["mandatory_score"] == 0.5
    assert res["preferred_score"] == 0.0

def test_calculate_experience_score(scoring_agent):
    """Test private experience scoring logic."""
    # Within range
    assert scoring_agent._calculate_experience_score(36, 24, 60) == 1.0
    # Below min
    assert scoring_agent._calculate_experience_score(20, 24, 60) == 0.0
    # Above max (still 1.0 as per current logic)
    assert scoring_agent._calculate_experience_score(70, 24, 60) == 1.0

def test_calculate_location_score(scoring_agent):
    """Test private location scoring logic."""
    assert scoring_agent._calculate_location_score("Pune, India", ["Pune"]) == 1.0
    assert scoring_agent._calculate_location_score("Mumbai", ["Pune"]) == 0.0
    assert scoring_agent._calculate_location_score("Mumbai", ["Remote"]) == 1.0

def test_execute_full_match(scoring_agent):
    """Test full execution of ScoringAgent with a perfect match."""
    rag_candidate = RAGCandidate(
        team_member_id="tm-1",
        final_similarity=1.0,
        mandatory_similarity=1.0,
        preferred_similarity=1.0,
        jd_level_similarity=1.0,
        certification_similarity=1.0
    )
    
    profile_data = {
        "skill_ids": ["PYTHON", "AI"],
        "mandatory_skill_ids": ["PYTHON"],
        "preferred_skill_ids": ["AI"],
        "experience_months": 48,
        "min_experience_months": 24,
        "max_experience_months": 60,
        "certifications": ["AWS Certified"],
        "required_certifications": ["AWS Certified"],
        "location": "Pune",
        "required_locations": ["Pune"],
        "work_mode": "wfo",
        "required_work_modes": ["wfo"],
    }
    
    result = scoring_agent.execute(rag_candidate, profile_data)
    
    assert result.match_score == 1.0
    assert result.detailed_breakdown.mandatory_score == 1.0
    assert result.detailed_breakdown.location_matched is True
    assert result.detailed_breakdown.experience_matched is True
    assert result.detailed_breakdown.work_mode_matched is True

def test_execute_no_match(scoring_agent):
    """Test full execution with no match."""
    rag_candidate = RAGCandidate(
        team_member_id="tm-2",
        final_similarity=0.0,
        mandatory_similarity=0.0,
        preferred_similarity=0.0,
        jd_level_similarity=0.0
    )
    
    profile_data = {
        "skill_ids": ["JAVA"],
        "mandatory_skill_ids": ["PYTHON"],
        "preferred_skill_ids": ["AI"],
        "experience_months": 12,
        "min_experience_months": 24,
    }
    
    result = scoring_agent.execute(rag_candidate, profile_data)
    
    # Certification (0.1), Location (0.1), Work Mode (0.05) are 1.0 because no requirements specified
    # Total = 0.25
    assert result.match_score == 0.25
    assert result.detailed_breakdown.mandatory_score == 0.0
    assert result.detailed_breakdown.experience_score == 0.0
