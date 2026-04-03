"""
Observability module for the agent framework.

Provides three pillars:
1. **Prometheus metrics** — per-agent counters, histograms, gauges.
2. **OpenTelemetry tracing** — optional span creation per agent dispatch.
3. **Structured log helpers** — inject trace_id / correlation_id into log records.

All three are opt-in.  If opentelemetry is not installed, tracing is a no-op.
Prometheus metrics always work (prometheus_client is required).

Usage in orchestrator
---------------------
    from .observability import AgentMetrics, AgentTracer

    metrics = AgentMetrics(registry=custom_registry)
    tracer  = AgentTracer(config.observability)

    # In _dispatch_with_retry:
    with tracer.span(agent_id, message) as span:
        ... handle message ...
        metrics.record_success(agent_id, elapsed_s)
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Any, Dict, Optional

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
)

log = logging.getLogger("agent.observability")


# ------------------------------------------------------------------ #
# 1. Prometheus Metrics
# ------------------------------------------------------------------ #

class AgentMetrics:
    """Per-agent Prometheus metrics for the orchestrator."""

    def __init__(
        self,
        registry: Optional[CollectorRegistry] = None,
        namespace: str = "agent_framework",
    ) -> None:
        self._registry = registry or CollectorRegistry()
        ns = namespace

        self.messages_total = Counter(
            f"{ns}_messages_total",
            "Total messages processed per agent",
            ["agent_id", "status"],  # status: success | failure | timeout | dead_letter
            registry=self._registry,
        )

        self.message_duration_seconds = Histogram(
            f"{ns}_message_duration_seconds",
            "Time spent processing a single message (seconds)",
            ["agent_id"],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
            registry=self._registry,
        )

        self.queue_depth = Gauge(
            f"{ns}_queue_depth",
            "Current number of messages queued per agent",
            ["agent_id"],
            registry=self._registry,
        )

        self.agent_state = Gauge(
            f"{ns}_agent_state",
            "Agent state as a numeric gauge (1=ok, 0.5=degraded, 0=unavailable)",
            ["agent_id"],
            registry=self._registry,
        )

        self.retry_total = Counter(
            f"{ns}_retry_total",
            "Number of retry attempts per agent",
            ["agent_id"],
            registry=self._registry,
        )

        self.dead_letter_total = Counter(
            f"{ns}_dead_letter_total",
            "Messages sent to dead-letter queue per agent",
            ["agent_id"],
            registry=self._registry,
        )

        self.pipeline_duration_seconds = Histogram(
            f"{ns}_pipeline_duration_seconds",
            "End-to-end pipeline latency (seconds)",
            buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
            registry=self._registry,
        )

    # Convenience methods ---------------------------------------------------

    def record_success(self, agent_id: str, elapsed_s: float) -> None:
        self.messages_total.labels(agent_id=agent_id, status="success").inc()
        self.message_duration_seconds.labels(agent_id=agent_id).observe(elapsed_s)

    def record_failure(self, agent_id: str, elapsed_s: float) -> None:
        self.messages_total.labels(agent_id=agent_id, status="failure").inc()
        self.message_duration_seconds.labels(agent_id=agent_id).observe(elapsed_s)

    def record_timeout(self, agent_id: str) -> None:
        self.messages_total.labels(agent_id=agent_id, status="timeout").inc()

    def record_dead_letter(self, agent_id: str) -> None:
        self.messages_total.labels(agent_id=agent_id, status="dead_letter").inc()
        self.dead_letter_total.labels(agent_id=agent_id).inc()

    def record_retry(self, agent_id: str) -> None:
        self.retry_total.labels(agent_id=agent_id).inc()

    def set_queue_depth(self, agent_id: str, depth: int) -> None:
        self.queue_depth.labels(agent_id=agent_id).set(depth)

    def set_agent_state(self, agent_id: str, gauge_value: float) -> None:
        """gauge_value: 1.0=ok, 0.5=degraded, 0.0=unavailable"""
        self.agent_state.labels(agent_id=agent_id).set(gauge_value)

    def record_pipeline_duration(self, elapsed_s: float) -> None:
        self.pipeline_duration_seconds.observe(elapsed_s)

    @property
    def registry(self) -> CollectorRegistry:
        return self._registry


# ------------------------------------------------------------------ #
# 2. OpenTelemetry Tracing (optional — no-op if not installed)
# ------------------------------------------------------------------ #

_OTEL_AVAILABLE = False
try:
    from opentelemetry import trace as otel_trace
    from opentelemetry.trace import StatusCode as OtelStatusCode
    _OTEL_AVAILABLE = True
except ImportError:
    pass


class _NoOpSpan:
    """Drop-in replacement when OTel is not installed."""
    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def set_status(self, status: Any, description: str = "") -> None:
        pass

    def record_exception(self, exc: BaseException) -> None:
        pass

    def add_event(self, name: str, attributes: Optional[Dict] = None) -> None:
        pass


class AgentTracer:
    """
    Thin wrapper around OpenTelemetry that degrades gracefully.

    If `opentelemetry` is installed and trace_exporter != 'none', creates
    real spans.  Otherwise every method is a no-op.
    """

    def __init__(self, exporter: str = "none") -> None:
        self._enabled = _OTEL_AVAILABLE and exporter != "none"
        if self._enabled:
            self._tracer = otel_trace.get_tracer("agent_framework")
        else:
            self._tracer = None

    @contextmanager
    def span(self, agent_id: str, message: Any):
        """
        Context manager that creates a trace span around agent dispatch.

        Yields a span-like object (real or no-op) that the caller can
        annotate with set_attribute / record_exception.

        Usage:
            with tracer.span("pii_scrubber", msg) as span:
                span.set_attribute("input_bytes", 1024)
                ... do work ...
        """
        if not self._enabled or self._tracer is None:
            yield _NoOpSpan()
            return

        # Extract trace context from message
        trace_id = getattr(message, "trace_id", "unknown")
        meta = getattr(message, "metadata", None)
        source = getattr(meta, "source_agent", "unknown") if meta else "unknown"
        msg_type = getattr(meta, "message_type", "unknown") if meta else "unknown"

        with self._tracer.start_as_current_span(
            f"agent.{agent_id}",
            attributes={
                "agent.id": agent_id,
                "agent.trace_id": trace_id,
                "agent.source": source,
                "agent.message_type": msg_type,
            },
        ) as span:
            try:
                yield span
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(OtelStatusCode.ERROR, str(exc))
                raise

    @property
    def enabled(self) -> bool:
        return self._enabled


# ------------------------------------------------------------------ #
# 3. Structured Log Context Injection
# ------------------------------------------------------------------ #

class TraceLogAdapter(logging.LoggerAdapter):
    """
    Injects trace_id and correlation_id into every log record.

    Usage:
        logger = TraceLogAdapter(logging.getLogger("my.agent"), trace_id="abc")
        logger.info("Processing message")
        # → {"trace_id": "abc", "correlation_id": "...", "message": "..."}
    """

    def __init__(
        self,
        logger: logging.Logger,
        trace_id: str = "",
        correlation_id: str = "",
        agent_id: str = "",
    ) -> None:
        super().__init__(logger, {})
        self._trace_id = trace_id
        self._correlation_id = correlation_id
        self._agent_id = agent_id

    def process(self, msg, kwargs):
        extra = kwargs.get("extra", {})
        extra["trace_id"] = self._trace_id
        extra["correlation_id"] = self._correlation_id
        extra["agent_id"] = self._agent_id
        kwargs["extra"] = extra
        return msg, kwargs


# ------------------------------------------------------------------ #
# 4. Dead-Letter Store
# ------------------------------------------------------------------ #

class DeadLetterStore:
    """
    In-memory dead-letter store.

    Stores failed messages with metadata for later inspection or replay.
    In production, replace with Redis (key_prefix + TTL from config).

    TODO(agent-migration): Wire Redis backend when Phase 7 Redis work
    is complete.  Config:  error_handling.dead_letter.backend = "redis"
    """

    def __init__(self, max_size: int = 1000) -> None:
        self._store: list[Dict[str, Any]] = []
        self._max_size = max_size

    def push(
        self,
        message: Any,
        source_agent: str,
        error: str = "",
    ) -> None:
        entry = {
            "trace_id": getattr(message, "trace_id", "unknown"),
            "source_agent": source_agent,
            "message_type": getattr(
                getattr(message, "metadata", None), "message_type", "unknown"
            ),
            "error": error,
            "payload_preview": str(getattr(message, "payload", {}))[:500],
            "timestamp": time.time(),
        }
        self._store.append(entry)
        # Ring-buffer: drop oldest when full
        if len(self._store) > self._max_size:
            self._store = self._store[-self._max_size:]
        log.warning(
            "Dead-letter stored: agent=%s trace_id=%s error=%s",
            source_agent, entry["trace_id"], error[:200],
        )

    def list_entries(self, limit: int = 50) -> list[Dict[str, Any]]:
        """Return most recent dead-letter entries."""
        return list(reversed(self._store[-limit:]))

    def count(self) -> int:
        return len(self._store)

    def clear(self) -> None:
        self._store.clear()
