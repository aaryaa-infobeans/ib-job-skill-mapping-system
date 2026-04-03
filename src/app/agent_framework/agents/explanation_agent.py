"""
ExplanationAgent — strangler-fig wrapper around the brownfield
explanation_generation_node (app.ai.agents.explanation_generation).

TODO(agent-migration): Replace module-level llm_client singleton with
an injected LLMClient instance.  Tracked in TASK-MIGRATE-009.
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

class ExplanationInput(BaseModel):
    request_id: str
    correlation_id: str
    scored_candidates: List[Dict[str, Any]]
    total_evaluated: int = 0
    # Job context for the prompt
    normalized_role: str = ""
    certifications_required: List[str] = Field(default_factory=list)
    mandatory_skill_ids: List[str] = Field(default_factory=list)
    preferred_skill_ids: List[str] = Field(default_factory=list)
    experience: Optional[Dict[str, Any]] = None
    location: List[str] = Field(default_factory=list)
    work_mode: List[str] = Field(default_factory=list)


class ExplanationOutput(BaseModel):
    request_id: str
    correlation_id: str
    # scored_candidates with 'explanation' field injected
    scored_candidates: List[Dict[str, Any]]
    total_evaluated: int = 0
    normalized_role: str = ""
    certifications_required: List[str] = Field(default_factory=list)
    mandatory_skill_ids: List[str] = Field(default_factory=list)
    preferred_skill_ids: List[str] = Field(default_factory=list)
    experience: Optional[Dict[str, Any]] = None


# ------------------------------------------------------------------ #
# Agent
# ------------------------------------------------------------------ #

@AgentRegistry.register
class ExplanationAgent(BaseAgent):
    """
    Generates plain-language explanations for top-N scored candidates.
    Wraps the brownfield explanation_generation_node (strangler-fig).
    """

    agent_id = "explanation_generation"
    version = "1.0.0"

    config_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "llm_model":        {"type": ["string", "null"]},
            "temperature":      {"type": "number"},
            "max_tokens":       {"type": "integer"},
            "max_explanations": {"type": "integer", "minimum": 1},
        },
        "additionalProperties": True,
    }

    async def initialize(self, config: Dict[str, Any]) -> None:
        await self._base_initialize(config)
        self._max_explanations: int = config.get("max_explanations", 2)
        self._log.info(
            "ExplanationAgent ready (max_explanations=%d)", self._max_explanations
        )

    async def handle(self, message: Message) -> AsyncIterator[Message]:
        self._assert_initialized()

        inp = ExplanationInput.model_validate(message.payload)

        # ── Build brownfield state fragment ───────────────────────────
        state = {
            "requisition_input": {
                "request_id": inp.request_id,
                "correlation_id": inp.correlation_id,
                "job_description": {},
            },
            "parsed_jd": {
                "normalized_role": inp.normalized_role,
                "certifications_required": inp.certifications_required,
                "experience": inp.experience,
                "location": inp.location,
                "work_mode": inp.work_mode,
                "extracted_mandatory_skills": inp.mandatory_skill_ids,
                "extracted_preferred_skills": inp.preferred_skill_ids,
            },
            "candidate_scores": inp.scored_candidates,
            "error_message": None,
        }

        # ── Delegate to brownfield node ───────────────────────────────
        from app.ai.agents.explanation_generation import explanation_generation_node
        updated_state = explanation_generation_node(state)

        # explanation_generation_node writes back into candidate_scores
        explained_candidates = updated_state.get("candidate_scores") or inp.scored_candidates

        output = ExplanationOutput(
            request_id=inp.request_id,
            correlation_id=inp.correlation_id,
            scored_candidates=explained_candidates,
            total_evaluated=inp.total_evaluated,
            normalized_role=inp.normalized_role,
            certifications_required=inp.certifications_required,
            mandatory_skill_ids=inp.mandatory_skill_ids,
            preferred_skill_ids=inp.preferred_skill_ids,
            experience=inp.experience,
        )

        yield Message.create(
            payload=output.model_dump(),
            metadata=MessageMetadata(
                source_agent=self.agent_id,
                message_type="explanation.complete",
                correlation_id=inp.correlation_id,
                request_id=inp.request_id,
            ),
            trace_id=message.trace_id,
        )

    async def health_check(self) -> HealthStatus:
        if not self._initialized:
            return HealthStatus.unavailable(self.agent_id, self.version, "Not initialized")
        try:
            from app.ai.utils.llm_client import llm_client
            if llm_client.client is not None:
                return HealthStatus.ok(self.agent_id, self.version,
                                       uptime_s=round(self.uptime_seconds, 1))
            return HealthStatus.degraded(
                self.agent_id, self.version,
                "LLM client not initialised",
            )
        except Exception as exc:
            return HealthStatus.unavailable(self.agent_id, self.version, str(exc))

    async def shutdown(self, graceful: bool = True) -> None:
        self._initialized = False
