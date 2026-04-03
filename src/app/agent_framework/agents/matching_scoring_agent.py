"""
MatchingScoringAgent — strangler-fig wrapper around the brownfield
matching_scoring_node (app.ai.agents.matching_scoring).

The brownfield node creates a SessionLocal() internally and receives a
full GraphState.  This adapter bridges that gap cleanly.

TODO(agent-migration): Replace the internal SessionLocal() with an
injected DB session.  Tracked in TASK-MIGRATE-007.

TODO(agent-migration): ScoringAgent reads weights directly from
settings.py.  Replace with config-injected weight profiles from
agents.yaml.  Tracked in TASK-MIGRATE-008.
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

class MatchingScoringInput(BaseModel):
    request_id: str
    correlation_id: str
    candidates: List[Dict[str, Any]]          # RetrievedCandidate dicts
    mandatory_skill_ids: List[str]
    preferred_skill_ids: List[str]
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


class ScoredCandidate(BaseModel):
    team_member_id: str
    skill_score: float = 0.0
    experience_score: float = 0.0
    certification_score: float = 0.0
    availability_score: float = 0.0
    final_score: float = 0.0
    is_available: bool = False
    certifications: List[str] = Field(default_factory=list)
    match_reasons: Dict[str, Any] = Field(default_factory=dict)
    score_breakdown: Dict[str, Any] = Field(default_factory=dict)


class MatchingScoringOutput(BaseModel):
    request_id: str
    correlation_id: str
    scored_candidates: List[ScoredCandidate]
    total_evaluated: int
    # Pass-through for explanation agent
    normalized_role: str = ""
    certifications_required: List[str] = Field(default_factory=list)
    mandatory_skill_ids: List[str] = Field(default_factory=list)
    preferred_skill_ids: List[str] = Field(default_factory=list)
    experience: Optional[Dict[str, Any]] = None
    location: List[str] = Field(default_factory=list)
    work_mode: List[str] = Field(default_factory=list)


# ------------------------------------------------------------------ #
# Agent
# ------------------------------------------------------------------ #

@AgentRegistry.register
class MatchingScoringAgent(BaseAgent):
    """
    Deterministic weighted scoring of candidates against the requisition.
    No LLM calls — pure DB reads + arithmetic.
    """

    agent_id = "matching_scoring"
    version = "1.0.0"

    config_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "role_weights":   {"type": "object"},
            "global_weights": {"type": "object"},
        },
        "additionalProperties": True,
    }

    async def initialize(self, config: Dict[str, Any]) -> None:
        await self._base_initialize(config)
        # TODO(agent-migration): load role_weights and global_weights from
        # config and pass to ScoringAgent instead of reading from settings.py.
        # Tracked in TASK-MIGRATE-008.
        self._log.info("MatchingScoringAgent ready (weights from settings.py until TASK-MIGRATE-008)")

    async def handle(self, message: Message) -> AsyncIterator[Message]:
        self._assert_initialized()

        inp = MatchingScoringInput.model_validate(message.payload)

        # ── Build brownfield GraphState fragment ──────────────────────
        state = self._build_state(inp)

        # ── Delegate to brownfield node ───────────────────────────────
        from app.ai.agents.matching_scoring import matching_scoring_node
        updated_state = matching_scoring_node(state)

        if updated_state.get("error_message"):
            self._log.error(
                "Matching scoring failed: %s", updated_state["error_message"],
                extra={"trace_id": message.trace_id},
            )
            yield Message.create(
                payload={
                    "request_id": inp.request_id,
                    "correlation_id": inp.correlation_id,
                    "error": updated_state["error_message"],
                },
                metadata=MessageMetadata(
                    source_agent=self.agent_id,
                    message_type="matching_scoring.failed",
                    correlation_id=inp.correlation_id,
                    request_id=inp.request_id,
                ),
                trace_id=message.trace_id,
            )
            return

        raw_scores = updated_state.get("candidate_scores") or []
        scored = [
            ScoredCandidate(
                team_member_id=c.get("team_member_id", ""),
                skill_score=float(c.get("skill_score", 0)),
                experience_score=float(c.get("experience_score", 0)),
                certification_score=float(c.get("certification_score", 0)),
                availability_score=float(c.get("availability_score", 0)),
                final_score=float(c.get("final_score", 0)),
                is_available=bool(c.get("is_available", False)),
                certifications=c.get("certifications", []),
                match_reasons=c.get("match_reasons", {}),
                score_breakdown=c.get("score_breakdown", {}),
            )
            for c in raw_scores
        ]

        output = MatchingScoringOutput(
            request_id=inp.request_id,
            correlation_id=inp.correlation_id,
            scored_candidates=scored,
            total_evaluated=updated_state.get("total_evaluated", len(scored)),
            normalized_role=inp.normalized_role,
            certifications_required=inp.certifications_required,
            mandatory_skill_ids=inp.mandatory_skill_ids,
            preferred_skill_ids=inp.preferred_skill_ids,
            experience=inp.experience,
            location=inp.location,
            work_mode=inp.work_mode,
        )

        yield Message.create(
            payload=output.model_dump(),
            metadata=MessageMetadata(
                source_agent=self.agent_id,
                message_type="matching_scoring.complete",
                correlation_id=inp.correlation_id,
                request_id=inp.request_id,
            ),
            trace_id=message.trace_id,
        )

    @staticmethod
    def _build_state(inp: MatchingScoringInput) -> dict:
        """Build minimal GraphState the brownfield node expects."""
        return {
            "requisition_input": {
                "request_id": inp.request_id,
                "correlation_id": inp.correlation_id,
                "job_description": {},
            },
            "parsed_jd": {
                "normalized_role": inp.normalized_role,
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
            },
            "retrieved_candidates": [c for c in inp.candidates],
            "error_message": None,
        }

    async def health_check(self) -> HealthStatus:
        if not self._initialized:
            return HealthStatus.unavailable(self.agent_id, self.version, "Not initialized")
        try:
            from app.db.session import SessionLocal
            from app.db.models import TeamMember
            with SessionLocal() as db:
                db.query(TeamMember).limit(1).count()
            return HealthStatus.ok(self.agent_id, self.version,
                                   uptime_s=round(self.uptime_seconds, 1))
        except Exception as exc:
            return HealthStatus.degraded(
                self.agent_id, self.version, f"DB probe failed: {exc}",
            )

    async def shutdown(self, graceful: bool = True) -> None:
        self._initialized = False
