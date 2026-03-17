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

        return json.loads(content), metrics
        
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

def explanation_generation_node(state: GraphState) -> GraphState:
    """Phase 3: Explainability node."""
    logger.info("Executing Explanation_Generation_Agent node (Phase 3)")
    state["error_message"] = None
    
    candidate_scores = state.get("candidate_scores")
    parsed_jd = state.get("parsed_jd")
    
    if not candidate_scores or not parsed_jd:
        return state
    
    from app.settings import settings
    max_llm_explanations = settings.max_llm_explanations
    
    # Initialize state fields for tracking
    if state.get("llm_call_logs") is None:
        state["llm_call_logs"] = []
    
    for i, candidate in enumerate(candidate_scores):
        is_qualified = candidate.get("is_qualified", False)
        
        # Only use LLM for the top N candidates
        if i < max_llm_explanations:
            llm_result, metrics = _generate_llm_explanation(
                team_member_id=candidate["team_member_id"],
                final_score=candidate["final_score"],
                fit_level="HIGH" if candidate["final_score"] >= 0.75 else "MEDIUM",
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
                candidate["detailed_explanation"] = _generate_template_explanation(candidate, parsed_jd)
        else:
            candidate["detailed_explanation"] = _generate_template_explanation(candidate, parsed_jd)
            
    return state

def _generate_template_explanation(candidate: Dict[str, Any], parsed_jd: Dict[str, Any]) -> Dict[str, str]:
    """Fallback template explanation with ledger details."""
    final_score = candidate.get("final_score", 0.0)
    score_breakdown = candidate.get("score_breakdown", {})
    
    m_group_score = score_breakdown.get("mandatory_skills_group", 0.0)
    s_score = score_breakdown.get("semantic_similarity", 0.0)
    c_boost = score_breakdown.get("context_boost", 0.0)
    penalties = score_breakdown.get("penalties", 0.0)
    ai_boost = candidate.get("ai_boost", 0.0)
    
    summary = f"Match Analysis for {candidate.get('team_member_id')}"
    fit_analysis = (
        f"Final Score: {final_score:.2f}. "
        f"Ledger: Mandatory Group={m_group_score:.2f}, Semantic={s_score:.2f}, "
        f"Context Boost={c_boost:.2f}, Penalties={penalties:.2f}, AI Boost={ai_boost:.2f}."
    )
    
    strengths = []
    if m_group_score >= 1.0: strengths.append("Satisfies all mandatory skill groups")
    if ai_boost > 0: strengths.append(f"AI Boost applied (+{ai_boost:.2f})")
    
    gaps = []
    if m_group_score < 1.0: gaps.append("Missing mandatory skill groups")
    if penalties > 0: gaps.append(f"Penalty applied ({penalties:.2f})")
    
    return {
        "summary": summary,
        "strengths": strengths,
        "gaps": gaps,
        "fit_analysis": fit_analysis,
        "recommendation": "Review profile for specific gaps."
    }
