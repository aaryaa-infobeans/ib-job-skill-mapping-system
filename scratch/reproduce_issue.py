
import logging
import sys
import os

# Add src to path
sys.path.append(os.path.abspath("src"))

# Mock settings before importing app components
os.environ["LOG_LEVEL"] = "INFO"
os.environ["SECRETS_BACKEND"] = "local"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.ai.utils.scoring import ScoringAgent

def test_matching():
    agent = ScoringAgent()
    member_skill_ids = [] # No normalized skills
    
    print("--- Mandatory Skills Tests ---")
    
    # Mandatory alternatives from JD: PostgreSQL
    mandatory_alternatives = {"PostgreSQL": ["skill_pg_id"]}
    
    # Negative Case: Profile text has "SQL" but not "PostgreSQL"
    result = agent._calculate_mandatory_group_score(
        member_skill_ids=member_skill_ids,
        mandatory_alternatives=mandatory_alternatives,
        profile_text="I have experience in SQL and Java."
    )
    print(f"Mandatory PostgreSQL with 'SQL' in text (Should be 0): {result['score']}")

    # Negative Case: Profile text has "Python" but not "FastAPI"
    mandatory_alternatives_2 = {"FastAPI": ["skill_fastapi_id"]}
    result_2 = agent._calculate_mandatory_group_score(
        member_skill_ids=member_skill_ids,
        mandatory_alternatives=mandatory_alternatives_2,
        profile_text="I am a Python developer."
    )
    print(f"Mandatory FastAPI with 'Python' in text (Should be 0): {result_2['score']}")

    # Positive Case: Profile text has "PostgreSQL"
    result_3 = agent._calculate_mandatory_group_score(
        member_skill_ids=member_skill_ids,
        mandatory_alternatives=mandatory_alternatives,
        profile_text="I have experience in PostgreSQL."
    )
    print(f"Mandatory PostgreSQL with 'PostgreSQL' in text (Should be 1): {result_3['score']}")

    print("\n--- Preferred Skills Tests ---")
    
    preferred_ids = ["FastAPI"]
    preferred_alternatives = {"FastAPI": ["skill_fastapi_id"]}
    
    # Case: Profile has 'Python'. Should NOT match FastAPI (Generic group name excluded).
    result_5 = agent._calculate_skill_score(
        member_skill_ids=[],
        mandatory_ids=[],
        preferred_ids=preferred_ids,
        preferred_alternatives=preferred_alternatives,
        profile_text="I am a Python developer."
    )
    print(f"Preferred FastAPI with 'Python' in text (Should be 0): {result_5['preferred_score']}")

    # Case: Profile has 'Django'. Should STILL match FastAPI (Siblings allowed for preferred).
    result_6 = agent._calculate_skill_score(
        member_skill_ids=[],
        mandatory_ids=[],
        preferred_ids=preferred_ids,
        preferred_alternatives=preferred_alternatives,
        profile_text="I am a Django developer."
    )
    print(f"Preferred FastAPI with 'Django' in text (Should be 1): {result_6['preferred_score']}")

if __name__ == "__main__":
    test_matching()
