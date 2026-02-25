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
        role_fit_threshold = candidate.get("role_fit_threshold", 0.5)
        
        # 1. Check Score Threshold (GATE)
        passed_score_gate = final_score >= role_fit_threshold
        
        # 2. Check Mandatory Gates
        # Semantic similarity gate: >= 0.50
        semantic_sim = candidate.get("semantic_similarity", 0.0)
        passed_semantic_gate = semantic_sim >= 0.50
        
        # 3. AI Override (SPEC-003)
        ai_override_applied = candidate.get("ai_override_applied", False)
        
        # Final Qualification Decision
        # QUALIFIED if: Score Gate passed AND (Semantic Gate passed OR AI Override)
        is_qualified = passed_score_gate and (passed_semantic_gate or ai_override_applied)
        
        status = "QUALIFIED" if is_qualified else "DISQUALIFIED"
        if is_qualified:
            total_qualified += 1
            
        fit_level = determine_fit_level(final_score)
        
        # Build explanation list
        explanation = []
        explanation.append(f"Status: {status}")
        explanation.append(f"Final Score: {final_score*100:.0f}% (Threshold: {role_fit_threshold*100:.0f}%)")
        
        if ai_override_applied:
            explanation.append("🤖 AI Override: Semantic gate waived for senior profile.")
        elif not passed_semantic_gate:
            explanation.append("❌ Disqualified: Did not meet semantic similarity threshold (0.50).")
            
        # Add AI reasoning if available
        ai_reasoning = candidate.get("ai_reasoning", "")
        if ai_reasoning:
            explanation.append(f"🧠 AI Reasoning: {ai_reasoning}")
            
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
                "gates": {
                    "score_gate": passed_score_gate,
                    "semantic_gate": passed_semantic_gate,
                    "ai_override": ai_override_applied
                }
            }
        }
        
        final_results.append(result_entry)
    
    state["total_qualified"] = total_qualified
    state["final_results"] = final_results
    
    logger.info(f"Phase 2 completed: {total_qualified} qualified out of {len(final_results)} evaluated")
    return state
