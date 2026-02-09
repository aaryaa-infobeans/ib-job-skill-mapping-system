"""Requisition parsing agent."""

import json
import logging
import os
from typing import Optional

from app.ai.state import GraphState

logger = logging.getLogger(__name__)

# System prompt for requisition parsing
REQUISITION_PARSING_PROMPT = """You are an expert HR assistant specialized in analyzing job requisitions.

Your task is to enrich requisition information by analyzing the job description text and normalizing existing data.

Given:
- Basic job metadata (title, role, client)
- Job description text (jd_text)
- Initial mandatory and preferred skill lists

Your responsibilities:
1. Extract additional technical skills, tools, and technologies from the `jd_text` that are not already in the provided lists.
2. Normalize all skills (extracted and provided) to a standard format (e.g., "python" -> "Python", "k8s" -> "Kubernetes").
3. Normalize the job title and role category to standard professional formats.
4. Extract or verify experience requirements (in months).
5. Identify expected start date and duration if explicitly mentioned in the text.

Return ONLY a valid JSON object with this exact structure:
{
  "normalized_title": "string - standardized job title",
  "normalized_role": "string - standardized role category",
  "extracted_mandatory_skills": ["skill1", "skill2"],
  "extracted_preferred_skills": ["skill3", "skill4"],
  "experience": {
    "min_months": number or null,
    "max_months": number or null
  },
  "expected_start_date": "YYYY-MM-DD or null",
  "requisition_duration_month": number or null
}

Important:
- Combine payload skills with newly extracted ones.
- Ensure the JSON is valid and only contains the requested fields.
- Use null for missing information.
"""


def parse_requisition_with_llm(
    job_description: dict,
    max_retries: int = 2
) -> Optional[dict]:
    """Enrich requisition data using LLM.
    
    This function merges the original payload with LLM-normalized and extracted data.
    
    Args:
        job_description: Job description dict from requisition_input
        max_retries: Maximum number of retry attempts
    
    Returns:
        Enriched requisition dict (ParsedJD) or None on failure
    """
    # For stub implementation, we'll simulate the LLM enrichment by merging
    # In production, this would call the actual LLM API with REQUISITION_PARSING_PROMPT
    
    logger.info("Enriching requisition (stub implementation)")
    
    # Simulate LLM enrichment/normalization
    llm_output = {
        "normalized_title": job_description.get("title", "Software Engineer"),
        "normalized_role": job_description.get("role", "Engineer"),
        "extracted_mandatory_skills": list(set(job_description.get("mandatory_skills", []))),
        "extracted_preferred_skills": list(set(job_description.get("preferred_skills", []))),
        "experience": job_description.get("experience", {"min_months": None, "max_months": None}),
        "expected_start_date": job_description.get("expected_start_date"),
        "requisition_duration_month": job_description.get("requisition_duration_month"),
    }
    
    # Merge LLM enrichment back into the full context
    enriched_jd = {
        # LLM Enriched fields
        "normalized_title": llm_output["normalized_title"],
        "normalized_role": llm_output["normalized_role"],
        "extracted_mandatory_skills": llm_output["extracted_mandatory_skills"],
        "extracted_preferred_skills": llm_output["extracted_preferred_skills"],
        "experience": llm_output["experience"],
        "expected_start_date": llm_output["expected_start_date"],
        "requisition_duration_month": llm_output["requisition_duration_month"],
        
        # Original Payload fields preserved
        "client_name": job_description.get("client_name"),
        "priority": job_description.get("priority"),
        "location": job_description.get("location", []),
        "work_mode": job_description.get("work_mode", []),
        "jd_text": job_description.get("jd_text", ""),
        "metadata": job_description.get("metadata", {}),
    }
    
    logger.info(f"Enriched requisition: {enriched_jd['normalized_title']}")
    return enriched_jd


def requisition_parsing_node(state: GraphState) -> GraphState:
    """Parse requisition and extract structured information.
    
    This node:
    1. Extracts job description / requisition data from requisition_input
    2. Calls LLM to parse and structure the information
    3. Validates the output against ParsedJD schema
    4. Populates state.parsed_jd on success
    5. Sets state.error_message on failure after retries
    """
    logger.info("Executing Requisition_Parsing_Agent node")
    logger.info(f"Processing request_id: {state['requisition_input']['request_id']}")
    
    requisition_input = state.get("requisition_input")
    if not requisition_input:
        logger.error("Missing requisition_input in state")
        state["error_message"] = "Missing requisition_input"
        return state
    
    job_description = requisition_input.get("job_description")
    if not job_description:
        # If job_description is a string (from earlier stub), create dict
        if isinstance(requisition_input.get("job_description"), str):
            job_description = {
                "jd_text": requisition_input["job_description"],
                "title": "Unknown",
                "role": "Unknown",
            }
        else:
            logger.error("Missing or invalid job_description in requisition_input")
            state["error_message"] = "Missing job_description"
            return state
    
    try:
        # Parse requisition using LLM
        parsed_jd = parse_requisition_with_llm(job_description)
        
        if parsed_jd:
            state["parsed_jd"] = parsed_jd
            logger.info("Requisition_Parsing_Agent completed successfully")
        else:
            logger.error("Failed to parse requisition after retries")
            state["error_message"] = "Requisition parsing failed after retries"
    
    except Exception as e:
        logger.error(f"Error in requisition_parsing_node: {str(e)}", exc_info=True)
        state["error_message"] = f"Requisition parsing error: {str(e)}"
    
    return state
