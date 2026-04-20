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
from app.settings import settings

from app.ai.utils.trulens_helper import instrument
logger = logging.getLogger(__name__)

# System prompt for skill normalization and ontology expansion
NORMALIZER_SYSTEM_PROMPT = """You are an expert HR assistant specialized in skill normalization and ontology expansion.

Your task is to:
1. Normalize raw skill names to their canonical forms (e.g., "js" -> "JavaScript", "postgres" -> "PostgreSQL").
2. Expand skills by identifying related terms from a provided ontology.

Given:
- A list of raw mandatory skills
- A list of raw preferred skills
- A list of raw required certifications
- A skill/certification ontology mapping (Core Skill/Cert -> Enriched Terms)

For each raw skill or certification:
- Find the closest matching "Core Skill/Cert" in the ontology.
- Return the "Core Skill/Cert" as the normalized name (canonical).
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
  ],
  "certifications": [
    {"raw": "string", "canonical": "string", "enriched": ["string"]},
    ...
  ]
}
"""

# Common skill aliases for deterministic matching
SKILL_ALIASES = {
    "js": "JavaScript",
    "ts": "TypeScript",
    "py": "Python",
    "postgres": "PostgreSQL",
    "pg": "PostgreSQL",
    "k8s": "Kubernetes",
    "docker": "Docker",
    "react": "React",
    "vue": "Vue.js",
    "angular": "Angular",
    "node": "Node.js",
    "nodejs": "Node.js",
    "aws": "Amazon Web Services",
    "azure": "Azure",
    "gcp": "Google Cloud Platform",
}

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

def _normalize_deterministic_fallback(raw_skills: List[str], skill_master_map: Dict[str, str]) -> List[str]:
    """Fallback to deterministic ID mapping if LLM fails usage of aliases."""
    normalized_ids = []
    for raw in raw_skills:
        name = raw.strip().lower()
        
        # Check direct match
        if name in skill_master_map:
            normalized_ids.append(skill_master_map[name])
            continue
            
        # Check alias match
        if name in SKILL_ALIASES:
            canonical = SKILL_ALIASES[name].lower()
            if canonical in skill_master_map:
                normalized_ids.append(skill_master_map[canonical])
                continue
                
    return list(set(normalized_ids))

def _find_fuzzy_matches(term: str, skill_master_map: Dict[str, str]) -> List[str]:
    """Find all skill IDs where the term is a substring of the skill name."""
    term = term.lower().strip()
    if len(term) < 3:  # Avoid matching very short terms like "js" or "go" too broadly
        return []
        
    matches = []
    for skill_name, skill_id in skill_master_map.items():
        # Check for substring match (e.g. "python" in "python developer")
        if term in skill_name:
            matches.append(skill_id)
    return matches

