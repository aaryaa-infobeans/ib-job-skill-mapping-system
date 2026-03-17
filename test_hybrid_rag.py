
import os
import sys
import numpy as np
import logging
from dotenv import load_dotenv

# Add src to sys.path
sys.path.append(os.path.join(os.getcwd(), "src"))

# Load env but force a low threshold for testing
load_dotenv()
os.environ["RAG_SIMILARITY_THRESHOLD"] = "0.0" 
os.environ["EMBEDDING_MODEL"] = "google/embeddinggemma-300m"

from app.db.session import SessionLocal
from app.ai.utils.embedding import EmbeddingAgent
from app.ai.utils.rag_retrieval import RAGRetrievalAgent
from app.ai.utils.models import NormalizedRequisition, RequisitionData

def test_hybrid_search(query_text, skills):
    print(f"\n{'='*60}")
    print(f"HYBRID SEARCH TEST")
    print(f"Query: {query_text}")
    print(f"Skills: {skills}")
    print(f"{'='*60}")

    db = SessionLocal()
    try:
        # Direct check
        from app.db.models.models import TeamMember, TeamMemberEmbedding
        count = db.query(TeamMember).join(TeamMemberEmbedding).filter(TeamMember.is_active == True).count()
        print(f"DEBUG: Found {count} active members with embeddings in DB before RAG search")

        # 1. Generate Embeddings (Gemma)
        emb_agent = EmbeddingAgent()
        print(f"Using Embedding Model: {emb_agent.model_name} (Type: {emb_agent.model_type})")
        
        # Mock a normalized requisition
        req_data = RequisitionData(
            structured_intent=query_text,
            mandatory_skills=skills,
            preferred_skills=[],
            experience_requirements="5 years",
            jd_level="Senior",
            location="Remote"
        )
        
        norm_req = NormalizedRequisition(
            original_mandatory_skills=skills,
            normalized_mandatory_skills=skills,
            expanded_mandatory_terms=skills,
            original_preferred_skills=[],
            normalized_preferred_skills=[],
            expanded_preferred_terms=[],
            original_requisition=req_data
        )
        
        emb_result = emb_agent.execute(norm_req)
        print(f"Embeddings generated.")

        # 2. Perform Hybrid Retrieval
        print("[2/3] Running 70/30 Hybrid Search (BM25 + Vector)...")
        rag_agent = RAGRetrievalAgent(db_connection=db)
        
        candidates = rag_agent.execute(
            embedding_result=emb_result,
            query_text=query_text,
            mandatory_ids=[], 
            preferred_ids=[]
        )
        
        # 3. Display Results
        print(f"[3/3] Found {len(candidates)} candidates\n")
        
        for i, cand in enumerate(candidates[:10]): # Show top 10
            score = cand.final_similarity
            breakdown = cand.phase0_score_breakdown
            print(f"{i+1}. Candidate ID: {cand.team_member_id}")
            print(f"   Final Score: {score:.4f}")
            if breakdown:
                print(f"   BM25 Component: {breakdown.get('bm25_component', 0.0):.4f} (Raw Norm: {breakdown.get('raw_bm25_norm', 0.0):.4f})")
                print(f"   Vector Component: {breakdown.get('vector_component', 0.0):.4f} (Raw Sim: {breakdown.get('raw_vector_sim', 0.0):.4f})")
            print("-" * 30)

        if not candidates:
            print("No candidates found matching the criteria.")

    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    # Test cases
    test_queries = [
        ("Senior Python Developer", ["Python", "FastAPI", "PostgreSQL"]),
        ("AI Lead", ["AI", "Generative AI", "RAG"]),
    ]
    
    for q_text, q_skills in test_queries:
        test_hybrid_search(q_text, q_skills)
