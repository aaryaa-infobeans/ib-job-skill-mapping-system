"""Result aggregation agent."""

import logging

from app.ai.state import GraphState

logger = logging.getLogger(__name__)


def result_aggregation_node(state: GraphState) -> GraphState:
    """Format final ranked list of candidates for API response.
    
    This is a stub implementation that logs execution.
    """
    logger.info("Executing Result_Aggregation_Agent node")
    
    candidate_scores = state.get("candidate_scores")
    if not candidate_scores:
        logger.warning("No candidate_scores found in state")
        state["final_results"] = []
        return state
    
    # Stub: Convert candidate scores to final results format
    final_results = []
    for candidate in candidate_scores:
        final_results.append({
            "team_member_id": candidate["team_member_id"],
            "profile_score": candidate["final_score"],
            "fit_level": "HIGH" if candidate["final_score"] >= 0.8 else "MEDIUM",
            "availability_match": candidate["is_available"],
            "explanation": [
                f"Candidate scored {candidate['final_score']:.2f} based on skills and experience",
                f"Skills matched: {', '.join(candidate['match_reasons'].get('skills_matched', []))}",
            ],
        })
    
    state["final_results"] = final_results
    logger.info(f"Result_Aggregation_Agent completed with {len(final_results)} results")
    return state
