"""
ResultAggregationAgent — strangler-fig wrapper around the brownfield
result_aggregation_node (app.ai.agents.result_aggregation).

This is the only fully pure agent — no DB, no LLM, no external deps.
It is also the closest to a clean rewrite candidate because the brownfield
node is simple (~50 lines) and has no hidden side effects.

TODO(agent-migration): After Phase 7 Redis wiring, write final results
to Redis cache from inside this agent (rather than in graph_executor.py).
Tracked in TASK-MIGRATE-010.
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

class ResultAggregationInput(BaseModel):
    request_id: str
    correlation_id: str
    scored_candidates: List[Dict[str, Any]]
    total_evaluated: int = 0
    normalized_role: str = ""
    certifications_required: List[str] = Field(default_factory=list)
    mandatory_skill_ids: List[str] = Field(default_factory=list)
    preferred_skill_ids: List[str] = Field(default_factory=list)
    experience: Optional[Dict[str, Any]] = None


class FinalResult(BaseModel):
    team_member_id: str
    profile_score: float
    fit_level: str
    availability_match: bool
    explanation: List[str] = Field(default_factory=list)


class ResultAggregationOutput(BaseModel):
    request_id: str
    correlation_id: str
    final_results: List[FinalResult]
    total_qualified: int
    total_evaluated: int


# ------------------------------------------------------------------ #
# Agent
# ------------------------------------------------------------------ #

@AgentRegistry.register
class ResultAggregationAgent(BaseAgent):
    """
    Assembles the final ranked result list.
    Pure transformation — no LLM calls, no DB writes.
    """

    agent_id = "result_aggregation"
    version = "1.0.0"

    config_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "qualification_threshold": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "fit_levels": {"type": "object"},
            "results_backend": {"type": "string", "enum": ["redis", "memory"]},
            "results_ttl_s":   {"type": "integer"},
        },
        "additionalProperties": True,
    }

    async def initialize(self, config: Dict[str, Any]) -> None:
        await self._base_initialize(config)
        self._qualification_threshold: float = config.get("qualification_threshold", 0.30)
        self._fit_levels: Dict[str, float] = config.get("fit_levels", {
            "STRONG_FIT": 0.75,
            "GOOD_FIT": 0.55,
            "PARTIAL_FIT": 0.30,
        })
        self._results_backend: str = config.get("results_backend", "memory")
        self._results_ttl_s: int = config.get("results_ttl_s", 3600)
        self._log.info(
            "ResultAggregationAgent ready (threshold=%.2f, backend=%s)",
            self._qualification_threshold, self._results_backend,
        )

    async def handle(self, message: Message) -> AsyncIterator[Message]:
        self._assert_initialized()

        inp = ResultAggregationInput.model_validate(message.payload)

        # ── Build brownfield state fragment ───────────────────────────
        state = {
            "requisition_input": {
                "request_id": inp.request_id,
                "correlation_id": inp.correlation_id,
                "job_description": {},
            },
            "candidate_scores": inp.scored_candidates,
            "total_evaluated": inp.total_evaluated,
            "error_message": None,
        }

        # ── Delegate to brownfield node ───────────────────────────────
        from app.ai.agents.result_aggregation import result_aggregation_node
        updated_state = result_aggregation_node(state)

        raw_results = updated_state.get("final_results") or []
        final_results = [
            FinalResult(
                team_member_id=r.get("team_member_id", ""),
                profile_score=float(r.get("profile_score", 0.0)),
                fit_level=r.get("fit_level", "LOW"),
                availability_match=bool(r.get("availability_match", False)),
                explanation=r.get("explanation", []),
            )
            for r in raw_results
        ]

        total_qualified = updated_state.get("total_qualified", len(final_results))

        # ── Write to results cache ────────────────────────────────────
        # TODO(agent-migration): replace in-memory dict with Redis when
        # backend="redis" and Phase 7 Redis wiring is complete.
        # Tracked in TASK-MIGRATE-010.
        from app.ai.results_cache import store_results
        store_results(
            inp.correlation_id,
            [r.model_dump() for r in final_results],
            metrics={
                "total_evaluated": inp.total_evaluated,
                "total_qualified": total_qualified,
            },
        )

        output = ResultAggregationOutput(
            request_id=inp.request_id,
            correlation_id=inp.correlation_id,
            final_results=final_results,
            total_qualified=total_qualified,
            total_evaluated=inp.total_evaluated,
        )

        yield Message.create(
            payload=output.model_dump(),
            metadata=MessageMetadata(
                source_agent=self.agent_id,
                message_type="result_aggregation.complete",
                correlation_id=inp.correlation_id,
                request_id=inp.request_id,
            ),
            trace_id=message.trace_id,
        )

    async def health_check(self) -> HealthStatus:
        return HealthStatus.ok(
            self.agent_id, self.version,
            uptime_s=round(self.uptime_seconds, 1),
            backend=self._results_backend if self._initialized else "n/a",
        )

    async def shutdown(self, graceful: bool = True) -> None:
        self._initialized = False
