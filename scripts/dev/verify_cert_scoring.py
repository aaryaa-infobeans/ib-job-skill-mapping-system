import sys
import os
import json
from datetime import datetime

# Add src to python path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from app.db.session import SessionLocal
from app.ai.agents.matching_scoring import matching_scoring_node
from app.ai.agents.explanation_generation import explanation_generation_node
from app.ai.state import GraphState

def verify_scoring():
    # Mock state
    state: GraphState = {
        "requisition_input": {
            "request_id": "TEST-REQ-123",
            "correlation_id": "CORR-TEST-123",
            "job_description": {
                "title": "AI Engineer",
                "jd_text": "We need an AI Engineer with AWS ML certification."
            }
        },
        "parsed_jd": {
            "normalized_title": "AI Engineer",
            "normalized_role": "AI Engineer",
            "extracted_mandatory_skills": ["python", "aws"],
            "extracted_preferred_skills": [],
            "experience": {"min_months": 24, "max_months": None},
            "certifications_required": ["AWS ML"],
            "jd_text": "We need an AI Engineer with AWS ML certification."
        },
        "normalized_skills": {
            "mandatory_skill_ids": ["python", "aws"],
            "preferred_skill_ids": []
        }
    }
    
    # Run matching_scoring_node
    print("Running matching_scoring_node...")
    state = matching_scoring_node(state)
    
    if "error_message" in state:
        print(f"Error in matching_scoring_node: {state['error_message']}")
        return

    scores = state.get("candidate_scores", [])
    print(f"Scored {len(scores)} candidates.")
    
    # Find a candidate with the certification (EMP_3425 was seeded with AWS ML)
    test_candidate = next((c for c in scores if c["team_member_id"] == "EMP_3425"), None)
    
    if test_candidate:
        print("\nVerification for EMP_3425 (should have AWS ML):")
        print(f"Final Score: {test_candidate['final_score']}")
        print(f"Certification Score: {test_candidate['certification_score']}")
        print(f"Certifications Found: {test_candidate['certifications']}")
        print(f"Match Reasons: {json.dumps(test_candidate['match_reasons'], indent=2)}")
        
        # Run explanation_generation_node
        print("\nRunning explanation_generation_node...")
        # Disable LLM for template verification
        os.environ["OPENAI_API_KEY"] = "" 
        state = explanation_generation_node(state)
        
        final_candidate = next((c for c in state["candidate_scores"] if c["team_member_id"] == "EMP_3425"), None)
        if final_candidate and "detailed_explanation" in final_candidate:
            print("\nTemplate Explanation Fit Analysis:")
            print(final_candidate["detailed_explanation"].get("fit_analysis"))
    else:
        print("\nEMP_3425 not found in scores.")

if __name__ == "__main__":
    verify_scoring()
