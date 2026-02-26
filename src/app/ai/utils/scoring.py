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
    
    SKILL_GROUPS = {
        "python": ["python", "django", "flask", "fastapi", "pandas", "numpy", "scikit-learn", "pytorch", "tensorflow"],
        "javascript": ["javascript", "js", "typescript", "ts", "react", "node", "next.js", "angular", "vue"],
        "sql": ["sql", "postgresql", "mysql", "sql server", "snowflake", "oracle", "db2"],
        "big_data": ["spark", "pyspark", "hadoop", "kafka", "databricks"],
        "ai_ml": ["machine learning", "ai", "ml", "nlp", "llm", "genai", "deep learning", "computer vision"],
        "cloud": ["aws", "azure", "gcp", "docker", "kubernetes", "terrafom"]
    }

    ROLE_CONFIGS = {
        "SENIOR": {
            "level": "SENIOR",
            "weights": {"m_skill": 0.50, "p_skill": 0.20, "semantic": 0.25, "context": 0.05},
            "gates": {"min_m_skill": 0.60, "min_semantic": 0.10},
            "fit_threshold": 0.60
        },
        "MID": {
            "level": "MID",
            "weights": {"m_skill": 0.40, "p_skill": 0.20, "semantic": 0.25, "context": 0.15},
            "gates": {"min_m_skill": 0.40, "min_semantic": 0.0},
            "fit_threshold": 0.50
        },
        "JUNIOR": {
            "level": "JUNIOR",
            "weights": {"m_skill": 0.30, "p_skill": 0.30, "semantic": 0.25, "context": 0.15},
            "gates": {"min_m_skill": 0.25, "min_semantic": 0.0},
            "fit_threshold": 0.50
        }
    }



    def _get_role_config(self, experience_months: int, jd_level: str = "") -> Dict[str, Any]:
        """Determine role config based on experience or JD level."""
        level = (jd_level or "").upper()
        if "SENIOR" in level or "SR" in level or experience_months >= 96: # 8 years
            role = "SENIOR"
        elif "JUNIOR" in level or "JR" in level or experience_months < 24: # 2 years
            role = "JUNIOR"
        else:
            role = "MID"
            
        return self.ROLE_CONFIGS[role]

    def _get_skill_group(self, skill: str) -> str:
        s_lower = skill.lower()
        for group, members in self.SKILL_GROUPS.items():
            if any(mem in s_lower for mem in members) or group in s_lower:
                return group
        return s_lower


    def _calculate_mandatory_group_score(
        self,
        member_skill_ids: List[str],
        mandatory_alternatives: Dict[str, List[str]],
        profile_text: str = ""
    ) -> float:
        """TASK-04+: Mandatory Skill Grouping Logic with Profile Text Check."""
        if not mandatory_alternatives:
            return 1.0
            
        member_skills = set(member_skill_ids)
        p_text_lower = profile_text.lower()
        satisfied_groups = 0
        total_groups = len(mandatory_alternatives)
        
        for canonical, alt_ids in mandatory_alternatives.items():
            # 1. Check in normalized skill IDs
            if any(sid in member_skills for sid in alt_ids):
                satisfied_groups += 1
                continue
            
            # 2. Check in profile text for group members or canonical name
            # This handles cases where normalization might have missed a mention
            group_name = self._get_skill_group(canonical)
            members = self.SKILL_GROUPS.get(group_name, [canonical])
            if any(mem.lower() in p_text_lower for mem in members):
                satisfied_groups += 1
                
        return satisfied_groups / total_groups if total_groups > 0 else 1.0

    def _get_skill_family_penalty(self, member_skill_ids: List[str], jd_text: str) -> float:
        """
        Calculates penalty for family mismatch (e.g. Frontend for Backend/AI role).
        """
        jd_lower = jd_text.lower()
        is_backend_ai = any(kw in jd_lower for kw in ["backend", "ai", "ml", "data", "python", "spark", "sql", "snowflake"])
        if not is_backend_ai:
            return 0.0

        # Simple keyword check for member skills (using group logic)
        frontend_count = 0
        backend_count = 0
        
        frontend_groups = ["javascript"]
        backend_groups = ["python", "sql", "big_data", "ai_ml"]
        
        for sid in member_skill_ids:
            # We don't have the skill name here, only ID. 
            # In the external project they had the name.
            # I might need to fetch names or rely on a different heuristic if names aren't available.
            # For now, I'll keep the skeleton and check if I can get names in matching_scoring_node.
            pass
            
        # If frontend > backend, apply -0.1 penalty
        return 0.0 # Placeholder until names are available


    def _calculate_context_boost(self, profile_data: Dict[str, Any]) -> float:
        """TASK-06+: Context Support Boost with Capping (Production Rule 8%)."""
        
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
        
        # Raw contributions using component weights
        c_exp = exp_score * settings.weight_experience
        c_cert = cert_res["score"] * settings.weight_certification
        c_loc = loc_score * settings.weight_location
        c_mode = mode_score * settings.weight_work_mode
        
        raw_total = c_exp + c_cert + c_loc + c_mode
        
        # Hard Cap at 8% (0.08)
        # If total exceeds 0.08, normalize down while keeping relative contribution
        if raw_total > 0.08:
            ratio = 0.08 / raw_total
            return 0.08 
        
        return raw_total

    def _get_skill_family_penalty(self, member_skill_names: List[str], jd_text: str) -> float:
        """
        Calculates penalty for family mismatch (e.g. Frontend for Backend/AI role).
        """
        jd_lower = jd_text.lower()
        is_backend_ai = any(kw in jd_lower for kw in ["backend", "ai", "ml", "data", "python", "spark", "sql", "snowflake"])
        if not is_backend_ai:
            return 0.0

        all_matched = [s.lower() for s in member_skill_names]
        
        frontend_kws = ["react", "angular", "vue", "html", "css", "javascript", "js", "frontend", "ui", "ux"]
        backend_kws = ["python", "java", "scala", "sql", "node", "backend", "api", "spark", "snowflake", "kafka", "ai", "ml"]
        
        f_count = sum(1 for s in all_matched if any(kw in s for kw in frontend_kws))
        b_count = sum(1 for s in all_matched if any(kw in s for kw in backend_kws))
        
        if f_count > b_count and f_count > 1:
            return -0.1
        return 0.0



    def _calculate_skill_score(self, member_skill_ids, mandatory_ids, preferred_ids, alternatives=None, preferred_alternatives=None):
        """Simplified skill score for preferred skills (mandatory handled by grouping)."""
        member_skills = set(member_skill_ids)
        matched_preferred = []
        if not preferred_ids:
            return {"preferred_score": 1.0, "matched_preferred": []}
            
        for pid in preferred_ids:
            alts = (preferred_alternatives or {}).get(pid, [pid])
            if any(aid in member_skills for aid in alts):
                matched_preferred.append(pid)
        
        score = len(matched_preferred) / len(preferred_ids) if preferred_ids else 1.0
        return {"preferred_score": score, "matched_preferred": matched_preferred}

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
        if not required_locs: return 1.0
        if not member_loc: return 0.0
        member_loc_lower = member_loc.lower()
        required_locs_lower = [l.lower() for l in required_locs]
        return 1.0 if member_loc_lower in required_locs_lower else 0.0

    def _calculate_work_mode_score(self, member_mode, required_modes):
        if not required_modes: return 1.0
        if not member_mode: return 0.5
        member_mode_lower = member_mode.lower()
        required_modes_lower = [m.lower() for m in required_modes]
        return 1.0 if member_mode_lower in required_modes_lower else 0.5 # Partial credit for mismatch

    @property
    def weights(self) -> Dict[str, float]:
        """Dynamic weights from settings."""
        return {
            "MANDATORY": settings.weight_mandatory_skills,
            "PREFERRED": settings.weight_preferred_skills,
            "SEMANTIC": settings.weight_semantic_fit,
            "CONTEXT": settings.weight_context_boost
        }



    def execute(self, rag_candidate: RAGCandidate, profile_data: Optional[Dict] = None) -> ScoringResult:
        """
        Refined Multi-Stage Scoring Logic from External Project:
        1. Role-specific configuration (Weights/Gates)
        2. Stage 1: Qualification Check (Hard Gates with AI Overrides for Seniors)
        3. Stage 2: Weighted Scoring with context capping and skill family penalties
        """
        profile_data = profile_data or {}
        experience_months = profile_data.get("experience_months", 0)
        jd_level = profile_data.get("jd_level", "MID")
        profile_text = profile_data.get("profile_text", "")
        jd_text = profile_data.get("jd_text", "")
        
        # --- PHASE 0: Configuration ---
        role_cfg = self._get_role_config(experience_months, jd_level)
        weights = role_cfg["weights"]
        gates = role_cfg["gates"]
        role_type = role_cfg["level"]
        
        # --- STAGE 1: Qualification Check ---
        
        # 1. Mandatory Skills Match (Group-based + Profile Text check)
        mandatory_alternatives = profile_data.get("mandatory_alternatives") or {}
        m_match_ratio = self._calculate_mandatory_group_score(
            profile_data.get("skill_ids", []),
            mandatory_alternatives,
            profile_text
        )
        
        # 2. Semantic Match (from RAG search)
        s_score = rag_candidate.jd_level_similarity
        
        # Qualification Logic
        is_qualified = True
        qualification_reason = "Qualified"
        
        if m_match_ratio < gates["min_m_skill"]:
            is_qualified = False
            qualification_reason = f"Disqualified: Mandatory skill match ({m_match_ratio:.0%}) below {gates['min_m_skill']:.0%} threshold."
        elif s_score < gates["min_semantic"]:
            # AI Override Check for Seniors will happen in matching_scoring_node 
            # where AI confidence is available. For now, we set is_qualified=False 
            # and allow the node to override if confidence is high.
            is_qualified = False
            qualification_reason = f"Disqualified: Semantic similarity ({s_score:.2f}) below {gates['min_semantic']:.2f} threshold."
            
        # --- STAGE 2: Weighted Scoring ---
        
        # Calculate individual components
        # Preferred Skills
        p_res = self._calculate_skill_score(
            profile_data.get("skill_ids", []),
            [], 
            profile_data.get("preferred_skill_ids", []),
            None,
            profile_data.get("preferred_alternatives")
        )
        p_score = p_res["preferred_score"]
        
        # Context Factors (with 0.08 cap and normalization)
        c_raw = self._calculate_context_boost(profile_data)
        
        # Skill Family Penalty
        # Note: profile_data should contain 'skill_names' for best results
        penalty = self._get_skill_family_penalty(profile_data.get("skill_names", []), jd_text)
        
        # Final Score Calculation
        if is_qualified:
            # Full weighted contribution
            match_score = (
                (m_match_ratio * weights["m_skill"]) +
                (p_score * weights["p_skill"]) +
                (s_score * weights["semantic"]) +
                (c_raw * weights["context"]) +
                penalty
            )
        else:
            # Disqualified: Cap at 15% 
            raw_score = (
                (m_match_ratio * weights["m_skill"]) +
                (p_score * weights["p_skill"]) +
                (s_score * weights["semantic"])
            )
            match_score = min(0.15, raw_score)
            
        match_score = round(max(0.0, min(1.0, match_score)), 4)
        
        # Prepare breakdown
        score_breakdown = {
            "mandatory_skills_group": m_match_ratio,
            "preferred_skills": p_score,
            "semantic_similarity": s_score,
            "context_score": c_raw,
            "weight_m": weights["m_skill"],
            "weight_p": weights["p_skill"],
            "weight_s": weights["semantic"],
            "weight_c": weights["context"],
            "penalty": penalty,
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
            skills_matched=p_res["matched_preferred"],
            mandatory_matched=[], # Handled by grouping
            preferred_matched=p_res["matched_preferred"],
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
