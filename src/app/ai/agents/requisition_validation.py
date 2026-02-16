"""Requisition validation helper for the parsing agent."""

import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


def validate_requisition_input(job_description: Dict) -> Tuple[bool, List[str]]:
    """
    Validate requisition input before processing.
    
    This function performs business logic validation on the requisition
    to catch invalid or unrealistic requests early, before expensive LLM processing.
    
    Args:
        job_description: Job description dict from requisition_input
        
    Returns:
        Tuple of (is_valid, reasons)
        - is_valid: True if validation passes, False otherwise
        - reasons: List of validation error messages
    """
    reasons = []
    
    # 1. Check JD text
    jd_text = job_description.get("jd_text", "").strip()
    if not jd_text or len(jd_text) < 50:
        reasons.append("Job description text is too short or empty (minimum 50 characters required)")
    
    # 2. Check title and role
    title = job_description.get("title", "").strip()
    role = job_description.get("role", "").strip()
    
    if not title or title.lower() == "unknown":
        reasons.append("Job title is missing or invalid")
    
    if not role or role.lower() == "unknown":
        reasons.append("Job role is missing or invalid")
    
    # 3. Check mandatory skills OR detailed JD text
    mandatory_skills = job_description.get("mandatory_skills", [])
    if not mandatory_skills and len(jd_text) < 200:
        reasons.append("Either mandatory skills must be provided OR job description must be detailed (at least 200 characters)")
    
    # 4. Validate skill count (warning for too many)
    if mandatory_skills and len(mandatory_skills) > 15:
        reasons.append(f"Unrealistic number of mandatory skills: {len(mandatory_skills)} (maximum recommended: 15)")
    
    # 5. Check experience requirements
    experience = job_description.get("experience")
    if experience:
        min_months = experience.get("min_months")
        max_months = experience.get("max_months")
        
        # Check for unrealistic experience
        if min_months is not None and min_months > 360:  # 30 years
            reasons.append(f"Unrealistic minimum experience: {min_months} months (maximum realistic: 360 months/30 years)")
        
        if max_months is not None and max_months > 360:  # 30 years
            reasons.append(f"Unrealistic maximum experience: {max_months} months (maximum realistic: 360 months/30 years)")
        
        # Check min <= max
        if min_months is not None and max_months is not None:
            if min_months > max_months:
                reasons.append(f"Invalid experience range: min ({min_months}) > max ({max_months})")
    
    # 6. Check location
    location = job_description.get("location", [])
    if not location or (isinstance(location, list) and len(location) == 0):
        reasons.append("Location is required and cannot be empty")
    
    # 7. Check work mode
    work_mode = job_description.get("work_mode", [])
    if not work_mode or (isinstance(work_mode, list) and len(work_mode) == 0):
        reasons.append("Work mode is required and cannot be empty")
    
    # 8. Check client name
    client_name = job_description.get("client_name", "").strip()
    if not client_name:
        reasons.append("Client name is required")
    
    # Determine if valid
    is_valid = len(reasons) == 0
    
    if is_valid:
        logger.info("✅ Requisition validation passed")
    else:
        logger.warning(f"❌ Requisition validation failed with {len(reasons)} error(s)")
        for reason in reasons:
            logger.warning(f"  - {reason}")
    
    return is_valid, reasons
