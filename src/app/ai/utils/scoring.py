"""Scoring Agent - Extended scoring with normalized skills and certifications."""

import logging
import re
from typing import Any, Dict, List, Optional

from app.settings import settings
from app.ai.utils.base import BaseAgent
from app.ai.utils.models import RAGCandidate, ScoringResult, ScoringBreakdown
from app.db.repositories.skill_config import get_skill_groups, get_family_keywords


class ScoringAgent(BaseAgent):
    """Score candidates based on weighted components defined in settings."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        super().__init__(agent_name="ScoringAgent", logger=logger)
    
    def validate_input(self, _input_data: Any) -> bool:
        return True

    def format_output(self, result: Any) -> Any:
        return result
    
    @property
    def skill_groups(self) -> Dict[str, List[str]]:
        return get_skill_groups()

    def _get_role_configs(self) -> Dict[str, Any]:
        """Expose ROLE_CONFIGS dynamically based on settings."""
        return {
            "SENIOR": {
                "level": "SENIOR",
                "weights": {
                    "mandatory": settings.weight_mandatory_senior,
                    "preferred": settings.weight_preferred_senior,
                    "semantic": settings.weight_semantic_senior,
                    "context": settings.weight_context_senior,
                    "availability": settings.weight_availability_senior,
                },
                "gates": {
                    "min_skill_weighted": settings.min_skill_weighted_senior,
                    "min_semantic": settings.min_semantic_senior
                },
                "fit_threshold": settings.fit_threshold_senior
            },
            "MID": {
                "level": "MID",
                "weights": {
                    "mandatory": settings.weight_mandatory_mid,
                    "preferred": settings.weight_preferred_mid,
                    "semantic": settings.weight_semantic_mid,
                    "context": settings.weight_context_mid,
                    "availability": settings.weight_availability_mid,
                },
                "gates": {
                    "min_skill_weighted": settings.min_skill_weighted_mid,
                    "min_semantic": settings.min_semantic_mid
                },
                "fit_threshold": settings.fit_threshold_mid
            },
            "JUNIOR": {
                "level": "JUNIOR",
                "weights": {
                    "mandatory": settings.weight_mandatory_junior,
                    "preferred": settings.weight_preferred_junior,
                    "semantic": settings.weight_semantic_junior,
                    "context": settings.weight_context_junior,
                    "availability": settings.weight_availability_junior,
                },
                "gates": {
                    "min_skill_weighted": settings.min_skill_weighted_junior,
                    "min_semantic": settings.min_semantic_junior
                },
                "fit_threshold": settings.fit_threshold_junior
            }
        }

    def _get_role_config(self, experience_months: int, jd_level: str = "") -> Dict[str, Any]:
        """Determine role config based on experience or JD level."""
        level = (jd_level or "").upper()
        configs = self._get_role_configs()
        
        if "SENIOR" in level or "SR" in level or experience_months >= settings.senior_exp_threshold:
            return configs["SENIOR"]
        elif "JUNIOR" in level or "JR" in level or experience_months < settings.junior_exp_threshold:
            return configs["JUNIOR"]
        return configs["MID"]

    def _get_skill_group(self, skill: str) -> str:
        s_lower = skill.lower()
        for group, members in self.skill_groups.items():
            if any(mem in s_lower for mem in members) or group in s_lower:
                return group
        return s_lower

    _SHORT_ALLOW = {"s3", "c#", "f#", "r", "go", "ui", "ux"}

    def _skill_found_in_text(self, members: List[str], text: str) -> bool:
        """Return True if any group member appears as a whole word in text."""
        for mem in members:
            if len(mem) <= 2 and mem.lower() not in self._SHORT_ALLOW:
                continue
            pattern = r'(?<![a-z0-9_])' + re.escape(mem.lower()) + r'(?![a-z0-9_])'
            if re.search(pattern, text):
                return True
        return False

    def _blend_skill_contribution(
        self,
        sid: str,
        skill_ratings: Optional[Dict[str, float]],
        skill_exp_months: Optional[Dict[str, Optional[int]]],
    ) -> float:
        """Return a 0–1 contribution for a single matched skill ID.

        Binary mode (SKILL_RATING_WEIGHT=0 and SKILL_EXP_WEIGHT=0 in .env):
          skill presence alone counts as full contribution (1.0).

        Weighted mode (default):
          blends normalised rating (60%) and experience (40%). None values
          default to 0.5 so missing metadata ranks below fully-rated skills."""
        # Binary mode: both weights set to 0 → presence is enough, depth ignored
        if settings.skill_rating_weight == 0 and settings.skill_exp_weight == 0:
            return 1.0

        norm_rating = skill_ratings.get(sid, 0.5) if skill_ratings is not None else 1.0
        if skill_exp_months is not None:
            raw_exp = skill_exp_months.get(sid)
            norm_exp = (
                min(raw_exp / settings.skill_exp_months_cap, 1.0)
                if raw_exp is not None
                else 0.5
            )
        else:
            norm_exp = 1.0
        return settings.skill_rating_weight * norm_rating + settings.skill_exp_weight * norm_exp

    def _calculate_skill_group_score(
        self,
        member_skill_ids: List[str],
        skill_alternatives: Dict[str, List[str]],
        profile_text: str = "",
        skill_ratings: Optional[Dict[str, float]] = None,
        skill_exp_months: Optional[Dict[str, Optional[int]]] = None,
    ) -> Dict[str, Any]:
        """Two-pass skill group matching: skill ID check then profile text fallback.
        Works for both mandatory and preferred skill groups.

        When skill_ratings / skill_exp_months are provided, each matched skill's
        contribution is a blend of normalised rating (60%) and experience (40%).
        Text-only matches contribute settings.profile_text_match_weight.
        When both dicts are None all contributions are 1.0 (backward-compatible)."""
        if not skill_alternatives:
            return {"score": 1.0, "matched": [], "missing": []}

        member_skills = set(member_skill_ids)
        p_text_lower = (profile_text or "").lower()
        matched, missing = [], []
        contribution_sum = 0.0

        for canonical, alt_ids in skill_alternatives.items():
            matched_ids = [sid for sid in alt_ids if sid in member_skills]
            if matched_ids:
                matched.append(canonical)
                contribution = max(
                    self._blend_skill_contribution(sid, skill_ratings, skill_exp_months)
                    for sid in matched_ids
                )
                contribution_sum += contribution
                continue

            group_name = self._get_skill_group(canonical)
            members = self.skill_groups.get(group_name, [canonical])
            found = self._skill_found_in_text(members, p_text_lower)
            if found:
                matched.append(canonical)
                # Binary mode: text match is also full credit
                text_contribution = (
                    1.0 if settings.skill_rating_weight == 0 and settings.skill_exp_weight == 0
                    else settings.profile_text_match_weight
                )
                contribution_sum += text_contribution
            else:
                missing.append(canonical)

        total = len(skill_alternatives)
        return {"score": contribution_sum / total if total else 1.0, "matched": matched, "missing": missing}

    # Location terms that mean "no fixed place" — never a physical constraint
    _VIRTUAL_LOCS = frozenset({
        "remote", "any", "wfh", "anywhere", "global", "worldwide",
        "virtual", "online", "n/a", "na", "none",
    })

    def _calculate_context_boost(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Dynamic context scoring: only criteria the JD actually constrains contribute.
        Non-constraining criteria (no certs required, remote-only location, flexible work
        mode) are excluded from both numerator and denominator so their weight flows to
        criteria that can actually differentiate candidates."""
        active_sum = 0.0
        active_weight = 0.0

        # --- Experience: active only when JD sets a minimum ---
        exp_score = self._calculate_experience_score(
            profile_data.get("experience_months", 0),
            profile_data.get("min_experience_months"),
            profile_data.get("max_experience_months"),
        )
        if profile_data.get("min_experience_months"):
            active_sum    += exp_score * settings.weight_experience
            active_weight += settings.weight_experience

        # --- Certification: active only when JD requires certs ---
        cert_res = self._calculate_certification_score(
            profile_data.get("certifications", []),
            profile_data.get("required_certifications", []),
            profile_data.get("cert_validity"),
        )
        if profile_data.get("required_certifications"):
            active_sum    += cert_res["score"] * settings.weight_certification
            active_weight += settings.weight_certification

        # --- Location: active only when at least one physical location is required ---
        required_locations = profile_data.get("required_locations", [])
        physical_locs = [l for l in required_locations if l.strip().lower() not in self._VIRTUAL_LOCS]
        loc_score = self._calculate_location_score(
            profile_data.get("location"), required_locations
        )
        if physical_locs:
            active_sum    += loc_score * settings.weight_location
            active_weight += settings.weight_location

        # --- Work mode: active only when a single mode is required (multiple = flexible) ---
        required_work_modes = profile_data.get("required_work_modes", [])
        mode_score = self._calculate_work_mode_score(
            profile_data.get("work_mode"), required_work_modes
        )
        if len(required_work_modes) == 1:
            active_sum    += mode_score * settings.weight_work_mode
            active_weight += settings.weight_work_mode

        # --- Title: always active ---
        jd_text = profile_data.get("jd_text") or ""
        lines = jd_text.splitlines()
        jd_title = lines[0].lower() if lines else ""
        if "title" in profile_data:
            jd_title = profile_data.get("title", "").lower()
        member_desig = (profile_data.get("designation") or "").lower()
        title_score = 0.0
        if jd_title and member_desig:
            if jd_title in member_desig or member_desig in jd_title:
                title_score = 1.0
        active_sum    += title_score * settings.weight_jd_text
        active_weight += settings.weight_jd_text

        aggregate = active_sum / active_weight if active_weight > 0 else 0.0

        exp_active   = bool(profile_data.get("min_experience_months"))
        cert_active  = bool(profile_data.get("required_certifications"))
        loc_active   = bool(physical_locs)
        mode_active  = len(required_work_modes) == 1

        context_breakdown = {
            "active_weight": round(active_weight, 4),
            "components": {
                "experience": {
                    "score": round(exp_score, 2),
                    "weight": settings.weight_experience,
                    "active": exp_active,
                    "weighted_contribution": round(exp_score * settings.weight_experience, 4) if exp_active else 0.0,
                },
                "certification": {
                    "score": round(cert_res["score"], 2),
                    "weight": settings.weight_certification,
                    "active": cert_active,
                    "weighted_contribution": round(cert_res["score"] * settings.weight_certification, 4) if cert_active else 0.0,
                },
                "location": {
                    "score": round(loc_score, 2),
                    "weight": settings.weight_location,
                    "active": loc_active,
                    "weighted_contribution": round(loc_score * settings.weight_location, 4) if loc_active else 0.0,
                },
                "work_mode": {
                    "score": round(mode_score, 2),
                    "weight": settings.weight_work_mode,
                    "active": mode_active,
                    "weighted_contribution": round(mode_score * settings.weight_work_mode, 4) if mode_active else 0.0,
                },
                "title": {
                    "score": round(title_score, 2),
                    "weight": settings.weight_jd_text,
                    "active": True,
                    "weighted_contribution": round(title_score * settings.weight_jd_text, 4),
                },
            },
        }

        return {
            "score": aggregate,
            "exp_score": exp_score,
            "cert_res": cert_res,
            "loc_score": loc_score,
            "mode_score": mode_score,
            "title_score": title_score,
            "context_breakdown": context_breakdown,
        }

    def _get_skill_family_penalty(self, member_skill_names: List[str], jd_text: str) -> float:
        """Penalty for a clearly mismatched skill family.

        Only fires when ALL three conditions are true:
          1. JD is clearly backend/AI dominated (≥2 backend indicators in jd_text)
          2. JD does NOT itself require frontend skills (< 2 frontend keywords in jd_text)
             — this prevents penalising full-stack roles like WordPress/PHP
          3. Candidate is frontend-dominant (frontend skill count > 2× backend skill count)
        """
        jd_lower = jd_text.lower()
        family = get_family_keywords()
        frontend_kws       = family.get("frontend", [])
        backend_kws        = family.get("backend", [])
        backend_indicators = family.get("backend_ai", [])

        # Condition 1: JD must have at least 2 backend/AI signals (not just "sql" in "MySQL")
        jd_backend_hits = sum(1 for kw in backend_indicators if kw in jd_lower)
        if jd_backend_hits < 2:
            return 0.0

        # Condition 2: If the JD itself asks for ≥2 frontend skills it is full-stack — no penalty
        jd_frontend_hits = sum(1 for kw in frontend_kws if kw in jd_lower)
        if jd_frontend_hits >= 2:
            return 0.0

        # Condition 3: Candidate must be clearly frontend-only (2× more frontend than backend)
        all_skills = [s.lower() for s in member_skill_names]
        f_count = sum(1 for s in all_skills if any(kw in s for kw in frontend_kws))
        b_count = sum(1 for s in all_skills if any(kw in s for kw in backend_kws))

        if f_count > 1 and f_count > b_count * 2:
            return settings.skill_family_penalty
        return 0.0


    def _calculate_experience_score(self, member_exp, min_exp, max_exp):
        if not min_exp: return 1.0
        if member_exp >= min_exp: return 1.0
        return member_exp / min_exp if min_exp > 0 else 1.0

    def _calculate_certification_score(
        self,
        member_certs: List[str],
        required_certs: List[str],
        cert_validity: Optional[Dict[str, bool]] = None,
    ) -> Dict[str, Any]:
        if not required_certs:
            return {"score": 1.0, "matched": [], "missing": [], "expired": []}
        matched, missing, expired = [], [], []
        for c in required_certs:
            if c not in member_certs:
                missing.append(c)
            elif cert_validity is not None and not cert_validity.get(c, True):
                expired.append(c)
            else:
                matched.append(c)
        score = len(matched) / len(required_certs)
        return {"score": score, "matched": matched, "missing": missing + expired, "expired": expired}

    def _calculate_location_score(self, member_loc, required_locs):
        if not required_locs: return 1.0 # Default to 1.0 if no requirement
        if not member_loc: return 0.0
        member_loc_lower = member_loc.lower()
        required_locs_lower = [l.lower() for l in required_locs]
        # Include 'remote' logic
        if "remote" in required_locs_lower or "any" in required_locs_lower:
            return 1.0
        return 1.0 if any(loc in member_loc_lower for loc in required_locs_lower) else 0.0

    def _calculate_work_mode_score(self, member_mode, required_modes):
        if not required_modes: return 1.0 # Default to 1.0 if no requirement
        if not member_mode: return 0.0
        
        # Handle wfh/remote mapping
        m_mode = member_mode.lower()
        if m_mode == "wfh": m_mode = "remote"
        
        req_modes_lower = [m.lower() for m in required_modes]
        # Map required modes too
        req_modes_normalized = []
        for rm in req_modes_lower:
            if rm == "wfh": req_modes_normalized.append("remote")
            else: req_modes_normalized.append(rm)

        return 1.0 if m_mode in req_modes_normalized else 0.0

    def execute(self, rag_candidate: RAGCandidate, profile_data: Optional[Dict] = None) -> ScoringResult:
        """
        Refined Multi-Stage Scoring Logic:
        1. Role-specific configuration (Weights/Gates)
        2. Stage 1: Qualification Check (Hard Gates)
        3. Stage 2: Weighted Scoring with context capping and skill family penalties
        """
        profile_data = profile_data or {}
        experience_months = profile_data.get("experience_months", 0)
        jd_level = profile_data.get("jd_level", "MID")
        profile_text = profile_data.get("profile_text", "")
        jd_text = profile_data.get("jd_text", "")
        skill_ratings = profile_data.get("skill_ratings")       # Dict[skill_id, norm_rating] or None
        skill_exp_months = profile_data.get("skill_exp_months") # Dict[skill_id, months|None] or None
        
        # --- PHASE 0: Configuration ---
        role_cfg = self._get_role_config(experience_months, jd_level)
        gates = role_cfg["gates"]
        role_weights = role_cfg["weights"]
        role_type = role_cfg["level"]
        
        # --- STAGE 1: Preliminary Qualification Check ---
        
        # 1. Mandatory Skills Match
        mandatory_alternatives = profile_data.get("mandatory_alternatives") or {}
        m_res = self._calculate_skill_group_score(
            profile_data.get("skill_ids", []),
            mandatory_alternatives,
            profile_text,
            skill_ratings,
            skill_exp_months,
        )
        m_match_ratio = m_res["score"]

        # 2. Preferred Skills Match
        _pref_alts = profile_data.get("preferred_alternatives") or {}
        if _pref_alts:
            _p = self._calculate_skill_group_score(
                profile_data.get("skill_ids", []),
                _pref_alts,
                profile_text,
                skill_ratings,
                skill_exp_months,
            )
            p_res = {"preferred_score": _p["score"], "matched_preferred": _p["matched"], "missing_preferred": _p["missing"]}
        else:
            p_res = {"preferred_score": 0.0, "matched_preferred": [], "missing_preferred": []}
        p_score = p_res["preferred_score"]
        
        # 3. Weighted Skill Score for Gate (Use role-specific Weights)
        weighted_skill_sum = (m_match_ratio * role_weights["mandatory"]) + (p_score * role_weights["preferred"])
        
        # 4. Semantic Match — blend seniority alignment with overall JD fit
        # full_jd_similarity is a pure vector signal (no experience/location overlap)
        _blend = settings.scoring_blend_full_jd_weight
        s_score = (
            rag_candidate.jd_level_similarity * (1.0 - _blend) +
            rag_candidate.full_jd_similarity   * _blend
        )
        
        # Qualification Logic
        is_qualified = True
        qualification_reason = "Qualified"
        
        if weighted_skill_sum < gates.get("min_skill_weighted", 0.20):
            is_qualified = False
            qualification_reason = f"Disqualified: Weighted skill score ({weighted_skill_sum:.2f}) below {gates.get('min_skill_weighted'):.2f} barrier."
        elif s_score < gates.get("min_semantic", 0.0):
            is_qualified = False
            qualification_reason = f"Disqualified: Semantic similarity ({s_score:.2f}) below {gates.get('min_semantic'):.2f} threshold."
            
        # --- STAGE 2: Full Scoring ---
        
        # Context Factors (Normalized 0-1)
        context_result = self._calculate_context_boost(profile_data)
        c_raw = context_result["score"]

        # Apply role-specific context weight; cap at the role's own weight (never exceeds it)
        context_contribution = c_raw * role_weights["context"]
        context_contribution = min(context_contribution, role_weights["context"])
        
        # Skill Family Penalty
        penalty = self._get_skill_family_penalty(profile_data.get("skill_names", []), jd_text)

        # Availability Score — normalised capacity (0–100 % → 0.0–1.0)
        avail_score = min(profile_data.get("available_capacity", 100.0) / 100.0, 1.0)

        # Final Score Calculation
        match_score = (
            (m_match_ratio * role_weights["mandatory"]) +
            (p_score * role_weights["preferred"]) +
            (s_score * role_weights["semantic"]) +
            context_contribution +
            (avail_score * role_weights["availability"]) +
            penalty
        )
        
        match_score = round(max(0.0, min(1.0, match_score)), 4)

        exp_score         = context_result["exp_score"]
        cert_res          = context_result["cert_res"]
        loc_score         = context_result["loc_score"]
        mode_score        = context_result["mode_score"]
        title_score       = context_result["title_score"]
        context_breakdown = context_result["context_breakdown"]

        # Prepare breakdown
        score_breakdown = {
            "mandatory_skills_group": m_match_ratio,
            "preferred_skills": p_score,
            "semantic_similarity": s_score,
            "context_score": c_raw,
            "context_contribution": context_contribution,
            "availability_score": avail_score,
            "title_score": title_score,
            "context_breakdown": context_breakdown,
            "weight_m": role_weights["mandatory"],
            "weight_p": role_weights["preferred"],
            "weight_s": role_weights["semantic"],
            "weight_c": role_weights["context"],
            "weight_a": role_weights["availability"],
            "penalties": penalty,
            "is_qualified": is_qualified,
            "role_type": role_type
        }

        detailed = ScoringBreakdown(
            skills_matched=p_res["matched_preferred"] + m_res["matched"],
            mandatory_matched=m_res["matched"],
            mandatory_missing=m_res["missing"],
            preferred_matched=p_res["matched_preferred"],
            preferred_missing=p_res["missing_preferred"],
            mandatory_score=round(m_match_ratio, 2),
            preferred_score=round(p_score, 2),
            certification_score=round(cert_res["score"], 2),
            certification_matched=cert_res["matched"],
            certification_missing=cert_res["missing"],
            certification_expired=cert_res.get("expired", []),
            experience_score=round(exp_score, 2),
            experience_matched=(exp_score >= 1.0),
            title_score=round(title_score, 2),
            location_score=round(loc_score, 2),
            location_matched=(loc_score >= 1.0),
            work_mode_score=round(mode_score, 2),
            work_mode_matched=(mode_score >= 1.0),
            semantic_similarity=round(s_score, 2),
            jd_level_similarity=round(rag_candidate.jd_level_similarity, 2),
            role_type=role_type,
            stage1_passed=is_qualified,
            qualification_reason=qualification_reason
        )

        return ScoringResult(
            team_member_id=rag_candidate.team_member_id,
            match_score=match_score,
            confidence=0.9,
            is_qualified=is_qualified,
            score_breakdown=score_breakdown,
            detailed_breakdown=detailed,
            is_available=profile_data.get("is_available", True),
            available_capacity=profile_data.get("available_capacity", 100.0)
        )


    
    def validate_input(self, input_data: Any) -> bool:
        return isinstance(input_data, RAGCandidate)
    
    def format_output(self, result: ScoringResult) -> ScoringResult:
        return result
