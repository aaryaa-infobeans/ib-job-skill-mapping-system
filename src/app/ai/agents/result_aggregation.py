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
    """Format final ranked list of candidates for API response.
    
    This node:
    1. Filters candidates by FIT_SCORE_THRESHOLD
    2. Takes candidate_scores from state
    3. Formats each candidate for API response
    4. Derives fit_level from final_score
    5. Includes availability information
    6. Populates state.final_results with sorted list
    """
    import os
    
    logger.info("Executing Result_Aggregation_Agent node")
    
    candidate_scores = state.get("candidate_scores")
    if not candidate_scores:
        logger.warning("No candidate_scores found in state")
        state["final_results"] = []
        state["total_evaluated"] = 0
        state["total_qualified"] = 0
        return state
    
    # Load FIT_SCORE_THRESHOLD from environment
    fit_score_threshold = float(os.getenv("FIT_SCORE_THRESHOLD", "0.5"))
    
    # Filter candidates by threshold (COST OPTIMIZATION: Only explain qualified candidates)
    qualified_candidates = [
        c for c in candidate_scores 
        if c.get("final_score", 0) >= fit_score_threshold
    ]
    
    logger.info(
        f"Filtered candidates: {len(qualified_candidates)} qualified out of {len(candidate_scores)} evaluated "
        f"(threshold: {fit_score_threshold:.2f})"
    )
    
    # Track evaluation metrics
    state["total_evaluated"] = len(candidate_scores)
    state["total_qualified"] = len(qualified_candidates)
    
    # Format results for API response
    final_results = []
    
    for candidate in qualified_candidates:
        # Determine fit level from score
        fit_level = determine_fit_level(candidate["final_score"])
        
        # Build explanation list - start with LLM-generated detailed explanation if available
        explanation = []
        
        # Add detailed LLM explanation if available
        detailed_explanation = candidate.get("detailed_explanation", {})
        if detailed_explanation:
            # Include LLM-generated summary and analysis
            if "summary" in detailed_explanation:
                explanation.append(f"📌 {detailed_explanation['summary']}")
            
            if detailed_explanation.get("strengths"):
                strengths_str = ", ".join(detailed_explanation["strengths"])
                explanation.append(f"✅ Strengths: {strengths_str}")
            
            if detailed_explanation.get("gaps"):
                gaps_str = ", ".join(detailed_explanation["gaps"])
                explanation.append(f"⚠️  Gaps: {gaps_str}")
            
            if "fit_analysis" in detailed_explanation:
                explanation.append(f"📊 Fit Analysis: {detailed_explanation['fit_analysis']}")
            
            if "recommendation" in detailed_explanation:
                explanation.append(f"💡 Recommendation: {detailed_explanation['recommendation']}")
        else:
            # Fallback to structured summary if LLM explanation not available
            explanation.append(
                f"Overall match score: {candidate['final_score']:.2f} ({fit_level} fit)"
            )
            
            # Add skill match details
            skill_score = candidate.get("skill_score", 0.0)
            matched_skills = candidate.get("match_reasons", {}).get("skills_matched", [])
            if matched_skills:
                explanation.append(
                    f"Skills matched: {', '.join(matched_skills)} (score: {skill_score:.2f})"
                )
            else:
                explanation.append(f"Skill match score: {skill_score:.2f}")
            
            # Add experience details
            experience_score = candidate.get("experience_score", 0.0)
            explanation.append(f"Experience match score: {experience_score:.2f}")
            
            # Add availability details
            is_available = candidate.get("is_available", False)
            availability_score = candidate.get("availability_score", 0.0)
            availability_pct = availability_score * 100
            explanation.append(
                f"Availability: {availability_pct:.0f}% capacity "
                f"({'Available' if is_available else 'Limited availability'})"
            )
        
        # Create result entry with detailed explanation
        result_entry = {
            "team_member_id": candidate["team_member_id"],
            "profile_score": round(candidate["final_score"], 2),
            "fit_level": fit_level,
            "availability_match": candidate.get("is_available", False),
            "explanation": explanation,
            "detailed_explanation": detailed_explanation if detailed_explanation else None,
        }
        
        final_results.append(result_entry)
    
    # Results are already sorted by final_score from matching_scoring_node
    state["final_results"] = final_results
    
    logger.info(f"Result_Aggregation_Agent completed with {len(final_results)} results")
    logger.debug(f"Top 3 candidates: {[r['team_member_id'] for r in final_results[:3]]}")
    
    return state
