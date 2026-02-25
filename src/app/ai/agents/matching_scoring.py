"""Matching and scoring agent."""

import logging

from sqlalchemy.orm import Session

from app.ai.availability import evaluate_availability
from app.ai.utils.scoring import ScoringAgent
from app.ai.utils.scoring_audit import ScoringAudit
from app.ai.utils.models import RAGCandidate
from app.ai.state import GraphState
from app.db.models import TeamMember, TeamMemberSkill, TeamMemberSkillCertification
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


def matching_scoring_node(state: GraphState) -> GraphState:
    """Execute deterministic matching and scoring for all team members.
    
    This node:
    1. Retrieves all active team members from the database
    2. Evaluates availability for each member
    3. Calculates skill and experience scores
    4. Populates state.candidate_scores with ranked results
    """
    logger.info("Executing Matching_Scoring_Agent node")
    
    # Reset error message for this node run
    state["error_message"] = None
    
    # Extract required data from state
    normalized_skills = state.get("normalized_skills")
    requisition_input = state.get("requisition_input")
    parsed_jd = state.get("parsed_jd")
    
    if not normalized_skills or not requisition_input:
        logger.error("Missing required state: normalized_skills or requisition_input")
        state["error_message"] = "Missing normalized_skills or requisition_input"
        return state
    
    # Extract requisition parameters
    mandatory_skill_ids = normalized_skills.get("mandatory_skill_ids", [])
    preferred_skill_ids = normalized_skills.get("preferred_skill_ids", [])
    mandatory_alternatives = normalized_skills.get("mandatory_alternatives", {})
    preferred_alternatives = normalized_skills.get("preferred_alternatives", {})
    required_certifications = parsed_jd.get("certifications_required", [])
    required_locations = parsed_jd.get("location", [])
    required_work_modes = parsed_jd.get("work_mode", [])
    
    # Extract experience requirements from parsed_jd
    min_experience_months = None
    max_experience_months = None
    if parsed_jd and parsed_jd.get("experience"):
        min_experience_months = parsed_jd["experience"].get("min_months")
        max_experience_months = parsed_jd["experience"].get("max_months")
    
    # Extract date requirements for availability check
    expected_start_date = None
    requisition_duration_month = None
    if parsed_jd:
        expected_start_date = parsed_jd.get("expected_start_date")
        requisition_duration_month = parsed_jd.get("requisition_duration_month")
    
    # Determine which team members to evaluate
    retrieved_candidates = state.get("retrieved_candidates")
    
    db: Session = SessionLocal()
    try:
        if retrieved_candidates:
            retrieved_results = {c["team_member_id"]: c for c in retrieved_candidates}
            retrieved_ids = list(retrieved_results.keys())
            
            team_members = db.query(TeamMember).filter(
                TeamMember.team_member_id.in_(retrieved_ids),
                TeamMember.is_active == True
            ).all()
            logger.info(f"Evaluating {len(team_members)} candidates filtered by RAG")
        else:
            retrieved_results = {}
            team_members = db.query(TeamMember).filter(TeamMember.is_active == True).all()
            logger.info(f"Found {len(team_members)} active team members to evaluate (No RAG filter)")
        
        candidate_scores = []
        scoring_agent = ScoringAgent(logger=logger)
        from app.ai.utils.ai_confidence import get_ai_fit_confidence, calculate_ai_boost
        from app.db.models.models import TeamMemberEmbedding
        
        jd_text = parsed_jd.get("jd_text", "")
        
        for member in team_members:
            try:
                # 1. Fetch skills, certs, and profile text
                member_skill_ids = [
                    skill.skill_id 
                    for skill in db.query(TeamMemberSkill)
                    .filter(TeamMemberSkill.team_member_id == member.team_member_id)
                    .all()
                ]
                
                member_certs = [
                    cert.certificate
                    for cert in db.query(TeamMemberSkillCertification)
                    .filter(TeamMemberSkillCertification.team_member_id == member.team_member_id)
                    .all()
                ]
                
                # Fetch profile text for AI Confidence
                embedding_record = db.query(TeamMemberEmbedding).filter(
                    TeamMemberEmbedding.team_member_id == member.team_member_id
                ).first()
                profile_text = embedding_record.profile_text if embedding_record else ""
                
                # 2. Evaluate availability
                availability_result = evaluate_availability(
                    db,
                    member.team_member_id,
                    expected_start_date,
                    requisition_duration_month,
                    threshold_percentage=80.0,
                )
                
                # 3. Deterministic Agentic Scoring (Phase 1 core)
                rag_scores_dict = retrieved_results.get(member.team_member_id, {})
                profile_data = {
                    "skill_ids": member_skill_ids,
                    "mandatory_skill_ids": mandatory_skill_ids,
                    "preferred_skill_ids": preferred_skill_ids,
                    "mandatory_alternatives": mandatory_alternatives,
                    "preferred_alternatives": preferred_alternatives,
                    "experience_months": member.experience_in_months or 0,
                    "min_experience_months": min_experience_months,
                    "max_experience_months": max_experience_months,
                    "certifications": member_certs,
                    "required_certifications": required_certifications,
                    "location": member.base_location,
                    "required_locations": required_locations,
                    "work_mode": member.work_type.value if member.work_type else None,
                    "required_work_modes": required_work_modes,
                    "jd_level": parsed_jd.get("level", "MID"),
                    "is_available": availability_result["is_available"],
                    "available_capacity": availability_result["available_capacity"],
                }
                
                rag_candidate = RAGCandidate(
                    team_member_id=member.team_member_id,
                    final_similarity=rag_scores_dict.get("final_similarity", 0.5),
                    mandatory_similarity=rag_scores_dict.get("mandatory_similarity", 0.5),
                    preferred_similarity=rag_scores_dict.get("preferred_similarity", 0.5),
                    jd_level_similarity=rag_scores_dict.get("jd_level_similarity", 0.5),
                    certification_similarity=rag_scores_dict.get("certification_similarity", 0.5),
                    phase0_score_breakdown=rag_scores_dict.get("phase0_score_breakdown", {})
                )
                
                scoring_result = scoring_agent.execute(rag_candidate, profile_data)
                
                # 4. AI Fit Confidence (TASK-08)
                ai_fit = get_ai_fit_confidence(jd_text, profile_text)
                confidence_score = ai_fit["confidence_score"]
                ai_boost = calculate_ai_boost(confidence_score)
                
                # Log AI Confidence LLM call
                if "llm_call_logs" not in state or state["llm_call_logs"] is None:
                    state["llm_call_logs"] = []
                
                if ai_fit.get("usage"):
                    usage = ai_fit["usage"]
                    state["llm_call_logs"].append({
                        "agent_name": "matching_scoring",
                        "prompt_name": "ai_fit_confidence",
                        "model": usage.get("model", "llama-3.1-8b"),
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                        "cost_usd": 0.0
                    })
                
                # Apply boost to final match score
                final_agentic_score = scoring_result.match_score + ai_boost
                final_agentic_score = round(max(0.0, min(1.0, final_agentic_score)), 4)
                
                # AI Override Check (SPEC-002)
                ai_override_applied = (confidence_score >= 0.75 and scoring_result.score_breakdown["role_type"] == "SENIOR")
                
                # Check Role Fit Threshold (GATE)
                role_type = scoring_result.score_breakdown["role_type"]
                role_weights = ScoringAgent.ROLE_WEIGHTS[role_type]
                role_fit_threshold = role_weights["GATE"]
                meets_threshold = final_agentic_score >= role_fit_threshold
                
                score_dict = {
                    "team_member_id": scoring_result.team_member_id,
                    "final_score": final_agentic_score,
                    "base_agentic_score": scoring_result.match_score,
                    "ai_confidence_score": confidence_score,
                    "ai_boost": ai_boost,
                    "ai_override_applied": ai_override_applied,
                    "ai_reasoning": ai_fit["reasoning"],
                    "role_type": role_type,
                    "role_fit_threshold": role_fit_threshold,
                    "meets_threshold": meets_threshold,
                    "is_available": scoring_result.is_available,
                    "semantic_similarity": round(scoring_result.detailed_breakdown.semantic_similarity, 2),
                    "experience_score": round(scoring_result.detailed_breakdown.experience_score, 2),
                    "phase0_ledger": rag_candidate.phase0_score_breakdown,
                    "score_breakdown": scoring_result.score_breakdown,
                    "match_reasons": {
                        "ai_reasoning": ai_fit["reasoning"],
                        "strengths": ai_fit.get("key_strengths", []),
                        "gaps": ai_fit.get("major_gaps", []),
                        "mandatory_score": scoring_result.detailed_breakdown.mandatory_score,
                        "preferred_score": scoring_result.detailed_breakdown.preferred_score,
                        "experience_score": scoring_result.detailed_breakdown.experience_score,
                        "certification_score": scoring_result.detailed_breakdown.certification_score,
                        "semantic_similarity": scoring_result.detailed_breakdown.semantic_similarity,
                        "location_matched": scoring_result.detailed_breakdown.location_matched,
                        "work_mode_matched": scoring_result.detailed_breakdown.work_mode_matched,
                    },
                    "total_m": len(mandatory_skill_ids),
                    "weight_m": role_weights.get("M", 0.5),
                    "weight_p": role_weights.get("P", 0.2),
                    "weight_s": role_weights.get("S", 0.25),
                    "reason": "Low Semantic Similarity (0.0)" if scoring_result.detailed_breakdown.semantic_similarity == 0.0 else "Baseline Evaluation"
                }
                
                # Log detailed walkthrough
                ScoringAudit.log_candidate_walkthrough(score_dict)
                
                candidate_scores.append(score_dict)
                
            except Exception as e:
                logger.error(f"Error scoring team member {member.team_member_id}: {str(e)}", exc_info=True)
                continue
        
        # Sort by final_score descending
        candidate_scores.sort(key=lambda x: x["final_score"], reverse=True)
        
        state["candidate_scores"] = candidate_scores
        logger.info(f"Phase 1 Agentic Scoring completed with {len(candidate_scores)} candidates")
        
    except Exception as e:
        logger.error(f"Error in matching_scoring_node: {str(e)}", exc_info=True)
        state["error_message"] = f"Phase 1 Scoring failed: {str(e)}"
    finally:
        db.close()
    
    return state
