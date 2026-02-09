"""Scoring Agent - Extended scoring with normalized skills and certifications."""

import logging
import os
from typing import Any, Dict, List, Optional
from app.ai.utils.base import BaseAgent
from app.ai.utils.models import RAGCandidate, ScoringResult


class ScoringAgent(BaseAgent):
    """Score candidates based on weighted components."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        super().__init__("scoring", logger)
        self._load_weights()
    
    def _load_weights(self):
        """Load scoring weights from environment."""
        self.weight_mandatory_skills = float(os.getenv("WEIGHT_MANDATORY_SKILLS", "0.35"))
        self.weight_preferred_skills = float(os.getenv("WEIGHT_PREFERRED_SKILLS", "0.20"))
        self.weight_experience = float(os.getenv("WEIGHT_EXPERIENCE", "0.15"))
        self.weight_semantic_similarity = float(os.getenv("WEIGHT_SEMANTIC_SIMILARITY", "0.10"))
        self.weight_certification = float(os.getenv("WEIGHT_CERTIFICATION", "0.10"))
        self.weight_jd_text = float(os.getenv("WEIGHT_JD_TEXT", "0.10"))
        
        # Validate weights sum to 1.0
        total = (
            self.weight_mandatory_skills +
            self.weight_preferred_skills +
            self.weight_experience +
            self.weight_semantic_similarity +
            self.weight_certification +
            self.weight_jd_text
        )
        
        if abs(total - 1.0) > 0.01:
            self.logger.warning(f"Weights sum to {total}, not 1.0. Normalizing.")
            # Normalize weights
            self.weight_mandatory_skills /= total
            self.weight_preferred_skills /= total
            self.weight_experience /= total
            self.weight_semantic_similarity /= total
            self.weight_certification /= total
            self.weight_jd_text /= total
    
    def execute(self, rag_candidate: RAGCandidate, profile_data: Optional[Dict] = None) -> ScoringResult:
        """
        Score a candidate based on RAG similarities and profile data.
        
        Args:
            rag_candidate: RAG retrieved candidate with similarity scores
            profile_data: Optional additional profile data for candidate
            
        Returns:
            ScoringResult with match_score and breakdown
        """
        profile_data = profile_data or {}
        
        # Extract components from RAG similarities
        mandatory_score = rag_candidate.mandatory_similarity
        preferred_score = rag_candidate.preferred_similarity
        jd_level_score = rag_candidate.jd_level_similarity
        certification_score = rag_candidate.certification_similarity
        
        # Experience score (from profile or normalized)
        experience_score = float(profile_data.get("experience_score", 0.5))
        
        # Semantic similarity
        semantic_score = rag_candidate.final_similarity
        
        # Compute weighted score
        match_score = (
            (self.weight_mandatory_skills * mandatory_score) +
            (self.weight_preferred_skills * preferred_score) +
            (self.weight_experience * experience_score) +
            (self.weight_semantic_similarity * semantic_score) +
            (self.weight_certification * certification_score) +
            (self.weight_jd_text * jd_level_score)
        )
        
        # Ensure score is between 0 and 1
        match_score = max(0.0, min(1.0, match_score))
        
        # Compute confidence (all scores should be closer to 1)
        confidence = 1.0
        if mandatory_score < 0.5:
            confidence -= 0.2
        if certification_score < 0.3:
            confidence -= 0.1
        confidence = max(0.0, confidence)
        
        score_breakdown = {
            "mandatory_skills": mandatory_score,
            "preferred_skills": preferred_score,
            "experience": experience_score,
            "semantic_similarity": semantic_score,
            "certification": certification_score,
            "jd_level": jd_level_score,
        }
        
        weighted_components = {
            "mandatory_skills": self.weight_mandatory_skills * mandatory_score,
            "preferred_skills": self.weight_preferred_skills * preferred_score,
            "experience": self.weight_experience * experience_score,
            "semantic_similarity": self.weight_semantic_similarity * semantic_score,
            "certification": self.weight_certification * certification_score,
            "jd_level": self.weight_jd_text * jd_level_score,
        }
        
        result = ScoringResult(
            team_member_id=rag_candidate.team_member_id,
            match_score=match_score,
            confidence=confidence,
            score_breakdown=score_breakdown,
            weighted_components=weighted_components
        )
        
        return result
    
    def validate_input(self, input_data: Any) -> bool:
        """Validate that input is RAGCandidate."""
        if not isinstance(input_data, RAGCandidate):
            self.logger.warning(f"Input must be RAGCandidate, got {type(input_data)}")
            return False
        return True
    
    def format_output(self, result: ScoringResult) -> ScoringResult:
        """Format output - already in correct format."""
        return result
