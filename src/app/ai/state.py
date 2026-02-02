"""LangGraph state schema definition."""

from typing import Dict, List, Optional, TypedDict


class RequisitionInput(TypedDict):
    """Initial requisition input data."""

    request_id: str
    correlation_id: str
    job_description: Dict  # The original job_description payload


class ParsedJD(TypedDict):
    """Structured output from JD parsing."""

    normalized_title: str
    normalized_role: str
    extracted_mandatory_skills: List[str]
    extracted_preferred_skills: List[str]


class NormalizedSkills(TypedDict):
    """Skills mapped to skill_master IDs."""

    mandatory_skill_ids: List[str]  # Mapped to skill_master
    preferred_skill_ids: List[str]  # Mapped to skill_master


class CandidateScores(TypedDict):
    """Scoring and matching results for a candidate."""

    team_member_id: str
    skill_score: float
    experience_score: float
    availability_score: float
    final_score: float
    is_available: bool
    match_reasons: Dict  # Structured reasons for the match


class FinalResult(TypedDict):
    """Final formatted result for API response."""

    team_member_id: str
    profile_score: float
    fit_level: str
    availability_match: bool
    explanation: List[str]


class GraphState(TypedDict):
    """Complete state object passed through the LangGraph execution."""

    # Initial input
    requisition_input: RequisitionInput

    # Populated by JD_Parsing_Agent
    parsed_jd: Optional[ParsedJD]

    # Populated by Skill_Normalization_Agent
    normalized_skills: Optional[NormalizedSkills]

    # Populated by Matching_Scoring_Agent
    candidate_scores: Optional[List[CandidateScores]]

    # Populated by Result_Aggregation_Agent
    final_results: Optional[List[FinalResult]]

    # To track errors
    error_message: Optional[str]
