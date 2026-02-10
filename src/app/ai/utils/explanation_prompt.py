"""Prompt templates for detailed explanation generation."""

DETAILED_EXPLANATION_PROMPT = """
You are an expert recruiter evaluating a candidate's fit for a job position. 
Generate a comprehensive, detailed explanation of why this candidate received their match score.

=== CANDIDATE PROFILE ===
Team Member ID: {team_member_id}
Overall Match Score: {final_score:.2%}
Fit Level: {fit_level}

=== REQUISITION REQUIREMENTS ===
Job Title: {job_title}
Job Role: {job_role}
Required Location: {job_location}

=== DETAILED CANDIDATE ASSESSMENT ===

**Mandatory Skills Match:**
- Required Skills: {mandatory_skills}
- Candidate's Skills: {candidate_mandatory_skills}
- Match Rate: {mandatory_score:.2%}
- Matched: {matched_mandatory_skills}
- Missing: {missing_mandatory_skills}

**Preferred Skills Match:**
- Preferred Skills: {preferred_skills}
- Candidate's Skills: {candidate_preferred_skills}
- Match Rate: {preferred_score:.2%}
- Matched: {matched_preferred_skills}
- Missing: {missing_preferred_skills}

**Experience Match:**
- Required Experience: {required_experience} months
- Candidate's Experience: {candidate_experience} months
- Experience Match Score: {experience_score:.2%}

**Certifications:**
- Required Certifications: {required_certifications}
- Candidate's Certifications: {candidate_certifications}
- Match Rate: {certification_score:.2%}
- Matched: {matched_certifications}
- Missing: {missing_certifications}

**Location/Work Mode:**
- Required Location: {job_location}
- Candidate's Location: {candidate_location}
- Work Mode Preference: {candidate_work_mode}
- Location Match Score: {location_score:.2%}
- Work Mode Match Score: {work_mode_score:.2%}

**JD Content & Role Match:**
- Overall Semantic Similarity: {semantic_similarity:.2%}
- Role Responsibility Match: {jd_level_similarity:.2%}

**Availability:**
- Start Date: {required_start_date}
- Duration: {requisition_duration} months
- Available Capacity: {available_capacity:.0f}%
- Is Available: {is_available}

=== YOUR TASK ===
Generate a detailed, professional explanation (3-5 sentences) that:
1. Summarizes the overall fit and how they rank
2. Highlights the key strengths (matched mandatory skills, relevant experience, etc.)
3. Clearly identifies critical gaps or missing skills
4. Explains how the different factors (skills, experience, certifications, location, work mode, JD similarity, availability) 
   contributed to their match score
5. Provides actionable context that helps the recruiter make a decision

Format the response as a clear, bullet-point explanation suitable for presentation to stakeholders.
Each point should reference specific skills/requirements and the candidate's corresponding qualifications.

=== RESPONSE FORMAT ===
Provide the explanation as a JSON object with this structure:
{{
    "summary": "Brief overall assessment (1-2 sentences)",
    "strengths": [
        "Key strength 1 with specific details",
        "Key strength 2 with specific details",
        "Key strength 3 with specific details"
    ],
    "gaps": [
        "Key gap 1 with specific details",
        "Key gap 2 with specific details"
    ],
    "fit_analysis": "Detailed explanation of how fit score was calculated (2-3 sentences)",
    "recommendation": "Brief recommendation for next steps"
}}
"""


def format_explanation_prompt(
    team_member_id: str,
    final_score: float,
    fit_level: str,
    job_title: str,
    job_role: str,
    job_location: str,
    mandatory_skills: list,
    candidate_mandatory_skills: list,
    matched_mandatory_skills: list,
    missing_mandatory_skills: list,
    mandatory_score: float,
    preferred_skills: list,
    candidate_preferred_skills: list,
    matched_preferred_skills: list,
    missing_preferred_skills: list,
    preferred_score: float,
    required_experience: int,
    candidate_experience: int,
    experience_score: float,
    required_certifications: list,
    candidate_certifications: list,
    matched_certifications: list,
    missing_certifications: list,
    certification_score: float,
    candidate_location: str,
    candidate_work_mode: str,
    location_score: float,
    work_mode_score: float,
    semantic_similarity: float,
    jd_level_similarity: float,
    required_start_date: str,
    requisition_duration: int,
    available_capacity: float,
    is_available: bool,
) -> str:
    """Format the detailed explanation prompt with candidate data."""
    
    return DETAILED_EXPLANATION_PROMPT.format(
        team_member_id=team_member_id,
        final_score=final_score,
        fit_level=fit_level,
        job_title=job_title,
        job_role=job_role,
        job_location=job_location,
        mandatory_skills=", ".join(mandatory_skills) if mandatory_skills else "None specified",
        candidate_mandatory_skills=", ".join(candidate_mandatory_skills) if candidate_mandatory_skills else "None",
        matched_mandatory_skills=", ".join(matched_mandatory_skills) if matched_mandatory_skills else "None",
        missing_mandatory_skills=", ".join(missing_mandatory_skills) if missing_mandatory_skills else "None",
        mandatory_score=mandatory_score,
        preferred_skills=", ".join(preferred_skills) if preferred_skills else "None specified",
        candidate_preferred_skills=", ".join(candidate_preferred_skills) if candidate_preferred_skills else "None",
        matched_preferred_skills=", ".join(matched_preferred_skills) if matched_preferred_skills else "None",
        missing_preferred_skills=", ".join(missing_preferred_skills) if missing_preferred_skills else "None",
        preferred_score=preferred_score,
        required_experience=required_experience,
        candidate_experience=candidate_experience,
        experience_score=experience_score,
        required_certifications=", ".join(required_certifications) if required_certifications else "None",
        candidate_certifications=", ".join(candidate_certifications) if candidate_certifications else "None",
        matched_certifications=", ".join(matched_certifications) if matched_certifications else "None",
        missing_certifications=", ".join(missing_certifications) if missing_certifications else "None",
        certification_score=certification_score,
        candidate_location=candidate_location,
        candidate_work_mode=candidate_work_mode,
        location_score=location_score,
        work_mode_score=work_mode_score,
        semantic_similarity=semantic_similarity,
        jd_level_similarity=jd_level_similarity,
        required_start_date=required_start_date,
        requisition_duration=requisition_duration,
        available_capacity=available_capacity,
        is_available="Yes" if is_available else "No",
    )
