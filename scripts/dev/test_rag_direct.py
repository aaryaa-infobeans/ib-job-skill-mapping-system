import sys
import os
import numpy as np
import logging

# Add src to python path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from app.db.session import SessionLocal
from app.ai.utils.rag_retrieval import RAGRetrievalAgent
from app.ai.utils.models import EmbeddingResult

logging.basicConfig(level=logging.INFO)

def test_rag_direct():
    db = SessionLocal()
    agent = RAGRetrievalAgent(db_connection=db)
    
    # Create dummy vectors (random)
    vec = np.random.rand(3072)
    # Normalize to avoid extreme distances
    vec = vec / np.linalg.norm(vec)
    
    result = EmbeddingResult(
        mandatory_vector=vec,
        preferred_vector=vec,
        jd_level_vector=vec,
        certification_vector=vec
    )
    
    print("Querying candidates...")
    candidates = agent._query_candidates(result)
    print(f"Candidates found after filtering: {len(candidates)}")
    
    # Debug row count
    from app.db.models.models import TeamMemberEmbedding
    rows_count = db.query(TeamMemberEmbedding).count()
    print(f"Total embeddings in DB: {rows_count}")
    
    # Query without filtering
    from sqlalchemy import type_coerce
    from pgvector.sqlalchemy import Vector
    vec_list = vec.tolist()
    
    sample_row = db.query(
        TeamMemberEmbedding.team_member_id,
        (1 - type_coerce(TeamMemberEmbedding.embedding, Vector(3072)).cosine_distance(vec_list)).label('sim')
    ).limit(5).all()
    
    print("\nSample Raw Similarities:")
    for r in sample_row:
        print(f"  ID: {r.team_member_id}, Sim: {r.sim}")
    
    db.close()

if __name__ == "__main__":
    test_rag_direct()
