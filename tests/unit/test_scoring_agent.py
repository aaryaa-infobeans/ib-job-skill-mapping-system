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
    # Preferred matched
    res = scoring_agent._calculate_skill_score(
        member_skill_ids=["PYTHON", "FASTAPI"],
        mandatory_ids=["PYTHON"],
        preferred_ids=["FASTAPI"]
    )
    assert res["preferred_score"] == 1.0
    
    # Preferred not matched
    res = scoring_agent._calculate_skill_score(
        member_skill_ids=["PYTHON"],
        mandatory_ids=["PYTHON"],
        preferred_ids=["DOCKER"]
    )
    assert res["preferred_score"] == 0.0

def test_calculate_mandatory_group_score(scoring_agent):
    """Test mandatory skill grouping logic."""
    # Group match
    alternatives = {"Python": ["PYTHON_ID"]}
    res = scoring_agent._calculate_mandatory_group_score(
        member_skill_ids=["PYTHON_ID"],
        mandatory_alternatives=alternatives
    )
    assert res["score"] == 1.0
    
    # Missing
    res = scoring_agent._calculate_mandatory_group_score(
        member_skill_ids=["JAVA_ID"],
        mandatory_alternatives=alternatives
    )
    assert res["score"] == 0.0

def test_calculate_experience_score(scoring_agent):
    """Test private experience scoring logic."""
    # Within range
    assert scoring_agent._calculate_experience_score(36, 24, 60) == 1.0
    # Below min (partial score)
    assert scoring_agent._calculate_experience_score(12, 24, 60) == 0.5
    # Above max (still 1.0)
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
        "jd_text": "Senior Python Developer\nLocation: Pune",
        "designation": "Senior Python Developer",
        "skill_ids": ["PYTHON_ID", "AI_ID"],
        "skill_names": ["Python", "AI"],
        "mandatory_skill_ids": ["PYTHON_ID"],
        "preferred_skill_ids": ["AI_ID"],
        "mandatory_alternatives": {"Python": ["PYTHON_ID"]},
        "experience_months": 100, # Senior
        "min_experience_months": 96,
        "location": "Pune",
        "required_locations": ["Pune"],
        "work_mode": "remote",
        "required_work_modes": ["remote"],
    }
    
    result = scoring_agent.execute(rag_candidate, profile_data)
    
    # Senior Context Weight is 0.05. 
    # M=50%, P=20%, S=25%, C=5%
    # If all 1.0, total is 1.0
    assert result.match_score == 1.0
    assert result.detailed_breakdown.mandatory_score == 1.0
    assert result.detailed_breakdown.location_matched is True
    assert result.detailed_breakdown.role_type == "SENIOR"

def test_execute_mid_role(scoring_agent):
    """Test MID role weighting."""
    rag_candidate = RAGCandidate(
        team_member_id="tm-mid",
        final_similarity=0.8,
        mandatory_similarity=0.8,
        preferred_similarity=0.8,
        jd_level_similarity=0.8
    )
    profile_data = {
        "jd_text": "Mid Developer",
        "experience_months": 48, # Mid
        "skill_ids": ["PYTHON_ID"],
        "skill_names": ["Python"],
        "mandatory_alternatives": {"Python": ["PYTHON_ID"]},
        "preferred_skill_ids": [],
    }
    result = scoring_agent.execute(rag_candidate, profile_data)
    # MID: M=40%, P=20%, S=25%, C=15%
    # M=1.0, P=0, S=0.8, C=1.0 (defaults if not required)
    # Score = 1.0*0.4 + 0*0.2 + 0.8*0.25 + (Contribution = 1.0*0.15 capped at 0.08)
    # Score = 0.4 + 0.2 + 0.08 = 0.68
    assert result.match_score == 0.68
    assert result.detailed_breakdown.role_type == "MID"
