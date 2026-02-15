"""
Integration Test: Efficient Vector-First Scoring Pipeline

This test demonstrates the high-performance matching strategy:
1. Stage 1 (Vector Search): Narrow down thousands of candidates to the top matched subset (e.g., top 100) using pgvector.
2. Stage 2 (Detailed Scoring): Fetch full profile details and apply complex business logic only on the filtered subset.

Performance Benefit:
Fetching full profile data (joins, skill lists, etc.) for 10,000 candidates and scoring them in Python is slow. 
Performing a cosine similarity search on the database is extremely fast (milliseconds) and allows us to 
ignore 99% of irrelevant profiles immediately.
"""

import pytest
import numpy as np
from typing import List

from app.db.session import SessionLocal
from app.db.models.models import TeamMember, TeamMemberSkill, TeamMemberEmbedding, SkillCertification
from app.ai.utils.rag_retrieval import RAGRetrievalAgent
from app.ai.utils.scoring import ScoringAgent
from app.ai.utils.models import EmbeddingResult, RAGCandidate

def test_rag_first_scoring_flow():
    """
    Demonstrates the optimized RAG-first scoring flow.
    """
    db = SessionLocal()
    try:
        # ---------------------------------------------------------
        # PREPARATION: Mock Requisition vectors
        # ---------------------------------------------------------
        # In practice, these vectors come from your EmbeddingAgent (OpenAI API)
        # For this test, we fetch EMP_3444's embedding to use as our 'Target' requirement.
        print("\n[PREP] Fetching target vector for query...")
        target_member = db.query(TeamMemberEmbedding).filter_by(team_member_id="EMP_3444").first()
        if not target_member:
            pytest.skip("EMP_3444 not found in database, cannot run demonstration.")
            
        target_vector = np.array(target_member.embedding)
        
        # Create the EmbeddingResult that represents our JD requirements
        query_embedding = EmbeddingResult(
            jd_level_vector=target_vector,
            mandatory_vector=target_vector,
            preferred_vector=target_vector,
            certification_vector=target_vector,
            model="demo-test"
        )

        # ---------------------------------------------------------
        # STAGE 1: Vector Similarity Search (PERFORMANCE CRITICAL)
        # ---------------------------------------------------------
        # We use RAGRetrievalAgent to search the vector database.
        # This executes a SQL query using pgvector's <=> (cosine distance).
        # It handles thousands/millions of records at the database layer.
        print("[STAGE 1] Executing Vector Search via RAGRetrievalAgent...")
        rag_agent = RAGRetrievalAgent(db_connection=db)
        
        # This only returns candidate IDs and their similarity scores.
        # No bulky profile data (skills, experience text) is fetched yet.
        top_candidates: List[RAGCandidate] = rag_agent.execute(query_embedding)
        
        print(f"   => Found {len(top_candidates)} raw candidates matching similarity criteria.")
        assert len(top_candidates) > 0
        
        # ---------------------------------------------------------
        # STAGE 2: Detailed Scoring on Filtered Subset
        # ---------------------------------------------------------
        # Now we fetch full profile details ONLY for the IDs returned by Stage 1.
        # This 'Batch Fetch' is much more efficient than fetching all members in the DB.
        print("[STAGE 2] Fetching full profile details for filtered subset...")
        candidate_ids = [c.team_member_id for c in top_candidates]
        
        # Bulk query for members
        members = db.query(TeamMember).filter(TeamMember.team_member_id.in_(candidate_ids)).all()
        member_map = {m.team_member_id: m for m in members}
        
        # Requisition parameters (In real app, comes from parsed_jd)
        requisition_params = {
            "mandatory_skill_ids": ["python", "fastapi"],
            "preferred_skill_ids": ["docker"],
            "min_experience_months": 24,
            "required_certifications": [],
            "required_locations": ["Pune", "Remote"],
            "required_work_modes": ["Hybrid"]
        }

        scoring_agent = ScoringAgent()
        final_results = []

        print(f"[STAGE 2] Applying detailed ScoringAgent logic to top {len(members)} candidates...")
        for rag_c in top_candidates:
            member = member_map.get(rag_c.team_member_id)
            if not member:
                continue
                
            # Fetch skills for this specific member (Efficient since it's only a few candidates)
            skills = db.query(TeamMemberSkill).filter_by(team_member_id=member.team_member_id).all()
            skill_ids = [s.skill_id for s in skills]
            
            # Prepare data for ScoringAgent
            profile_data = {
                "skill_ids": skill_ids,
                "experience_months": member.experience_in_months or 0,
                "location": member.base_location,
                "work_mode": member.work_type.value if member.work_type else "WFO",
                "certifications": [], # Would fetch from DB in full app
                "is_available": member.is_active,
                **requisition_params
            }
            
            # This applies the 0.35/0.20/0.15 etc. weighted logic
            score_res = scoring_agent.execute(rag_c, profile_data)
            final_results.append(score_res)

        # ---------------------------------------------------------
        # VALIDATION
        # ---------------------------------------------------------
        # Sort results by match_score
        final_results.sort(key=lambda x: x.match_score, reverse=True)
        
        print(f"\n[DONE] Pipeline Complete. Top Candidate: {final_results[0].team_member_id}")
        print(f"      Match Score: {final_results[0].match_score}")
        print(f"      Base Similarity: {final_results[0].score_breakdown['semantic_similarity']}")
        
        assert final_results[0].match_score >= 0.0

    finally:
        db.close()

if __name__ == "__main__":
    # Allow running directly for manual verification
    test_rag_first_scoring_flow()
