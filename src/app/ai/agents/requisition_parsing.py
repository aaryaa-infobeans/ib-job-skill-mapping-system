"""Requisition parsing agent."""

import json
import logging
import os
from datetime import datetime, date
from typing import Optional

from app.ai.state import GraphState

logger = logging.getLogger(__name__)
from app.settings import settings

from app.ai.utils.llm_client import llm_client

# System prompt for requisition parsing
REQUISITION_PARSING_PROMPT = """You are an expert talent matcher and HR analyst specialized in analyzing job requisitions.

Your task is to analyze the job description text and normalize existing data to identify the best candidates.

Given:
- Basic job metadata (title, role, client)
- Job description text (jd_text)
- Initial mandatory and preferred skill lists
- Initial required certifications (certifications)

Your responsibilities:
1. Infer and normalize the best mandatory skills and preferred skills from the description.
2. If skills are missing or incomplete, extract them from the `jd_text`.
3. Normalize all skills to a standard technical format.
4. Enhance the certification list with canonical certification names.
5. Extract or verify experience requirements (in months).
6. Return ONLY a valid JSON object with fields mandatory_skills, preferred_skills, certifications, experience, normalized_title, and normalized_role.

Return ONLY a valid JSON object with this exact structure:
{
  "normalized_title": "string - standardized job title",
  "normalized_role": "string - standardized role category",
  "mandatory_skills": ["skill1", "skill2"],
  "preferred_skills": ["skill3", "skill4"],
  "experience": {
    "min_months": number or null,
    "max_months": number or null
  },
  "certifications": ["cert1", "cert2"]
}

Important:
- Return ONLY the JSON object.
- Keep skills distinct and professional.
"""


def _normalize_string_list(value: any) -> list[str]:
    """Helper to normalize string lists from various formats."""
    import re
    if not value:
        return []
    if isinstance(value, str):
        return [item.strip() for item in re.split(r"[\n,;]+", value) if item.strip()]
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def parse_requisition_with_llm(
    job_description: dict,
    max_retries: int = 2
) -> Optional[dict]:
    """Enrich requisition data using LLM following logic from embed_search.py."""
    try:
        # Prepare context for LLM
        context = {
            "title": job_description.get("title", "Unknown"),
            "role": job_description.get("role", "Unknown"),
            "client_name": job_description.get("client_name", "Unknown"),
            "mandatory_skills": job_description.get("mandatory_skills", []),
            "preferred_skills": job_description.get("preferred_skills", []),
            "certifications": job_description.get("certifications") or job_description.get("certifications_required", []),
            "jd_text": job_description.get("jd_text", ""),
            "experience": job_description.get("experience", {}),
        }
        
        def json_serial(obj):
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        content, usage = llm_client.chat_completion(
            messages=[
                {"role": "system", "content": REQUISITION_PARSING_PROMPT + "\nIMPORTANT: Return ONLY valid JSON."},
                {"role": "user", "content": f"Please parse this job description:\n{json.dumps(context, default=json_serial)}"}
            ],
            response_format={"type": "json_object"} if llm_client.provider in ["openai", "groq"] else None
        )

        if not content:
            logger.error("LLM parsing failed - no content returned")
            return _fallback_parse(job_description), None

        llm_output = json.loads(content)
        
        # Capture originals to prevent "downgrading" or "moving" as per embed_search.py
        original_mandatory = set(_normalize_string_list(job_description.get("mandatory_skills", [])))
        original_preferred = set(_normalize_string_list(job_description.get("preferred_skills", [])))
        original_certs = set(_normalize_string_list(job_description.get("certifications") or job_description.get("certifications_required", [])))

        # Process Skills and Certs with enrichment logic
        def merge_enriched_items(key, original_set, exclude_set):
            enriched_items = _normalize_string_list(llm_output.get(key, []))
            # Merge: Use existing + any new ones the LLM found
            # But if an item was already in exclude_set (e.g. Preferred), don't let it become Mandatory
            new_items = [i for i in enriched_items if i not in exclude_set]
            return sorted(list(original_set.union(set(new_items))))

        final_mandatory = merge_enriched_items("mandatory_skills", original_mandatory, original_preferred)
        final_preferred = merge_enriched_items("preferred_skills", original_preferred, original_mandatory)
        final_certs = sorted(list(original_certs.union(set(_normalize_string_list(llm_output.get("certifications", []))))))

        # Merge LLM enrichment back into the full context
        enriched_jd = {
            "normalized_title": llm_output.get("normalized_title", job_description.get("title")),
            "normalized_role": llm_output.get("normalized_role", job_description.get("role")),
            "extracted_mandatory_skills": final_mandatory,
            "extracted_preferred_skills": final_preferred,
            "experience": llm_output.get("experience", job_description.get("experience")),
            "certifications_required": final_certs,
            
            # Preserve metadata and other fields
            "client_name": job_description.get("client_name"),
            "priority": job_description.get("priority"),
            "location": job_description.get("location", []),
            "work_mode": job_description.get("work_mode", []),
            "jd_text": job_description.get("jd_text", ""),
            "metadata": job_description.get("metadata", {}),
            "expected_start_date": job_description.get("expected_start_date"),
            "requisition_duration_month": job_description.get("requisition_duration_month"),
        }
        
        # Track tokens and cost
        cost = llm_client.get_completion_cost(usage) if usage else 0.0
        
        metrics = {
            "agent_name": "requisition_parsing",
            "prompt_name": "job_description_enrichment",
            "model": usage.get("model", "unknown") if usage else "unknown",
            "prompt_tokens": usage.get("prompt_tokens", 0) if usage else 0,
            "completion_tokens": usage.get("completion_tokens", 0) if usage else 0,
            "total_tokens": usage.get("total_tokens", 0) if usage else 0,
            "cost_usd": cost,
            "status": "SUCCESS"
        }
        
        logger.info(f"LLM successfully parsed requisition: {enriched_jd['normalized_title']}")
        return enriched_jd, metrics
        
    except Exception as e:
        logger.error(f"Error in LLM parsing: {str(e)}")
        metrics = {
            "agent_name": "requisition_parsing",
            "prompt_name": "job_description_enrichment",
            "model": "unknown",
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
    
    # Reset error message for this node run
    state["error_message"] = None
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
            # Enforce that we predicted at least some skills if they were provided
            m_skills = parsed_jd.get("extracted_mandatory_skills", [])
            p_skills = parsed_jd.get("extracted_preferred_skills", [])
            
            had_skills = bool(job_description.get("mandatory_skills") or job_description.get("preferred_skills"))
            
            if had_skills and not m_skills and not p_skills:
                # We couldn't predict anything valid from what they gave us
                error_msg = "SEMANTIC_VALIDATION_FAILED: Could not predict any valid skills from the provided text."
                state["error_message"] = error_msg
                logger.error(f"❌ {error_msg}")
                return state

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
