"""
CandidateSearchAgent — strangler-fig wrapper that merges the brownfield
embedding_node + rag_retrieval_node into a single agent.

These two nodes were separated in LangGraph only because the state dict
made it cheap to thread intermediate values through.  In the new
message-passing model they are a single concern: "find best-matching
candidates by semantic vector search."

Anti-corruption layer
---------------------
embedding_node writes np.ndarray vectors into state as plain Python lists
(for JSON serialisation).  rag_retrieval_node reads them back and re-wraps
as np.array.  This adapter handles that conversion.

TODO(agent-migration): Instantiate EmbeddingAgent with the injected
embedding_model / embedding_device from config instead of reading from
settings.py inside EmbeddingAgent.__init__.  Tracked in TASK-MIGRATE-005.

TODO(agent-migration): Replace SessionLocal() inside RAGRetrievalAgent
with an injected async session.  Tracked in TASK-MIGRATE-006.
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Dict, List, Optional

from pydantic import BaseModel, Field

from app.agent_framework.base_agent import BaseAgent
from app.agent_framework.health import HealthStatus
from app.agent_framework.message import Message, MessageMetadata
from app.agent_framework.registry import AgentRegistry


# ------------------------------------------------------------------ #
# I/O schemas
# ------------------------------------------------------------------ #

class SimilarityWeights(BaseModel):
    mandatory: float = 0.45
    preferred: float = 0.25
    jd_level: float = 0.15
    certification: float = 0.15


class CandidateSearchInput(BaseModel):
    request_id: str
    correlation_id: str
    # From SkillNormalizationAgent
    mandatory_skill_ids: List[str]
    preferred_skill_ids: List[str]
    mandatory_enriched: Dict[str, List[str]] = Field(default_factory=dict)
    preferred_enriched: Dict[str, List[str]] = Field(default_factory=dict)
    mandatory_alternatives: Dict[str, List[str]] = Field(default_factory=dict)
    preferred_alternatives: Dict[str, List[str]] = Field(default_factory=dict)
    normalized_certifications: List[str] = Field(default_factory=list)
    # Pass-through parsed JD fields
    normalized_title: str = ""
    normalized_role: str = ""
    mandatory_skills_raw: List[str] = Field(default_factory=list)
    preferred_skills_raw: List[str] = Field(default_factory=list)
    certifications_required: List[str] = Field(default_factory=list)
    experience: Optional[Dict[str, Any]] = None
    expected_start_date: Optional[str] = None
    duration_months: Optional[int] = None
    location: List[str] = Field(default_factory=list)
    work_mode: List[str] = Field(default_factory=list)
    jd_text: str = ""
    client_name: Optional[str] = None


class RetrievedCandidate(BaseModel):
    team_member_id: str
    final_similarity: float
    mandatory_similarity: float = 0.0
    preferred_similarity: float = 0.0
    jd_level_similarity: float = 0.0
    certification_similarity: float = 0.0
    profile_text: Optional[str] = None


class CandidateSearchOutput(BaseModel):
    request_id: str
    correlation_id: str
    candidates: List[RetrievedCandidate]
    retrieval_strategy: str = "multi-vector-weighted"
    # Pass-through fields for downstream scoring
    mandatory_skill_ids: List[str] = Field(default_factory=list)
    preferred_skill_ids: List[str] = Field(default_factory=list)
    mandatory_enriched: Dict[str, List[str]] = Field(default_factory=dict)
    preferred_enriched: Dict[str, List[str]] = Field(default_factory=dict)
    mandatory_alternatives: Dict[str, List[str]] = Field(default_factory=dict)
    preferred_alternatives: Dict[str, List[str]] = Field(default_factory=dict)
    certifications_required: List[str] = Field(default_factory=list)
    normalized_role: str = ""
    experience: Optional[Dict[str, Any]] = None
    expected_start_date: Optional[str] = None
    duration_months: Optional[int] = None
    location: List[str] = Field(default_factory=list)
    work_mode: List[str] = Field(default_factory=list)
    jd_text: str = ""


# ------------------------------------------------------------------ #
# Agent
# ------------------------------------------------------------------ #

@AgentRegistry.register
class CandidateSearchAgent(BaseAgent):
    """
    Generates JD embeddings and retrieves top-K candidates via pgvector ANN.

    Merges the brownfield embedding_node + rag_retrieval_node (strangler-fig).
    """

    agent_id = "candidate_search"
    version = "1.0.0"

    config_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "top_k":               {"type": "integer", "minimum": 1},
            "similarity_weights":  {"type": "object"},
            "min_similarity":      {"type": "number"},
        },
        "additionalProperties": True,
    }

    async def initialize(self, config: Dict[str, Any]) -> None:
        await self._base_initialize(config)
        self._top_k: int = config.get("top_k", 20)
        weights_cfg = config.get("similarity_weights", {})
        self._weights = SimilarityWeights(**weights_cfg)
        self._min_similarity: float = config.get("min_similarity", 0.30)
        self._log.info(
            "CandidateSearchAgent ready (top_k=%d, min_sim=%.2f)",
            self._top_k, self._min_similarity,
        )

    async def handle(self, message: Message) -> AsyncIterator[Message]:
        self._assert_initialized()

        inp = CandidateSearchInput.model_validate(message.payload)

        # ── Step 1: Build brownfield state fragment for embedding_node ─
        state = self._build_embedding_state(inp)

        # ── Step 2: Delegate to brownfield embedding_node ─────────────
        from app.ai.agents.embedding import embedding_node
        state = embedding_node(state)

        if state.get("error_message"):
            yield self._error_message(
                inp, message.trace_id,
                f"Embedding failed: {state['error_message']}",
                "candidate_search.embed_failed",
            )
            return

        # ── Step 3: Delegate to brownfield rag_retrieval_node ─────────
        from app.ai.agents.rag_retrieval import rag_retrieval_node
        state = rag_retrieval_node(state)

        if state.get("error_message"):
            yield self._error_message(
                inp, message.trace_id,
                f"RAG retrieval failed: {state['error_message']}",
                "candidate_search.rag_failed",
            )
            return

        # ── Step 4: Adapt brownfield output → typed output ────────────
        raw_candidates = state.get("retrieved_candidates") or []
        candidates = [
            RetrievedCandidate(
                team_member_id=c.get("team_member_id") or c.get("id", ""),
                final_similarity=float(c.get("final_similarity", 0.0)),
                mandatory_similarity=float(c.get("mandatory_similarity", 0.0)),
                preferred_similarity=float(c.get("preferred_similarity", 0.0)),
                jd_level_similarity=float(c.get("jd_level_similarity", 0.0)),
                certification_similarity=float(c.get("certification_similarity", 0.0)),
                profile_text=c.get("profile_text"),
            )
            for c in raw_candidates
        ]

        output = CandidateSearchOutput(
            request_id=inp.request_id,
            correlation_id=inp.correlation_id,
            candidates=candidates,
            mandatory_skill_ids=inp.mandatory_skill_ids,
            preferred_skill_ids=inp.preferred_skill_ids,
            mandatory_enriched=inp.mandatory_enriched,
            preferred_enriched=inp.preferred_enriched,
            mandatory_alternatives=inp.mandatory_alternatives,
            preferred_alternatives=inp.preferred_alternatives,
            certifications_required=inp.certifications_required or inp.normalized_certifications,
            normalized_role=inp.normalized_role,
            experience=inp.experience,
            expected_start_date=inp.expected_start_date,
            duration_months=inp.duration_months,
            location=inp.location,
            work_mode=inp.work_mode,
            jd_text=inp.jd_text,
        )

        yield Message.create(
            payload=output.model_dump(),
            metadata=MessageMetadata(
                source_agent=self.agent_id,
                message_type="candidate_search.complete",
                correlation_id=inp.correlation_id,
                request_id=inp.request_id,
            ),
            trace_id=message.trace_id,
        )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_embedding_state(inp: CandidateSearchInput) -> dict:
        """Build the minimal GraphState fragment both brownfield nodes expect."""
        return {
            "requisition_input": {
                "request_id": inp.request_id,
                "correlation_id": inp.correlation_id,
                "job_description": {
                    "mandatory_skills": inp.mandatory_skills_raw,
                    "preferred_skills": inp.preferred_skills_raw,
                    "certifications": inp.certifications_required,
                },
            },
            "parsed_jd": {
                "normalized_title": inp.normalized_title,
                "normalized_role": inp.normalized_role,
                "extracted_mandatory_skills": inp.mandatory_skills_raw,
                "extracted_preferred_skills": inp.preferred_skills_raw,
                "certifications_required": inp.certifications_required,
                "experience": inp.experience,
                "expected_start_date": inp.expected_start_date,
                "requisition_duration_month": inp.duration_months,
                "location": inp.location,
                "work_mode": inp.work_mode,
                "jd_text": inp.jd_text,
            },
            "normalized_skills": {
                "mandatory_skill_ids": inp.mandatory_skill_ids,
                "preferred_skill_ids": inp.preferred_skill_ids,
                "mandatory_enriched": inp.mandatory_enriched,
                "preferred_enriched": inp.preferred_enriched,
                "mandatory_alternatives": inp.mandatory_alternatives,
                "preferred_alternatives": inp.preferred_alternatives,
                "normalized_certifications": inp.normalized_certifications,
            },
            "error_message": None,
        }

    def _error_message(
        self,
        inp: CandidateSearchInput,
        trace_id: str,
        error: str,
        msg_type: str,
    ) -> Message:
        self._log.error(error, extra={"trace_id": trace_id})
        return Message.create(
            payload={"request_id": inp.request_id,
                     "correlation_id": inp.correlation_id, "error": error},
            metadata=MessageMetadata(
                source_agent=self.agent_id,
                message_type=msg_type,
                correlation_id=inp.correlation_id,
                request_id=inp.request_id,
            ),
            trace_id=trace_id,
        )

    async def health_check(self) -> HealthStatus:
        if not self._initialized:
            return HealthStatus.unavailable(self.agent_id, self.version, "Not initialized")
        try:
            from app.db.session import SessionLocal
            from app.db.models import TeamMemberEmbedding
            with SessionLocal() as db:
                db.query(TeamMemberEmbedding).limit(1).count()
            return HealthStatus.ok(self.agent_id, self.version,
                                   uptime_s=round(self.uptime_seconds, 1))
        except Exception as exc:
            return HealthStatus.degraded(
                self.agent_id, self.version,
                f"pgvector probe failed: {exc}",
            )

    async def shutdown(self, graceful: bool = True) -> None:
        self._initialized = False
