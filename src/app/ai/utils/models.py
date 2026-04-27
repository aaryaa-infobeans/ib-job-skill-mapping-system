"""Data models for agent pipeline stages."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import numpy as np


@dataclass
class RequisitionData:
    """Parsed and structured requisition data."""
    structured_intent: str
    mandatory_skills: List[str]
    preferred_skills: List[str]
    experience_requirements: str
    jd_level: str
    location: str
    certifications: Optional[List[str]] = None
    raw_requisition: Optional[Dict[str, Any]] = None


@dataclass
class ValidationResult:
    """Result of requisition validation."""
    is_valid: bool
    reasons: List[str] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class NormalizedRequisition:
    """Requisition with normalized and expanded skills."""
    original_mandatory_skills: List[str]
    normalized_mandatory_skills: List[str]
    expanded_mandatory_terms: List[str]
    original_preferred_skills: List[str]
    normalized_preferred_skills: List[str]
    expanded_preferred_terms: List[str]
    original_certifications: List[str] = field(default_factory=list)
    normalized_certifications: List[str] = field(default_factory=list)
    expanded_certification_terms: List[str] = field(default_factory=list)
    original_requisition: RequisitionData = None


@dataclass
class EmbeddingResult:
    """Embedding vectors for JD components."""
    jd_level_vector: Optional[np.ndarray] = None
    mandatory_vector: Optional[np.ndarray] = None
    preferred_vector: Optional[np.ndarray] = None
    certification_vector: Optional[np.ndarray] = None
    full_jd_vector: Optional[np.ndarray] = None
    model: str = "models/embedding-001"
    
    def __post_init__(self):
        """Validate vector dimensions."""
        # Support both 3072 (OpenAI) and 768 (Gemma) or other common sizes
        expected_dim = 768 
        for name, vec in [
            ("jd_level", self.jd_level_vector),
            ("mandatory", self.mandatory_vector),
            ("preferred", self.preferred_vector),
            ("certification", self.certification_vector),
            ("full_jd", self.full_jd_vector)
        ]:
            if vec is not None and len(vec) not in [3072, 768]:
                raise ValueError(f"{name}_vector must be 768 or 3072-dimensional, got {len(vec)}")


@dataclass
class RAGCandidate:
    """Candidate retrieved from RAG search."""
    team_member_id: str
    final_similarity: float
    mandatory_similarity: float
    preferred_similarity: float
    jd_level_similarity: float
    certification_similarity: float = 0.0
    experience_in_months: Optional[int] = None
    profile_text: Optional[str] = None
    phase0_score_breakdown: Dict[str, float] = field(default_factory=dict)


@dataclass
class ScoringBreakdown:
    """Detailed breakdown of scoring components."""
    skills_matched: List[str] = field(default_factory=list)
    mandatory_matched: List[str] = field(default_factory=list)
    mandatory_missing: List[str] = field(default_factory=list)
    preferred_matched: List[str] = field(default_factory=list)
    preferred_missing: List[str] = field(default_factory=list)
    mandatory_score: float = 0.0
    preferred_score: float = 0.0
    certification_matched: List[str] = field(default_factory=list)
    certification_missing: List[str] = field(default_factory=list)
    certification_score: float = 0.0
    location_matched: bool = False
    location_score: float = 0.0
    work_mode_matched: bool = False
    work_mode_score: float = 0.0
    experience_matched: bool = False
    experience_score: float = 0.0
    semantic_similarity: float = 0.0
    jd_level_similarity: float = 0.0
    # Multi-stage scoring fields
    stage1_passed: bool = True
    role_type: str = "MID"
    qualification_reason: str = ""



@dataclass
class ScoringResult:
    """Scoring result for a candidate."""
    team_member_id: str
    match_score: float
    confidence: float
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    weighted_components: Dict[str, float] = field(default_factory=dict)
    detailed_breakdown: Optional[ScoringBreakdown] = None
    is_available: bool = True
    available_capacity: float = 100.0
    is_qualified: bool = True



@dataclass
class RankedCandidate:
    """Ranked candidate with justification."""
    team_member_id: str
    match_score: float
    narrative_justification: str
    rank_position: int


@dataclass
class RankedCandidateList:
    """Final ranking result."""
    candidates: List[RankedCandidate] = field(default_factory=list)
    total_evaluated: int = 0
    total_qualified: int = 0
