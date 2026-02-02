"""Explanation generation agent."""

import logging

from app.ai.state import GraphState

logger = logging.getLogger(__name__)


def explanation_generation_node(state: GraphState) -> GraphState:
    """Generate human-readable explanations for candidate matches.
    
    This node adds detailed explanation context to candidate_scores.
    The explanations are then used by result_aggregation_node.
    
    Note: Currently explanations are generated deterministically.
    Future enhancement: Use LLM to generate more detailed, personalized explanations.
    """
    logger.info("Executing Explanation_Generation_Agent node")
    
    candidate_scores = state.get("candidate_scores")
    if not candidate_scores:
        logger.warning("No candidate_scores found in state")
        return state
    
    # Enhance each candidate with detailed explanation context
    for candidate in candidate_scores:
        match_reasons = candidate.get("match_reasons", {})
        
        # Extract match details
        mandatory_matched = match_reasons.get("mandatory_matched", [])
        preferred_matched = match_reasons.get("preferred_matched", [])
        mandatory_score = match_reasons.get("mandatory_score", 0.0)
        preferred_score = match_reasons.get("preferred_score", 0.0)
        
        # Build detailed explanation context
        explanation_context = {
            "mandatory_skills_summary": (
                f"{len(mandatory_matched)} mandatory skills matched "
                f"({mandatory_score:.0%} of requirements)"
            ),
            "preferred_skills_summary": (
                f"{len(preferred_matched)} preferred skills matched "
                f"({preferred_score:.0%} of preferences)"
            ),
            "strengths": [],
            "gaps": [],
        }
        
        # Identify strengths
        if mandatory_score >= 0.8:
            explanation_context["strengths"].append("Strong match on mandatory skills")
        if preferred_score >= 0.5:
            explanation_context["strengths"].append("Good match on preferred skills")
        if candidate.get("experience_score", 0) >= 0.8:
            explanation_context["strengths"].append("Experience level meets requirements")
        if candidate.get("is_available", False):
            explanation_context["strengths"].append("Available for assignment")
        
        # Identify gaps
        if mandatory_score < 0.5:
            explanation_context["gaps"].append("Limited mandatory skills coverage")
        if preferred_score < 0.3:
            explanation_context["gaps"].append("Few preferred skills present")
        if candidate.get("experience_score", 0) < 0.5:
            explanation_context["gaps"].append("Experience may not fully meet requirements")
        if not candidate.get("is_available", False):
            explanation_context["gaps"].append("Limited availability")
        
        # Add context to candidate
        candidate["explanation_context"] = explanation_context
    
    logger.info(f"Explanation_Generation_Agent completed for {len(candidate_scores)} candidates")
    return state
