"""Matching and scoring agent."""

import logging
import re
from datetime import date
from typing import Dict

from sqlalchemy.orm import Session

from app.ai.availability import evaluate_availability
from app.ai.utils.scoring import ScoringAgent
from app.ai.utils.scoring_audit import ScoringAudit
from app.ai.utils.models import RAGCandidate
from app.ai.state import GraphState
from app.db.models import TeamMember, TeamMemberSkill, TeamMemberSkillCertification
from app.db.session import SessionLocal
from app.observability.tracing import trace_node
from app.settings import settings


logger = logging.getLogger(__name__)


def _sanitize_skill_list(skill_list: list) -> list:
    """Remove tokenized/PII values from skill lists."""
    if not skill_list:
        return []
    sanitized = []
    for skill in skill_list:
        if isinstance(skill, str):
            if re.match(r'(CLIENT|PROJECT)_TOKEN_[a-f0-9]{8}', skill, re.IGNORECASE):
                logger.warning(f"Filtered out tokenized value from skill list: {skill}")
                continue
            if re.match(r'^[a-f0-9]+$', skill, re.IGNORECASE):
                logger.warning(f"Filtered out hex-only value from skill list: {skill}")
                continue
            sanitized.append(skill.strip())
    return sanitized


def _fmt_rating(raw) -> str:
    return f"{raw}/5" if raw is not None else "unrated"


def _fmt_experience(exp_m) -> str:
    if exp_m is None:
        return "unknown"
    yrs, mths = divmod(exp_m, 12)
    return f"{yrs}y {mths}m" if yrs else f"{mths}m"


def _enrich_skill_details(
    skill_names: list,
    alternatives: dict,
    skill_raw_ratings: dict,
    skill_exp_months: dict,
    member_skill_ids: list,
) -> list:
    """Return matched skill names enriched with rating and experience for output display."""
    member_set = set(member_skill_ids)
    result = []
    for name in _sanitize_skill_list(skill_names or []):
        alt_ids = alternatives.get(name, [])
        matched_ids = [sid for sid in alt_ids if sid in member_set]
        if not matched_ids:
            result.append({"skill": name, "rating": "profile mention", "experience": "unknown", "experience_months": None})
            continue
        best_id = max(matched_ids, key=lambda sid: skill_raw_ratings.get(sid) or 0)
        exp_m = skill_exp_months.get(best_id)
        result.append({
            "skill": name,
            "rating": _fmt_rating(skill_raw_ratings.get(best_id)),
            "experience": _fmt_experience(exp_m),
            "experience_months": exp_m,
        })
    return result


def _build_candidate_context(
    member,
    skill_records,
    skill_name_map: Dict[str, str],
    cert_records,
    profile_text: str,
    mandatory_matched: list = None,
    mandatory_missing: list = None,
) -> str:
    """Append live structured data to profile_text before LLM evaluation."""
    name_to_skill: Dict[str, tuple] = {}
    for s in skill_records:
        name = skill_name_map.get(s.skill_id)
        if name:
            name_to_skill[name] = (s.rating, s.experience_in_months)

    skill_lines = []
    for s in skill_records:
        name = skill_name_map.get(s.skill_id, str(s.skill_id))
        rating = f"{s.rating}/5" if s.rating is not None else "unrated"
        if s.experience_in_months is not None:
            yrs, mths = divmod(s.experience_in_months, 12)
            exp = f"{yrs}y {mths}m" if yrs else f"{mths}m"
        else:
            exp = "duration unknown"
        skill_lines.append(f"  - {name}: {rating}, {exp}")

    mandatory_lines = []
    for name in (mandatory_matched or []):
        clean_name = name.replace(" (semantic)", "")
        if clean_name in name_to_skill:
            r, em = name_to_skill[clean_name]
            r_str = f"{r}/5" if r is not None else "unrated"
            if em is not None:
                yrs, mths = divmod(em, 12)
                e_str = f"{yrs}y {mths}m" if yrs else f"{mths}m"
            else:
                e_str = "duration unknown"
            mandatory_lines.append(f"  - {clean_name}: PRESENT ({r_str}, {e_str})")
        else:
            mandatory_lines.append(f"  - {clean_name}: PRESENT (proficiency data unavailable)")
    for name in (mandatory_missing or []):
        mandatory_lines.append(f"  - {name}: ABSENT — not on candidate profile")

    active_certs = [
        c.certificate for c in cert_records
        if c.certificate and (c.valid_till is None or c.valid_till >= date.today())
    ]

    total_exp = member.experience_in_months or 0
    exp_str = f"{total_exp // 12}y {total_exp % 12}m"

    mandatory_section = (
        "JD Mandatory Skills (deterministic result — align your language here):\n"
        + ("\n".join(mandatory_lines) if mandatory_lines else "  None required")
    )

    structured_block = (
        f"\n\n--- Structured Candidate Data ---\n"
        f"Designation: {member.designation or 'N/A'}\n"
        f"Total Experience: {exp_str}\n\n"
        f"{mandatory_section}\n\n"
        f"All skills on record:\n"
        f"{chr(10).join(skill_lines) if skill_lines else '  None on record'}\n\n"
        f"Active Certifications:\n"
        f"  {', '.join(active_certs) if active_certs else 'None'}"
    )
    return (profile_text or "") + structured_block


