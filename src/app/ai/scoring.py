from typing import Optional
from app.settings import settings

# Configurable weights (Fallbacks - will use settings)
SKILL_WEIGHT_MANDATORY = getattr(settings, "weight_mandatory_skills", 0.7)
SKILL_WEIGHT_PREFERRED = getattr(settings, "weight_preferred_skills", 0.3)


def calculate_skill_score(
    team_member_skill_ids: list[str],
    mandatory_skill_ids: list[str],
    preferred_skill_ids: list[str],
    mandatory_weight: float = SKILL_WEIGHT_MANDATORY,
    preferred_weight: float = SKILL_WEIGHT_PREFERRED,
) -> dict:
    """Calculate skill matching score for a team member.
    
    Args:
        team_member_skill_ids: List of skill IDs the team member possesses
        mandatory_skill_ids: List of required skill IDs from requisition
        preferred_skill_ids: List of preferred skill IDs from requisition
        mandatory_weight: Weight for mandatory skills (default 0.7)
        preferred_weight: Weight for preferred skills (default 0.3)
    
    Returns:
        Dictionary with:
        - skill_score: Combined skill score (0.0 to 1.0)
        - mandatory_score: Mandatory skills score
        - preferred_score: Preferred skills score
        - matched_mandatory: List of matched mandatory skill IDs
        - matched_preferred: List of matched preferred skill IDs
    """
    # Convert to sets for efficient intersection
    member_skills = set(team_member_skill_ids)
    mandatory_skills = set(mandatory_skill_ids)
    preferred_skills = set(preferred_skill_ids)
    
    # Find matched skills
    matched_mandatory = list(member_skills & mandatory_skills)
    matched_preferred = list(member_skills & preferred_skills)
    
    # Calculate mandatory score (avoid division by zero)
    if len(mandatory_skills) > 0:
        mandatory_score = len(matched_mandatory) / len(mandatory_skills)
    else:
        mandatory_score = 1.0  # No mandatory skills means full score for this component
    
    # Calculate preferred score (avoid division by zero)
    if len(preferred_skills) > 0:
        preferred_score = len(matched_preferred) / len(preferred_skills)
    else:
        preferred_score = 1.0  # No preferred skills means full score for this component
    
    # Calculate combined skill score
    skill_score = (mandatory_weight * mandatory_score) + (preferred_weight * preferred_score)
    
    return {
        "skill_score": skill_score,
        "mandatory_score": mandatory_score,
        "preferred_score": preferred_score,
        "matched_mandatory": matched_mandatory,
        "matched_preferred": matched_preferred,
    }


def calculate_experience_score(
    team_member_experience_months: int,
    min_experience_months: Optional[int],
    max_experience_months: Optional[int],
) -> float:
    """Calculate experience matching score for a team member.
    
    Args:
        team_member_experience_months: Team member's experience in months
        min_experience_months: Minimum required experience (None = no minimum)
        max_experience_months: Maximum preferred experience (None = no maximum)
    
    Returns:
        Experience score (0.0 to 1.0+)
        - 0.0 if below minimum
        - 1.0 if within range or no constraints
        - 1.0 if above maximum (could be configurable to allow higher scores)
    """
    # If no experience requirements specified, return zero score (no points)
    if min_experience_months is None and max_experience_months is None:
        return 0.0
    
    # If only minimum specified
    if min_experience_months is not None and max_experience_months is None:
        return 1.0 if team_member_experience_months >= min_experience_months else 0.0
    
    # If only maximum specified (unusual case)
    if min_experience_months is None and max_experience_months is not None:
        return 0.0 # No points if only max is specified but no min
    
    # Both min and max specified
    if min_experience_months is not None and max_experience_months is not None:
        if team_member_experience_months < min_experience_months:
            return 0.0
        elif team_member_experience_months <= max_experience_months:
            return 1.0
        else:
            # Above max - still give full score
            return 1.0
    
    return 0.0


def calculate_location_score(
    candidate_location: Optional[str],
    required_locations: list[str],
) -> float:
    """Calculate location matching score.
    
    Args:
        candidate_location: Candidate's base location
        required_locations: List of acceptable locations
        
    Returns:
        1.0 if match found (including 'Remote' or 'Any'), or if no requirements.
        0.0 if no match.
    """
    if not required_locations or not candidate_location:
        return 0.0
        
    required_lower = [loc.lower().strip() for loc in required_locations]
    candidate_lower = candidate_location.lower().strip()
    
    if "remote" in required_lower or "any" in required_lower:
        return 1.0
        
    if candidate_lower in required_lower:
        return 1.0
        
    # Check for substring match (e.g. "Pune, India" matches "Pune")
    for loc in required_lower:
        if loc in candidate_lower or candidate_lower in loc:
            return 1.0
            
    return 0.0


