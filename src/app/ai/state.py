"""LangGraph state schema definition."""

from typing import Dict, List, Optional, TypedDict, Any
import numpy as np


class RequisitionInput(TypedDict):
    """Initial requisition input data."""

    request_id: str
    correlation_id: str
    job_description: Dict  # The original job_description payload


class ParsedJD(TypedDict):
    """Structured output from JD parsing, enriched with payload data."""

    normalized_title: str
    normalized_role: str
    extracted_mandatory_skills: List[str]
    extracted_preferred_skills: List[str]
    client_name: Optional[str]
    experience: Optional[Dict]
    expected_start_date: Optional[str]
    requisition_duration_month: Optional[int]
    priority: Optional[str]
    location: Optional[List[str]]
    work_mode: Optional[List[str]]
    jd_text: str
    certifications_required: Optional[List[str]]
    metadata: Optional[Dict]


class NormalizedSkills(TypedDict):
    """Skills mapped to skill_master IDs."""

    mandatory_skill_ids: List[str]  # Mapped to skill_master
    preferred_skill_ids: List[str]  # Mapped to skill_master
    mandatory_enriched: Optional[Dict[str, List[str]]]  # core_skill -> [terms]
    preferred_enriched: Optional[Dict[str, List[str]]]  # core_skill -> [terms]
    mandatory_alternatives: Optional[Dict[str, List[str]]]  # canonical_name -> [skill_ids]
    preferred_alternatives: Optional[Dict[str, List[str]]]  # canonical_name -> [skill_ids]


class CandidateScores(TypedDict):
    """Scoring and matching results for a candidate."""

    team_member_id: str
    skill_score: float
    experience_score: float
    certification_score: float
    availability_score: float
    final_score: float
    is_available: bool
    certifications: List[str]  # Candidate's actual certifications
    match_reasons: Dict  # Structured reasons for the match


class FinalResult(TypedDict):
    """Final formatted result for API response."""

    team_member_id: str
    profile_score: float
    fit_level: str
    availability_match: bool
    explanation: List[str]


class TokenMetrics(TypedDict):
    """Token tracking metrics per checkpoint."""
    
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    model: str


class LLMCallLog(TypedDict):
    """Record of a single LLM call for database logging."""

    agent_name: str
    prompt_name: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float


class PIIScrubMetadata(TypedDict):
    """PII scrubbing metadata (TASK-PII-102)."""
    
    detections: List[Dict]  # List of PII entities detected
    fields_scrubbed: List[str]  # Field names that were scrubbed
    total_pii_found: int  # Total count of PII instances


class GraphState(TypedDict):
    """Complete state object passed through the LangGraph execution.
    
    Version 1.1 (CR-PII-001):
    - Added pii_scrubbed flag (TASK-PII-103)
    - Added pii_scrub_metadata (TASK-PII-102)
    """

    # Initial input
    requisition_input: RequisitionInput

    # Populated by PII_Scrubber_Agent (NEW - TASK-PII-100)
    pii_scrubbed: Optional[bool]  # Flag indicating if PII scrubbing completed (TASK-PII-103)
    pii_scrub_metadata: Optional[PIIScrubMetadata]  # Scrubbing operation metadata (TASK-PII-102)

    # Populated by JD_Parsing_Agent
    parsed_jd: Optional[ParsedJD]

    # Populated by Skill_Normalization_Agent
    normalized_skills: Optional[NormalizedSkills]

    # Populated by Matching_Scoring_Agent
    candidate_scores: Optional[List[CandidateScores]]

    # Populated by Result_Aggregation_Agent
    final_results: Optional[List[FinalResult]]

    # Populated by Embedding_Agent
    embedding_result: Optional[Dict[str, Any]]  # Map of component names to vectors
    
    # Populated by RAG_Retrieval_Agent
    retrieved_candidates: Optional[List[Dict[str, Any]]]  # Candidates from vector search
    
    # Tracking metrics
    total_evaluated: Optional[int]
    total_qualified: Optional[int]
    
    # Token tracking (optional, for LLM observability)
    token_metrics: Optional[Dict[str, TokenMetrics]]
    llm_call_logs: Optional[List[LLMCallLog]]  # Individual LLM calls
    cumulative_tokens: Optional[int]
    cumulative_cost_usd: Optional[float]

    # To track errors
    error_message: Optional[str]
