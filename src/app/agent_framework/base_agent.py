"""
BaseAgent — the universal abstract interface every agent must implement.

Contract
--------
1. Every agent has a stable `agent_id` and a `version` (semver).
2. `config_schema` is a JSONSchema dict.  The orchestrator validates the
   agent-specific config block against it at startup — before any agent
   is instantiated.  Violations are fatal (fail-fast).
3. `initialize(config)` is called ONCE by the orchestrator after validation.
   Agents load models, open DB connections, warm caches here.
4. `handle(message)` is the hot path.  It is:
   - async (never blocks the event loop on I/O)
   - an AsyncIterator so an agent can emit 0-N output messages per input
     (most agents emit exactly one; explanation agent emits one per candidate)
   - IDEMPOTENT — safe to retry with the same message.trace_id
5. `health_check()` returns a HealthStatus snapshot; the orchestrator polls
   this to populate /health and Prometheus metrics.
6. `shutdown(graceful)` is called on SIGTERM.  Graceful=True means drain
   in-flight work before closing connections.

Dependency injection
--------------------
Agents MUST NOT import from `app.settings` directly.  All config is
injected by the orchestrator via `initialize(config: dict)`.  This keeps
agents testable in isolation:

    agent = MyAgent()
    await agent.initialize({"llm_model": "gpt-4o", "temperature": 0.1})
    async for msg in agent.handle(test_message):
        assert msg.payload ...

No shared mutable state
-----------------------
Agents communicate ONLY via messages.  Module-level globals are forbidden
inside agent classes (singletons, caches, etc.).  Instance-level state
is fine as long as it is not shared across concurrent handle() calls
without a lock.
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict

from .health import HealthStatus
from .message import Message


class BaseAgent(ABC):
    """
    Universal abstract base class for every agent in the pipeline.

    Subclass checklist
    ------------------
    1. Set class attributes  agent_id  and  version.
    2. Define  config_schema  as a valid JSONSchema dict.
    3. Implement  initialize, handle, health_check, shutdown.
    4. Inside  handle, always propagate  msg.trace_id  to output messages.
    5. Log with  self._log  (pre-configured with agent_id context).
    """

    # ------------------------------------------------------------------ #
    # Class-level identity — override in every subclass
    # ------------------------------------------------------------------ #
    agent_id: str = ""          # e.g. "pii_scrubber"
    version: str = "0.0.0"     # semver
    config_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {},
        "additionalProperties": True,
    }

    # ------------------------------------------------------------------ #
    # Runtime state (set by orchestrator)
    # ------------------------------------------------------------------ #
    def __init__(self) -> None:
        self._config: Dict[str, Any] = {}
        self._initialized: bool = False
        self._start_time: float = time.monotonic()
        self._log: logging.Logger = logging.getLogger(
            f"agent.{self.agent_id or self.__class__.__name__}"
        )

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> None:
        """
        Load models, open connections, warm caches.

        Called ONCE by the orchestrator after config validation.
        Must be idempotent (safe to call again on hot-reload).

        Parameters
        ----------
        config:
            The agent-specific config block from the YAML, already
            validated against config_schema.
        """
        ...

    @abstractmethod
    async def handle(self, message: Message) -> AsyncIterator[Message]:
        """
        Process one incoming message and yield 0-N output messages.

        Requirements
        ------------
        - MUST be idempotent: replaying the same message.trace_id must
          produce the same logical output (deduplication is the
          orchestrator's job; this contract just says "don't corrupt state").
        - MUST propagate message.trace_id to all emitted messages.
        - MUST NOT mutate the incoming message.
        - SHOULD yield promptly; long-running work should be async.

        Parameters
        ----------
        message:
            Typed envelope from the orchestrator.

        Yields
        ------
        Message
            One or more output messages.  Most agents yield exactly one.
        """
        ...

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """
        Return a snapshot of the agent's current health.

        Should be cheap (< 100ms).  Check dependency reachability if
        meaningful (e.g. a quick DB ping), but avoid full model inference.
        """
        ...

    @abstractmethod
    async def shutdown(self, graceful: bool = True) -> None:
        """
        Release resources.

        Parameters
        ----------
        graceful:
            True  → drain in-flight work, then close connections.
            False → close immediately (e.g. SIGKILL scenario).
        """
        ...

    # ------------------------------------------------------------------ #
    # Convenience helpers available to all subclasses
    # ------------------------------------------------------------------ #
    @property
    def uptime_seconds(self) -> float:
        return time.monotonic() - self._start_time

    def _assert_initialized(self) -> None:
        """Guard: call at the top of handle() to catch mis-use."""
        if not self._initialized:
            raise RuntimeError(
                f"Agent '{self.agent_id}' received a message before "
                f"initialize() was called. Orchestrator bug."
            )

    # ------------------------------------------------------------------ #
    # Default initialize helper — subclasses call super() then add logic
    # ------------------------------------------------------------------ #
    async def _base_initialize(self, config: Dict[str, Any]) -> None:
        """Store config and mark as initialized.  Call via super()."""
        self._config = config
        self._initialized = True
        self._log.info(
            "Agent initialized",
            extra={"agent_id": self.agent_id, "version": self.version},
        )

    # ------------------------------------------------------------------ #
    # Repr
    # ------------------------------------------------------------------ #
    def __repr__(self) -> str:
        state = "initialized" if self._initialized else "uninitialized"
        return f"<{self.__class__.__name__} id={self.agent_id!r} v={self.version} {state}>"
