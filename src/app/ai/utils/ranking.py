"""Ranking Agent - Filter, sort, and rank candidates with narratives."""

import logging
from typing import Any, List, Optional
from app.ai.utils.base import BaseAgent
from app.ai.utils.models import ScoringResult, RankedCandidate, RankedCandidateList
from app.settings import settings


class RankingAgent(BaseAgent):
    """Filter and rank candidates with justifications."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        super().__init__("ranking", logger)
        self.fit_score_threshold = settings.fit_score_threshold
    
    def execute(self, scored_candidates: List[ScoringResult]) -> RankedCandidateList:
        """
        Filter and rank candidates with narratives.
        
        Args:
            scored_candidates: List of ScoringResult from scoring agent
            
        Returns:
            RankedCandidateList with filtered and ranked candidates
        """
        # Filter by threshold
        qualified = [c for c in scored_candidates if c.match_score >= self.fit_score_threshold]
        
        # Sort by match_score descending
        qualified.sort(key=lambda c: c.match_score, reverse=True)
        
        # Create ranked candidates
        ranked_candidates = []
        for rank, candidate in enumerate(qualified, 1):
            narrative = self._generate_narrative(candidate)
            ranked_candidate = RankedCandidate(
                team_member_id=candidate.team_member_id,
                match_score=candidate.match_score,
                narrative_justification=narrative,
                rank_position=rank
            )
            ranked_candidates.append(ranked_candidate)
        
        result = RankedCandidateList(
            candidates=ranked_candidates,
            total_evaluated=len(scored_candidates),
            total_qualified=len(qualified)
        )
        
        self.logger.info(
            f"Ranking complete: {len(qualified)} qualified out of {len(scored_candidates)} candidates"
        )
        
        return result
    
    def _generate_narrative(self, candidate: ScoringResult) -> str:
        """Generate a professional narrative justification with hybrid search insights."""
        breakdown = candidate.score_breakdown
        strengths = []
        
        if breakdown.get("mandatory_skills", 0) > 0.8:
            strengths.append("strong alignment in mandatory skills")
        if breakdown.get("experience", 0) > 0.8:
            strengths.append("suitable experience level")
        if breakdown.get("semantic_similarity", 0) > 0.7:
            strengths.append("high semantic relevance")
            
        # Build narrative
        if not strengths:
            narrative = f"Candidate shows baseline fit with a match score of {candidate.match_score:.2%}."
        else:
            strengths_str = ", ".join(strengths)
            narrative = f"Strong match with {strengths_str}. "
            
            # Add hybrid search insight if available
            if candidate.score_breakdown.get("semantic_similarity", 0) > 0.6:
                narrative += "Retrieval confirmed via hybrid search (Vector + Keyword) for higher accuracy. "
                
            narrative += f"Final Match Score: {candidate.match_score:.2%}."
        
        return narrative
    
    def validate_input(self, input_data: Any) -> bool:
        """Validate that input is list of ScoringResult."""
        if not isinstance(input_data, list):
            self.logger.warning(f"Input must be list, got {type(input_data)}")
            return False
        
        if len(input_data) == 0:
            # Empty list is valid, will return empty ranking
            return True
        
        if not all(isinstance(c, ScoringResult) for c in input_data):
            self.logger.warning("All items in list must be ScoringResult")
            return False
        
        return True
    
    def format_output(self, result: RankedCandidateList) -> RankedCandidateList:
        """Format output - already in correct format."""
        return result
