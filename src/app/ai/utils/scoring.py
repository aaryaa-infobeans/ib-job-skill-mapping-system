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
    
    ROLE_WEIGHTS = {
        "SENIOR": {"M": 0.50, "P": 0.20, "S": 0.25, "C": 0.05, "GATE": 0.60},
        "MID":    {"M": 0.40, "P": 0.20, "S": 0.25, "C": 0.15, "GATE": 0.50},
        "JUNIOR": {"M": 0.30, "P": 0.30, "S": 0.25, "C": 0.15, "GATE": 0.50}
    }

    def _get_role_category(self, experience_months: int, jd_level: str = "") -> str:
        """Determine role category based on experience or JD level."""
        level = (jd_level or "").upper()
        if "SENIOR" in level or "SR" in level or experience_months >= 96: # 8 years
            return "SENIOR"
        if "JUNIOR" in level or "JR" in level or experience_months < 24: # 2 years
            return "JUNIOR"
        return "MID"

    def _calculate_mandatory_group_score(
        self,
        member_skill_ids: List[str],
        mandatory_alternatives: Dict[str, List[str]]
    ) -> float:
        """TASK-04: Mandatory Skill Grouping Logic."""
        if not mandatory_alternatives:
            return 1.0
            
        member_skills = set(member_skill_ids)
        satisfied_groups = 0
        total_groups = len(mandatory_alternatives)
        
        for canonical, alt_ids in mandatory_alternatives.items():
            if any(sid in member_skills for sid in alt_ids):
                satisfied_groups += 1
                
        return satisfied_groups / total_groups if total_groups > 0 else 1.0

    def _calculate_context_boost(self, profile_data: Dict[str, Any]) -> float:
        """TASK-06: Context Support Boost (Hard Cap 0.08)."""
        # Components: Experience (5/15), Certifications (5/15), Location (3/15), Work Mode (2/15)
        
        # 1. Experience
        exp_score = self._calculate_experience_score(
            profile_data.get("experience_months", 0),
            profile_data.get("min_experience_months"),
            profile_data.get("max_experience_months")
        )
        # 2. Certifications
        cert_res = self._calculate_certification_score(
            profile_data.get("certifications", []),
            profile_data.get("required_certifications", [])
        )
        # 3. Location
        loc_score = self._calculate_location_score(
            profile_data.get("location"),
            profile_data.get("required_locations", [])
        )
        # 4. Work Mode
        mode_score = self._calculate_work_mode_score(
            profile_data.get("work_mode"),
            profile_data.get("required_work_modes", [])
        )
        
        raw_context = (
            (exp_score * 5/15) + 
            (cert_res["score"] * 5/15) + 
            (loc_score * 3/15) + 
            (mode_score * 2/15)
        )
        
        return raw_context # Return raw [0,1], clamping happens in execute

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

    def execute(self, rag_candidate: RAGCandidate, profile_data: Optional[Dict] = None) -> ScoringResult:
        """
        Phase 1: Agentic Scoring with Role-Aware weights.
        """
        profile_data = profile_data or {}
        experience_months = profile_data.get("experience_months", 0)
        jd_level = profile_data.get("jd_level", "MID")
        
        role_type = self._get_role_category(experience_months, jd_level)
        weights = self.ROLE_WEIGHTS[role_type]
        
        # 1. Mandatory Skill Grouping (M)
        m_score = self._calculate_mandatory_group_score(
            profile_data.get("skill_ids", []),
            profile_data.get("mandatory_alternatives") or {}
        )
        
        # 2. Preferred Skills (P) - Using group-based if alternatives available
        p_res = self._calculate_skill_score(
            profile_data.get("skill_ids", []),
            [], # mandatory_skill_ids (already handled by grouping)
            profile_data.get("preferred_skill_ids", []),
            None,
            profile_data.get("preferred_alternatives")
        )
        p_score = p_res["preferred_score"]
        
        # 3. Semantic Similarity (S)
        s_score = rag_candidate.jd_level_similarity
        
        # 4. Context Boost (C) helper calls for breakdown
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
        
        c_raw = (
            (exp_score * 5/15) + 
            (cert_res["score"] * 5/15) + 
            (loc_score * 3/15) + 
            (mode_score * 2/15)
        )
        c_contribution = min(c_raw * weights["C"], 0.08)
        
        # 5. Penalties (TASK-07)
        penalties = 0.0
        if m_score < 1.0:
            penalties += 0.10
            
        # Final Score calculation
        match_score = (
            (m_score * weights["M"]) +
            (p_score * weights["P"]) +
            (s_score * weights["S"]) +
            c_contribution -
            penalties
        )
        match_score = max(0.0, min(1.0, match_score))
        
        # Prepare breakdown
        score_breakdown = {
            "mandatory_skills_group": m_score,
            "preferred_skills": p_score,
            "semantic_similarity": s_score,
            "context_boost": c_contribution,
            "penalties": penalties,
            "role_type": role_type
        }
        
        detailed = ScoringBreakdown(
            skills_matched=p_res["matched_preferred"],
            mandatory_matched=[], 
            preferred_matched=p_res["matched_preferred"],
            mandatory_score=round(m_score, 2),
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
            jd_level_similarity=round(rag_candidate.jd_level_similarity, 2)
        )
        
        return ScoringResult(
            team_member_id=rag_candidate.team_member_id,
            match_score=round(match_score, 2),
            confidence=0.9,
            score_breakdown=score_breakdown,
            detailed_breakdown=detailed,
            is_available=profile_data.get("is_available", True),
            available_capacity=profile_data.get("available_capacity", 100.0)
        )
    
    def validate_input(self, input_data: Any) -> bool:
        return isinstance(input_data, RAGCandidate)
    
    def format_output(self, result: ScoringResult) -> ScoringResult:
        return result
