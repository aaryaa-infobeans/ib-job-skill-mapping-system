"""
HealthStatus — standardised health report returned by every agent.

States
------
OK          Agent is fully operational.
DEGRADED    Agent is functional but operating under constraints
            (e.g. LLM rate-limited, using fallback model, DB slow).
UNAVAILABLE Agent cannot process messages (dependency down, model not loaded).

Diagnostics dict is open-ended; agents should include at minimum:
    - 'last_error'   : str | None
    - 'dependency'   : dict[name, bool]  — which deps are reachable
    - 'uptime_s'     : float
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class HealthState(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class HealthStatus(BaseModel):
    """Returned by BaseAgent.health_check()."""

    agent_id: str
    state: HealthState
    checked_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )
    version: str = Field(description="Semver string of the agent.")
    # Freeform diagnostics — surfaced in /health aggregation endpoint.
    diagnostics: Dict[str, Any] = Field(default_factory=dict)
    # Optional human-readable description of the current state.
    message: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Convenience constructors
    # ------------------------------------------------------------------ #
    @classmethod
    def ok(cls, agent_id: str, version: str, **diagnostics: Any) -> "HealthStatus":
        return cls(
            agent_id=agent_id,
            state=HealthState.OK,
            version=version,
            diagnostics=diagnostics,
        )

    @classmethod
    def degraded(
        cls,
        agent_id: str,
        version: str,
        message: str,
        **diagnostics: Any,
    ) -> "HealthStatus":
        return cls(
            agent_id=agent_id,
            state=HealthState.DEGRADED,
            version=version,
            message=message,
            diagnostics=diagnostics,
        )

    @classmethod
    def unavailable(
        cls,
        agent_id: str,
        version: str,
        message: str,
        **diagnostics: Any,
    ) -> "HealthStatus":
        return cls(
            agent_id=agent_id,
            state=HealthState.UNAVAILABLE,
            version=version,
            message=message,
            diagnostics=diagnostics,
        )

    # ------------------------------------------------------------------ #
    # Prometheus-compatible numeric gauge
    # ------------------------------------------------------------------ #
    @property
    def prometheus_gauge(self) -> int:
        """1 = ok, 0 = degraded or unavailable (for agent_health metric)."""
        return 1 if self.state == HealthState.OK else 0
