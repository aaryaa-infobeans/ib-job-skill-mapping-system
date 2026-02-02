"""Job description parsing agent."""

import json
import logging
import os
from typing import Optional

from app.ai.state import GraphState

logger = logging.getLogger(__name__)

# System prompt for JD parsing
JD_PARSING_PROMPT = """You are an expert HR assistant specialized in analyzing job descriptions.

Your task is to parse job description information and return a structured JSON object.

Given:
- Job title and role
- Job description text (jd_text)
- Existing mandatory_skills and preferred_skills lists

Your responsibilities:
1. Extract all technical skills, tools, platforms, and technologies from the jd_text
2. Combine extracted skills with provided skill lists
3. Categorize skills into mandatory (required/must-have) vs preferred (nice-to-have/optional)
4. Normalize the job title to standard format (e.g., "Sr. Python Dev" -> "Senior Python Developer")
5. Extract experience requirements if mentioned (in months)
6. Extract location and work mode preferences if mentioned

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
- Skills should be normalized (e.g., "python" -> "Python", "k8s" -> "Kubernetes")
- All fields must be present in the JSON
- Use null for missing information
- Extract experience in months (e.g., "3-5 years" -> min_months: 36, max_months: 60)
"""


def parse_jd_with_llm(
    job_description: dict,
    max_retries: int = 2
) -> Optional[dict]:
    """Parse job description using LLM.
    
    Args:
        job_description: Job description dict from requisition_input
        max_retries: Maximum number of retry attempts
    
    Returns:
        Parsed JD dict or None on failure
    """
    # For stub implementation without LLM dependency, return structured data
    # In production, this would call OpenAI API
    
    logger.info("Parsing JD (stub implementation - would call LLM in production)")
    
    # Extract input data
    title = job_description.get("title", "")
    role = job_description.get("role", "")
    jd_text = job_description.get("jd_text", "")
    mandatory_skills = job_description.get("mandatory_skills", [])
    preferred_skills = job_description.get("preferred_skills", [])
    expected_start_date = job_description.get("expected_start_date")
    requisition_duration_month = job_description.get("requisition_duration_month")
    experience = job_description.get("experience")
    
    # Stub: Return deterministic parsed output
    # In production, this would be LLM-generated
    parsed_jd = {
        "normalized_title": title or "Software Engineer",
        "normalized_role": role or "Engineer",
        "extracted_mandatory_skills": mandatory_skills or [],
        "extracted_preferred_skills": preferred_skills or [],
        "experience": {
            "min_months": experience.get("min_months") if experience else None,
            "max_months": experience.get("max_months") if experience else None,
        },
        "expected_start_date": expected_start_date,
        "requisition_duration_month": requisition_duration_month,
    }
    
    logger.info(f"Parsed JD: {parsed_jd['normalized_title']} - "
                f"{len(parsed_jd['extracted_mandatory_skills'])} mandatory, "
                f"{len(parsed_jd['extracted_preferred_skills'])} preferred skills")
    
    return parsed_jd


def jd_parsing_node(state: GraphState) -> GraphState:
    """Parse job description and extract structured information.
    
    This node:
    1. Extracts job description from requisition_input
    2. Calls LLM to parse and structure the information
    3. Validates the output against ParsedJD schema
    4. Populates state.parsed_jd on success
    5. Sets state.error_message on failure after retries
    """
    logger.info("Executing JD_Parsing_Agent node")
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
        # Parse JD using LLM
        parsed_jd = parse_jd_with_llm(job_description)
        
        if parsed_jd:
            state["parsed_jd"] = parsed_jd
            logger.info("JD_Parsing_Agent completed successfully")
        else:
            logger.error("Failed to parse JD after retries")
            state["error_message"] = "JD parsing failed after retries"
    
    except Exception as e:
        logger.error(f"Error in jd_parsing_node: {str(e)}", exc_info=True)
        state["error_message"] = f"JD parsing error: {str(e)}"
    
    return state
