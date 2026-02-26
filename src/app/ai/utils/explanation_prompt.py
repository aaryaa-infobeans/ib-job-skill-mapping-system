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

**3. Semantic Similarity & JD Alignment:**
- Semantic Similarity Score: {semantic_score:.2%}

**4. Context Support Boost:**
- Context Boost Applied: {context_boost:.4f} (Max 0.08)
- (Includes Experience, Certifications, Location, Work Mode)
- Candidate Experience: {candidate_experience} months

**5. Penalties & Deficiencies:**
- Total Penalties applied: {penalties:.2f}
- (e.g. Skill-family mismatch, Missing mandatory groups)

**6. AI Fit Confidence (AI Analysis):**
- AI Confidence Score: {ai_confidence:.2f}
- AI Score Boost: +{ai_boost:.4f}
- AI Semantic Override: {'Applied' if ai_override_applied else 'Not Applied'}
- AI Reasoning: {ai_reasoning}


=== YOUR TASK ===
Generate a detailed, professional explanation (3-5 sentences) that:
1. Summarizes the overall fit and status (Qualified/Disqualified)
2. Highlights how the Role Category influenced the weights
3. Explains specific strengths (e.g. Mandatory group satisfaction, AI boost)
4. Addresses any penalties or gaps (e.g. Why the score was reduced)
5. Provides a clear recommendation based on the ledger evidence.

=== RESPONSE FORMAT ===
Provide the explanation as a JSON object with this structure:
{{
    "summary": "Brief overall assessment (1-2 sentences)",
    "strengths": ["Strength 1", "Strength 2"],
    "gaps": ["Gap 1", "Gap 2"],
    "fit_analysis": "Detailed explanation of factors and ledger impact",
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
        ai_override_applied=ai_override_applied,
        matched_mandatory_skills=", ".join(matched_mandatory_skills) if matched_mandatory_skills else "None",
        missing_mandatory_skills=", ".join(missing_mandatory_skills) if missing_mandatory_skills else "None",
        matched_preferred_skills=", ".join(matched_preferred_skills) if matched_preferred_skills else "None",
        missing_preferred_skills=", ".join(missing_preferred_skills) if missing_preferred_skills else "None",
        candidate_experience=candidate_experience,
        ai_reasoning=ai_reasoning
    )

