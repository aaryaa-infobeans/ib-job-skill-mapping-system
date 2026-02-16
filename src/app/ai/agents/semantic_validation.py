"""LLM-based semantic validation for requisition data quality."""

import json
import logging
import os
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# Global client cache
_client_cache = {}


def _get_openai_client():
    """Get or create OpenAI client."""
    if "client" in _client_cache:
        return _client_cache["client"], True
        
    from app.settings import settings
    api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
    
    if not api_key or api_key == "sk-your-openai-api-key-here" or len(api_key) < 20:
        logger.warning("⚠️  OPENAI_API_KEY not configured for semantic validation")
        return None, False
        
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        _client_cache["client"] = client
        return client, True
    except Exception as e:
        logger.error(f"❌ Failed to initialize OpenAI client: {str(e)}")
        return None, False


SEMANTIC_VALIDATION_PROMPT = """You are a data quality validator for job requisitions. Your task is to identify nonsensical, garbage, or invalid values in the requisition data.

Analyze the following fields and check if they contain valid, professional data:

1. **Job Title**: Is it a real professional job title? (e.g., "Senior Software Engineer" is valid, "sdfdsf" is garbage)
2. **Job Role**: Is it a valid role category? (e.g., "Software Development" is valid, "sdf" is garbage)
3. **Skills**: Are they actual technologies, tools, or competencies? (e.g., "Python", "React" are valid, "sdfsdf" is garbage)
4. **Client Name**: Is it a plausible company name? (e.g., "Acme Corp" is valid, "sdf" is garbage)
5. **Location**: Are they real places? (e.g., "New York" is valid, "dsfdsfsd" is garbage)
6. **Job Description**: Is it coherent and professional? (Random characters or keyboard mashing is garbage)

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


def validate_requisition_semantics(job_description: Dict, max_retries: int = 2) -> Tuple[bool, List[str]]:
    """
    Use LLM to validate semantic quality of requisition data.
    
    This function checks if the requisition contains meaningful, professional data
    or if it's filled with garbage/nonsensical values.
    
    Args:
        job_description: Job description dict from requisition_input
        max_retries: Maximum number of retry attempts for LLM call
        
    Returns:
        Tuple of (is_valid, validation_errors)
        - is_valid: True if data appears valid, False if garbage detected
        - validation_errors: List of semantic validation error messages
    """
    client, llm_enabled = _get_openai_client()
    
    if not llm_enabled:
        logger.warning("⚠️  LLM not available for semantic validation - skipping quality check")
        # If LLM is not available, we can't do semantic validation
        # Return True to allow processing (basic validation already passed)
        return True, []
    
    try:
        # Prepare data for validation
        validation_context = {
            "title": job_description.get("title", ""),
            "role": job_description.get("role", ""),
            "client_name": job_description.get("client_name", ""),
            "mandatory_skills": job_description.get("mandatory_skills", []),
            "preferred_skills": job_description.get("preferred_skills", []),
            "location": job_description.get("location", []),
            "jd_text": job_description.get("jd_text", "")[:500],  # Limit to first 500 chars
        }
        
        logger.info("🔍 Running LLM semantic validation...")
        
        from app.settings import settings
        response = client.chat.completions.create(
            model=settings.openai_model or "gpt-4o-mini",
            messages=[
                {"role": "system", "content": SEMANTIC_VALIDATION_PROMPT},
                {"role": "user", "content": f"Validate this requisition data:\n{json.dumps(validation_context, indent=2)}"}
            ],
            temperature=0.0,  # Deterministic validation
            max_tokens=500
        )
        
        # Parse LLM response
        llm_output = json.loads(response.choices[0].message.content)
        
        is_valid = llm_output.get("is_valid", True)
        validation_errors = llm_output.get("validation_errors", [])
        
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
