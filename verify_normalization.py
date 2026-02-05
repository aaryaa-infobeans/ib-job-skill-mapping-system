import sys
import os
import json
from dotenv import load_dotenv
load_dotenv()

# Add src to path
sys.path.insert(0, "src")

from app.db.session import SessionLocal
from app.ai.agents.skill_normalization import skill_normalization_node

def test_normalization():
    print("Testing Skill Normalization with Ontology...")
    state = {
        "parsed_jd": {
            "extracted_mandatory_skills": ["Python", "js", "postgres"],
            "extracted_preferred_skills": ["Docker", "k8s"]
        },
        "llm_call_logs": [],
        "cumulative_tokens": 0,
        "cumulative_cost_usd": 0.0
    }
    
    try:
        final_state = skill_normalization_node(state)
        
        print("\nNormalized Skills Result:")
        print(json.dumps(final_state.get("normalized_skills"), indent=2))
        
        print("\nLLM Logs:")
        print(json.dumps(final_state.get("llm_call_logs"), indent=2))
        
        print(f"\nCumulative Tokens: {final_state.get('cumulative_tokens')}")
        print(f"Cumulative Cost: ${final_state.get('cumulative_cost_usd'):.6f}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_normalization()
