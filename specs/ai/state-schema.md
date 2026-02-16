# LangGraph State Schema

**Version:** 1.1  
**Modified By:** CR_PII_scrubber (CR-PII-001)  
**Last Updated:** 2026-02-16  

## 1. Purpose
This document defines the schema for the state object that is passed through the LangGraph execution graph. This state is mutated by each agent/node in the pipeline.

## 2. State Schema
The state will be a Pydantic or TypedDict object with the following structure. This ensures type safety and clarity throughout the process.

```python
from typing import List, Dict, TypedDict, Optional

class PIIScrubMetadata(TypedDict):  # NEW: CR-PII-001
    """Metadata about PII scrubbing operations."""
    scrubbed: bool
    pii_detected: List[Dict]  # [{"type": "email", "confidence": 1.0, "action": "hash"}]
    rule_version: str
    scrubber_version: str
    timestamp: str
    audit_id: str  # Reference to pii_scrub_audit.audit_id

class RequisitionInput(TypedDict):
    request_id: str
    correlation_id: str
    job_description: Dict # The original job_description payload
    pii_scrub_metadata: Optional[PIIScrubMetadata]  # NEW: CR-PII-001
    # ... other metadata from the original request

class ParsedJD(TypedDict):
    normalized_title: str
    normalized_role: str
    extracted_mandatory_skills: List[str]
    extracted_preferred_skills: List[str]

class NormalizedSkills(TypedDict):
    mandatory_skill_ids: List[str] # Mapped to skill_master
    preferred_skill_ids: List[str] # Mapped to skill_master

class CandidateScores(TypedDict):
    team_member_id: str
    skill_score: float
    experience_score: float
    availability_score: float
    final_score: float
    is_available: bool
    match_reasons: Dict # Structured reasons for the match

class FinalResult(TypedDict):
    team_member_id: str
    profile_score: float
    fit_level: str
    availability_match: bool
    explanation: List[str]

class GraphState(TypedDict):
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
```

## 3. State Lifecycle

1.  **Initialization**: The graph is initialized with the `requisition_input` state populated from the API request (FR-1).
2.  **`PII_Scrubber_Agent` (NEW: CR-PII-001)**: First node (Node 0) scrubs all PII from requisition data. Populates `pii_scrub_metadata` with scrubbing details and audit trail reference. Validates all data is scrubbed before proceeding.
3.  **`JD_Parsing_Agent`**: Populates the `parsed_jd` field. Receives only PII-scrubbed data.
3.  **`Skill_Normalization_Agent`**: Populates the `normalized_skills` field.
4.  **`Availability_Evaluation_Agent` & `Matching_Scoring_Agent`**: These deterministic nodes work together to populate the `candidate_scores` list. They retrieve team member data from the database and perform all calculations.
5.  **`Explanation_Generation_Agent`**: Takes the `candidate_scores` (specifically the `match_reasons`) and generates the human-readable `explanation` strings.
6.  **`Result_Aggregation_Agent`**: Consumes `candidate_scores` and the generated explanations to create the final, clean `final_results` list, which matches the API response schema (FR-2).
7.  **Termination**: The final state, including the `final_results`, is persisted or passed back for the API response.

This structured state ensures that data flows through the pipeline in a predictable and auditable manner. The full state object at each step will be saved in the `langgraph_checkpoints` table.
