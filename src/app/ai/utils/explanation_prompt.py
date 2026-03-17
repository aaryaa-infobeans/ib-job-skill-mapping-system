"""Prompt templates for detailed explanation generation."""

DETAILED_EXPLANATION_PROMPT = """
You are an expert recruiter evaluating a candidate's fit for a job position. 
Generate a comprehensive, detailed explanation of why this candidate received their match score based on the Phase 1 Agentic Scoring Ledger.

=== CANDIDATE PROFILE ===
Team Member ID: {team_member_id}
Final Agentic Score: {final_score:.2%}
Role Category: {role_type}
Fit Level: {fit_level}

=== REQUISITION REQUIREMENTS ===
Job Title: {job_title}
Job Role: {job_role}
Required Location: {job_location}

=== PHASE 1 SCORING LEDGER ===

**1. Mandatory Skills Grouping:**
- Required Skills: {mandatory_skills}
- Group Satisfaction Rate: {mandatory_group_score:.2%}
- Matched Skills: {matched_mandatory_skills}
- Missing Skills: {missing_mandatory_skills}

**2. Preferred Skills:**
- Matched Preferred: {matched_preferred_skills}
- Missing Preferred: {missing_preferred_skills}

**3. Certifications:**
- Matched Certs: {matched_certs}
- Missing Certs: {missing_certs}

**4. Semantic Similarity & JD Alignment:**
- Semantic Similarity Score: {semantic_score:.2%}

**5. Location & Work Mode Fit:**
- Location Matched: {location_matched_icon}
- Work Mode Matched: {work_mode_matched_icon}

**6. Context Support Boost:**
- Context Boost Applied: {context_boost:.4f}
- Candidate Experience: {candidate_experience} months

**7. Penalties & Deficiencies:**
- Total Penalties applied: {penalties:.2f}

**8. AI Fit Confidence (AI Analysis):**
- AI Confidence Score: {ai_confidence:.2f}
- AI Score Boost: +{ai_boost:.4f}
- AI Semantic Override: {ai_override_icon}
- AI Reasoning: {ai_reasoning}


=== YOUR TASK ===
Generate a professional, structured evaluation (3-5 sentences) that:
1. Summarizes the overall fit and qualification status.
2. Performs a parameter-by-parameter analysis based ONLY on the provided ledger:
   - Skills (Mandatory & Preferred): How well the candidate's skill set aligns with requirements.
   - Experience: Whether the candidate's tenure meets expectations.
   - Location & Work Mode: Compatibility with the requested work arrangement.
   - Certifications: Presence or absence of REQUIRED credentials (only mention those listed in REQUISITION REQUIREMENTS).
3. Highlights specific strengths as "Matches" and critical deficiencies as "Gaps".
4. Provides a clear, evidence-based recommendation derived strictly from the scoring ledger.
   - IMPORTANT: Do not assume or hallucinate requirements not explicitly listed in the REQUISITION REQUIREMENTS or PHASE 1 SCORING LEDGER sections above.

=== RESPONSE FORMAT ===
Provide the explanation as a JSON object with this structure:
{{
    "summary": "Brief overall assessment (1-2 sentences)",
    "strengths": ["Strength 1", "Strength 2"],
    "gaps": ["Gap 1", "Gap 2"],
    "fit_analysis": "Concise explanation of factors and ledger impact",
    "recommendation": "Brief recommendation"
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
    """Format the Phase 1 Agentic Scoring Ledger prompt."""
    
    return DETAILED_EXPLANATION_PROMPT.format(
        team_member_id=team_member_id,
        final_score=final_score,
        fit_level=fit_level,
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