@instrument
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
    
    # Reset error message for this node run
    state["error_message"] = None
    
    # Ensure state keys exist
    if state.get("llm_call_logs") is None:
        state["llm_call_logs"] = []
    
    parsed_jd = state.get("parsed_jd")
    if not parsed_jd:
        logger.error("Missing parsed_jd in state")
        state["error_message"] = "Missing parsed_jd"
        # Always ensure normalized_skills is set to avoid downstream crashes
        state["normalized_skills"] = {
            "mandatory_skill_ids": [],
            "preferred_skill_ids": [],
            "mandatory_enriched": {},
            "preferred_enriched": {},
            "mandatory_alternatives": {},
            "preferred_alternatives": {}
        }
        return state
    
    mandatory_skills = parsed_jd.get("extracted_mandatory_skills", [])
    preferred_skills = parsed_jd.get("extracted_preferred_skills", [])
    required_certifications = parsed_jd.get("certifications_required", [])
    
    # Initialize normalized_skills in state
    state["normalized_skills"] = {
        "mandatory_skill_ids": [],
        "preferred_skill_ids": [],
        "mandatory_enriched": {},
        "preferred_enriched": {},
        "mandatory_alternatives": {},
        "preferred_alternatives": {},
        "original_certifications": required_certifications,
        "normalized_certifications": [],
        "certification_enriched": {}
    }

    if not mandatory_skills and not preferred_skills and not required_certifications:
        logger.warning("No skills or certifications found to normalize")
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
            "certifications": required_certifications,
            "ontology": ontology_data
        }
        
        from app.ai.utils.llm_client import llm_client
        
        # Call LLM for fuzzy-logic normalization and enrichment
        logger.info("Calling LLM for skill normalization")
        content, usage = llm_client.chat_completion(
            messages=[
                {"role": "system", "content": NORMALIZER_SYSTEM_PROMPT + "\nIMPORTANT: Return ONLY valid JSON. Do not include any pre-amble or post-amble."},
                {"role": "user", "content": f"Normalize these skills: {json.dumps(raw_input)}"}
            ],
            response_format={"type": "json_object"} if llm_client.provider in ["openai", "groq"] else None
        )

        
        if not content:
            raise ValueError("LLM normalization failed - no content returned")

        # Parse result
        result = json.loads(content)
        
        # Extract metadata for logging
        cost = llm_client.get_completion_cost(usage) if usage else 0.0
        
        # Add to LLM logs for observability
        state["llm_call_logs"].append({
            "agent_name": "skill_normalization",
            "prompt_name": "skill_ontology_normalization",
            "model": usage.get("model", "unknown") if usage else "unknown",
            "prompt_tokens": usage.get("prompt_tokens", 0) if usage else 0,
            "completion_tokens": usage.get("completion_tokens", 0) if usage else 0,
            "total_tokens": usage.get("total_tokens", 0) if usage else 0,
            "cost_usd": cost
        })
        
        # Update cumulative metrics
        if usage:
            state["cumulative_tokens"] = (state.get("cumulative_tokens") or 0) + usage["total_tokens"]
        state["cumulative_cost_usd"] = (state.get("cumulative_cost_usd") or 0.0) + cost

        # Map results to skill IDs and enriched terms
        normalized_mandatory_ids = []
        mandatory_enriched = {}
        mandatory_alternatives = {}
        
        for item in (result.get("mandatory") or []):
            canonical = item.get("canonical")
            if canonical:
                # Skill group for this requirement
                skill_group = []
                
                # Resolve alias if exists
                if canonical.lower() in SKILL_ALIASES:
                    canonical = SKILL_ALIASES[canonical.lower()]

                # Direct match
                skill_id = skill_master_map.get(canonical.lower())
                if skill_id:
                    normalized_mandatory_ids.append(skill_id)
                    mandatory_enriched[skill_id] = item.get("enriched", [])
                    skill_group.append(skill_id)
                
                # Fuzzy match extension
                fuzzy_ids = _find_fuzzy_matches(canonical, skill_master_map)
                normalized_mandatory_ids.extend(fuzzy_ids)
                skill_group.extend(fuzzy_ids)
                
                # Store unique IDs for this requirement group
                if skill_group:
                    mandatory_alternatives[canonical] = list(set(skill_group))
                else:
                    # If no core skill match, preserve the original raw name in the alternatives map
                    # This allows subsequent scoring to at least show it was requested.
                    raw_name = item.get("raw") or canonical
                    mandatory_alternatives[raw_name] = []
        
        normalized_preferred_ids = []
        preferred_enriched = {}
        preferred_alternatives = {}
        
        for item in (result.get("preferred") or []):
            canonical = item.get("canonical")
            if canonical:
                # Skill group for this requirement
                skill_group = []

                # Resolve alias if exists
                if canonical.lower() in SKILL_ALIASES:
                    canonical = SKILL_ALIASES[canonical.lower()]

                # Direct match
                skill_id = skill_master_map.get(canonical.lower())
                if skill_id:
                    normalized_preferred_ids.append(skill_id)
                    preferred_enriched[skill_id] = item.get("enriched", [])
                    skill_group.append(skill_id)

                # Fuzzy match extension
                fuzzy_ids = _find_fuzzy_matches(canonical, skill_master_map)
                normalized_preferred_ids.extend(fuzzy_ids)
                skill_group.extend(fuzzy_ids)
                
                # Store unique IDs for this requirement group
                if skill_group:
                    preferred_alternatives[canonical] = list(set(skill_group))
                else:
                    # If no core skill match, preserve the original raw name in the alternatives map
                    raw_name = item.get("raw") or canonical
                    preferred_alternatives[raw_name] = []
                    
        normalized_certs = []
        certification_enriched = {}
        for item in (result.get("certifications") or []):
            canonical = item.get("canonical")
            if canonical:
                # Resolve alias if exists
                if canonical.lower() in SKILL_ALIASES:
                    canonical = SKILL_ALIASES[canonical.lower()]

                normalized_certs.append(canonical)
                certification_enriched[canonical] = item.get("enriched", [])

                
        # Populate state
        state["normalized_skills"] = {
            "mandatory_skill_ids": list(set(normalized_mandatory_ids)),
            "preferred_skill_ids": list(set(normalized_preferred_ids)),
            "mandatory_enriched": mandatory_enriched,
            "preferred_enriched": preferred_enriched,
            "mandatory_alternatives": mandatory_alternatives,
            "preferred_alternatives": preferred_alternatives,
            "original_certifications": required_certifications,
            "normalized_certifications": list(set(normalized_certs)),
            "certification_enriched": certification_enriched
        }
        
    except Exception as e:
        logger.error(f"Error in skill_normalization_node, falling back to deterministic: {str(e)}")
        
        # Add failed LLM attempt to logs
        state["llm_call_logs"].append({
            "agent_name": "skill_normalization",
            "prompt_name": "skill_ontology_normalization",
            "model": "gpt-4",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
            "status": "FAILED",
            "error_message": str(e)
        })
        
        # FALLBACK: Use deterministic matching if LLM fails (e.g. RateLimitError)
        skill_master_map = _get_skill_master_map(db)
        mand_ids = _normalize_deterministic_fallback(mandatory_skills, skill_master_map)
        pref_ids = _normalize_deterministic_fallback(preferred_skills, skill_master_map)
        
        # Simple alternatives map for fallback (1:1 mapping if possible)
        mand_alts = {}
        for skill in mandatory_skills:
             # Basic deterministic lookup for fallback alternatives
             resolved = _normalize_deterministic_fallback([skill], skill_master_map)
             if resolved:
                 mand_alts[skill] = resolved

        pref_alts = {}
        for skill in preferred_skills:
             resolved = _normalize_deterministic_fallback([skill], skill_master_map)
             if resolved:
                 pref_alts[skill] = resolved
        
        state["normalized_skills"] = {
            "mandatory_skill_ids": mand_ids,
            "preferred_skill_ids": pref_ids,
            "mandatory_enriched": {},
            "preferred_enriched": {},
            "mandatory_alternatives": mand_alts,
            "preferred_alternatives": pref_alts,
            "original_certifications": required_certifications,
            "normalized_certifications": required_certifications, # Fallback to original
            "certification_enriched": {}
        }
        state["error_message"] = f"Normalization fallback used due to: {str(e)}"
    finally:
        db.close()
    
    return state
