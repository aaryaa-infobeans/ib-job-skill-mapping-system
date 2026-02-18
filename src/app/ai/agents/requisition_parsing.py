"""Requisition parsing agent."""

import json
import logging
import os
from datetime import datetime, date
from typing import Optional

from app.ai.state import GraphState

logger = logging.getLogger(__name__)
from app.settings import settings

# Global client cache
_client_cache = {}

from app.ai.llm_factory import get_llm
from langchain_core.messages import SystemMessage, HumanMessage
from app.ai.utils.json_utils import extract_json_from_response

# Removed local _get_llm as it is now handled by app.ai.llm_factory.get_llm

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
  "requisition_duration_month": number or null,
  "certifications_required": ["cert1", "cert2"]
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
    llm = get_llm(temperature=0.0)
    if not llm:
        logger.info("LLM not enabled, using fallback parsing logic")
        return _fallback_parse(job_description), None
    
    try:
        # Prepare context for LLM
        context = {
            "title": job_description.get("title", "Unknown"),
            "role": job_description.get("role", "Unknown"),
            "client_name": job_description.get("client_name", "Unknown"),
            "mandatory_skills": job_description.get("mandatory_skills", []),
            "preferred_skills": job_description.get("preferred_skills", []),
            "jd_text": job_description.get("jd_text", ""),
            "experience": job_description.get("experience", {}),
            "expected_start_date": job_description.get("expected_start_date"),
            "requisition_duration_month": job_description.get("requisition_duration_month"),
        }
        
        def json_serial(obj):
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        messages = [
            SystemMessage(content=REQUISITION_PARSING_PROMPT + "\nIMPORTANT: Return ONLY valid JSON."),
            HumanMessage(content=f"Please parse this job description:\n{json.dumps(context, default=json_serial)}")
        ]
        
        response = llm.invoke(messages)
        llm_output = extract_json_from_response(response.content)
        
        if not llm_output:
            raise ValueError("Failed to extract valid JSON from LLM response")
        
        # Merge LLM enrichment back into the full context
        enriched_jd = {
            "normalized_title": llm_output.get("normalized_title", job_description.get("title")),
            "normalized_role": llm_output.get("normalized_role", job_description.get("role")),
            "extracted_mandatory_skills": llm_output.get("extracted_mandatory_skills", []),
            "extracted_preferred_skills": llm_output.get("extracted_preferred_skills", []),
            "experience": llm_output.get("experience", job_description.get("experience")),
            "expected_start_date": llm_output.get("expected_start_date", job_description.get("expected_start_date")),
            "requisition_duration_month": llm_output.get("requisition_duration_month", job_description.get("requisition_duration_month")),
            "certifications_required": list(set(llm_output.get("certifications_required", []) + job_description.get("certifications_required", []))),
            
            # Original Payload fields preserved
            "client_name": job_description.get("client_name"),
            "priority": job_description.get("priority"),
            "location": job_description.get("location", []),
            "work_mode": job_description.get("work_mode", []),
            "jd_text": job_description.get("jd_text", ""),
            "metadata": job_description.get("metadata", {}),
        }
        
        # Track tokens (Modern LangChain uses usage_metadata on the response object)
        usage = getattr(response, "usage_metadata", None) or response.response_metadata.get("usage_metadata") or response.response_metadata.get("token_usage", {})
        prompt_tokens = usage.get("input_tokens") or usage.get("prompt_token_count") or usage.get("prompt_tokens") or 0
        completion_tokens = usage.get("output_tokens") or usage.get("candidates_token_count") or usage.get("completion_tokens") or 0
        total_tokens = usage.get("total_tokens") or usage.get("total_token_count") or (prompt_tokens + completion_tokens)
        
        model_name = settings.google_model if settings.llm_provider == "google" else settings.openai_model
        
        # Cost calculation based on provider
        if settings.llm_provider == "google":
            cost = (prompt_tokens / 1_000_000 * settings.input_cost_google) + (completion_tokens / 1_000_000 * settings.output_cost_google)
        elif settings.llm_provider == "groq":
            cost = (prompt_tokens / 1_000_000 * settings.input_cost_groq) + (completion_tokens / 1_000_000 * settings.output_cost_groq)
        else:
            cost = (prompt_tokens / 1_000_000 * settings.input_cost_openai) + (completion_tokens / 1_000_000 * settings.output_cost_openai)
        
        # Add to LLM logs if request_id is available in a global way or passed
        # For now, we will return the metrics along with enriched_jd
        metrics = {
            "agent_name": "requisition_parsing",
            "prompt_name": "job_description_enrichment",
            "model": model_name,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost_usd": cost,
            "status": "SUCCESS"
        }
        
        logger.info(f"LLM successfully parsed requisition: {enriched_jd['normalized_title']}")
        return enriched_jd, metrics
        
    except Exception as e:
        logger.error(f"Error in LLM parsing: {str(e)}")
        # Create failure metrics to log the error to DB
        metrics = {
            "agent_name": "requisition_parsing",
            "prompt_name": "job_description_enrichment",
            "model": settings.google_model if settings.llm_provider == "google" else settings.openai_model,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
            "status": "FAILED",
            "error_message": str(e)
        }
        return _fallback_parse(job_description), metrics


