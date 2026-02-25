"""Scoring Audit Utility - Formatted logging for candidate scoring walkthroughs."""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

class ScoringAudit:
    """Utility to generate formatted audit logs for candidate scoring."""
    
    @staticmethod
    def log_candidate_walkthrough(candidate_data: Dict[str, Any]):
        """Generate and log a detailed math walkthrough for a candidate."""
        
        member_id = candidate_data.get("team_member_id", "Unknown")
        final_score = candidate_data.get("final_score", 0.0)
        role_type = candidate_data.get("role_type", "MID")
        threshold = candidate_data.get("role_fit_threshold", 0.5)
        status = "QUALIFIED" if candidate_data.get("meets_threshold") else "DISQUALIFIED"
        reason = candidate_data.get("reason", "N/A")
        
        # 1. Header
        walkthrough = [
            f"\n[{status}] Candidate: {member_id} (ID: {member_id})",
            f"Final Score: {final_score:.4f} (Threshold: {threshold})",
            f"   Reason: {reason}"
        ]
        
        # 2. Phase 1: Search & Ranking (Algorithm Details)
        phase0 = candidate_data.get("phase0_ledger", {})
        walkthrough.extend([
            "\n🔍 PHASE 1: SEARCH & RANKING (Algorithm Details)",
            "🔹 MANDATORY_SKILLS (Phase 0):",
            f"   Skill Boost: {phase0.get('skill_boost', 0.0):.4f}",
            f"   Raw Match: {phase0.get('m_count', 0)} / {candidate_data.get('total_m', 0)}",
            "🔹 PREFERRED_SKILLS (Phase 0):",
            f"   Preferred Boost: {phase0.get('preferred_boost', 0.0):.4f}",
            "🔹 JD_TEXT (Vector):",
            f"   Vector Similarity: {phase0.get('vector_similarity', 0.0):.4f}",
            f"   Hybrid Score (P0): {phase0.get('hybrid_score', 0.0):.4f}"
        ])
        
        # 3. Phase 2: Scoring & Weighting (Math Walkthrough)
        breakdown = candidate_data.get("score_breakdown", {})
        walkthrough.extend([
            f"\n📈 PHASE 2: SCORING & WEIGHTING (Math Walkthrough)",
            f"   CANDIDATE: {member_id} (Role: {role_type}, Fit Threshold: {threshold})",
            "   ----------------------------------",
            "   PHASE 1: SKILLS",
            f"   Mandatory (Groups): {breakdown.get('mandatory_skills_group', 0.0):.1%} -> +{breakdown.get('mandatory_skills_group', 0.0) * candidate_data.get('weight_m', 0.5):.4f}",
            f"   Preferred: {breakdown.get('preferred_skills', 0.0):.1%} -> +{breakdown.get('preferred_skills', 0.0) * candidate_data.get('weight_p', 0.2):.4f}",
            "   PHASE 2: SEMANTIC FIT",
            f"   Vector Similarity: {breakdown.get('semantic_similarity', 0.0):.2f} -> +{breakdown.get('semantic_similarity', 0.0) * candidate_data.get('weight_s', 0.25):.4f}",
            "   PHASE 3: CONTEXT SUPPORT (Max 0.08)",
            f"   Total Context Boost: +{breakdown.get('context_boost', 0.0):.4f}",
            f"   AI FIT CONFIDENCE: {candidate_data.get('ai_confidence_score', 0.0):.1f} (Boost: +{candidate_data.get('ai_boost', 0.0):.4f})",
            f"   PENALTIES: -{breakdown.get('penalties', 0.0):.4f}",
            f"   FINAL HYBRID SCORE: {final_score:.4f}",
            f"   QUALIFICATION LOGIC: {'Standard' if not candidate_data.get('ai_override_applied') else 'AI Override'}",
            "------------------------------"
        ])
        
        logger.info("\n".join(walkthrough))