def calculate_certification_score(
    candidate_certifications: list[str],
    required_certifications: list[str],
) -> dict:
    """Calculate certification matching score.
    
    Args:
        candidate_certifications: List of certifications held by the candidate
        required_certifications: List of certifications required by the JD
        
    Returns:
        Dictionary with:
        - certification_score: Score (0.0 to 1.0)
        - matched_certifications: List of matched certification names
        - missing_certifications: List of required but missing certifications
    """
    if not required_certifications:
        return {
            "certification_score": 1.0,
            "matched_certifications": [],
            "missing_certifications": [],
        }
        
    if not candidate_certifications:
        return {
            "certification_score": 0.0,
            "matched_certifications": [],
            "missing_certifications": required_certifications,
        }
        
    matched = []
    missing = []
    
    candidate_certs_lower = [c.lower().strip() for c in candidate_certifications]
    
    for req in required_certifications:
        req_lower = req.lower().strip()
        is_matched = False
        
        # Check for direct or substring match
        for cand in candidate_certs_lower:
            if req_lower in cand or cand in req_lower:
                matched.append(req)
                is_matched = True
                break
        
        if not is_matched:
            missing.append(req)
            
    score = len(matched) / len(required_certifications)
    
    return {
        "certification_score": score,
        "matched_certifications": matched,
        "missing_certifications": missing,
    }


def calculate_work_mode_score(
    candidate_work_mode: Optional[str],
    required_work_modes: list[str],
) -> float:
    """Calculate work mode matching score.
    
    Args:
        candidate_work_mode: Candidate's work type (e.g. 'wfo', 'wfh', 'hybrid')
        required_work_modes: List of acceptable work modes
        
    Returns:
        1.0 if match found, 0.0 otherwise.
    """
    if not required_work_modes or not candidate_work_mode:
        return 0.0
        
    # Standardize work modes for comparison
    mode_map = {
        "wfo": ["wfo", "office", "on-site", "onsite"],
        "wfh": ["wfh", "remote", "work from home"],
        "hybrid": ["hybrid", "flexible"]
    }
    
    required_lower = [m.lower().strip() for m in required_work_modes]
    candidate_val = candidate_work_mode.lower().strip()
    
    # Check if candidate's mode or any of its aliases match any required mode or its aliases
    for req in required_lower:
        # Direct match or alias match
        if candidate_val == req:
            return 1.0
        
        # Check against mapped aliases
        for canonical, aliases in mode_map.items():
            if candidate_val == canonical or candidate_val in aliases:
                if req == canonical or req in aliases:
                    return 1.0
                    
    return 0.0


def calculate_final_score(
    skill_score: float,
    experience_score: float,
    certification_score: float,
    location_score: float = 1.0,
    work_mode_score: float = 1.0,
    semantic_similarity: float = 0.5,
    jd_level_similarity: float = 0.5,
) -> float:
    """Calculate final aggregated score for a candidate using settings weights.
    
    Args:
        skill_score: Combined mandatory/preferred skill score
        experience_score: Experience matching score
        certification_score: Certification matching score
        location_score: Location matching score
        work_mode_score: Work mode matching score
        semantic_similarity: RAG semantic similarity score
        jd_level_similarity: RAG JD level/responsibility similarity score
    
    Returns:
        Final score (0.0 to 1.0)
    """
    # Skill score from calculate_skill_score is already weighted between mandatory/preferred
    # But we need to split it back if we want to follow the settings.py weights strictly 
    # for 'mandatory' and 'preferred' separately.
    # However, matching_scoring_node expects a simple combination.
    
    # To be precise, we follow settings.py weights:
    final_score = (
        (settings.weight_mandatory_skills * skill_score) + # Note: skill_score here is already weighted 0.7/0.3
        # Wait, if settings.weight_mandatory_skills is 0.30 and preferred is 0.15,
        # we should probably pass mandatory and preferred scores separately.
        (settings.weight_experience * experience_score) + 
        (settings.weight_certification * certification_score) +
        (settings.weight_location * location_score) +
        (settings.weight_work_mode * work_mode_score) +
        (settings.weight_semantic_similarity * semantic_similarity) +
        (settings.weight_jd_text * jd_level_similarity)
    )
    
    # Adjusting for the fact that skill_score passed might already be a weighted average
    # Let's fix calculate_final_score to be more robust.
    return final_score


