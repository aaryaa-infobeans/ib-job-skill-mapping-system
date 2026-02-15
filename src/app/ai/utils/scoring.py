"""Scoring Agent - Extended scoring with normalized skills and certifications."""

import logging
from typing import Any, Dict, List, Optional

from app.settings import settings
from app.ai.utils.base import BaseAgent
from app.ai.utils.models import RAGCandidate, ScoringResult, ScoringBreakdown


class ScoringAgent(BaseAgent):
    """Score candidates based on weighted components defined in settings."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        super().__init__("scoring", logger)
    
    def _calculate_skill_score(
        self,
        team_member_skill_ids: List[str],
        mandatory_skill_ids: List[str],
        preferred_skill_ids: List[str],
        mandatory_alternatives: Optional[Dict[str, List[str]]] = None,
        preferred_alternatives: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, Any]:
        """Calculate skill matching score with support for skill groups (alternatives)."""
        member_skills = set(team_member_skill_ids)
        
        # 1. Mandatory Skills Calculation
        matched_mandatory = []
        if mandatory_alternatives:
            # Group-based scoring
            total_mandatory = len(mandatory_alternatives)
            for canonical, alt_ids in mandatory_alternatives.items():
                # Check if ANY of the alternative IDs are in member skills
                if any(sid in member_skills for sid in alt_ids):
                    matched_mandatory.append(canonical)
            mandatory_score = len(matched_mandatory) / total_mandatory if total_mandatory > 0 else 1.0
        else:
            # Fallback to direct ID matching
            mandatory_skills = set(mandatory_skill_ids)
            matched_mandatory = list(member_skills & mandatory_skills)
            mandatory_score = len(matched_mandatory) / len(mandatory_skills) if mandatory_skills else 1.0

        # 2. Preferred Skills Calculation
        matched_preferred = []
        if preferred_alternatives:
            # Group-based scoring
            total_preferred = len(preferred_alternatives)
            for canonical, alt_ids in preferred_alternatives.items():
                if any(sid in member_skills for sid in alt_ids):
                    matched_preferred.append(canonical)
            preferred_score = len(matched_preferred) / total_preferred if total_preferred > 0 else 1.0
        else:
            # Fallback to direct ID matching
            preferred_skills = set(preferred_skill_ids)
            matched_preferred = list(member_skills & preferred_skills)
            preferred_score = len(matched_preferred) / len(preferred_skills) if preferred_skills else 1.0
        
        return {
            "mandatory_score": mandatory_score,
            "preferred_score": preferred_score,
            "matched_mandatory": matched_mandatory,
            "matched_preferred": matched_preferred,
        }

    def _calculate_experience_score(
        self,
        team_member_months: int,
        min_months: Optional[int],
        max_months: Optional[int],
    ) -> float:
        """Calculate experience matching score."""
        if min_months is None and max_months is None:
            return 1.0
        
        if min_months is not None and max_months is None:
            return 1.0 if team_member_months >= min_months else 0.0
        
        if min_months is None and max_months is not None:
            return 0.0
        
        if min_months is not None and max_months is not None:
            if team_member_months < min_months:
                return 0.0
            return 1.0 # Within range or above max
            
        return 0.0

    def _calculate_location_score(
        self,
        candidate_location: Optional[str],
        required_locations: List[str],
    ) -> float:
        """Calculate location matching score."""
        if not required_locations:
            return 1.0
            
        if not candidate_location:
            return 0.0
            
        required_lower = [loc.lower().strip() for loc in required_locations]
        candidate_lower = candidate_location.lower().strip()
        
        if "remote" in required_lower or "any" in required_lower:
            return 1.0
            
        if candidate_lower in required_lower:
            return 1.0
            
        for loc in required_lower:
            if loc in candidate_lower or candidate_lower in loc:
                return 1.0
                
        return 0.0

    def _calculate_certification_score(
        self,
        candidate_certs: List[str],
        required_certs: List[str],
    ) -> Dict[str, Any]:
        """Calculate certification matching score."""
        if not required_certs:
            return {"score": 1.0, "matched": [], "missing": []}
            
        if not candidate_certs:
            return {"score": 0.0, "matched": [], "missing": required_certs}
            
        matched = []
        missing = []
        candidate_certs_lower = [c.lower().strip() for c in candidate_certs]
        
        for req in required_certs:
            req_lower = req.lower().strip()
            is_matched = False
            for cand in candidate_certs_lower:
                if req_lower in cand or cand in req_lower:
                    matched.append(req)
                    is_matched = True
                    break
            if not is_matched:
                missing.append(req)
                
        score = len(matched) / len(required_certs)
        return {"score": score, "matched": matched, "missing": missing}

    def _calculate_work_mode_score(
        self,
        candidate_mode: Optional[str],
        required_modes: List[str],
    ) -> float:
        """Calculate work mode matching score."""
        if not required_modes:
            return 1.0
            
        if not candidate_mode:
            return 0.0
            
        mode_map = {
            "wfo": ["wfo", "office", "on-site", "onsite"],
            "wfh": ["wfh", "remote", "work from home"],
            "hybrid": ["hybrid", "flexible"]
        }
        
        required_lower = [m.lower().strip() for m in required_modes]
        candidate_val = candidate_mode.lower().strip()
        
        for req in required_lower:
            if candidate_val == req:
                return 1.0
            for canonical, aliases in mode_map.items():
                if (candidate_val == canonical or candidate_val in aliases) and \
                   (req == canonical or req in aliases):
                    return 1.0
        return 0.0

    def execute(self, rag_candidate: RAGCandidate, profile_data: Optional[Dict] = None) -> ScoringResult:
        """
        Score a candidate based on RAG similarities and profile data.
        """
        profile_data = profile_data or {}
        
        # 1. Skill Matching
        # 1. Skill Matching
        skill_res = self._calculate_skill_score(
            profile_data.get("skill_ids", []),
            profile_data.get("mandatory_skill_ids", []),
            profile_data.get("preferred_skill_ids", []),
            mandatory_alternatives=profile_data.get("mandatory_alternatives"),
            preferred_alternatives=profile_data.get("preferred_alternatives"),
        )
        
        # 2. Experience Matching
        experience_score = self._calculate_experience_score(
            profile_data.get("experience_months", 0),
            profile_data.get("min_experience_months"),
            profile_data.get("max_experience_months"),
        )
        
        # 3. Certification Matching
        cert_res = self._calculate_certification_score(
            profile_data.get("certifications", []),
            profile_data.get("required_certifications", []),
        )
        
        # 4. Location and Work Mode Matching
        location_score = self._calculate_location_score(
            profile_data.get("location"),
            profile_data.get("required_locations", []),
        )
        work_mode_score = self._calculate_work_mode_score(
            profile_data.get("work_mode"),
            profile_data.get("required_work_modes", []),
        )
        
        # 5. Semantic similarities (from RAG)
        semantic_score = rag_candidate.final_similarity
        jd_level_score = rag_candidate.jd_level_similarity
        
        # Calculate final weighted score
        match_score = (
            (settings.weight_mandatory_skills * skill_res["mandatory_score"]) +
            (settings.weight_preferred_skills * skill_res["preferred_score"]) +
            (settings.weight_experience * experience_score) +
            (settings.weight_certification * cert_res["score"]) +
            (settings.weight_location * location_score) +
            (settings.weight_work_mode * work_mode_score) +
            (settings.weight_semantic_similarity * semantic_score) +
            (settings.weight_jd_text * jd_level_score)
        )
        
        match_score = max(0.0, min(1.0, match_score))
        
        # Breakdown of components
        score_breakdown = {
            "mandatory_skills": skill_res["mandatory_score"],
            "preferred_skills": skill_res["preferred_score"],
            "experience": experience_score,
            "certification": cert_res["score"],
            "location": location_score,
            "work_mode": work_mode_score,
            "semantic_similarity": semantic_score,
            "jd_level": jd_level_score,
        }
        
        weighted_components = {
            k: v * getattr(settings, f"weight_{k if k != 'jd_level' else 'jd_text'}")
            for k, v in score_breakdown.items()
        }
        
        # Detailed Breakdown as requested
        detailed = ScoringBreakdown(
            skills_matched=skill_res["matched_mandatory"] + skill_res["matched_preferred"],
            mandatory_matched=skill_res["matched_mandatory"],
            preferred_matched=skill_res["matched_preferred"],
            mandatory_score=round(skill_res["mandatory_score"], 2),
            preferred_score=round(skill_res["preferred_score"], 2),
            certification_matched=cert_res["matched"],
            certification_missing=cert_res["missing"],
            certification_score=round(cert_res["score"], 2),
            location_matched=location_score > 0,
            location_score=round(location_score, 2),
            work_mode_matched=work_mode_score > 0,
            work_mode_score=round(work_mode_score, 2),
            experience_matched=experience_score > 0,
            experience_score=round(experience_score, 2),
            semantic_similarity=round(semantic_score, 2),
            jd_level_similarity=round(jd_level_score, 2),
        )
        
        return ScoringResult(
            team_member_id=rag_candidate.team_member_id,
            match_score=round(match_score, 2),
            confidence=0.9,  # TODO: Implement confidence logic
            score_breakdown=score_breakdown,
            weighted_components=weighted_components,
            detailed_breakdown=detailed,
            is_available=profile_data.get("is_available", True),
            available_capacity=profile_data.get("available_capacity", 100.0)
        )
    
    def validate_input(self, input_data: Any) -> bool:
        """Validate that input is RAGCandidate."""
        if not isinstance(input_data, RAGCandidate):
            self.logger.warning(f"Input must be RAGCandidate, got {type(input_data)}")
            return False
        return True
    
    def format_output(self, result: ScoringResult) -> ScoringResult:
        """Format output - already in correct format."""
        return result
