"""Skill normalization agent."""

import logging

from app.ai.state import GraphState

logger = logging.getLogger(__name__)


def skill_normalization_node(state: GraphState) -> GraphState:
    """Map extracted skills to canonical skill_master IDs.
    
    This is a stub implementation that logs execution.
    """
    logger.info("Executing Skill_Normalization_Agent node")
    
    parsed_jd = state.get("parsed_jd")
    if not parsed_jd:
        logger.warning("No parsed_jd found in state")
        return state
    
    # Stub: Map skills to placeholder IDs
    state["normalized_skills"] = {
        "mandatory_skill_ids": ["PYTHON", "FASTAPI"],
        "preferred_skill_ids": ["DOCKER", "K8S"],
    }
    
    logger.info("Skill_Normalization_Agent completed")
    return state