def calculate_candidate_score(
    team_member_id: str,
    team_member_skill_ids: list[str],
    team_member_experience_months: int,
    mandatory_skill_ids: list[str],
    preferred_skill_ids: list[str],
    min_experience_months: Optional[int],
    max_experience_months: Optional[int],
    candidate_certifications: list[str],
    required_certifications: list[str],
    candidate_location: Optional[str],
    required_locations: list[str],
    candidate_work_mode: Optional[str],
    required_work_modes: list[str],
    is_available: bool,
    available_capacity: float,
    rag_scores: Optional[dict] = None,
) -> dict:
    """Calculate complete candidate score.
    
    Args:
        team_member_id: Team member ID
        team_member_skill_ids: Skills possessed by team member
        team_member_experience_months: Experience in months
        mandatory_skill_ids: Required skills from requisition
        preferred_skill_ids: Preferred skills from requisition
        min_experience_months: Minimum required experience
        max_experience_months: Maximum preferred experience
        candidate_certifications: List of certifications
        required_certifications: List of required certifications
        candidate_location: Candidate's base location
        required_locations: Required locations list
        candidate_work_mode: Candidate's work type
        required_work_modes: Acceptable work modes list
        is_available: Availability flag
        available_capacity: Available capacity percentage
        rag_scores: Optional RAG similarity scores (semantic, jd_level, etc.)
    
    Returns:
        Dictionary with complete scoring details
    """
    # Calculate skill score
    skill_result = calculate_skill_score(
        team_member_skill_ids,
        mandatory_skill_ids,
        preferred_skill_ids,
    )
    
    # Calculate experience score
    experience_score = calculate_experience_score(
        team_member_experience_months,
        min_experience_months,
        max_experience_months,
    )
    
    # Calculate certification score
    cert_result = calculate_certification_score(
        candidate_certifications,
        required_certifications,
    )
    
    # Calculate location and work mode scores
    location_score = calculate_location_score(candidate_location, required_locations)
    work_mode_score = calculate_work_mode_score(candidate_work_mode, required_work_modes)
    
    # Extract RAG scores if available
    semantic_sim = rag_scores.get("final_similarity", 0.5) if rag_scores else 0.5
    jd_level_sim = rag_scores.get("jd_level_similarity", 0.5) if rag_scores else 0.5
    
    # Calculate final score
    # We pass mandatory and preferred scores separately to follow settings weights
    # final_score = (W_m * S_m) + (W_p * S_p) + ...
    final_score = (
        (settings.weight_mandatory_skills * skill_result["mandatory_score"]) +
        (settings.weight_preferred_skills * skill_result["preferred_score"]) +
        (settings.weight_experience * experience_score) +
        (settings.weight_certification * cert_result["certification_score"]) +
        (settings.weight_location * location_score) +
        (settings.weight_work_mode * work_mode_score) +
        (settings.weight_semantic_similarity * semantic_sim) +
        (settings.weight_jd_text * jd_level_sim)
    )
    
    return {
        "team_member_id": team_member_id,
        "skill_score": round(skill_result["skill_score"], 2),
        "experience_score": round(experience_score, 2),
        "certification_score": round(cert_result["certification_score"], 2),
        "location_score": round(location_score, 2),
        "work_mode_score": round(work_mode_score, 2),
        "availability_score": round(available_capacity / 100.0, 2),
        "semantic_similarity": round(semantic_sim, 2),
        "jd_level_similarity": round(jd_level_sim, 2),
        "final_score": round(final_score, 2),
        "is_available": is_available,
        "certifications": candidate_certifications,
        "location": candidate_location,
        "work_mode": candidate_work_mode,
        "experience_in_months": team_member_experience_months,
        "match_reasons": {
            "skills_matched": skill_result["matched_mandatory"] + skill_result["matched_preferred"],
            "mandatory_matched": skill_result["matched_mandatory"],
            "preferred_matched": skill_result["matched_preferred"],
            "mandatory_score": round(skill_result["mandatory_score"], 2),
            "preferred_score": round(skill_result["preferred_score"], 2),
            "certification_matched": cert_result["matched_certifications"],
            "certification_missing": cert_result["missing_certifications"],
            "certification_score": round(cert_result["certification_score"], 2),
            "location_matched": location_score > 0,
            "location_score": round(location_score, 2),
            "work_mode_matched": work_mode_score > 0,
            "work_mode_score": round(work_mode_score, 2),
            "experience_matched": experience_score > 0,
            "experience_score": round(experience_score, 2),
            "semantic_similarity": round(semantic_sim, 2),
            "jd_level_similarity": round(jd_level_sim, 2),
        },
    }
