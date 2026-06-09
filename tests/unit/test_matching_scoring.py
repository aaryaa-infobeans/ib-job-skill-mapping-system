"""Unit tests for matching_scoring helpers."""

from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest

from app.ai.agents.matching_scoring import _build_candidate_context


@pytest.fixture
def member():
    m = MagicMock()
    m.designation = "Backend Engineer"
    m.experience_in_months = 36
    return m


def _skill(skill_id, rating, exp_months):
    s = MagicMock()
    s.skill_id = skill_id
    s.rating = rating
    s.experience_in_months = exp_months
    return s


def _cert(name, valid_till):
    c = MagicMock()
    c.certificate = name
    c.valid_till = valid_till
    return c


def test_includes_skill_rating_and_exp(member):
    skill = _skill("PY1", 3, 18)
    result = _build_candidate_context(member, [skill], {"PY1": "Python"}, [], "base")
    assert "Python: 3/5, 1y 6m" in result
    assert "Designation: Backend Engineer" in result
    assert "3y 0m" in result


def test_active_cert_included(member):
    cert = _cert("AWS-SAA", None)  # no expiry → permanent → active
    result = _build_candidate_context(member, [], {}, [cert], "base")
    assert "AWS-SAA" in result


def test_expired_cert_excluded(member):
    cert = _cert("OLD-CERT", date.today() - timedelta(days=1))
    result = _build_candidate_context(member, [], {}, [cert], "base")
    assert "OLD-CERT" not in result
    assert "None" in result


def test_no_skills_no_certs(member):
    result = _build_candidate_context(member, [], {}, [], "base")
    assert "None on record" in result
    assert "None" in result


def test_unrated_skill_shows_label(member):
    skill = _skill("SK1", None, None)
    result = _build_candidate_context(member, [skill], {"SK1": "Kubernetes"}, [], "base")
    assert "Kubernetes: unrated, duration unknown" in result


def test_profile_text_preserved(member):
    result = _build_candidate_context(member, [], {}, [], "original prose")
    assert result.startswith("original prose")
    assert "--- Structured Candidate Data ---" in result


def test_empty_profile_text_still_produces_block(member):
    result = _build_candidate_context(member, [], {}, [], "")
    assert "--- Structured Candidate Data ---" in result
    assert "Designation: Backend Engineer" in result


def test_future_expiry_cert_included(member):
    cert = _cert("PMP", date.today() + timedelta(days=30))
    result = _build_candidate_context(member, [], {}, [cert], "base")
    assert "PMP" in result
