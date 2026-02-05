"""Skill normalization agent."""

import json
import logging
import os
from typing import Dict, List, Any, Optional

from sqlalchemy.orm import Session
from openai import OpenAI

from app.ai.state import GraphState
from app.db.models import SkillMaster, SkillOntology
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

# System prompt for skill normalization and ontology expansion
NORMALIZER_SYSTEM_PROMPT = """You are an expert HR assistant specialized in skill normalization and ontology expansion.

Your task is to:
1. Normalize raw skill names to their canonical forms (e.g., "js" -> "JavaScript", "postgres" -> "PostgreSQL").
2. Expand skills by identifying related terms from a provided ontology.

Given:
- A list of raw mandatory skills
- A list of raw preferred skills
- A skill ontology mapping (Core Skill -> Enriched Terms)

For each raw skill:
- Find the closest matching "Core Skill" in the ontology.
- Return the "Core Skill" as the normalized name (canonical).
- Include the "Enriched Terms" for better matching downstream.
- If no close match exists in the ontology, normalize the name to a standard form and leave enriched terms empty.

Return a JSON object with this exact structure:
{
  "mandatory": [
    {"raw": "string", "canonical": "string", "enriched": ["string"]},
    ...
  ],
  "preferred": [
    {"raw": "string", "canonical": "string", "enriched": ["string"]},
    ...
  ]
}
"""

def _get_ontology_data(db: Session) -> Dict[str, List[str]]:
    """Fetch all skills from the ontology table."""
    try:
        ontology_items = db.query(SkillOntology).all()
        return {item.core_skill: item.enriched_terms or [] for item in ontology_items}
    except Exception as e:
        logger.error(f"Error fetching ontology: {str(e)}")
        return {}

def _get_skill_master_map(db: Session) -> Dict[str, str]:
    """Fetch all skills from the skill_master table for ID mapping."""
    try:
        skills = db.query(SkillMaster).all()
        return {skill.skill_name.lower(): skill.skill_id for skill in skills}
    except Exception as e:
        logger.error(f"Error fetching skill master: {str(e)}")
        return {}

def skill_normalization_node(state: GraphState) -> GraphState:
    """Normalize and expand skills using the skill ontology and LLM.
    
    This node:
    1. Extracts skills from parsed_jd
    2. Queries skill_ontology for canonical core skills and expanded terms
    3. Uses LLM to map raw skills to canonical ontology skills
    4. Maps canonical names to skill_master IDs
    5. Populates state.normalized_skills with IDs and enriched terms
    """
    logger.info("Executing Skill_Normalization_Agent node with ontology")
    
    parsed_jd = state.get("parsed_jd")
    if not parsed_jd:
        logger.error("Missing parsed_jd in state")
        state["error_message"] = "Missing parsed_jd"
        return state
    
    mandatory_skills = parsed_jd.get("extracted_mandatory_skills", [])
    preferred_skills = parsed_jd.get("extracted_preferred_skills", [])
    
    if not mandatory_skills and not preferred_skills:
        logger.warning("No skills found to normalize")
        state["normalized_skills"] = {
            "mandatory_skill_ids": [],
            "preferred_skill_ids": [],
            "mandatory_enriched": {},
            "preferred_enriched": {}
        }
        return state

    db: Session = SessionLocal()
    try:
        # Load data for LLM context and ID mapping
        ontology_data = _get_ontology_data(db)
        skill_master_map = _get_skill_master_map(db)
        
        logger.info(f"Loaded {len(ontology_data)} ontology items and {len(skill_master_map)} skill master items")
        
        # Prepare inputs for LLM
        raw_input = {
            "mandatory": mandatory_skills,
            "preferred": preferred_skills,
            "ontology": ontology_data
        }
        
        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
            
        client = OpenAI(api_key=api_key)
        
        # Call LLM for fuzzy-logic normalization and enrichment
        logger.info("Calling LLM for skill normalization")
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": NORMALIZER_SYSTEM_PROMPT + "\nIMPORTANT: Return ONLY valid JSON. Do not include any pre-amble or post-amble."},
                {"role": "user", "content": f"Normalize these skills: {json.dumps(raw_input)}"}
            ],
            temperature=0.0
        )
        
        # Parse result
        result_text = response.choices[0].message.content
        result = json.loads(result_text)
        
        # Extract metadata for logging
        usage = response.usage
        cost = (usage.prompt_tokens / 1_000_000 * 0.03) + (usage.completion_tokens / 1_000_000 * 0.06)
        
        # Add to LLM logs for observability
        if "llm_call_logs" not in state or state["llm_call_logs"] is None:
            state["llm_call_logs"] = []
            
        state["llm_call_logs"].append({
            "agent_name": "skill_normalization",
            "prompt_name": "skill_ontology_normalization",
            "model": "gpt-4",
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "cost_usd": cost
        })
        
        # Update cumulative metrics
        state["cumulative_tokens"] = (state.get("cumulative_tokens") or 0) + usage.total_tokens
        state["cumulative_cost_usd"] = (state.get("cumulative_cost_usd") or 0.0) + cost

        # Map results to skill IDs and enriched terms
        normalized_mandatory_ids = []
        mandatory_enriched = {}
        for item in result.get("mandatory", []):
            canonical = item.get("canonical")
            if canonical:
                # Map to skill_master ID
                skill_id = skill_master_map.get(canonical.lower())
                if skill_id:
                    normalized_mandatory_ids.append(skill_id)
                    mandatory_enriched[skill_id] = item.get("enriched", [])
                else:
                    logger.warning(f"Canonical skill '{canonical}' not found in SkillMaster")
        
        normalized_preferred_ids = []
        preferred_enriched = {}
        for item in result.get("preferred", []):
            canonical = item.get("canonical")
            if canonical:
                # Map to skill_master ID
                skill_id = skill_master_map.get(canonical.lower())
                if skill_id:
                    normalized_preferred_ids.append(skill_id)
                    preferred_enriched[skill_id] = item.get("enriched", [])
                else:
                    logger.warning(f"Canonical skill '{canonical}' not found in SkillMaster")
                    
        # Populate state
        state["normalized_skills"] = {
            "mandatory_skill_ids": list(set(normalized_mandatory_ids)),
            "preferred_skill_ids": list(set(normalized_preferred_ids)),
            "mandatory_enriched": mandatory_enriched,
            "preferred_enriched": preferred_enriched,
        }
        
        logger.info(f"Skill_Normalization_Agent completed: "
                    f"{len(normalized_mandatory_ids)} mandatory, "
                    f"{len(normalized_preferred_ids)} preferred")
        
    except Exception as e:
        logger.error(f"Error in skill_normalization_node: {str(e)}", exc_info=True)
        state["error_message"] = f"Skill normalization failed: {str(e)}"
        # Fallback to empty if absolutely failed
        if "normalized_skills" not in state:
            state["normalized_skills"] = {
                "mandatory_skill_ids": [],
                "preferred_skill_ids": [],
                "mandatory_enriched": {},
                "preferred_enriched": {}
            }
    finally:
        db.close()
    
    return state
