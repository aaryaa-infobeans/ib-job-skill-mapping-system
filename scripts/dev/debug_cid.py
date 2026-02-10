import sys
import os
import json
from sqlalchemy import text

# Add src to python path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from app.db.session import SessionLocal

def debug_correlation(correlation_id):
    db = SessionLocal()
    try:
        # Check requisition_requests to get request_id
        print(f"--- Requisition Request for {correlation_id} ---")
        req = db.execute(
            text("SELECT * FROM requisition_requests WHERE correlation_id = :cid"),
            {"cid": correlation_id}
        ).fetchone()
        
        if not req:
            print("Not found in requisition_requests")
            return
            
        print(f"ID: {req.id}, Request ID: {req.request_id}, Status: {req.status}")
        request_id = req.request_id

        # Check langgraph_checkpoints
        print(f"\n--- Checkpoints for {request_id} ---")
        checkpoints = db.execute(
            text("SELECT node_name, CAST(state_json AS TEXT) FROM langgraph_checkpoints WHERE request_id = :rid ORDER BY created_at ASC"),
            {"rid": request_id}
        ).fetchall()
        
        for cp in checkpoints:
            node_name = cp[0]
            state = json.loads(cp[1])
            print(f"Node: {node_name}")
            
            if node_name == "requisition_parsing":
                parsed_jd = state.get("parsed_jd", {})
                print(f"  Certifications Required: {parsed_jd.get('certifications_required')}")
                print(f"  JD Text Preview: {parsed_jd.get('jd_text', '')[:200]}...")
            
            if node_name == "rag_retrieval":
                retrieved = state.get("retrieved_candidates", [])
                print(f"  Retrieved Candidates Count: {len(retrieved)}")
                if retrieved:
                    print(f"  First Candidate Sim: {retrieved[0].get('final_similarity')}")
            
            if node_name == "matching_scoring":
                scores = state.get("candidate_scores", [])
                print(f"  Scored Candidates Count: {len(scores)}")
                if scores:
                    top = scores[0]
                    print(f"  Top Candidate ID: {top.get('team_member_id')}")
                    print(f"  Final Score: {top.get('final_score')}")
                    print(f"  Location Match: {top.get('match_reasons', {}).get('location_matched')}")
                    print(f"  Work Mode Match: {top.get('match_reasons', {}).get('work_mode_matched')}")
                    print(f"  Semantic Sim: {top.get('match_reasons', {}).get('semantic_similarity')}")

    finally:
        db.close()

if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else "CORR-20260210064616-REQ-TEST"
    debug_correlation(cid)
