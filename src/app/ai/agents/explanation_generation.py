"""Explanation generation agent with LLM-powered detailed explanations."""

import json
import logging
import os
from typing import Optional, Dict, Any

from app.ai.state import GraphState
from app.ai.utils.explanation_prompt import format_explanation_prompt

logger = logging.getLogger(__name__)

# Initialize OpenAI client (graceful fallback if key not set)
try:
    from openai import OpenAI
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    
    # Check if API key is valid (not empty, not placeholder, starts with sk-)
    is_valid_key = (
        openai_api_key and 
        len(openai_api_key) > 20 and
        openai_api_key.startswith("sk-") and
        openai_api_key != "sk-your-openai-api-key-here"
    )
    
    if is_valid_key:
        client = OpenAI(api_key=openai_api_key)
        llm_enabled = True
        logger.info(f"✅ OpenAI client initialized with API key (starts with {openai_api_key[:20]}...)")
    else:
        client = None
        llm_enabled = False
        logger.warning("⚠️  OPENAI_API_KEY not configured or invalid - using template-based explanations")
except Exception as e:
    logger.error(f"❌ Failed to initialize OpenAI client: {str(e)}")
    client = None
    llm_enabled = False


def _generate_llm_explanation(
    team_member_id: str,
    final_score: float,
    fit_level: str,
    parsed_jd: Dict[str, Any],
    candidate_data: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Generate detailed explanation using OpenAI LLM.
    
    Args:
        team_member_id: Team member ID
        final_score: Final match score
        fit_level: Fit level (HIGH, MEDIUM, LOW)
        parsed_jd: Parsed job description from state
        candidate_data: Candidate's scoring data
    
    Returns:
        Dictionary with detailed explanation or None if LLM call fails or not enabled
    """
    # Check if LLM is enabled
    if not llm_enabled or not client:
        logger.debug(f"LLM not enabled, skipping LLM explanation for {team_member_id}")
        return None
    
    try:
        # Extract candidate match details
        match_reasons = candidate_data.get("match_reasons", {})
        
        # Format the prompt with candidate details
        prompt = format_explanation_prompt(
            team_member_id=team_member_id,
            final_score=final_score,
            fit_level=fit_level,
            job_title=parsed_jd.get("normalized_title", "Unknown"),
            job_role=parsed_jd.get("normalized_role", "Unknown"),
            job_location=", ".join(parsed_jd.get("location", [])) if parsed_jd.get("location") else "Not specified",
            mandatory_skills=parsed_jd.get("extracted_mandatory_skills", []),
            candidate_mandatory_skills=match_reasons.get("candidate_mandatory_skills", []),
            matched_mandatory_skills=match_reasons.get("mandatory_matched", []),
            missing_mandatory_skills=match_reasons.get("mandatory_missing", []),
            mandatory_score=match_reasons.get("mandatory_score", 0.0),
            preferred_skills=parsed_jd.get("extracted_preferred_skills", []),
            candidate_preferred_skills=match_reasons.get("candidate_preferred_skills", []),
            matched_preferred_skills=match_reasons.get("preferred_matched", []),
            missing_preferred_skills=match_reasons.get("preferred_missing", []),
            preferred_score=match_reasons.get("preferred_score", 0.0),
            required_experience=parsed_jd.get("experience", {}).get("min_months", 0),
            candidate_experience=candidate_data.get("experience_in_months", 0),
            experience_score=candidate_data.get("experience_score", 0.0),
            required_certifications=parsed_jd.get("certifications_required", []),
            candidate_certifications=match_reasons.get("certifications", []),
            certification_score=match_reasons.get("certification_score", 0.0),
            candidate_location=candidate_data.get("location", "Unknown"),
            candidate_work_mode=candidate_data.get("work_mode", "Unknown"),
            location_score=match_reasons.get("location_score", 0.0),
            required_start_date=parsed_jd.get("expected_start_date", "Not specified"),
            requisition_duration=parsed_jd.get("requisition_duration_month", 0),
            available_capacity=candidate_data.get("availability_score", 0.0) * 100,
            is_available=candidate_data.get("is_available", False),
        )
        
        # Call OpenAI API
        logger.info(f"Generating LLM explanation for {team_member_id}")
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert recruiter. Generate detailed, professional explanations for candidate matching decisions. Always respond with valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=500,
        )
        
        # Parse response
        explanation_text = response.choices[0].message.content
        logger.debug(f"Raw LLM response for {team_member_id}: {explanation_text}")
        
        # Try to parse as JSON
        try:
            explanation_data = json.loads(explanation_text)
        except json.JSONDecodeError:
            # If not valid JSON, create structured response from text
            logger.warning(f"LLM response not valid JSON for {team_member_id}, wrapping as text")
            explanation_data = {
                "summary": explanation_text[:200],
                "detailed_explanation": explanation_text,
                "strengths": [],
                "gaps": [],
                "fit_analysis": explanation_text,
                "recommendation": "Review candidate profile for more details"
            }
        
        # Track tokens
        token_count = response.usage.prompt_tokens + response.usage.completion_tokens
        cost = (
            (response.usage.prompt_tokens / 1_000_000 * 0.03) +
            (response.usage.completion_tokens / 1_000_000 * 0.06)
        )
        
        logger.info(
            f"LLM explanation generated for {team_member_id}: "
            f"tokens={token_count}, cost=${cost:.6f}"
        )
        
        return {
            "explanation_data": explanation_data,
            "token_count": token_count,
            "cost_usd": cost,
        }
        
    except Exception as e:
        logger.error(f"Error generating LLM explanation for {team_member_id}: {str(e)}", exc_info=True)
        return None


def explanation_generation_node(state: GraphState) -> GraphState:
    """Generate detailed LLM-powered explanations for qualified candidates.
    
    This node uses OpenAI GPT-4 to generate comprehensive explanations for each
    qualified candidate, including:
    - Skills matched and missing
    - Experience analysis
    - Certification assessment
    - Location/work mode fit
    - Availability assessment
    - Overall fit analysis
    
    IMPORTANT: Only generates explanations for candidates meeting FIT_SCORE_THRESHOLD
    to optimize costs - no point explaining candidates we won't use.
    
    The detailed explanations are then used by result_aggregation_node.
    """
    import os
    
    logger.info("Executing Explanation_Generation_Agent node with LLM")
    
    candidate_scores = state.get("candidate_scores")
    parsed_jd = state.get("parsed_jd")
    
    if not candidate_scores:
        logger.warning("No candidate_scores found in state")
        return state
    
    if not parsed_jd:
        logger.warning("No parsed_jd found in state")
        return state
    
    # Load thresholds and limits
    fit_score_threshold = float(os.getenv("FIT_SCORE_THRESHOLD", "0.5"))
    max_llm_explanations = int(os.getenv("MAX_LLM_EXPLANATIONS", "5"))
    
    # Count totals for logging
    total_candidates = len(candidate_scores)
    qualified_candidates = [c for c in candidate_scores if c.get("final_score", 0) >= fit_score_threshold]
    qualified_count = len(qualified_candidates)
    
    # Sort qualified candidates by score descending to ensure we pick the top ones
    qualified_candidates.sort(key=lambda x: x.get("final_score", 0), reverse=True)
    
    llm_target_count = min(qualified_count, max_llm_explanations)
    
    logger.info(
        f"Explanation generation: Found {qualified_count}/{total_candidates} qualified candidates. "
        f"Generating LLM explanations for TOP {llm_target_count} (limit: {max_llm_explanations}) "
        "and template explanations for the rest - COST & PERFORMANCE OPTIMIZATION"
    )
    
    # Track tokens for this node
    total_tokens = 0
    total_cost = 0.0
    explanations_generated = 0
    explanations_failed = 0
    templates_used = 0
    
    # Process all candidates
    for i, candidate in enumerate(candidate_scores):
        team_member_id = candidate.get("team_member_id")
        final_score = candidate.get("final_score", 0.0)
        
        # 1. Skip candidates below threshold
        if final_score < fit_score_threshold:
            logger.debug(
                f"Skipping explanation for {team_member_id} "
                f"(score: {final_score:.2f} < {fit_score_threshold:.2f})"
            )
            continue
            
        fit_level = "HIGH" if final_score >= 0.75 else "MEDIUM" if final_score >= 0.5 else "LOW"
        
        # 2. Check if this candidate is in the top N for LLM explanation
        # Note: qualified_candidates is sorted, so we can check if this candidate is one of the top N
        is_top_candidate = any(c.get("team_member_id") == team_member_id for c in qualified_candidates[:max_llm_explanations])
        
        if is_top_candidate:
            # Generate LLM explanation
            llm_result = _generate_llm_explanation(
                team_member_id=team_member_id,
                final_score=final_score,
                fit_level=fit_level,
                parsed_jd=parsed_jd,
                candidate_data=candidate,
            )
            
            if llm_result:
                # Add explanation to candidate
                candidate["detailed_explanation"] = llm_result["explanation_data"]
                candidate["explanation_tokens"] = llm_result["token_count"]
                candidate["explanation_cost_usd"] = llm_result["cost_usd"]
                
                total_tokens += llm_result["token_count"]
                total_cost += llm_result["cost_usd"]
                explanations_generated += 1
            else:
                # Fallback to template-based explanation on LLM failure
                logger.warning(f"LLM failed for {team_member_id}, using template-based explanation")
                candidate["detailed_explanation"] = _generate_template_explanation(candidate, parsed_jd)
                explanations_failed += 1
        else:
            # 3. Use template-based explanation for qualified but non-top candidates
            logger.debug(f"Using template explanation for {team_member_id} (outside top {max_llm_explanations})")
            candidate["detailed_explanation"] = _generate_template_explanation(candidate, parsed_jd)
            templates_used += 1
    
    # Store node metrics in state for tracking
    if not state.get("token_metrics"):
        state["token_metrics"] = {}
    
    state["token_metrics"]["explanation_generation"] = {
        "prompt_tokens": total_tokens // 2,  # Estimate
        "completion_tokens": total_tokens // 2,
        "total_tokens": total_tokens,
        "cost_usd": total_cost,
        "model": "gpt-4",
        "llm_explanations": explanations_generated,
        "template_explanations": templates_used + explanations_failed
    }
    
    # Update cumulative tracking
    state["cumulative_tokens"] = (state.get("cumulative_tokens", 0) or 0) + total_tokens
    state["cumulative_cost_usd"] = (state.get("cumulative_cost_usd", 0.0) or 0.0) + total_cost
    
    logger.info(
        f"Explanation_Generation_Agent completed: "
        f"LLM explanations: {explanations_generated}, "
        f"Template explanations: {templates_used}, "
        f"LLM failures: {explanations_failed}, "
        f"Total tokens: {total_tokens:,}, Cost: ${total_cost:.4f}"
    )
    
    return state


def _generate_template_explanation(candidate: Dict[str, Any], parsed_jd: Dict[str, Any]) -> Dict[str, str]:
    """Generate template-based explanation as fallback when LLM fails.
    
    Args:
        candidate: Candidate scoring data
        parsed_jd: Parsed job description
        
    Returns:
        Dictionary with template-based explanation
    """
    match_reasons = candidate.get("match_reasons", {})
    final_score = candidate.get("final_score", 0.0)
    
    mandatory_score = match_reasons.get("mandatory_score", 0.0)
    preferred_score = match_reasons.get("preferred_score", 0.0)
    experience_score = candidate.get("experience_score", 0.0)
    
    strengths = []
    gaps = []
    
    # Identify strengths
    if mandatory_score >= 0.8:
        strengths.append("Strong match on mandatory skills (80%+ coverage)")
    if preferred_score >= 0.5:
        strengths.append("Good match on preferred skills (50%+ coverage)")
    if experience_score >= 0.8:
        strengths.append("Experience level exceeds requirements")
    if candidate.get("is_available", False):
        strengths.append("Available for assignment immediately")
    
    # Identify gaps
    if mandatory_score < 0.5:
        gaps.append("Limited mandatory skills coverage (<50%)")
    if preferred_score < 0.3:
        gaps.append("Few preferred skills present (<30%)")
    if experience_score < 0.5:
        gaps.append("Experience below ideal level")
    if not candidate.get("is_available", False):
        gaps.append("Limited availability during required period")
    
    return {
        "summary": f"Candidate is a {('strong', 'moderate', 'light')[min(2, int(final_score * 3))]} fit for the role with a match score of {final_score:.0%}",
        "strengths": strengths if strengths else ["Basic skill coverage"],
        "gaps": gaps if gaps else ["No major gaps identified"],
        "fit_analysis": f"The match score reflects {mandatory_score:.0%} mandatory skill coverage, {preferred_score:.0%} preferred skills, and {experience_score:.0%} experience alignment.",
        "recommendation": "Review detailed profile for skill-specific matches" if gaps else "Good candidate for consideration"
    }
