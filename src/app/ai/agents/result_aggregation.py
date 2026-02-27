"""Result aggregation agent."""

import logging

from app.ai.state import GraphState

logger = logging.getLogger(__name__)


def determine_fit_level(final_score: float) -> str:
    """Determine fit level based on final score.
    
    Args:
        final_score: Final score (0.0 to 1.0)
    
    Returns:
        Fit level: HIGH, MEDIUM, or LOW
    """
    if final_score >= 0.75:
        return "HIGH"
    elif final_score >= 0.50:
        return "MEDIUM"
    else:
        return "LOW"


def result_aggregation_node(state: GraphState) -> GraphState:
    """
    Phase 2: Qualification Decision.
    Establishes QUALIFIED/DISQUALIFIED status based on SPEC-003.
    """
    import os
    
    logger.info("Executing Result_Aggregation_Agent node (Phase 2)")
    
    # Reset error message
    state["error_message"] = None
    
    candidate_scores = state.get("candidate_scores")
    if not candidate_scores:
        logger.warning("No candidate_scores found in state")
        state["final_results"] = []
        state["total_evaluated"] = 0
        state["total_qualified"] = 0
        return state
    
    # Track evaluation metrics
    state["total_evaluated"] = len(candidate_scores)
    
    final_results = []
    total_qualified = 0
    
    for candidate in candidate_scores:
        final_score = candidate.get("final_score", 0.0)
        is_qualified = candidate.get("is_qualified", False)
        qualification_reason = candidate.get("qualification_reason", "No reason provided")
        
        status = "QUALIFIED" if is_qualified else "DISQUALIFIED"
        if is_qualified:
            total_qualified += 1
            
        fit_level = determine_fit_level(final_score)
        
        # Build explanation list (Enriched with detailed narrative)
        explanation = []
        detailed_exp = candidate.get("detailed_explanation")
        
        if detailed_exp:
            # Use LLM-generated or Template-based detailed explanation
            explanation.append(f"Summary: {detailed_exp.get('summary', 'No summary available')}")
            
            fit_analysis = detailed_exp.get('fit_analysis', '')
            if fit_analysis:
                explanation.append(f"Analysis: {fit_analysis}")
            
            strengths = detailed_exp.get('strengths', [])
            if strengths:
                explanation.append(f"Strengths: {', '.join(strengths)}")
            
            gaps = detailed_exp.get('gaps', [])
            if gaps:
                explanation.append(f"Gaps: {', '.join(gaps)}")
                
            rec = detailed_exp.get('recommendation', '')
            if rec:
                explanation.append(f"Recommendation: {rec}")
        else:
            # Legacy/Fallback if detailed_explanation is somehow missing
            explanation.append(f"Status: {status}")
            explanation.append(f"Reasoning: {qualification_reason}")
            ai_reasoning = candidate.get("ai_reasoning", "")
            if ai_reasoning:
                explanation.append(f"🧠 AI Analysis: {ai_reasoning}")

            
        # Create result entry
        result_entry = {
            "team_member_id": candidate["team_member_id"],
            "profile_score": round(final_score * 100, 2),
            "fit_level": fit_level,
            "status": status,
            "availability_match": candidate.get("is_available", False),
            "explanation": explanation,
            "detailed_breakdown": {
                "phase0_ledger": candidate.get("phase0_ledger"),
                "score_breakdown": candidate.get("score_breakdown"),
                "match_reasons": candidate.get("match_reasons", {}),
                "ai_confidence_score": candidate.get("ai_confidence_score"),
                "ai_boost_applied": candidate.get("ai_boost", 0.0),
                "role_type": candidate.get("role_type"),
                "is_qualified": is_qualified,
                "qualification_reason": qualification_reason
            }
        }

        
        final_results.append(result_entry)
    
    state["total_qualified"] = total_qualified
    state["final_results"] = final_results
    
    # Consolidate metrics for easier retrieval and caching
    state["metrics"] = {
        "total_evaluated": len(final_results),
        "total_qualified": total_qualified,
        "token_count": state.get("cumulative_tokens", 0),
        "cost_usd": state.get("cumulative_cost_usd", 0.0)
    }
    
    logger.info(f"Phase 2 completed: {total_qualified} qualified out of {len(final_results)} evaluated")
    return state
