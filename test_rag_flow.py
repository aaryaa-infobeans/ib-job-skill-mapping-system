import sys
import os
import asyncio
import logging
from dotenv import load_dotenv

# Load env before app imports
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

# Add src to sys.path
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

from app.db.session import SessionLocal
from app.ai.graph import create_graph
from app.ai.state import GraphState

async def test_rag():
    graph = create_graph()
    
    # Mock JD input
    input_state: GraphState = {
        "requisition_input": {
            "request_id": "TEST_RAG_FLOW_003",
            "job_description": {
                "jd_text": "We are looking for a Salesforce Developer with 10 years of experience in Bangalore. Must have Apex, Visualforce and LWC skills. Copado certification is a plus.",
                "title": "Senior Salesforce Developer",
                "role": "Salesforce Developer",
                "mandatory_skills": ["Apex", "Visualforce", "LWC"],
                "preferred_skills": ["Copado"],
                "experience": {"min_months": 120, "max_months": None},
                "jd_level": "Senior"
            }
        },
        "token_metrics": {},
        "llm_call_logs": []
    }
    
    print("Executing graph...")
    result = await graph.ainvoke(input_state)
    
    print("\n--- State Check ---")
    if "embedding_result" in result and result["embedding_result"]:
        print("✅ embedding_result found in state")
    else:
        print("❌ embedding_result MISSING from state")
        
    print("\n--- RAG Results ---")
    retrieved = result.get("retrieved_candidates", [])
    print(f"Retrieved {len(retrieved)} candidates via RAG")
    for i, c in enumerate(retrieved[:5]):
        print(f"{i+1}. {c['team_member_id']} - Final Similarity: {c['final_similarity']:.4f}")
        
    print("\n--- Final Results (Scored) ---")
    candidate_scores = result.get("candidate_scores", [])
    print(f"Total scored: {len(candidate_scores)}")
    for i, c in enumerate(candidate_scores[:5]):
        print(f"{i+1}. {c['team_member_id']} - Score: {c['final_score']} (Skills: {c['skill_score']}, Exp: {c['experience_score']})")

if __name__ == "__main__":
    asyncio.run(test_rag())
