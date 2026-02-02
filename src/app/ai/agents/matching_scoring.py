"""Matching and scoring agent."""

import logging

from app.ai.state import GraphState

logger = logging.getLogger(__name__)


def matching_scoring_node(state: GraphState) -> GraphState:
    """Execute deterministic matching and scoring algorithm.
    
    This is a stub implementation that logs execution.
    """
    logger.info("Executing Matching_Scoring_Agent node")
    
    normalized_skills = state.get("normalized_skills")
    if not normalized_skills:
        logger.warning("No normalized_skills found in state")
        return state
    
    # Stub: Create placeholder candidate scores
    state["candidate_scores"] = [
        {
            "team_member_id": "TM001",
            "skill_score": 0.85,
            "experience_score": 0.75,
            "availability_score": 1.0,
            "final_score": 0.87,
            "is_available": True,
            "match_reasons": {"skills_matched": ["Python", "FastAPI"]},
        },
        {
            "team_member_id": "TM002",
            "skill_score": 0.70,
            "experience_score": 0.80,
            "availability_score": 0.5,
            "final_score": 0.67,
            "is_available": True,
            "match_reasons": {"skills_matched": ["Python"]},
        },
    ]
    
    logger.info(f"Matching_Scoring_Agent completed with {len(state['candidate_scores'])} candidates")
    return state
