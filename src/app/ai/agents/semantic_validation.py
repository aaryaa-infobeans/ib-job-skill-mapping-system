"""LLM-based semantic validation for requisition data quality."""

import json
import logging
import os
import re
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

from app.ai.utils.llm_client import llm_client

SEMANTIC_VALIDATION_PROMPT = """You are a data quality validator for job requisitions. Your task is to identify nonsensical, garbage, or invalid values in the requisition data.

IMPORTANT: The data may have been pre-processed by a PII scrubber. The following patterns are VALID and should NOT be flagged as garbage:
- `CLIENT_TOKEN_...` (e.g., `CLIENT_TOKEN_a7b9c2d1`) - Valid anonymized client/company name.
- `PROJECT_TOKEN_...` (e.g., `PROJECT_TOKEN_e4f8a9b2`) - Valid anonymized project name.
- `[REDACTED]`, `[NAME_REDACTED]`, `[EMAIL_REDACTED]`, `[PHONE_REDACTED]`, etc. - Valid anonymized data.

Analyze the following fields and check if they contain valid, professional data:

1. **Job Title**: Is it a real professional job title? (e.g., "Senior Software Engineer" is valid, "sdfdsf" is garbage)
2. **Job Role**: Is it a valid role category? (e.g., "Software Development" is valid, "sdf" is garbage)
3. **Skills**: Are they actual technologies, tools, or competencies? (e.g., "Python", "React" are valid, "sdfsdf" is garbage)
4. **Client Name**: Is it a plausible company name OR a valid PII token (e.g., `CLIENT_TOKEN_...`)?
5. **Location**: Are they real places? (e.g., "New York" is valid, "dsfdsfsd" is garbage)
6. **Job Description**: Is it coherent and professional? (Random characters or keyboard mashing is garbage). Note that it may contain PII tokens or redaction markers.

Return ONLY valid JSON with this exact structure:
{
  "is_valid": boolean,
  "validation_errors": ["error message 1", "error message 2", ...]
}

If all data appears valid and professional, return:
{
  "is_valid": true,
  "validation_errors": []
}

Be strict but reasonable. Minor typos are acceptable, but obvious garbage data (random characters, keyboard mashing, nonsensical values) should be flagged.
"""

def _normalize_role(role: str, title: str) -> str:
    role_norm = (role or "").strip()
    title_norm = (title or "").strip()
    if not role_norm or role_norm.lower() in ["unknown", "n/a", "na"]:
        return "Software Development"
    if role_norm.lower() == title_norm.lower():
        # If role is identical to title, fallback to a generic role category
        return "Software Development" if "software" in title_norm.lower() else "Engineering"
    return role_norm


def _normalize_client_name(client_name: str) -> str:
    clean = (client_name or "").strip()
    if not clean or clean.lower() in ["na", "n/a", "none", "unknown", "tbd"]:
        return "CLIENT_TOKEN_UNKNOWN"
    return clean


def validate_requisition_semantics(job_description: Dict, max_retries: int = 2) -> Tuple[bool, List[str]]:
    """
    Use LLM to validate semantic quality of requisition data.
    """
    try:
        # Prepare data for validation (with heuristics for common false positives)
        title = job_description.get("title", "")
        raw_role = job_description.get("role", "")
        raw_client = job_description.get("client_name", "")

        validation_context = {
            "title": title,
            "role": _normalize_role(raw_role, title),
            "client_name": _normalize_client_name(raw_client),
            "mandatory_skills": job_description.get("mandatory_skills", []),
            "preferred_skills": job_description.get("preferred_skills", []),
            "location": job_description.get("location", []),
            "jd_text": job_description.get("jd_text", "")[:500],  # Limit to first 500 chars
        }
        
        logger.info("🔍 Running LLM semantic validation...")
        
        content, usage = llm_client.chat_completion(
            messages=[
                {"role": "system", "content": SEMANTIC_VALIDATION_PROMPT},
                {"role": "user", "content": f"Validate this requisition data:\n{json.dumps(validation_context, indent=2)}"}
            ],
            response_format={"type": "json_object"} if llm_client.provider in ["openai", "groq"] else None
        )

        
        if not content:
            logger.warning("⚠️  LLM call failed for semantic validation - skipping quality check")
            return True, []

        # Parse LLM response
        llm_output = json.loads(content)
        
        is_valid = llm_output.get("is_valid", True)
        validation_errors = llm_output.get("validation_errors", [])

        # Post-process known false positives (role/title overlap, scrubbed client shortcuts)
        filtered_errors = []
        for error in validation_errors:
            if "Job Role" in error and "not a valid role category" in error:
                continue
            if "Client Name" in error and "not a plausible company name" in error:
                continue
            filtered_errors.append(error)

        if filtered_errors:
            is_valid = False
            validation_errors = filtered_errors
        else:
            is_valid = True
            validation_errors = []

        if is_valid:
            logger.info("✅ Semantic validation passed - data appears valid")
        else:
            logger.warning(f"❌ Semantic validation failed with {len(validation_errors)} error(s)")
            for error in validation_errors:
                logger.warning(f"  - {error}")

        return is_valid, validation_errors
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM validation response: {str(e)}")
        # If we can't parse the response, assume valid to avoid blocking legitimate requests
        return True, []
        
    except Exception as e:
        logger.error(f"Error in semantic validation: {str(e)}", exc_info=True)
        # On error, assume valid to avoid blocking legitimate requests
        return True, []
