"""
Message — typed envelope for all inter-agent communication.

Design decisions:
- trace_id is ALWAYS set (either propagated from upstream or auto-generated).
  Agents MUST NOT strip it.
- payload is intentionally Any so the framework stays decoupled from domain
  schemas.  Agents cast to their own typed input model on entry.
- metadata is open-ended but carries a required 'source_agent' key so the
  routing engine can enforce routing rules and produce useful traces.
- Messages are immutable after construction (frozen=True).  Agents produce
  NEW messages for their outputs; they never mutate an incoming message.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field, model_validator


class MessageMetadata(BaseModel):
    """Routing and observability metadata attached to every message."""

    source_agent: str = Field(
        ...,
        description="agent_id of the agent that produced this message.",
    )
    message_type: str = Field(
        ...,
        description="Dot-separated type tag, e.g. 'requisition.scrubbed'.",
    )
    # Populated by the orchestrator on routing; absent on first message.
    destination_agent: Optional[str] = Field(
        default=None,
        description="agent_id this message is routed to.",
    )
    # Correlation to the original client request (not the same as trace_id).
    correlation_id: Optional[str] = Field(
        default=None,
        description="Business-level correlation key (e.g. from HTTP header).",
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Unique ID for the top-level requisition request.",
    )
    # Allow arbitrary extra keys without breaking existing senders.
    model_config = {"extra": "allow"}


class Message(BaseModel):
    """
    Immutable typed envelope passed between agents.

    Usage
    -----
    # Producing a new message
    msg = Message.create(
        payload=my_output,
        metadata=MessageMetadata(
            source_agent="pii_scrubber",
            message_type="requisition.scrubbed",
            correlation_id=correlation_id,
            request_id=request_id,
        ),
        trace_id=incoming_msg.trace_id,   # propagate from upstream
    )

    # Reading the payload as a typed model
    output: PIIScrubberOutput = PIIScrubberOutput.model_validate(msg.payload)
    """

    trace_id: str = Field(
        description="Globally unique ID propagated across the entire pipeline.",
    )
    timestamp: datetime = Field(
        description="UTC timestamp when this message was produced.",
    )
    payload: Any = Field(
        description="The typed output of the producing agent.",
    )
    metadata: MessageMetadata

    # ------------------------------------------------------------------ #
    # Immutability
    # ------------------------------------------------------------------ #
    model_config = {"frozen": True}

    # ------------------------------------------------------------------ #
    # Factory helpers
    # ------------------------------------------------------------------ #
    @classmethod
    def create(
        cls,
        payload: Any,
        metadata: MessageMetadata,
        *,
        trace_id: Optional[str] = None,
    ) -> "Message":
        """
        Construct a new Message.

        Parameters
        ----------
        payload:
            The producing agent's typed output object (or a dict).
        metadata:
            Routing / observability metadata.
        trace_id:
            If propagating from an upstream message, pass its trace_id.
            If this is the entry message, omit and a fresh UUID is generated.
        """
        return cls(
            trace_id=trace_id or str(uuid.uuid4()),
            timestamp=datetime.now(tz=timezone.utc),
            payload=payload,
            metadata=metadata,
        )

    @property
    def input_size_bytes(self) -> int:
        """Approximate serialised payload size for OTel span attributes."""
        try:
            import json
            return len(json.dumps(self.payload, default=str).encode())
        except Exception:
            return 0
