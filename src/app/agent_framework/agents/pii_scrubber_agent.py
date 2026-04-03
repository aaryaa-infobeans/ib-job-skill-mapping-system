"""
PIIScrubberAgent — Phase 3 reference implementation of BaseAgent.

This is the STRANGLER FIG wrapper (Phase 6 migration step 1):
it delegates all real work to the existing pii.scrubber module and
exposes it through the new BaseAgent contract.  The inner scrubber
logic is untouched — we migrate the interface, not the logic.

Config schema (injected by orchestrator):
    enabled_types:    list of PII type names to detect (default: all)
    action:           "redact" | "tokenize"   (default: "redact")
    audit_log_db:     bool — write audit records to DB  (default: true)
    nfr_p95_ms:       int  — SLA budget for p95 latency (default: 50)
"""

from __future__ import annotations

import time
from typing import Any, AsyncIterator, Dict, List, Optional

from pydantic import BaseModel, Field

from app.agent_framework.base_agent import BaseAgent
from app.agent_framework.health import HealthStatus
from app.agent_framework.message import Message, MessageMetadata
from app.agent_framework.registry import AgentRegistry


# ------------------------------------------------------------------ #
# I/O schemas
# ------------------------------------------------------------------ #

class PIIScrubberInput(BaseModel):
    """Payload expected on the incoming Message."""
    request_id: str
    correlation_id: str
    job_description: Dict[str, Any]


class PIIDetection(BaseModel):
    field: str
    pii_type: str
    detection_method: str


class PIIScrubberOutput(BaseModel):
    """Payload placed on the outgoing Message."""
    request_id: str
    correlation_id: str
    scrubbed_job_description: Dict[str, Any]
    pii_found: bool
    detections: List[PIIDetection] = Field(default_factory=list)
    fields_scrubbed: List[str] = Field(default_factory=list)
    total_pii_count: int = 0


# ------------------------------------------------------------------ #
# Agent implementation
# ------------------------------------------------------------------ #

@AgentRegistry.register
class PIIScrubberAgent(BaseAgent):
    """
    Compliance gate: scrubs PII from incoming job descriptions.

    Wraps the existing  app.pii.scrubber.PIIScrubber  implementation.
    If scrubbing is not confirmed the pipeline is halted — no downstream
    LLM call is made.  This satisfies FR-PII-005.
    """

    agent_id = "pii_scrubber"
    version = "1.0.0"

    config_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "enabled_types": {
                "type": "array",
                "items": {"type": "string"},
                "description": "PII type names to detect. Empty = all.",
            },
            "action": {
                "type": "string",
                "enum": ["redact", "tokenize"],
                "default": "redact",
            },
            "audit_log_db": {
                "type": "boolean",
                "default": True,
                "description": "Write audit records to DB.",
            },
            "nfr_p95_ms": {
                "type": "integer",
                "default": 50,
                "description": "p95 latency SLA in milliseconds.",
            },
        },
        "additionalProperties": False,
    }

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    async def initialize(self, config: Dict[str, Any]) -> None:
        await self._base_initialize(config)
        # Lazy-import so the agent can be imported without the full app
        # being initialised (useful in tests and plugin loading).
        from app.pii.scrubber import PIIScrubber
        from app.pii.config import PIIConfig

        pii_config = PIIConfig(
            enabled_types=config.get("enabled_types", []),
            default_action=config.get("action", "redact"),
        )
        self._scrubber = PIIScrubber(config=pii_config)
        self._audit_log_db: bool = config.get("audit_log_db", True)
        self._nfr_budget_ms: int = config.get("nfr_p95_ms", 50)
        self._log.info(
            "PIIScrubberAgent ready",
            extra={"action": config.get("action", "redact")},
        )

    # ------------------------------------------------------------------ #
    # Handle
    # ------------------------------------------------------------------ #

    async def handle(self, message: Message) -> AsyncIterator[Message]:
        """
        Scrub PII from the job description payload.

        Yields exactly one Message:
        - message_type "requisition.scrubbed"  if scrubbing succeeded.
        - message_type "requisition.pii_blocked"  if scrubbing confirmed
          PII and the pipeline should halt (orchestrator reads this and
          routes to END).
        """
        self._assert_initialized()

        inp = PIIScrubberInput.model_validate(message.payload)
        t0 = time.monotonic()

        # ---- Delegate to existing scrubber (strangler fig) ----
        result = self._scrubber.scrub(inp.job_description)

        elapsed_ms = (time.monotonic() - t0) * 1000
        if elapsed_ms > self._nfr_budget_ms:
            self._log.warning(
                "PII scrub exceeded latency budget",
                extra={
                    "elapsed_ms": round(elapsed_ms, 1),
                    "budget_ms": self._nfr_budget_ms,
                    "trace_id": message.trace_id,
                },
            )

        # ---- Optionally persist audit record ----
        if self._audit_log_db:
            # TODO(agent-migration): wire audit logger to injected DB session
            # rather than importing directly.  Deferred: requires session
            # injection pattern to be agreed in Phase 5 orchestrator.
            pass

        output = PIIScrubberOutput(
            request_id=inp.request_id,
            correlation_id=inp.correlation_id,
            scrubbed_job_description=result.scrubbed_payload,
            pii_found=result.pii_found,
            detections=[
                PIIDetection(
                    field=d.field,
                    pii_type=d.pii_type,
                    detection_method=d.method,
                )
                for d in result.detections
            ],
            fields_scrubbed=result.fields_scrubbed,
            total_pii_count=result.total_pii_count,
        )

        # Determine message type for routing
        msg_type = (
            "requisition.scrubbed"
            if result.scrubbing_confirmed
            else "requisition.pii_blocked"
        )

        yield Message.create(
            payload=output.model_dump(),
            metadata=MessageMetadata(
                source_agent=self.agent_id,
                message_type=msg_type,
                correlation_id=inp.correlation_id,
                request_id=inp.request_id,
            ),
            trace_id=message.trace_id,
        )

    # ------------------------------------------------------------------ #
    # Health
    # ------------------------------------------------------------------ #

    async def health_check(self) -> HealthStatus:
        if not self._initialized:
            return HealthStatus.unavailable(
                self.agent_id,
                self.version,
                "Not initialized",
            )
        # Check NER model availability via a cheap probe
        try:
            ok = self._scrubber.probe()
            if ok:
                return HealthStatus.ok(
                    self.agent_id,
                    self.version,
                    uptime_s=round(self.uptime_seconds, 1),
                )
            return HealthStatus.degraded(
                self.agent_id,
                self.version,
                "NER model probe returned False — using regex-only mode",
                uptime_s=round(self.uptime_seconds, 1),
            )
        except Exception as exc:
            return HealthStatus.unavailable(
                self.agent_id,
                self.version,
                f"Scrubber probe raised: {exc}",
                last_error=str(exc),
            )

    # ------------------------------------------------------------------ #
    # Shutdown
    # ------------------------------------------------------------------ #

    async def shutdown(self, graceful: bool = True) -> None:
        self._log.info(
            "PIIScrubberAgent shutting down",
            extra={"graceful": graceful},
        )
        # No long-lived resources to drain for this agent.
        self._initialized = False
