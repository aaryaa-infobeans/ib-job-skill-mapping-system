"""Unit tests for the new ScoringAgent."""

import pytest
from pytest import approx
from unittest.mock import MagicMock
from app.ai.utils.scoring import ScoringAgent
from app.ai.utils.models import RAGCandidate

@pytest.fixture
def scoring_agent():
    return ScoringAgent()

def test_skill_group_score_id_match(scoring_agent):
    res = scoring_agent._calculate_skill_group_score(
        ["PYTHON_ID"], {"Python": ["PYTHON_ID"]}
    )
    assert res["score"] == approx(1.0)
    assert res["matched"] == ["Python"]

def test_skill_group_score_missing(scoring_agent):
    res = scoring_agent._calculate_skill_group_score(
        ["JAVA_ID"], {"Python": ["PYTHON_ID"]}
    )
    assert res["score"] == approx(0.0)
    assert res["missing"] == ["Python"]

def test_skill_group_score_alternative_id(scoring_agent):
    # Primary bug fix: alternative IDs in the list are checked correctly
    res = scoring_agent._calculate_skill_group_score(
        ["sk-010b"], {"Docker": ["sk-010", "sk-010b"]}
    )
    assert res["score"] == approx(1.0)
    assert res["matched"] == ["Docker"]

def test_skill_group_score_empty(scoring_agent):
    res = scoring_agent._calculate_skill_group_score(["PYTHON_ID"], {})
    assert res["score"] == approx(1.0)

def test_skill_group_score_rating_and_exp_weighted(scoring_agent):
    """ID-matched skill with rating=3 and exp=24m produces blended contribution."""
    # norm_rating=0.6, norm_exp=0.5 → 0.6*0.6 + 0.4*0.5 = 0.56
    res = scoring_agent._calculate_skill_group_score(
        ["PYTHON_ID"],
        {"Python": ["PYTHON_ID"]},
        skill_ratings={"PYTHON_ID": 0.6},
        skill_exp_months={"PYTHON_ID": 24},
    )
    assert res["score"] == approx(0.56)
    assert res["matched"] == ["Python"]
    assert res["missing"] == []


def test_skill_group_score_rating_differentiates_candidates(scoring_agent):
    """Same skill, different ratings → different mandatory_score."""
    alts = {"Python": ["PYTHON_ID"]}
    res_high = scoring_agent._calculate_skill_group_score(
        ["PYTHON_ID"], alts,
        skill_ratings={"PYTHON_ID": 1.0},
        skill_exp_months={"PYTHON_ID": 48},
    )
    res_low = scoring_agent._calculate_skill_group_score(
        ["PYTHON_ID"], alts,
        skill_ratings={"PYTHON_ID": 0.4},
        skill_exp_months={"PYTHON_ID": 12},
    )
    assert res_high["score"] == approx(1.0)
    assert res_low["score"] < res_high["score"]


def test_skill_group_score_none_fields_neutral(scoring_agent):
    """Both rating=None and exp=None → neutral 0.5 contribution, not 1.0."""
    # norm_rating=0.5 (None), norm_exp=0.5 (None) → 0.6*0.5 + 0.4*0.5 = 0.50
    res = scoring_agent._calculate_skill_group_score(
        ["PYTHON_ID"],
        {"Python": ["PYTHON_ID"]},
        skill_ratings={"PYTHON_ID": 0.5},
        skill_exp_months={"PYTHON_ID": None},
    )
    assert res["score"] == approx(0.5)


def test_skill_group_score_profile_text_match_weight(scoring_agent):
    """Text-only match contributes profile_text_match_weight, not 1.0."""
    from app.settings import settings
    res = scoring_agent._calculate_skill_group_score(
        [],
        {"Python": ["PYTHON_ID"]},
        profile_text="senior python developer with 5 years experience",
        skill_ratings={},
        skill_exp_months={},
    )
    assert res["score"] == approx(settings.profile_text_match_weight)
    assert res["matched"] == ["Python"]
    assert res["missing"] == []


def test_skill_group_score_short_string_guard(scoring_agent):
    # Short strings not in the allow-list must not produce false positives
    res = scoring_agent._calculate_skill_group_score(
        [], {"XY": []}, profile_text="senior developer architecture"
    )
    assert res["score"] == approx(0.0)

def test_calculate_experience_score(scoring_agent):
    """Test private experience scoring logic."""
    assert scoring_agent._calculate_experience_score(36, 24, 60) == approx(1.0)
    assert scoring_agent._calculate_experience_score(12, 24, 60) == approx(0.5)
    assert scoring_agent._calculate_experience_score(70, 24, 60) == approx(1.0)

def test_calculate_location_score(scoring_agent):
    """Test private location scoring logic."""
    assert scoring_agent._calculate_location_score("Pune, India", ["Pune"]) == approx(1.0)
    assert scoring_agent._calculate_location_score("Mumbai", ["Pune"]) == approx(0.0)
    assert scoring_agent._calculate_location_score("Mumbai", ["Remote"]) == approx(1.0)

def test_execute_full_match(scoring_agent):
    """Test full execution of ScoringAgent with a perfect match."""
    rag_candidate = RAGCandidate(
        team_member_id="tm-1",
        final_similarity=1.0,
        mandatory_similarity=1.0,
        preferred_similarity=1.0,
        jd_level_similarity=1.0,
        certification_similarity=1.0,
        full_jd_similarity=1.0,
    )
    
    profile_data = {
        "jd_text": "Senior Python Developer\nLocation: Pune",
        "designation": "Senior Python Developer",
        "skill_ids": ["PYTHON_ID", "AI_ID"],
        "skill_names": ["Python", "AI"],
        "mandatory_alternatives": {"Python": ["PYTHON_ID"]},
        "preferred_alternatives": {"AI": ["AI_ID"]},
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
    assert result.match_score == approx(1.0)
    assert result.detailed_breakdown.mandatory_score == approx(1.0)
    assert result.detailed_breakdown.location_matched is True
    assert result.detailed_breakdown.role_type == "SENIOR"

def test_execute_mid_role(scoring_agent):
    """Test MID role weighting."""
    rag_candidate = RAGCandidate(
        team_member_id="tm-mid",
        final_similarity=0.8,
        mandatory_similarity=0.8,
        preferred_similarity=0.8,
        jd_level_similarity=0.8,
        full_jd_similarity=0.8,
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
    assert result.match_score == approx(0.68)
    assert result.detailed_breakdown.role_type == "MID"
