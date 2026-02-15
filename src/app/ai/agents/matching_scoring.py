"""Matching and scoring agent."""

import logging

from sqlalchemy.orm import Session

from app.ai.availability import evaluate_availability
from app.ai.utils.scoring import ScoringAgent
from app.ai.utils.models import RAGCandidate
from app.ai.state import GraphState
from app.db.models import TeamMember, TeamMemberSkill, SkillCertification
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
            # Filter members by retrieved IDs and store RAG results for lookup
            retrieved_results = {c["team_member_id"]: c for c in retrieved_candidates}
            retrieved_ids = list(retrieved_results.keys())
            
            team_members = db.query(TeamMember).filter(
                TeamMember.team_member_id.in_(retrieved_ids),
                TeamMember.is_active == True
            ).all()
            logger.info(f"Evaluating {len(team_members)} candidates filtered by RAG")
        else:
            retrieved_results = {}
            # Fallback to all active members
            team_members = db.query(TeamMember).filter(TeamMember.is_active == True).all()
            logger.info(f"Found {len(team_members)} active team members to evaluate (No RAG filter)")
        
        candidate_scores = []
        scoring_agent = ScoringAgent(logger=logger)
        
        for member in team_members:
            try:
                # Get member's skills
                member_skill_ids = [
                    skill.skill_id 
                    for skill in db.query(TeamMemberSkill)
                    .filter(TeamMemberSkill.team_member_id == member.team_member_id)
                    .all()
                ]
                
                # Get member's certifications
                member_certs = [
                    cert.certificate
                    for cert in db.query(SkillCertification)
                    .filter(SkillCertification.team_member_id == member.team_member_id)
                    .all()
                ]
                
                # Evaluate availability
                availability_result = evaluate_availability(
                    db,
                    member.team_member_id,
                    expected_start_date,
                    requisition_duration_month,
                    threshold_percentage=80.0,
                )
                
                # Prepare profile data for scoring agent
                rag_scores = retrieved_results.get(member.team_member_id, {})
                
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
                    "is_available": availability_result["is_available"],
                    "available_capacity": availability_result["available_capacity"],
                }
                
                # Create RAG candidate object
                rag_candidate = RAGCandidate(
                    team_member_id=member.team_member_id,
                    final_similarity=rag_scores.get("final_similarity", 0.5) if rag_scores else 0.5,
                    mandatory_similarity=rag_scores.get("mandatory_similarity", 0.5) if rag_scores else 0.5,
                    preferred_similarity=rag_scores.get("preferred_similarity", 0.5) if rag_scores else 0.5,
                    jd_level_similarity=rag_scores.get("jd_level_similarity", 0.5) if rag_scores else 0.5,
                    certification_similarity=rag_scores.get("certification_similarity", 0.5) if rag_scores else 0.5,
                )
                
                # Calculate complete candidate score using multi-agent utility
                scoring_result = scoring_agent.execute(rag_candidate, profile_data)
                
                # Convert back to dict format expected by the rest of the app
                # The 'skill_score' shown to users is typically a weighted combination 
                # of mandatory (0.7) and preferred (0.3)
                combined_skill_score = (
                    0.7 * scoring_result.detailed_breakdown.mandatory_score + 
                    0.3 * scoring_result.detailed_breakdown.preferred_score
                )
                
                score_dict = {
                    "team_member_id": scoring_result.team_member_id,
                    "skill_score": round(combined_skill_score, 2),
                    "experience_score": round(scoring_result.score_breakdown["experience"], 2),
                    "certification_score": round(scoring_result.score_breakdown["certification"], 2),
                    "location_score": round(scoring_result.score_breakdown["location"], 2),
                    "work_mode_score": round(scoring_result.score_breakdown["work_mode"], 2),
                    "availability_score": round(scoring_result.available_capacity / 100.0, 2),
                    "semantic_similarity": round(scoring_result.score_breakdown["semantic_similarity"], 2),
                    "jd_level_similarity": round(scoring_result.score_breakdown["jd_level"], 2),
                    "final_score": scoring_result.match_score,
                    "is_available": scoring_result.is_available,
                    "certifications": member_certs,
                    "location": member.base_location,
                    "work_mode": member.work_type.value if member.work_type else None,
                    "experience_in_months": member.experience_in_months or 0,
                    "match_reasons": {
                        "skills_matched": scoring_result.detailed_breakdown.skills_matched,
                        "mandatory_matched": scoring_result.detailed_breakdown.mandatory_matched,
                        "preferred_matched": scoring_result.detailed_breakdown.preferred_matched,
                        "mandatory_score": scoring_result.detailed_breakdown.mandatory_score,
                        "preferred_score": scoring_result.detailed_breakdown.preferred_score,
                        "certification_matched": scoring_result.detailed_breakdown.certification_matched,
                        "certification_missing": scoring_result.detailed_breakdown.certification_missing,
                        "certification_score": scoring_result.detailed_breakdown.certification_score,
                        "location_matched": scoring_result.detailed_breakdown.location_matched,
                        "location_score": scoring_result.detailed_breakdown.location_score,
                        "work_mode_matched": scoring_result.detailed_breakdown.work_mode_matched,
                        "work_mode_score": scoring_result.detailed_breakdown.work_mode_score,
                        "experience_matched": scoring_result.detailed_breakdown.experience_matched,
                        "experience_score": scoring_result.detailed_breakdown.experience_score,
                        "semantic_similarity": scoring_result.detailed_breakdown.semantic_similarity,
                        "jd_level_similarity": scoring_result.detailed_breakdown.jd_level_similarity,
                    }
                }
                
                candidate_scores.append(score_dict)
                
            except Exception as e:
                logger.error(f"Error scoring team member {member.team_member_id}: {str(e)}", exc_info=True)
                continue
        
        # Sort candidates by final_score descending
        candidate_scores.sort(key=lambda x: x["final_score"], reverse=True)
        
        state["candidate_scores"] = candidate_scores
        logger.info(f"Matching_Scoring_Agent completed with {len(candidate_scores)} scored candidates")
        
    except Exception as e:
        logger.error(f"Error in matching_scoring_node: {str(e)}", exc_info=True)
        state["error_message"] = f"Matching scoring failed: {str(e)}"
    finally:
        db.close()
    
    return state
