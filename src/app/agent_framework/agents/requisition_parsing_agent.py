"""
RequisitionParsingAgent — strangler-fig wrapper around the brownfield
requisition_parsing_node (app.ai.agents.requisition_parsing).

Migration step: EXTRACT — the existing parse_requisition_with_llm()
function is called unchanged.  The only new code is the BaseAgent
adapter shell around it.

TODO(agent-migration): Once this wrapper is stable, inline the prompt
template and LLM call directly so the agent owns its own LLM client
instance (injected via config), eliminating the module-level
`llm_client` singleton.  Tracked in TASK-MIGRATE-002.
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

class RequisitionParsingInput(BaseModel):
    request_id: str
    correlation_id: str
    scrubbed_job_description: Dict[str, Any]


class RequisitionParsingOutput(BaseModel):
    request_id: str
    correlation_id: str
    normalized_title: str = ""
    normalized_role: str = ""
    mandatory_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    experience: Optional[Dict[str, Any]] = None
    expected_start_date: Optional[str] = None
    duration_months: Optional[int] = None
    priority: Optional[str] = None
    location: List[str] = Field(default_factory=list)
    work_mode: List[str] = Field(default_factory=list)
    certifications_required: List[str] = Field(default_factory=list)
    jd_text: str = ""
    client_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# ------------------------------------------------------------------ #
# Agent
# ------------------------------------------------------------------ #

@AgentRegistry.register
class RequisitionParsingAgent(BaseAgent):
    """
    Parses and enriches a scrubbed job description using an LLM.

    Wraps the existing  parse_requisition_with_llm()  function unchanged
    (strangler-fig step 1).  On success emits 'requisition.parsed';
    on LLM failure emits 'requisition.parse_failed' so the orchestrator
    can route to the dead-letter queue.
    """

    agent_id = "requisition_parsing"
    version = "1.0.0"

    config_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "llm_model":    {"type": ["string", "null"]},
            "temperature":  {"type": "number", "minimum": 0.0, "maximum": 2.0},
            "max_tokens":   {"type": "integer", "minimum": 1},
            "prompt_version": {"type": "string"},
        },
        "additionalProperties": True,
    }

    async def initialize(self, config: Dict[str, Any]) -> None:
        await self._base_initialize(config)
        # TODO(agent-migration): instantiate an injected LLMClient here
        # using config["llm_api_key"] / config["llm_model"] instead of the
        # module-level singleton.  Blocked on TASK-MIGRATE-002.
        self._log.info("RequisitionParsingAgent ready (using legacy llm_client singleton)")

    async def handle(self, message: Message) -> AsyncIterator[Message]:
        self._assert_initialized()

        inp = RequisitionParsingInput.model_validate(message.payload)

        # ── Delegate to existing brownfield function ──────────────────
        from app.ai.agents.requisition_parsing import parse_requisition_with_llm
        parsed = parse_requisition_with_llm(inp.scrubbed_job_description)

        if not parsed:
            self._log.error(
                "parse_requisition_with_llm returned None",
                extra={"trace_id": message.trace_id, "request_id": inp.request_id},
            )
            yield Message.create(
                payload={
                    "request_id": inp.request_id,
                    "correlation_id": inp.correlation_id,
                    "error": "LLM parsing returned no result",
                },
                metadata=MessageMetadata(
                    source_agent=self.agent_id,
                    message_type="requisition.parse_failed",
                    correlation_id=inp.correlation_id,
                    request_id=inp.request_id,
                ),
                trace_id=message.trace_id,
            )
            return

        # Map the brownfield dict shape → typed output
        jd = inp.scrubbed_job_description
        output = RequisitionParsingOutput(
            request_id=inp.request_id,
            correlation_id=inp.correlation_id,
            normalized_title=parsed.get("normalized_title", jd.get("title", "")),
            normalized_role=parsed.get("normalized_role", jd.get("role", "")),
            mandatory_skills=parsed.get("extracted_mandatory_skills", []),
            preferred_skills=parsed.get("extracted_preferred_skills", []),
            experience=parsed.get("experience"),
            expected_start_date=parsed.get("expected_start_date"),
            duration_months=parsed.get("requisition_duration_month"),
            priority=jd.get("priority"),
            location=jd.get("location") if isinstance(jd.get("location"), list)
                     else ([jd["location"]] if jd.get("location") else []),
            work_mode=jd.get("work_mode") if isinstance(jd.get("work_mode"), list)
                      else ([jd["work_mode"]] if jd.get("work_mode") else []),
            certifications_required=parsed.get("certifications_required", []),
            jd_text=jd.get("jd_text", ""),
            client_name=jd.get("client_name"),
            metadata=jd.get("metadata"),
        )

        yield Message.create(
            payload=output.model_dump(),
            metadata=MessageMetadata(
                source_agent=self.agent_id,
                message_type="requisition.parsed",
                correlation_id=inp.correlation_id,
                request_id=inp.request_id,
            ),
            trace_id=message.trace_id,
        )

    async def health_check(self) -> HealthStatus:
        if not self._initialized:
            return HealthStatus.unavailable(self.agent_id, self.version, "Not initialized")
        # TODO(agent-migration): probe the injected LLMClient when available.
        # For now, check the module-level singleton's provider config.
        try:
            from app.ai.utils.llm_client import llm_client
            provider_ok = llm_client.client is not None
            if provider_ok:
                return HealthStatus.ok(self.agent_id, self.version,
                                       uptime_s=round(self.uptime_seconds, 1))
            return HealthStatus.degraded(
                self.agent_id, self.version,
                "LLM client not initialised — check API key config",
            )
        except Exception as exc:
            return HealthStatus.unavailable(self.agent_id, self.version, str(exc))

    async def shutdown(self, graceful: bool = True) -> None:
        self._initialized = False
