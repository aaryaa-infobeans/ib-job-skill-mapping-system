
import os
import sys
import numpy as np
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Add src to sys.path
sys.path.append(os.path.join(os.getcwd(), "src"))

load_dotenv()
os.environ["RAG_SIMILARITY_THRESHOLD"] = "0.1"

from app.db.session import SessionLocal
from app.ai.utils.embedding import EmbeddingAgent
from app.ai.utils.rag_retrieval import RAGRetrievalAgent
from app.ai.utils.models import NormalizedRequisition, RequisitionData
from app.settings import settings
print(f"DB URL: {settings.get_database_url()}")

def test_hybrid_search(query_text, skills):
    print(f"\n{'='*60}")
    print(f"HYBRID SEARCH TEST")
    print(f"Query: {query_text}")
    print(f"Skills: {skills}")
    print(f"{'='*60}")
    
    db = SessionLocal()
    try:
        # 1. Generate Embedding
        print("[1/3] Generating embeddings using Gemma...")
        agent_emb = EmbeddingAgent()
        
        # Prepare mock normalized requisition for embedding
        req_data = RequisitionData(
            structured_intent=query_text,
            mandatory_skills=skills,
            preferred_skills=[],
            experience_requirements="any",
            jd_level="any",
            location="any"
        )
        
        norm_req = NormalizedRequisition(
            original_mandatory_skills=skills,
            normalized_mandatory_skills=[], 
            expanded_mandatory_terms=[],
            original_preferred_skills=[],
            normalized_preferred_skills=[],
            expanded_preferred_terms=[],
            original_requisition=req_data
        )
        
        emb_result = agent_emb.execute(norm_req)
        print(f"Embeddings generated with model: {emb_result.model}")
        
        # 2. Run Hybrid Retrieval
        print("[2/3] Running 70/30 Hybrid Search (BM25 + Vector)...")
        rag_agent = RAGRetrievalAgent(db_connection=db)
        
        # We pass query_text directly for BM25
        candidates = rag_agent.execute(
            embedding_result=emb_result,
            query_text=query_text,
            mandatory_ids=[], # We use text search for this simple test
            preferred_ids=[]
        )
        
        # 3. Display Results
        print(f"[3/3] Found {len(candidates)} candidates above threshold\n")
        
        if not candidates:
            print("No candidates found matching the criteria.")
            return

        print(f"{'ID':<15} | {'Score':<10} | {'Vector':<10} | {'BM25':<10}")
        print("-" * 55)
        for c in candidates[:10]:
            breakdown = c.phase0_score_breakdown
            print(f"{c.team_member_id:<15} | {c.final_similarity:<10.4f} | "
                  f"{breakdown.get('raw_vector_sim', 0):<10.4f} | "
                  f"{breakdown.get('raw_bm25_norm', 0):<10.4f}")

    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    # Test cases
    test_queries = [
        ("Mumbai", ["AI"]),
        ("AI Lead", ["Generative AI", "RAG"]),
        ("Python Developer with AWS experience", ["Python", "AWS"]),
    ]
    
    for q_text, q_skills in test_queries:
        test_hybrid_search(q_text, q_skills)