def _fallback_parse(job_description: dict) -> dict:
    """Fallback logic when LLM is disabled or fails."""
    return {
        "normalized_title": job_description.get("title", "Unknown"),
        "normalized_role": job_description.get("role", "Unknown"),
        "extracted_mandatory_skills": list(set(job_description.get("mandatory_skills", []))),
        "extracted_preferred_skills": list(set(job_description.get("preferred_skills", []))),
        "experience": job_description.get("experience", {"min_months": None, "max_months": None}),
        "expected_start_date": job_description.get("expected_start_date"),
        "requisition_duration_month": job_description.get("requisition_duration_month"),
        "certifications_required": job_description.get("certifications_required", []),
        "client_name": job_description.get("client_name"),
        "priority": job_description.get("priority"),
        "location": job_description.get("location", []),
        "work_mode": job_description.get("work_mode", []),
        "jd_text": job_description.get("jd_text", ""),
        "metadata": job_description.get("metadata", {}),
    }


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
        # ========================================
        # STEP 1: BASIC VALIDATION
        # ========================================
        from app.ai.agents.requisition_validation import validate_requisition_input
        
        logger.info("🔍 Step 1: Validating requisition input (basic checks)...")
        is_valid, validation_reasons = validate_requisition_input(job_description)
        
        if not is_valid:
            # Basic validation failed - set error and return immediately
            error_msg = "VALIDATION_FAILED: " + "; ".join(validation_reasons)
            state["error_message"] = error_msg
            state["validation_errors"] = validation_reasons  # Store as list for structured access
            logger.error(f"❌ Basic validation failed for request_id={state['requisition_input']['request_id']}")
            logger.error(f"   Validation errors: {validation_reasons}")
            return state
        
        logger.info("✅ Basic validation passed")
        
        # ========================================
        # STEP 2: SEMANTIC VALIDATION (LLM-based)
        # ========================================
        from app.ai.agents.semantic_validation import validate_requisition_semantics
        
        logger.info("🔍 Step 2: Validating data quality (semantic checks)...")
        is_semantically_valid, semantic_errors = validate_requisition_semantics(job_description)
        
        if not is_semantically_valid:
            # Semantic validation failed - data appears to be garbage
            error_msg = "SEMANTIC_VALIDATION_FAILED: " + "; ".join(semantic_errors)
            state["error_message"] = error_msg
            state["validation_errors"] = semantic_errors  # Store as list for structured access
            logger.error(f"❌ Semantic validation failed for request_id={state['requisition_input']['request_id']}")
            logger.error(f"   Semantic errors: {semantic_errors}")
            return state
        
        logger.info("✅ Semantic validation passed, proceeding with LLM parsing")
        
        # ========================================
        # STEP 3: PARSE REQUISITION USING LLM
        # ========================================
        # Parse requisition using LLM
        parsed_jd, metrics = parse_requisition_with_llm(job_description)
        
        if parsed_jd:
            state["parsed_jd"] = parsed_jd
            if metrics:
                if state.get("llm_call_logs") is None:
                    state["llm_call_logs"] = []
                state["llm_call_logs"].append(metrics)
                state["cumulative_tokens"] = (state.get("cumulative_tokens") or 0) + metrics["total_tokens"]
                state["cumulative_cost_usd"] = (state.get("cumulative_cost_usd") or 0.0) + metrics["cost_usd"]
                
            logger.info("Requisition_Parsing_Agent completed successfully")
        else:
            logger.error("Failed to parse requisition after retries")
            state["error_message"] = "Requisition parsing failed after retries"
    
    except Exception as e:
        logger.error(f"Error in requisition_parsing_node: {str(e)}", exc_info=True)
        state["error_message"] = f"Requisition parsing error: {str(e)}"
    
    return state
