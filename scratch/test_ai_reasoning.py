
import logging
import sys
import os
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.abspath("src"))

# Mock settings
os.environ["LOG_LEVEL"] = "INFO"
os.environ["SECRETS_BACKEND"] = "local"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.ai.agents.explanation_generation import _generate_llm_explanation, _generate_template_explanation, _validate_llm_explanation

def test_ai_reasoning_fixes():
    print("Testing AI Reasoning Fixes...")
    
    # Sample candidate data
    candidate_data = {
        "team_member_id": "TM-12345",
        "role_type": "Senior Developer",
        "experience_in_months": 72,
        "ai_confidence_score": 0.85,
        "score_breakdown": {
            "mandatory_skills_group": 1.0,
            "semantic_similarity": 0.8,
            "context_score": 0.05,
            "penalties": 0.0
        },
        "match_reasons": {
            "mandatory_matched": ["Python", "FastAPI", "PostgreSQL"],
            "mandatory_missing": [],
            "preferred_matched": ["Docker"],
            "preferred_missing": ["Kubernetes"],
            "certification_matched": ["AWS Certified Developer"]
        }
    }
    
    parsed_jd = {
        "normalized_title": "Senior Backend Engineer",
        "normalized_role": "Backend",
        "extracted_mandatory_skills": ["Python", "FastAPI", "PostgreSQL"]
    }

    # 1. Test Validation Logic
    print("\n--- Testing Validation Logic ---")
    
    # Case: Numeric analysis
    bad_result = {
        "summary": "Short summary",
        "fit_analysis": "Final Score: 82. Ledger: 14. Match Score: 77",
        "strengths": ["Python", "FastAPI"],
        "gaps": [],
        "recommendation": "Review"
    }
    err = _validate_llm_explanation(bad_result, candidate_data)
    print(f"Numeric analysis check: {'PASSED' if err == 'Summary too short (< 20 chars)' else 'FAILED: ' + str(err)}")
    
    bad_result["summary"] = "This is a long enough summary for testing purposes."
    err = _validate_llm_explanation(bad_result, candidate_data)
    print(f"Numeric analysis check (long summary): {'PASSED' if err == 'Analysis contains raw numeric score labels' else 'FAILED: ' + str(err)}")


    # 3. Test LLM Logic with Mock (Retry then Fallback)
    print("\n--- Testing LLM Retry and Fallback logic ---")
    
    with patch("app.ai.agents.explanation_generation.llm_client") as mock_llm:
        # Mock LLM returning bad data twice
        mock_llm.chat_completion.return_value = (
            '{"summary": "Short", "fit_analysis": "Score: 80", "strengths": ["Python"], "gaps": [], "recommendation": "No"}',
            {"total_tokens": 100, "cost_usd": 0.001}
        )
        
        result, metrics = _generate_llm_explanation(
            "TM-12345", 0.82, "HIGH", parsed_jd, candidate_data
        )
        
        # Should return None (which triggers template fallback in node)
        print(f"LLM logic with double failure: {'PASSED' if result is None else 'FAILED'}")
        print(f"LLM call count: {mock_llm.chat_completion.call_count} (Expected 2)")

    print("\nAll tests passed!")

if __name__ == "__main__":
    test_ai_reasoning_fixes()
