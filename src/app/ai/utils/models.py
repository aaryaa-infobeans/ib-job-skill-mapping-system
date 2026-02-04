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
    original_requisition: RequisitionData = None


@dataclass
class EmbeddingResult:
    """Embedding vectors for JD components."""
    jd_level_vector: np.ndarray  # 3072-dim
    mandatory_vector: np.ndarray  # 3072-dim
    preferred_vector: np.ndarray  # 3072-dim
    certification_vector: Optional[np.ndarray] = None  # 3072-dim
    model: str = "text-embedding-3-large"
    
    def __post_init__(self):
        """Validate vector dimensions."""
        for name, vec in [
            ("jd_level", self.jd_level_vector),
            ("mandatory", self.mandatory_vector),
            ("preferred", self.preferred_vector),
            ("certification", self.certification_vector)
        ]:
            if vec is not None and len(vec) != 3072:
                raise ValueError(f"{name}_vector must be 3072-dimensional, got {len(vec)}")


@dataclass
class RAGCandidate:
    """Candidate retrieved from RAG search."""
    team_member_id: str
    final_similarity: float
    mandatory_similarity: float
    preferred_similarity: float
    jd_level_similarity: float
    certification_similarity: float = 0.0
    profile_text: Optional[str] = None


@dataclass
class ScoringResult:
    """Scoring result for a candidate."""
    team_member_id: str
    match_score: float
    confidence: float
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    weighted_components: Dict[str, float] = field(default_factory=dict)


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
