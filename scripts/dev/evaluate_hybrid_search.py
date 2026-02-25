"""Evaluation Script - Compare BM25-heavy vs Vector-heavy Ranking."""

import os
import sys
import numpy as np
from typing import List

# Setup path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from app.db.session import SessionLocal
from app.db.models.models import TeamMemberEmbedding, TeamMember
from app.ai.utils.rag_retrieval import RAGRetrievalAgent
from app.ai.utils.models import EmbeddingResult
from sqlalchemy import text

def run_evaluation():
    db = SessionLocal()
    try:
        # 1. Selection of a few test cases
        print("[SETUP] Inserting mock 768d evaluation data...")
        members = db.query(TeamMember).limit(5).all()
        if not members:
            print("No team members found in DB.")
            return

        mock_ids = []
        for m in members:
            # Create mock 768d embedding
            mock_vec = np.random.randn(768).astype(np.float32).tolist()
            # Insert into truncated table
            db.execute(
                text("INSERT INTO team_member_embeddings (team_member_id, embedding, profile_text) VALUES (:tid, :vec, :txt)"),
                {"tid": m.team_member_id, "vec": str(mock_vec), "txt": f"{m.designation} with skills in Python and Cloud Architecture"}
            )
            mock_ids.append(m.team_member_id)
        db.commit()

        # 2. Run Comparison
        for tid in mock_ids[:2]:
            print(f"\n--- EVALUATION CASE: {tid} ---")
            vector = np.random.randn(768).astype(np.float32)

            query_embedding = EmbeddingResult(
                jd_level_vector=vector,
                mandatory_vector=vector,
                preferred_vector=vector,
                certification_vector=vector,
                model="gemma-eval"
            )
            query_text = "Senior Software Engineer with Python expertise"

            # CASE A: BM25 Heavy
            os.environ["HYBRID_BM25_WEIGHT"] = "1.0"
            os.environ["HYBRID_VECTOR_WEIGHT"] = "0.0"
            agent_bm25_heavy = RAGRetrievalAgent(db_connection=db)
            results_bm25 = agent_bm25_heavy.execute(query_embedding, query_text=query_text)

            # CASE B: Vector Heavy
            os.environ["HYBRID_BM25_WEIGHT"] = "0.0"
            os.environ["HYBRID_VECTOR_WEIGHT"] = "1.0"
            agent_vector_heavy = RAGRetrievalAgent(db_connection=db)
            results_vector = agent_vector_heavy.execute(query_embedding, query_text=query_text)

            print(f"BM25-Only Top 5 IDs: {[r.team_member_id for r in results_bm25[:5]]}")
            print(f"Vector-Only Top 5 IDs: {[r.team_member_id for r in results_vector[:5]]}")
            
            # Calculate overlap
            set_bm25 = set(r.team_member_id for r in results_bm25[:10])
            set_vector = set(r.team_member_id for r in results_vector[:10])
            overlap = set_bm25.intersection(set_vector)
            print(f"Overlap in Top 10: {len(overlap)} candidates")

    finally:
        db.close()

if __name__ == "__main__":
    run_evaluation()
