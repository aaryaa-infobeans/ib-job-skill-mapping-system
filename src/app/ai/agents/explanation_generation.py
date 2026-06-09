"""Explanation generation agent with Phase 1 Ledger support."""

import json
import logging
import os
from typing import Optional, Dict, Any, List

from app.ai.state import GraphState
from app.ai.utils.explanation_prompt import format_explanation_prompt
from app.ai.utils.llm_client import llm_client
from app.ai.audit import save_llm_request_log
from app.db.session import SessionLocal
from app.observability.tracing import trace_node

logger = logging.getLogger(__name__)

def _generate_llm_explanation(
    team_member_id: str,
    final_score: float,
    fit_level: str,
    parsed_jd: Dict[str, Any],
    candidate_data: Dict[str, Any]
) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Generate detailed explanation using Phase 1 metrics."""
    try:
        match_reasons = candidate_data.get("match_reasons", {})
        score_breakdown = candidate_data.get("score_breakdown", {})
        
        prompt = format_explanation_prompt(
            team_member_id=team_member_id,
            final_score=final_score,
            fit_level=fit_level,
            job_title=parsed_jd.get("normalized_title", "Unknown"),
            job_role=parsed_jd.get("normalized_role", "Unknown"),
            job_location=", ".join(parsed_jd.get("location", [])) if parsed_jd.get("location") else "Not specified",
            mandatory_skills=parsed_jd.get("extracted_mandatory_skills", []),
            # Pass Phase 1 metrics
            role_type=candidate_data.get("role_type", "MID"),
            mandatory_group_score=score_breakdown.get("mandatory_skills_group", 0.0),
            semantic_score=score_breakdown.get("semantic_similarity", 0.0),
            context_boost=score_breakdown.get("context_score", 0.0),
            penalties=score_breakdown.get("penalties", 0.0),
            ai_confidence=candidate_data.get("ai_confidence_score", 0.0),
            ai_boost=candidate_data.get("ai_boost", 0.0),
            ai_override_applied=candidate_data.get("ai_override_applied", False),
            
            matched_mandatory_skills=match_reasons.get("mandatory_matched", []),
            missing_mandatory_skills=match_reasons.get("mandatory_missing", []),
            matched_preferred_skills=match_reasons.get("preferred_matched", []),
            missing_preferred_skills=match_reasons.get("preferred_missing", []),
            candidate_experience=candidate_data.get("experience_in_months", 0),
            is_available=candidate_data.get("is_available", False),
            ai_reasoning=candidate_data.get("ai_reasoning", ""),
            # Pass new Phase 1 Ledger fields
            matched_certs=match_reasons.get("certification_matched", []),
            missing_certs=match_reasons.get("certification_missing", []),
            bonus_certs=match_reasons.get("bonus_certifications", []),
            location_matched=match_reasons.get("location_matched", False),
            work_mode_matched=match_reasons.get("work_mode_matched", False)
        )
        
        content, usage = llm_client.chat_completion(
            messages=[
                {"role": "system", "content": "You are an expert HR recruitment assistant. Provide professional candidate evaluations based on the provided match ledger."},
                {"role": "user", "content": prompt}
            ],
            model=None, # Use system default from settings via llm_client
            response_format={"type": "json_object"}
        )
        
        metrics = None
        if usage:
            cost = llm_client.get_completion_cost(usage)
            metrics = {
                "agent_name": "explanation_generation",
                "prompt_name": "detailed_explanation",
                "model": usage.get("model", "unknown"),
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
                "cost_usd": cost,
                "status": "SUCCESS"
            }
        
        if not content:
            return None, metrics

        result = json.loads(content)
        
        # Validation Layer
        validation_error = _validate_llm_explanation(result, candidate_data)
        if validation_error:
            logger.warning(f"LLM explanation validation failed for {team_member_id}: {validation_error}. Retrying with stricter constraints...")
            # Simple one-time retry
            content, usage = llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": "CRITICAL: Your previous response failed validation. You MUST provide a narrative evaluation. NO RAW NUMBERS in fit_analysis. Strengths MUST NOT be just a list of JD skills. Summary MUST be > 20 characters."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            if content:
                result = json.loads(content)
                validation_error = _validate_llm_explanation(result, candidate_data)
                if validation_error:
                    logger.error(f"LLM explanation failed validation again: {validation_error}. Using narrative template fallback.")
                    return None, metrics
            else:
                return None, metrics

        # Post-processing: Ensure gaps include actual missing skills from match_reasons
        match_reasons = candidate_data.get("match_reasons", {})
        mandatory_missing = match_reasons.get("mandatory_missing", [])
        preferred_missing = match_reasons.get("preferred_missing", [])
        cert_missing = match_reasons.get("certification_missing", [])
        
        current_gaps = result.get("gaps", [])
        
        # Add missing mandatory skills if not already mentioned in gaps
        if mandatory_missing:
            missing_str = f"Missing mandatory skills: {', '.join(mandatory_missing)}"
            if not any("mandatory" in gap.lower() for gap in current_gaps):
                current_gaps.insert(0, missing_str)
        
        # Add missing preferred skills if not already mentioned
        if preferred_missing and len(preferred_missing) > 0:
            missing_str = f"Missing preferred skills: {', '.join(preferred_missing[:3])}"
            if not any("preferred" in gap.lower() for gap in current_gaps):
                current_gaps.append(missing_str)
        
        # Add missing certifications if not already mentioned
        if cert_missing:
            missing_str = f"Missing certifications: {', '.join(cert_missing)}"
            if not any("certification" in gap.lower() for gap in current_gaps):
                current_gaps.append(missing_str)
        
        result["gaps"] = current_gaps
        
        return result, metrics
        
    except Exception as e:
        logger.error(f"LLM explanation failed for {team_member_id}: {str(e)}")
        metrics = {
            "agent_name": "explanation_generation",
            "prompt_name": "detailed_explanation",
            "status": "FAILED",
            "error_message": str(e),
            "total_tokens": 0,
            "cost_usd": 0.0
        }
        return None, metrics

@trace_node("explanation_generation")
def explanation_generation_node(state: GraphState) -> GraphState:
    """Phase 3: Explainability node."""
    logger.info("Executing Explanation_Generation_Agent node (Phase 3)")
    state["error_message"] = None
    
    candidate_scores = state.get("candidate_scores")
    parsed_jd = state.get("parsed_jd")
    
    if not candidate_scores or not parsed_jd:
        return state
    
    from app.settings import settings
    # We increase the max LLM explanations to ensure better coverage for top candidates
    max_llm_explanations = settings.max_llm_explanations
    
    # Initialize state fields for tracking
    if state.get("llm_call_logs") is None:
        state["llm_call_logs"] = []
    
    for i, candidate in enumerate(candidate_scores):
        final_score = candidate.get("final_score", 0.0)
        
        # Determine fit level correctly
        if final_score >= 0.75:
            fit_level = "HIGH"
        elif final_score >= 0.50:
            fit_level = "MEDIUM"
        else:
            fit_level = "LOW"
            
        # Strategy: Top candidates get LLM reasoning, rest get high-quality Template fallback
        if i < max_llm_explanations:
            llm_result, metrics = _generate_llm_explanation(
                team_member_id=candidate["team_member_id"],
                final_score=final_score,
                fit_level=fit_level,
                parsed_jd=parsed_jd,
                candidate_data=candidate
            )

            if metrics:
                state["llm_call_logs"].append(metrics)
                state["cumulative_tokens"] = (state.get("cumulative_tokens") or 0) + metrics.get("total_tokens", 0)
                state["cumulative_cost_usd"] = (state.get("cumulative_cost_usd") or 0.0) + metrics.get("cost_usd", 0.0)
            
            if llm_result:
                candidate["detailed_explanation"] = llm_result
            else:
                # If LLM fails or validation fails, use the narrative template fallback
                candidate["detailed_explanation"] = _generate_template_explanation(candidate, parsed_jd)
        else:
            # Candidates beyond the limit get the high-quality template explanation
            candidate["detailed_explanation"] = _generate_template_explanation(candidate, parsed_jd)
            
    return state

def _generate_template_explanation(candidate: Dict[str, Any], parsed_jd: Dict[str, Any]) -> Dict[str, str]:
    """Narrative fallback template explanation with improved user-friendliness."""
    final_score = candidate.get("final_score", 0.0)
    score_breakdown = candidate.get("score_breakdown", {})
    match_reasons = candidate.get("match_reasons", {})
    
    # Fit level determination (consistent with result_aggregation)
    if final_score >= 0.75:
        fit_level = "HIGH"
    elif final_score >= 0.50:
        fit_level = "MEDIUM"
    else:
        fit_level = "LOW"
    
    # Inferred professional summary
    role_type = candidate.get("role_type", "professional")
    exp_months = candidate.get("experience_in_months", 0)
    
    if exp_months > 0:
        exp_years = round(exp_months / 12, 1)
        exp_text = f"approximately {exp_years} years of professional experience"
    else:
        exp_text = "an entry-level professional background"
    
    summary = f"This is a {fit_level.lower()} match for a {role_type.lower()} role. The candidate possesses {exp_text}."
    
    # Narrative fit analysis
    m_group_score = score_breakdown.get("mandatory_skills_group", 0.0)
    if m_group_score >= 1.0:
        fit_narrative = f"The candidate demonstrates a {fit_level.lower()} alignment, meeting all core technical requirements identified for this position."
    elif m_group_score >= 0.5:
        fit_narrative = f"The candidate shows a {fit_level.lower()} alignment with significant match on essential skills, though some specific core requirements are not fully met."
    else:
        fit_narrative = f"The candidate has a {fit_level.lower()} alignment with limited overlap across the core technical requirements requested."

    # Strengths (Candidate-Focused)
    strengths = []
    if exp_months >= 60: # 5 years
        strengths.append("Substantial professional experience and industry depth")
    if candidate.get("ai_confidence_score", 0) > 0.7:
        strengths.append("Strong overall compatibility with the job role intent")
    
    matched_certs = match_reasons.get("certification_matched", [])
    if matched_certs:
        strengths.append(f"Possesses relevant certifications: {', '.join(matched_certs[:2])}")

    bonus_certs = match_reasons.get("bonus_certifications", [])
    if bonus_certs:
        strengths.append(
            f"Holds additional certifications relevant to this role type (not required by JD): "
            f"{', '.join(bonus_certs[:2])}"
        )

    if not strengths:
        strengths.append("Demonstrated foundational knowledge in the required technology domain")

    # Gaps
    gaps = []
    mandatory_missing = match_reasons.get("mandatory_missing", [])
    if mandatory_missing:
        gaps.append(f"Does not meet some core technical requirements: {', '.join(mandatory_missing)}")
    
    cert_missing = match_reasons.get("certification_missing", [])
    if cert_missing:
        gaps.append(f"Missing required certifications: {', '.join(cert_missing)}")

    if not gaps:
        gaps.append("Minor misalignments in secondary skill preferences or domain-specific depth")

    return {
        "summary": summary,
        "strengths": strengths,
        "gaps": gaps,
        "fit_analysis": fit_narrative,
        "recommendation": f"Review for {fit_level.lower()} match fitment."
    }

def _validate_llm_explanation(result: Dict[str, Any], candidate_data: Dict[str, Any]) -> Optional[str]:
    """Validate LLM generated explanation for quality and structure."""
    if not result:
        return "Empty result"
    
    # 1. Summary check
    summary = result.get("summary", "")
    if len(summary) < 20:
        return "Summary too short (< 20 chars)"
    
    # 2. Numeric analysis check
    analysis = result.get("fit_analysis", "")
    import re
    numeric_patterns = [r"final score", r"score:", r"ledger:", r"match score"]
    if any(re.search(p, analysis.lower()) for p in numeric_patterns):
        return "Analysis contains raw numeric score labels"
    
    # 3. Strengths vs JD check
    strengths = result.get("strengths", [])
    if not strengths:
        return "No strengths provided"
        
    return None
