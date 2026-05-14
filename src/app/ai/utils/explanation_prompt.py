"""Prompt templates for detailed explanation generation."""

DETAILED_EXPLANATION_PROMPT = """
You are an expert recruiter evaluating a candidate's fit for a job position. 
Generate a comprehensive, professional, and narrative evaluation of why this candidate received their match status based on the Professional Evaluation Ledger provided below.

=== CANDIDATE PROFILE ===
Team Member ID: {team_member_id}
Final Match Score: {final_score:.2%}
Role Category: {role_type}
Match Level: {fit_level} (MANDATORY: Mention this level explicitly in your summary and analysis)

=== REQUISITION REQUIREMENTS ===
Job Title: {job_title}
Job Role: {job_role}
Required Location: {job_location}

=== CANDIDATE MATCH DATA ===
1. Core Technical Requirements:
- Required: {mandatory_skills}
- Satisfaction: {mandatory_group_score:.2%}
- Matched: {matched_mandatory_skills}
- Missing: {missing_mandatory_skills}

2. Secondary Preferences:
- Matched: {matched_preferred_skills}
- Missing: {missing_preferred_skills}

3. Certifications:
- Matched: {matched_certs}
- Missing: {missing_certs}

4. Overall Intent Alignment: {semantic_score:.2%}

5. Location & Work Mode:
- Location Match: {location_matched_icon}
- Work Mode Match: {work_mode_matched_icon}

6. Experience & Context:
- Fit Boost: {context_boost:.4f}
- Professional Tenure: {candidate_experience} months (Note: 0 months means entry-level)

7. Deficiencies/Penalties: {penalties:.2f}

8. AI Confidence Analysis:
- Confidence Score: {ai_confidence:.2f}
- Narrative Reasoning: {ai_reasoning}

=== YOUR TASK ===
Generate a high-quality evaluation for a business user. Follow these STRICT rules:
1. **Match Level Consistency**: You MUST explicitly state the match level ({fit_level}) in your summary (e.g., "This is a {fit_level_lower} match...").
2. **Summary**: Write a 1-2 sentence professional summary. If experience is 0, describe as "early career" or "entry-level" (NEVER say "0.0 years").
3. **Analysis (No Raw Numbers)**: Explain *why* the candidate is a {fit_level_lower} match. Use business language, not technical score labels.

=== RESPONSE FORMAT ===
Return ONLY a valid JSON object:
{{
    "summary": "Professional summary including match level (min 20 chars)",
    "strengths": ["Business strength 1", "Business strength 2"],
    "gaps": ["Specific gap 1", "Specific gap 2"],
    "fit_analysis": "Narrative explanation of the {fit_level_lower} match alignment",
    "recommendation": "Clear recommendation"
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
    role_type: str,
    mandatory_group_score: float,
    semantic_score: float,
    context_boost: float,
    penalties: float,
    ai_confidence: float,
    ai_boost: float,
    ai_override_applied: bool,
    matched_mandatory_skills: list,
    missing_mandatory_skills: list,
    matched_preferred_skills: list,
    missing_preferred_skills: list,
    candidate_experience: int,
    is_available: bool,
    ai_reasoning: str,
    # New Phase 1 Ledger Fields
    matched_certs: list = None,
    missing_certs: list = None,
    location_matched: bool = False,
    work_mode_matched: bool = False
) -> str:
    """Format the Professional Evaluation prompt."""
    
    return DETAILED_EXPLANATION_PROMPT.format(
        team_member_id=team_member_id,
        final_score=final_score,
        fit_level=fit_level,
        fit_level_lower=fit_level.lower(),
        job_title=job_title,
        job_role=job_role,
        job_location=job_location,
        mandatory_skills=", ".join(mandatory_skills) if mandatory_skills else "Not explicitly listed",
        role_type=role_type,
        mandatory_group_score=mandatory_group_score,
        semantic_score=semantic_score,
        context_boost=context_boost,
        penalties=penalties,
        ai_confidence=ai_confidence,
        ai_boost=ai_boost,
        ai_override_icon="Applied" if ai_override_applied else "Not Applied",
        matched_mandatory_skills=", ".join(matched_mandatory_skills) if matched_mandatory_skills else "None",
        missing_mandatory_skills=", ".join(missing_mandatory_skills) if missing_mandatory_skills else "None",
        matched_preferred_skills=", ".join(matched_preferred_skills) if matched_preferred_skills else "None",
        missing_preferred_skills=", ".join(missing_preferred_skills) if missing_preferred_skills else "None",
        matched_certs=", ".join(matched_certs) if matched_certs else "None",
        missing_certs=", ".join(missing_certs) if missing_certs else "None",
        location_matched_icon="✅" if location_matched else "❌",
        work_mode_matched_icon="✅" if work_mode_matched else "❌",
        candidate_experience=candidate_experience,
        ai_reasoning=ai_reasoning
    )
