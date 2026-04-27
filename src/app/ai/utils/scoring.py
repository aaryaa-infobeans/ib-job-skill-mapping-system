"""Scoring Agent - Extended scoring with normalized skills and certifications."""

import logging
from typing import Any, Dict, List, Optional

from app.settings import settings
from app.ai.utils.base import BaseAgent
from app.ai.utils.models import RAGCandidate, ScoringResult, ScoringBreakdown


class ScoringAgent(BaseAgent):
    """Score candidates based on weighted components defined in settings."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        super().__init__(agent_name="ScoringAgent", logger=logger)
    
    def validate_input(self, input_data: Any) -> bool:
        return True
        
    def format_output(self, result: Any) -> Any:
        return result
    
    @property
    def skill_groups(self) -> Dict[str, List[str]]:
        """Fetch skill groups dynamically from settings."""
        return {
            "python": [k.strip() for k in settings.skill_group_python.split(",")],
            "javascript": [k.strip() for k in settings.skill_group_javascript.split(",")],
            "sql": [k.strip() for k in settings.skill_group_sql.split(",")],
            "big_data": [k.strip() for k in settings.skill_group_big_data.split(",")],
            "ai_ml": [k.strip() for k in settings.skill_group_ai_ml.split(",")],
            "cloud": [k.strip() for k in settings.skill_group_cloud.split(",")]
        }

    def _get_role_configs(self) -> Dict[str, Any]:
        """Expose ROLE_CONFIGS dynamically based on settings."""
        return {
            "SENIOR": {
                "level": "SENIOR",
                "weights": {
                    "mandatory": settings.weight_mandatory_senior,
                    "preferred": settings.weight_preferred_senior,
                    "semantic": settings.weight_semantic_senior,
                    "context": settings.weight_context_senior
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
                    "context": settings.weight_context_mid
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
                    "context": settings.weight_context_junior
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

    def _calculate_mandatory_group_score(
        self,
        member_skill_ids: List[str],
        mandatory_alternatives: Dict[str, List[str]],
        profile_text: str = ""
    ) -> Dict[str, Any]:
        """TASK-04+: Mandatory Skill Grouping Logic with Profile Text Check."""
        if not mandatory_alternatives:
            return {"score": 1.0, "matched": [], "missing": []}
            
        member_skills = set(member_skill_ids)
        p_text_lower = (profile_text or "").lower()
        matched = []
        missing = []
        
        for canonical, alt_ids in mandatory_alternatives.items():
            # 1. Check in normalized skill IDs
            if any(sid in member_skills for sid in alt_ids):
                matched.append(canonical)
                continue
            
            # 2. Check in profile text for canonical name ONLY (Strict for mandatory)
            import re
            
            found_in_text = False
            # Search only for the specific canonical name in the text
            escaped_mem = re.escape(canonical.lower())
            # prevent substring matches (e.g. 'git' in 'digital', 'scala' in 'scalable')
            pattern = r'(?<![a-z0-9_])' + escaped_mem + r'(?![a-z0-9_])'
            if re.search(pattern, p_text_lower):
                found_in_text = True
                    
            if found_in_text:
                matched.append(canonical)
            else:
                missing.append(canonical)
                
        total_groups = len(mandatory_alternatives)
        score = len(matched) / total_groups if total_groups > 0 else 1.0
        return {"score": score, "matched": matched, "missing": missing}

    def _calculate_context_boost(self, profile_data: Dict[str, Any]) -> float:
        """Normalized 0-1 score for context factors (Exp, Cert, Loc, Mode, Title)."""
        
        exp_score = self._calculate_experience_score(
            profile_data.get("experience_months", 0),
            profile_data.get("min_experience_months"),
            profile_data.get("max_experience_months")
        )
        cert_res = self._calculate_certification_score(
            profile_data.get("certifications", []),
            profile_data.get("required_certifications", [])
        )
        loc_score = self._calculate_location_score(
            profile_data.get("location"),
            profile_data.get("required_locations", [])
        )
        mode_score = self._calculate_work_mode_score(
            profile_data.get("work_mode"),
            profile_data.get("required_work_modes", [])
        )
        
        # Title Match (Production Rule: 0.05 weight)
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
        
        # Context Factors (Using individual weights from settings)
        raw_context_sum = (
            exp_score * settings.weight_experience + 
            cert_res["score"] * settings.weight_certification + 
            loc_score * settings.weight_location + 
            mode_score * settings.weight_work_mode + 
            title_score * settings.weight_jd_text
        )
        
        # Normalize to 0-1 for the context group (total weight of context components)
        total_context_weight = (
            settings.weight_experience + 
            settings.weight_certification + 
            settings.weight_location + 
            settings.weight_work_mode + 
            settings.weight_jd_text
        )
        return raw_context_sum / total_context_weight if total_context_weight > 0 else 0.0

    def _get_skill_family_penalty(self, member_skill_names: List[str], jd_text: str) -> float:
        """
        Calculates penalty for family mismatch (e.g. Frontend for Backend/AI role).
        """
        jd_lower = jd_text.lower()
        backend_ai_indicators = [k.strip() for k in settings.backend_ai_indicators.split(",")]
        is_backend_ai = any(kw in jd_lower for kw in backend_ai_indicators)
        if not is_backend_ai:
            return 0.0

        all_matched = [s.lower() for s in member_skill_names]
        
        frontend_kws = [k.strip() for k in settings.frontend_keywords.split(",")]
        backend_kws = [k.strip() for k in settings.backend_keywords.split(",")]
        
        f_count = sum(1 for s in all_matched if any(kw in s for kw in frontend_kws))
        b_count = sum(1 for s in all_matched if any(kw in s for kw in backend_kws))
        
        if f_count > b_count and f_count > 1:
            return settings.skill_family_penalty
        return 0.0

    def _calculate_skill_score(self, member_skill_ids, mandatory_ids, preferred_ids, alternatives=None, preferred_alternatives=None, profile_text=""):
        """Skill score for preferred skills with profile text fallback."""
        member_skills = set(member_skill_ids)
        matched_preferred = []
        missing_preferred = []
        if not preferred_ids:
            return {"preferred_score": 0.0, "matched_preferred": [], "missing_preferred": []}
            
        p_text_lower = (profile_text or "").lower()
        import re
        
        for pid in preferred_ids:
            alts = (preferred_alternatives or {}).get(pid, [pid])
            # 1. Check direct skill IDs
            if any(aid in member_skills for aid in alts):
                matched_preferred.append(pid)
                continue
                
            # 2. Fallback to profile text using the canonical name and its skill group
            # For preferred skills, we search group members BUT exclude the broad group name
            # to avoid matching 'FastAPI' just because 'Python' was mentioned.
            group_name = self._get_skill_group(pid)
            all_members = self.skill_groups.get(group_name, [pid])
            
            # Filter out the generic group name if the skill itself is not that group
            members = [m for m in all_members if m != group_name or pid.lower() == group_name]
            
            found_in_text = False
            for mem in members:
                # Protect against very short strings being matched broadly
                if len(mem) <= 2 and mem.lower() not in ["s3", "c#", "f#", "r", "go", "ui", "ux"]:
                    continue
                escaped_mem = re.escape(mem.lower())
                pattern = r'(?<![a-z0-9_])' + escaped_mem + r'(?![a-z0-9_])'
                if re.search(pattern, p_text_lower):
                    found_in_text = True
                    break
            
            if found_in_text:
                matched_preferred.append(pid)
            else:
                missing_preferred.append(pid)
        
        score = len(matched_preferred) / len(preferred_ids) if preferred_ids else 0.0
        return {"preferred_score": score, "matched_preferred": matched_preferred, "missing_preferred": missing_preferred}

    def _calculate_experience_score(self, member_exp, min_exp, max_exp):
        if not min_exp: return 1.0
        if member_exp >= min_exp: return 1.0
        return member_exp / min_exp if min_exp > 0 else 1.0

    def _calculate_certification_score(self, member_certs, required_certs):
        if not required_certs: return {"score": 1.0, "matched": [], "missing": []}
        matched = [c for c in required_certs if c in member_certs]
        missing = [c for c in required_certs if c not in member_certs]
        score = len(matched) / len(required_certs)
        return {"score": score, "matched": matched, "missing": missing}

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
        
        # --- PHASE 0: Configuration ---
        role_cfg = self._get_role_config(experience_months, jd_level)
        gates = role_cfg["gates"]
        role_weights = role_cfg["weights"]
        role_type = role_cfg["level"]
        
        # --- STAGE 1: Preliminary Qualification Check ---
        
        # 1. Mandatory Skills Match (Group-based + Profile Text check)
        mandatory_alternatives = profile_data.get("mandatory_alternatives") or {}
        m_res = self._calculate_mandatory_group_score(
            profile_data.get("skill_ids", []),
            mandatory_alternatives,
            profile_text
        )
        m_match_ratio = m_res["score"]
        
        # 2. Preferred Skills (Primary Skills Match)
        p_res = self._calculate_skill_score(
            profile_data.get("skill_ids", []),
            [], 
            profile_data.get("preferred_skill_ids", []),
            None,
            profile_data.get("preferred_alternatives"),
            profile_text=profile_text
        )
        p_score = p_res["preferred_score"]
        
        # 3. Weighted Skill Score for Gate (Use role-specific Weights)
        weighted_skill_sum = (m_match_ratio * role_weights["mandatory"]) + (p_score * role_weights["preferred"])
        
        # 4. Semantic Match (from RAG search)
        s_score = rag_candidate.jd_level_similarity
        
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
        c_raw = self._calculate_context_boost(profile_data)
        
        # Apply Role-Specific Context Weight and CAP at 8%
        context_contribution = c_raw * role_weights["context"]
        context_contribution = min(context_contribution, settings.context_boost_cap)
        
        # Skill Family Penalty
        penalty = self._get_skill_family_penalty(profile_data.get("skill_names", []), jd_text)
        
        # Final Score Calculation
        match_score = (
            (m_match_ratio * role_weights["mandatory"]) +
            (p_score * role_weights["preferred"]) +
            (s_score * role_weights["semantic"]) +
            context_contribution +
            penalty
        )
        
        match_score = round(max(0.0, min(1.0, match_score)), 4)
        
        # Prepare breakdown
        score_breakdown = {
            "mandatory_skills_group": m_match_ratio,
            "preferred_skills": p_score,
            "semantic_similarity": s_score,
            "context_score": c_raw,
            "context_contribution": context_contribution,
            "weight_m": role_weights["mandatory"],
            "weight_p": role_weights["preferred"],
            "weight_s": role_weights["semantic"],
            "weight_c": role_weights["context"],
            "penalties": penalty,
            "is_qualified": is_qualified,
            "role_type": role_type
        }

        # Fetch individual context scores for breakdown
        exp_score = self._calculate_experience_score(
            experience_months,
            profile_data.get("min_experience_months"),
            profile_data.get("max_experience_months")
        )
        cert_res = self._calculate_certification_score(
            profile_data.get("certifications", []),
            profile_data.get("required_certifications", [])
        )
        loc_score = self._calculate_location_score(
            profile_data.get("location"),
            profile_data.get("required_locations", [])
        )
        mode_score = self._calculate_work_mode_score(
            profile_data.get("work_mode"),
            profile_data.get("required_work_modes", [])
        )

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
            experience_score=round(exp_score, 2),
            experience_matched=(exp_score >= 1.0),
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