@trace_node("matching_scoring")
def matching_scoring_node(state: GraphState) -> GraphState:
    """Execute deterministic matching and scoring for all team members."""
    logger.info("Executing Matching_Scoring_Agent node")

    state["error_message"] = None

    normalized_skills = state.get("normalized_skills")
    requisition_input = state.get("requisition_input")
    parsed_jd = state.get("parsed_jd")

    if not normalized_skills or not requisition_input:
        logger.error("Missing required state: normalized_skills or requisition_input")
        state["error_message"] = "Missing normalized_skills or requisition_input"
        return state

    mandatory_skill_ids     = normalized_skills.get("mandatory_skill_ids", [])
    preferred_skill_ids     = normalized_skills.get("preferred_skill_ids", [])
    mandatory_alternatives  = normalized_skills.get("mandatory_alternatives", {})
    preferred_alternatives  = normalized_skills.get("preferred_alternatives", {})
    required_certifications = parsed_jd.get("certifications_required", [])
    required_locations      = parsed_jd.get("location", [])
    required_work_modes     = parsed_jd.get("work_mode", [])

    min_experience_months = None
    max_experience_months = None
    if parsed_jd and parsed_jd.get("experience"):
        min_experience_months = parsed_jd["experience"].get("min_months")
        max_experience_months = parsed_jd["experience"].get("max_months")

    expected_start_date        = parsed_jd.get("expected_start_date") if parsed_jd else None
    requisition_duration_month = parsed_jd.get("requisition_duration_month") if parsed_jd else None

    retrieved_candidates = state.get("retrieved_candidates")
    jd_text = parsed_jd.get("jd_text", "")

    db: Session = SessionLocal()
    try:
        # --- Resolve candidate pool ---
        if retrieved_candidates is not None:
            retrieved_results = {c["team_member_id"]: c for c in retrieved_candidates}
            retrieved_ids = list(retrieved_results.keys())
            team_members = (
                db.query(TeamMember)
                .filter(TeamMember.team_member_id.in_(retrieved_ids), TeamMember.is_active == True)
                .all()
            ) if retrieved_ids else []
            logger.info("Evaluating %d candidates matched by RAG Search", len(team_members))
        else:
            retrieved_results = {}
            team_members = db.query(TeamMember).filter(TeamMember.is_active == True).all()
            logger.info("RAG skipped. Evaluating %d active team members (fallback)", len(team_members))

        candidate_scores = []
        scoring_agent = ScoringAgent(logger=logger)
        from app.ai.utils.ai_confidence import get_ai_fit_confidence, calculate_ai_boost
        from app.db.models.models import TeamMemberEmbedding

        for member in team_members:
            try:
                # 1. Skills
                skill_records = (
                    db.query(TeamMemberSkill)
                    .filter(TeamMemberSkill.team_member_id == member.team_member_id)
                    .all()
                )
                member_skill_ids_candidate = [s.skill_id for s in skill_records]
                skill_ratings = {
                    s.skill_id: (s.rating / 5.0) if s.rating is not None else 0.5
                    for s in skill_records
                }
                skill_raw_ratings = {s.skill_id: s.rating for s in skill_records}
                skill_exp_months  = {s.skill_id: s.experience_in_months for s in skill_records}

                # 2. Certifications
                cert_records = (
                    db.query(TeamMemberSkillCertification)
                    .filter(TeamMemberSkillCertification.team_member_id == member.team_member_id)
                    .all()
                )
                member_certs = [c.certificate for c in cert_records if c.certificate]
                cert_validity = {
                    c.certificate: (c.valid_till is None or c.valid_till >= date.today())
                    for c in cert_records if c.certificate
                }

                # 3. Profile text & skill names
                embedding_record = db.query(TeamMemberEmbedding).filter(
                    TeamMemberEmbedding.team_member_id == member.team_member_id
                ).first()
                profile_text = embedding_record.profile_text if embedding_record else ""

                from app.db.models import SkillMaster
                skill_name_rows = (
                    db.query(SkillMaster.skill_id, SkillMaster.skill_name)
                    .join(TeamMemberSkill, SkillMaster.skill_id == TeamMemberSkill.skill_id)
                    .filter(TeamMemberSkill.team_member_id == member.team_member_id)
                    .all()
                )
                member_skill_names = [r.skill_name for r in skill_name_rows]
                skill_name_map = {r.skill_id: r.skill_name for r in skill_name_rows}

                # 4. Availability
                availability_result = evaluate_availability(
                    db,
                    member.team_member_id,
                    expected_start_date,
                    requisition_duration_month,
                    threshold_percentage=settings.availability_threshold_percentage,
                )

                # 5. Build RAGCandidate
                rag_scores_dict = retrieved_results.get(member.team_member_id, {})
                rag_candidate = RAGCandidate(
                    team_member_id=member.team_member_id,
                    final_similarity=rag_scores_dict.get("final_similarity", 0.5),
                    mandatory_similarity=rag_scores_dict.get("mandatory_similarity", 0.5),
                    preferred_similarity=rag_scores_dict.get("preferred_similarity", 0.5),
                    jd_level_similarity=rag_scores_dict.get("jd_level_similarity", 0.5),
                    full_jd_similarity=rag_scores_dict.get("full_jd_similarity", 0.5),
                    certification_similarity=rag_scores_dict.get("certification_similarity", 0.5),
                    experience_in_months=member.experience_in_months or 0,
                    phase0_score_breakdown=rag_scores_dict.get("phase0_score_breakdown", {}),
                )

                # 6. Score
                profile_data = {
                    "skill_ids":              member_skill_ids_candidate,
                    "skill_ratings":          skill_ratings,
                    "skill_exp_months":       skill_exp_months,
                    "skill_names":            member_skill_names,
                    "designation":            member.designation,
                    "mandatory_skill_ids":    mandatory_skill_ids,
                    "preferred_skill_ids":    preferred_skill_ids,
                    "mandatory_alternatives": mandatory_alternatives,
                    "preferred_alternatives": preferred_alternatives,
                    "experience_months":      member.experience_in_months or 0,
                    "min_experience_months":  min_experience_months,
                    "max_experience_months":  max_experience_months,
                    "certifications":         member_certs,
                    "cert_validity":          cert_validity,
                    "profile_text":           profile_text,
                    "required_certifications":  required_certifications,
                    "location":                 member.base_location,
                    "required_locations":       required_locations,
                    "work_mode":                member.work_type.value if member.work_type else None,
                    "required_work_modes":      required_work_modes,
                    "jd_level":                 parsed_jd.get("level", "MID"),
                    "jd_text":                  jd_text,
                    "is_available":             availability_result["is_available"],
                    "available_capacity":       availability_result["available_capacity"],
                }

                scoring_result = scoring_agent.execute(rag_candidate, profile_data)

                is_qualified = scoring_result.detailed_breakdown.stage1_passed
                role_type    = scoring_result.detailed_breakdown.role_type

                # --- AI Override & Boost ---
                ai_fit = {
                    "confidence_score": 0.0,
                    "reasoning": "Skipped due to Skill Gate failure",
                    "key_strengths": [],
                    "major_gaps": [],
                }
                confidence_score  = 0.0
                ai_boost          = 0.0
                ai_override_applied = False

                if is_qualified:
                    enriched_context = _build_candidate_context(
                        member, skill_records, skill_name_map, cert_records, profile_text,
                        mandatory_matched=scoring_result.detailed_breakdown.mandatory_matched,
                        mandatory_missing=scoring_result.detailed_breakdown.mandatory_missing,
                    )
                    ai_fit = get_ai_fit_confidence(jd_text, enriched_context)
                    confidence_score = ai_fit["confidence_score"]

                    if (not scoring_result.is_qualified
                            and role_type == "SENIOR"
                            and confidence_score >= settings.ai_override_threshold_senior):
                        qual_reason = scoring_result.detailed_breakdown.qualification_reason
                        if "Semantic similarity" in qual_reason or "below threshold" in qual_reason:
                            is_qualified = True
                            ai_override_applied = True

                    if is_qualified:
                        ai_boost = calculate_ai_boost(confidence_score)

                final_agentic_score = scoring_result.match_score
                if is_qualified and ai_boost > 0:
                    final_agentic_score += ai_boost
                final_agentic_score = round(max(0.0, min(1.0, final_agentic_score)), 4)

                bd = scoring_result.score_breakdown
                score_dict = {
                    "team_member_id":       scoring_result.team_member_id,
                    "final_score":          final_agentic_score,
                    "is_qualified":         is_qualified,
                    "qualification_reason": scoring_result.detailed_breakdown.qualification_reason,
                    "base_agentic_score":   scoring_result.match_score,
                    "ai_confidence_score":  confidence_score,
                    "ai_boost":             ai_boost if is_qualified else 0.0,
                    "ai_override_applied":  ai_override_applied,
                    "ai_reasoning":         ai_fit["reasoning"],
                    "role_type":            role_type,
                    "experience_in_months": member.experience_in_months or 0,
                    "meets_threshold":      is_qualified,

                    "is_available":         scoring_result.is_available,
                    "semantic_similarity":  round(scoring_result.detailed_breakdown.semantic_similarity, 2),
                    "experience_score":     round(scoring_result.detailed_breakdown.experience_score, 2),
                    "phase0_ledger":        rag_candidate.phase0_score_breakdown,
                    "rag_signals": {
                        "final_similarity":    round(rag_candidate.final_similarity, 4),
                        "full_jd_similarity":  round(rag_candidate.full_jd_similarity, 4),
                        "jd_level_similarity": round(rag_candidate.jd_level_similarity, 4),
                        "mandatory_rag_sim":   round(rag_candidate.mandatory_similarity, 4),
                        "preferred_rag_sim":   round(rag_candidate.preferred_similarity, 4),
                        "cert_rag_sim":        round(rag_candidate.certification_similarity, 4),
                    },
                    "score_breakdown": bd,
                    "match_reasons": {
                        "ai_reasoning":           ai_fit["reasoning"],
                        "strengths":              ai_fit.get("key_strengths", []),
                        "gaps":                   ai_fit.get("major_gaps", []),
                        "availability_score":     round(availability_result.get("available_capacity", 100.0) / 100.0, 2),
                        "available_capacity_pct": round(availability_result.get("available_capacity", 100.0), 2),
                        "mandatory_score":        scoring_result.detailed_breakdown.mandatory_score,
                        "mandatory_matched":      _sanitize_skill_list(scoring_result.detailed_breakdown.mandatory_matched),
                        "mandatory_matched_detail": _enrich_skill_details(
                            scoring_result.detailed_breakdown.mandatory_matched,
                            mandatory_alternatives,
                            skill_raw_ratings,
                            skill_exp_months,
                            member_skill_ids_candidate,
                        ),
                        "mandatory_missing":      _sanitize_skill_list(scoring_result.detailed_breakdown.mandatory_missing),
                        "preferred_score":        scoring_result.detailed_breakdown.preferred_score,
                        "preferred_matched":      _sanitize_skill_list(scoring_result.detailed_breakdown.preferred_matched)[:5],
                        "preferred_matched_detail": _enrich_skill_details(
                            scoring_result.detailed_breakdown.preferred_matched,
                            preferred_alternatives,
                            skill_raw_ratings,
                            skill_exp_months,
                            member_skill_ids_candidate,
                        )[:5],
                        "preferred_missing":      _sanitize_skill_list(scoring_result.detailed_breakdown.preferred_missing)[:5],
                        "experience_score":       scoring_result.detailed_breakdown.experience_score,
                        "title_score":            scoring_result.detailed_breakdown.title_score,
                        "certification_score":    scoring_result.detailed_breakdown.certification_score,
                        "certification_matched":  _sanitize_skill_list(scoring_result.detailed_breakdown.certification_matched),
                        "certification_missing":  _sanitize_skill_list(scoring_result.detailed_breakdown.certification_missing),
                        "certification_expired":  _sanitize_skill_list(scoring_result.detailed_breakdown.certification_expired),
                        "semantic_similarity":    scoring_result.detailed_breakdown.semantic_similarity,
                        "location_matched":       scoring_result.detailed_breakdown.location_matched,
                        "work_mode_matched":      scoring_result.detailed_breakdown.work_mode_matched,
                        "qualification_status":   "QUALIFIED" if is_qualified else "DISQUALIFIED",
                        "qualification_reason":   scoring_result.detailed_breakdown.qualification_reason,
                    },
                    "total_m":  len(mandatory_skill_ids),
                    "weight_m": bd.get("weight_m", 0.0),
                    "weight_p": bd.get("weight_p", 0.0),
                    "weight_s": bd.get("weight_s", 0.0),
                    "weight_c": bd.get("weight_c", 0.0),
                    "weight_a": bd.get("weight_a", 0.0),
                    "reason":   scoring_result.detailed_breakdown.qualification_reason,
                }

                ScoringAudit.log_candidate_walkthrough(score_dict)
                candidate_scores.append(score_dict)

            except Exception as e:
                logger.error(
                    "Error scoring team member %s: %s", member.team_member_id, str(e), exc_info=True
                )
                continue

        candidate_scores.sort(key=lambda x: x["final_score"], reverse=True)
        state["candidate_scores"] = candidate_scores
        logger.info("Scoring completed: %d candidates", len(candidate_scores))

    except Exception as e:
        logger.error("Error in matching_scoring_node: %s", str(e), exc_info=True)
        state["error_message"] = f"Scoring failed: {str(e)}"
    finally:
        db.close()

    return state
