"""Scoring Audit Utility — formatted logging for candidate scoring walkthroughs."""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ScoringAudit:
    """Generate formatted audit logs for candidate scoring walkthroughs."""

    @staticmethod
    def log_candidate_walkthrough(candidate_data: Dict[str, Any]) -> None:
        """Log a math walkthrough for a candidate."""

        member_id   = candidate_data.get("team_member_id", "Unknown")
        final_score = candidate_data.get("final_score", 0.0)
        threshold   = candidate_data.get("role_fit_threshold", 0.5)
        status      = "QUALIFIED" if candidate_data.get("meets_threshold") else "DISQUALIFIED"
        reason      = candidate_data.get("reason", "N/A")

        walkthrough = [
            f"\n[{status}] Candidate: {member_id}",
            f"Final Score: {final_score:.4f}  (threshold: {threshold})",
            f"   Reason: {reason}",
        ]

        # Phase 0 — RAG search signals
        phase0 = candidate_data.get("phase0_ledger", {})
        walkthrough += [
            "\n PHASE 0: RAG SEARCH",
            f"   Hybrid Score:       {phase0.get('hybrid_score', 0.0):.4f}",
            f"   Vector Similarity:  {phase0.get('vector_similarity', 0.0):.4f}",
            f"   Skill Boost:        {phase0.get('skill_boost', 0.0):.4f}",
        ]

        bd = candidate_data.get("score_breakdown", {})
        logger.info("\n".join(walkthrough + ScoringAudit._score_lines(bd, candidate_data)))

    @staticmethod
    def _score_lines(bd: Dict, candidate_data: Dict) -> list:
        return [
            "\n SCORING: ADDITIVE COMPONENTS",
            f"   Mandatory Skills:   {bd.get('mandatory_skills_group', 0.0):.1%}"
            f" -> +{bd.get('mandatory_skills_group', 0.0) * candidate_data.get('weight_m', 0.5):.4f}",
            f"   Preferred Skills:   {bd.get('preferred_skills', 0.0):.1%}"
            f" -> +{bd.get('preferred_skills', 0.0) * candidate_data.get('weight_p', 0.2):.4f}",
            f"   Semantic:           {bd.get('semantic_similarity', 0.0):.4f}"
            f" -> +{bd.get('semantic_similarity', 0.0) * candidate_data.get('weight_s', 0.25):.4f}",
            f"   Context Boost:      +{bd.get('context_contribution', 0.0):.4f}",
            f"   Availability:       +{bd.get('availability_score', 0.0) * candidate_data.get('weight_a', 0.05):.4f}",
            f"   Skill Family Pen:   {bd.get('penalties', 0.0):.4f}",
            f"   AI Boost:           +{candidate_data.get('ai_boost', 0.0):.4f}",
            f"   FINAL:              {candidate_data.get('final_score', 0.0):.4f}",
            "------------------------------",
        ]
