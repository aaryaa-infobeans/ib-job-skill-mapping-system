"""
Orchestrator — manages agent lifecycle and routes messages between agents.

Responsibilities (per Phase 5 spec)
-------------------------------------
1. Load config → validate → instantiate agents via AgentRegistry.
2. Resolve routing graph: detect cycles, missing agents, dead ends.
3. Manage agent lifecycle:  init → ready → running → shutdown.
4. Route messages between agents per the routing config (data-driven).
5. Handle backpressure: asyncio.Queue per agent with bounded capacity;
   if a downstream agent's queue is full the upstream coroutine blocks.
6. Expose aggregate health via  get_health()  (consumed by /health endpoint).
7. Support SIGTERM graceful shutdown: drain in-flight messages, then stop.

Routing engine is purely data-driven.  Adding a new route requires only
a config change — zero code changes.

Thread / concurrency model
--------------------------
Each agent runs in its own asyncio Task.  Messages are passed through
per-agent asyncio.Queues (bounded by  QUEUE_CAPACITY).  The orchestrator
itself is not a coroutine — callers invoke  process(payload)  which
enqueues the entry message and awaits the result via a Future tied to the
message's trace_id.

Backpressure
------------
Queues are bounded (default capacity 64).  When a downstream queue is
full,  asyncio.Queue.put()  blocks the upstream task, naturally applying
backpressure all the way back to the HTTP layer.  No messages are dropped.

Graceful shutdown
-----------------
On  shutdown(), a sentinel  _SHUTDOWN  token is enqueued for every agent.
Workers drain their queues, process the sentinel, then exit.  The
orchestrator awaits all worker tasks with a configurable drain timeout.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .base_agent import BaseAgent
from .config_loader import AgentConfig, AgentSystemConfig, RouteConfig
from .health import HealthState, HealthStatus
from .message import Message, MessageMetadata
from .observability import AgentMetrics, AgentTracer, DeadLetterStore, TraceLogAdapter
from .registry import AgentRegistry
from .router import RoutingEngine

log = logging.getLogger("orchestrator")

# Sentinel object enqueued to tell a worker to stop.
_SHUTDOWN = object()

# Default bounded queue capacity per agent.
QUEUE_CAPACITY = 64


# ------------------------------------------------------------------ #
# Agent lifecycle state machine
# ------------------------------------------------------------------ #

class AgentState:
    PENDING     = "pending"      # not yet started
    INITIALIZING = "initializing"
    READY       = "ready"        # initialized, worker running
    RUNNING     = "running"      # actively processing a message
    DEGRADED    = "degraded"     # running but health check failed
    SHUTTING_DOWN = "shutting_down"
    STOPPED     = "stopped"


@dataclass
class AgentSlot:
    """Runtime holder for one agent instance."""
    config: AgentConfig
    agent: BaseAgent
    queue: asyncio.Queue
    state: str = AgentState.PENDING
    worker_task: Optional[asyncio.Task] = None
    messages_processed: int = 0
    messages_failed: int = 0
    last_error: Optional[str] = None
    started_at: float = field(default_factory=time.monotonic)


# ------------------------------------------------------------------ #
# Orchestrator
# ------------------------------------------------------------------ #

class Orchestrator:
    """
    Manages the full lifecycle of the agent pipeline.

    Usage
    -----
        config = load_and_validate_config("config/agents.yaml")
        orch = Orchestrator(config)
        await orch.start()

        # Process a single requisition
        result_msg = await orch.process(
            payload={"request_id": "...", "correlation_id": "...", ...},
            timeout_s=60,
        )

        await orch.shutdown()
    """

    def __init__(
        self,
        config: AgentSystemConfig,
        queue_capacity: int = QUEUE_CAPACITY,
        metrics: Optional[AgentMetrics] = None,
    ) -> None:
        self._config = config
        self._queue_capacity = queue_capacity
        self._slots: Dict[str, AgentSlot] = {}
        self._router = RoutingEngine(config.routing)
        # trace_id → Future[Message] for callers awaiting pipeline results
        self._pending: Dict[str, asyncio.Future] = {}
        self._started = False
        self._shutdown_event = asyncio.Event()

        # Observability
        self._metrics = metrics or AgentMetrics()
        self._tracer = AgentTracer(
            exporter=config.observability.trace_exporter
        )
        self._dlq = DeadLetterStore(max_size=1000)

    # ------------------------------------------------------------------ #
    # Startup
    # ------------------------------------------------------------------ #

    async def start(self) -> None:
        """
        Initialise all enabled agents and start their worker tasks.

        Raises RuntimeError if any agent fails to initialise.
        All failures are collected and reported together.
        """
        if self._started:
            raise RuntimeError("Orchestrator.start() called more than once.")

        log.info(
            "Orchestrator starting",
            extra={"system": self._config.system.name},
        )

        failures: List[str] = []

        for agent_cfg in self._config.agents:
            if not agent_cfg.enabled:
                log.info("Agent '%s' is disabled — skipping.", agent_cfg.id)
                continue
            try:
                await self._init_agent(agent_cfg)
            except Exception as exc:
                failures.append(f"Agent '{agent_cfg.id}': {exc}")
                log.exception("Failed to initialise agent '%s'", agent_cfg.id)

        if failures:
            bullet = "\n  ".join(failures)
            raise RuntimeError(
                f"Orchestrator startup failed — {len(failures)} agent(s) "
                f"could not initialise:\n  {bullet}"
            )

        # Validate routing graph against the actual running agents
        running_ids = set(self._slots.keys())
        self._router.validate(running_ids)

        self._started = True
        log.info(
            "Orchestrator started — %d agent(s) ready.",
            len(self._slots),
        )

    async def _init_agent(self, agent_cfg: AgentConfig) -> None:
        """Resolve class, instantiate, inject config, start worker."""
        cls = AgentRegistry.resolve(agent_cfg.id, agent_cfg.version)
        agent: BaseAgent = cls()

        # Build the agent-scoped config dict by merging infra references
        # into the agent's own config block.
        scoped_config = self._build_scoped_config(agent_cfg)

        agent._log.info(
            "Initialising agent v%s", agent_cfg.version or agent.version
        )
        await agent.initialize(scoped_config)

        queue: asyncio.Queue = asyncio.Queue(maxsize=self._queue_capacity)
        slot = AgentSlot(config=agent_cfg, agent=agent, queue=queue)
        slot.state = AgentState.READY
        self._slots[agent_cfg.id] = slot

        # Start the worker coroutine
        slot.worker_task = asyncio.create_task(
            self._worker(slot),
            name=f"worker:{agent_cfg.id}",
        )
        log.info("Agent '%s' worker started.", agent_cfg.id)

    def _build_scoped_config(self, agent_cfg: AgentConfig) -> Dict[str, Any]:
        """
        Merge infrastructure config references into the agent config block.

        Each agent receives:
          - Its own config block (from agents.yaml)
          - Infra sub-objects it needs (db_url, llm_*, embedding_*)
          - Log level override if specified in observability section
        """
        infra = self._config.infrastructure
        scoped = dict(agent_cfg.config)

        # Always inject DB and Redis URLs so agents don't need settings.py
        scoped.setdefault("db_url", infra.database.url)
        scoped.setdefault("redis_url", infra.redis.url)

        # LLM config
        scoped.setdefault("llm_provider", infra.llm.provider)
        scoped.setdefault("llm_temperature", infra.llm.temperature)
        scoped.setdefault("llm_max_tokens", infra.llm.max_tokens)
        # Provider-specific keys
        if infra.llm.provider == "openai":
            scoped.setdefault("llm_api_key", infra.llm.openai_api_key)
            scoped.setdefault("llm_model", infra.llm.openai_model)
        elif infra.llm.provider == "groq":
            scoped.setdefault("llm_api_key", infra.llm.groq_api_key)
            scoped.setdefault("llm_model", infra.llm.groq_model)
        elif infra.llm.provider == "google":
            scoped.setdefault("llm_api_key", infra.llm.google_api_key)
            scoped.setdefault("llm_model", infra.llm.google_model)

        # Embedding config
        scoped.setdefault("embedding_provider", infra.embedding.provider)
        scoped.setdefault("embedding_model", infra.embedding.model)
        scoped.setdefault("embedding_device", infra.embedding.device)
        if infra.embedding.gemma_model_path:
            scoped.setdefault("gemma_model_path", infra.embedding.gemma_model_path)

        # Log level override
        level_overrides = self._config.observability.agent_log_levels
        if agent_cfg.id in level_overrides:
            scoped["log_level"] = level_overrides[agent_cfg.id]
            agent_logger = logging.getLogger(f"agent.{agent_cfg.id}")
            agent_logger.setLevel(
                logging.getLevelName(level_overrides[agent_cfg.id].upper())
            )

        return scoped

    # ------------------------------------------------------------------ #
    # Worker coroutine (one per agent)
    # ------------------------------------------------------------------ #

    async def _worker(self, slot: AgentSlot) -> None:
        """
        Drain messages from the agent's queue and call agent.handle().

        Handles:
        - Retry logic with configurable backoff
        - Dead-letter on exhausted retries
        - Routing output messages to downstream agents
        - Resolving the caller's Future on __sink__ arrival
        """
        agent_id = slot.config.id
        retry_cfg = slot.config.retry
        log.debug("Worker for '%s' entering message loop.", agent_id)

        while True:
            item = await slot.queue.get()

            # Shutdown sentinel
            if item is _SHUTDOWN:
                log.info("Worker '%s' received shutdown sentinel.", agent_id)
                slot.queue.task_done()
                break

            message: Message = item
            slot.state = AgentState.RUNNING

            success = await self._dispatch_with_retry(
                slot=slot,
                message=message,
                max_attempts=retry_cfg.max_attempts,
                backoff_strategy=retry_cfg.backoff,
                backoff_ms=retry_cfg.backoff_ms,
            )

            if not success:
                await self._send_to_dead_letter(message, agent_id)

            slot.state = AgentState.READY
            slot.queue.task_done()

        slot.state = AgentState.STOPPED
        log.info("Worker '%s' stopped.", agent_id)

    async def _dispatch_with_retry(
        self,
        slot: AgentSlot,
        message: Message,
        max_attempts: int,
        backoff_strategy: str,
        backoff_ms: int,
    ) -> bool:
        """
        Call agent.handle() with retry logic.

        Returns True if at least one attempt succeeded, False if all failed.
        """
        agent_id = slot.config.id
        timeout_s = slot.config.timeout_ms / 1000

        for attempt in range(1, max_attempts + 1):
            t0 = time.monotonic()
            try:
                output_messages: List[Message] = []

                async def _collect():
                    async for out_msg in slot.agent.handle(message):
                        output_messages.append(out_msg)

                with self._tracer.span(agent_id, message) as span:
                    span.set_attribute("agent.attempt", attempt)
                    span.set_attribute("agent.timeout_s", timeout_s)

                    await asyncio.wait_for(_collect(), timeout=timeout_s)

                    span.set_attribute("agent.output_count", len(output_messages))

                elapsed = time.monotonic() - t0

                # Route all output messages
                for out_msg in output_messages:
                    await self._route(out_msg)

                slot.messages_processed += 1
                slot.last_error = None
                self._metrics.record_success(agent_id, elapsed)
                return True

            except asyncio.TimeoutError:
                elapsed = time.monotonic() - t0
                slot.last_error = f"Timeout after {timeout_s}s"
                self._metrics.record_timeout(agent_id)
                log.warning(
                    "Agent '%s' timed out (attempt %d/%d) trace_id=%s",
                    agent_id, attempt, max_attempts, message.trace_id,
                )
            except Exception as exc:
                elapsed = time.monotonic() - t0
                slot.last_error = str(exc)
                self._metrics.record_failure(agent_id, elapsed)
                log.error(
                    "Agent '%s' raised on attempt %d/%d trace_id=%s: %s",
                    agent_id, attempt, max_attempts, message.trace_id, exc,
                    exc_info=True,
                )

            slot.messages_failed += 1

            if attempt < max_attempts:
                self._metrics.record_retry(agent_id)
                delay_s = self._backoff_delay(backoff_strategy, backoff_ms, attempt) / 1000
                await asyncio.sleep(delay_s)

        return False

    @staticmethod
    def _backoff_delay(strategy: str, base_ms: int, attempt: int) -> float:
        if strategy == "fixed":
            return base_ms
        if strategy == "linear":
            return base_ms * attempt
        # exponential (default)
        return base_ms * (2 ** (attempt - 1))

    # ------------------------------------------------------------------ #
    # Routing engine
    # ------------------------------------------------------------------ #

    async def _route(self, message: Message) -> None:
        """
        Resolve the destination(s) for a message and enqueue it.

        Special destinations:
          __sink__        → resolve the caller's pending Future
          __dead_letter__ → send to DLQ
          (none)          → drop with a warning
        """
        destinations = self._router.resolve(message)

        if not destinations:
            log.warning(
                "No route found for message type '%s' from agent '%s' "
                "(trace_id=%s). Message dropped.",
                message.metadata.message_type,
                message.metadata.source_agent,
                message.trace_id,
            )
            return

        for dest in destinations:
            if dest == "__sink__":
                await self._resolve_future(message)
            elif dest == "__dead_letter__":
                await self._send_to_dead_letter(
                    message, message.metadata.source_agent
                )
            elif dest in self._slots:
                await self._slots[dest].queue.put(message)
            else:
                log.error(
                    "Route points to unknown agent '%s' — message dropped "
                    "(trace_id=%s).",
                    dest, message.trace_id,
                )

    async def _resolve_future(self, message: Message) -> None:
        """Resolve the caller's Future when a message reaches __sink__."""
        fut = self._pending.get(message.trace_id)
        if fut and not fut.done():
            fut.set_result(message)
        elif not fut:
            log.warning(
                "Sink received message with unknown trace_id=%s — "
                "caller may have timed out.",
                message.trace_id,
            )

    async def _send_to_dead_letter(self, message: Message, source: str) -> None:
        """Forward a failed message to the dead-letter store and metrics."""
        error_text = f"Dead-lettered at agent '{source}'"
        log.error(
            "Dead-letter: agent='%s' trace_id=%s message_type='%s'",
            source,
            message.trace_id,
            message.metadata.message_type,
        )

        # Store in dead-letter store for inspection / replay
        self._dlq.push(message, source_agent=source, error=error_text)
        self._metrics.record_dead_letter(source)

        # If a caller is waiting, fail their Future so they're not stuck.
        fut = self._pending.get(message.trace_id)
        if fut and not fut.done():
            fut.set_exception(
                RuntimeError(
                    f"Pipeline failed for trace_id={message.trace_id} "
                    f"(dead-lettered at agent '{source}')"
                )
            )

    # ------------------------------------------------------------------ #
    # Public API: process one requisition
    # ------------------------------------------------------------------ #

    async def process(
        self,
        payload: Any,
        *,
        trace_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
        timeout_s: float = 120.0,
    ) -> Message:
        """
        Submit a payload to the pipeline and await the final result.

        Parameters
        ----------
        payload:
            The raw input dict (job description + metadata).
        trace_id:
            If provided, propagates an existing trace.  Auto-generated if None.
        correlation_id, request_id:
            Business-level identifiers forwarded through the pipeline.
        timeout_s:
            How long to wait for the full pipeline to complete.

        Returns
        -------
        Message
            The final output message (from the agent that routes to __sink__).

        Raises
        ------
        RuntimeError   If the pipeline dead-letters the message.
        asyncio.TimeoutError  If the pipeline exceeds timeout_s.
        """
        if not self._started:
            raise RuntimeError("Orchestrator has not been started.")

        entry_message = Message.create(
            payload=payload,
            metadata=MessageMetadata(
                source_agent="__entry__",
                message_type="requisition.submitted",
                correlation_id=correlation_id,
                request_id=request_id,
            ),
            trace_id=trace_id,
        )

        # Register a Future so the __sink__ handler can resolve it
        loop = asyncio.get_running_loop()
        fut: asyncio.Future[Message] = loop.create_future()
        self._pending[entry_message.trace_id] = fut

        pipeline_start = time.monotonic()
        try:
            # Enqueue to the first agent in the pipeline
            first_destinations = self._router.resolve(entry_message)
            for dest in first_destinations:
                if dest in self._slots:
                    await self._slots[dest].queue.put(entry_message)

            result = await asyncio.wait_for(fut, timeout=timeout_s)
            self._metrics.record_pipeline_duration(time.monotonic() - pipeline_start)
            return result
        finally:
            self._pending.pop(entry_message.trace_id, None)

    # ------------------------------------------------------------------ #
    # Health
    # ------------------------------------------------------------------ #

    async def get_health(self) -> Dict[str, Any]:
        """
        Aggregate health across all running agents.

        Returns a dict suitable for the /health endpoint:
        {
            "status": "ok" | "degraded" | "unavailable",
            "agents": { agent_id: HealthStatus.dict() },
            "queue_depths": { agent_id: int },
        }
        """
        agent_statuses: Dict[str, HealthStatus] = {}
        queue_depths: Dict[str, int] = {}
        worst = HealthState.OK

        for agent_id, slot in self._slots.items():
            try:
                status = await asyncio.wait_for(
                    slot.agent.health_check(), timeout=5.0
                )
            except Exception as exc:
                status = HealthStatus.unavailable(
                    agent_id, slot.agent.version,
                    f"health_check raised: {exc}",
                )

            agent_statuses[agent_id] = status
            queue_depths[agent_id] = slot.queue.qsize()

            # Update Prometheus gauges
            self._metrics.set_queue_depth(agent_id, slot.queue.qsize())
            self._metrics.set_agent_state(agent_id, status.prometheus_gauge)

            if status.state == HealthState.UNAVAILABLE:
                worst = HealthState.UNAVAILABLE
            elif status.state == HealthState.DEGRADED and worst == HealthState.OK:
                worst = HealthState.DEGRADED

        return {
            "status": worst.value,
            "agents": {
                aid: s.model_dump() for aid, s in agent_statuses.items()
            },
            "queue_depths": queue_depths,
        }

    # ------------------------------------------------------------------ #
    # Shutdown
    # ------------------------------------------------------------------ #

    async def shutdown(self, graceful: bool = True, drain_timeout_s: float = 30.0) -> None:
        """
        Stop all agent workers.

        Graceful=True → enqueue shutdown sentinels, wait for queues to drain,
                        then call agent.shutdown().
        Graceful=False → cancel worker tasks immediately.
        """
        if not self._started:
            return

        log.info(
            "Orchestrator shutting down (graceful=%s, drain_timeout=%ss).",
            graceful, drain_timeout_s,
        )

        for agent_id, slot in self._slots.items():
            slot.state = AgentState.SHUTTING_DOWN
            if graceful:
                await slot.queue.put(_SHUTDOWN)
            elif slot.worker_task and not slot.worker_task.done():
                slot.worker_task.cancel()

        if graceful and self._slots:
            tasks = [
                s.worker_task for s in self._slots.values()
                if s.worker_task and not s.worker_task.done()
            ]
            if tasks:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*tasks, return_exceptions=True),
                        timeout=drain_timeout_s,
                    )
                except asyncio.TimeoutError:
                    log.warning(
                        "Drain timeout (%ss) exceeded — cancelling remaining tasks.",
                        drain_timeout_s,
                    )
                    for t in tasks:
                        t.cancel()

        # Call agent.shutdown() on all agents
        for agent_id, slot in self._slots.items():
            try:
                await slot.agent.shutdown(graceful=graceful)
            except Exception as exc:
                log.error(
                    "Agent '%s' raised during shutdown: %s", agent_id, exc
                )

        # Fail any still-pending Futures
        for trace_id, fut in self._pending.items():
            if not fut.done():
                fut.set_exception(
                    RuntimeError("Orchestrator shut down while awaiting result.")
                )
        self._pending.clear()

        self._started = False
        self._shutdown_event.set()
        log.info("Orchestrator shutdown complete.")

    def register_signal_handlers(self) -> None:
        """
        Register SIGTERM / SIGINT handlers for graceful shutdown.

        Call this in the main process after start().
        """
        loop = asyncio.get_running_loop()

        def _handle_signal(sig_name: str):
            log.info("Received %s — initiating graceful shutdown.", sig_name)
            asyncio.create_task(self.shutdown(graceful=True))

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, _handle_signal, sig.name)

    # ------------------------------------------------------------------ #
    # Context manager support
    # ------------------------------------------------------------------ #

    # ------------------------------------------------------------------ #
    # Observability accessors
    # ------------------------------------------------------------------ #

    @property
    def metrics(self) -> AgentMetrics:
        return self._metrics

    @property
    def dead_letter_store(self) -> DeadLetterStore:
        return self._dlq

    # ------------------------------------------------------------------ #
    # Context manager support
    # ------------------------------------------------------------------ #

    async def __aenter__(self) -> "Orchestrator":
        await self.start()
        return self

    async def __aexit__(self, *_) -> None:
        await self.shutdown()
