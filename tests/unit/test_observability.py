"""
Phase 7 — Observability tests.

Tests:
1. AgentMetrics — counters, histograms, gauges update correctly
2. AgentTracer — graceful no-op when OTel is not installed
3. DeadLetterStore — push/list/count/clear/ring-buffer
4. TraceLogAdapter — injects trace_id into log records
5. Orchestrator integration — metrics update during dispatch
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator, Dict, List
from unittest.mock import MagicMock

import pytest

from prometheus_client import CollectorRegistry

from app.agent_framework.base_agent import BaseAgent
from app.agent_framework.config_loader import (
    AgentConfig, AgentSystemConfig, DatabaseConfig,
    DeadLetterConfig, ErrorHandlingConfig, InfrastructureConfig,
    LLMConfig, EmbeddingConfig, ObservabilityConfig, RedisConfig,
    RetryConfig, RouteConfig, SystemConfig, AlertingConfig,
)
from app.agent_framework.health import HealthState, HealthStatus
from app.agent_framework.message import Message, MessageMetadata
from app.agent_framework.observability import (
    AgentMetrics,
    AgentTracer,
    DeadLetterStore,
    TraceLogAdapter,
)
from app.agent_framework.orchestrator import Orchestrator
from app.agent_framework.registry import AgentRegistry


# ================================================================== #
# 1. AgentMetrics
# ================================================================== #

class TestAgentMetrics:

    def test_record_success_increments_counter_and_histogram(self):
        registry = CollectorRegistry()
        m = AgentMetrics(registry=registry)
        m.record_success("agent_a", 0.5)

        # Counter should be 1
        val = registry.get_sample_value(
            "agent_framework_messages_total",
            {"agent_id": "agent_a", "status": "success"},
        )
        assert val == 1.0

    def test_record_failure_increments_counter(self):
        registry = CollectorRegistry()
        m = AgentMetrics(registry=registry)
        m.record_failure("agent_b", 1.2)

        val = registry.get_sample_value(
            "agent_framework_messages_total",
            {"agent_id": "agent_b", "status": "failure"},
        )
        assert val == 1.0

    def test_record_timeout_increments_counter(self):
        registry = CollectorRegistry()
        m = AgentMetrics(registry=registry)
        m.record_timeout("agent_c")

        val = registry.get_sample_value(
            "agent_framework_messages_total",
            {"agent_id": "agent_c", "status": "timeout"},
        )
        assert val == 1.0

    def test_dead_letter_increments_both_counters(self):
        registry = CollectorRegistry()
        m = AgentMetrics(registry=registry)
        m.record_dead_letter("agent_d")

        msg_val = registry.get_sample_value(
            "agent_framework_messages_total",
            {"agent_id": "agent_d", "status": "dead_letter"},
        )
        dlq_val = registry.get_sample_value(
            "agent_framework_dead_letter_total",
            {"agent_id": "agent_d"},
        )
        assert msg_val == 1.0
        assert dlq_val == 1.0

    def test_queue_depth_gauge(self):
        registry = CollectorRegistry()
        m = AgentMetrics(registry=registry)
        m.set_queue_depth("agent_e", 42)

        val = registry.get_sample_value(
            "agent_framework_queue_depth",
            {"agent_id": "agent_e"},
        )
        assert val == 42.0

    def test_agent_state_gauge(self):
        registry = CollectorRegistry()
        m = AgentMetrics(registry=registry)
        m.set_agent_state("agent_f", 0.5)

        val = registry.get_sample_value(
            "agent_framework_agent_state",
            {"agent_id": "agent_f"},
        )
        assert val == 0.5

    def test_pipeline_duration(self):
        registry = CollectorRegistry()
        m = AgentMetrics(registry=registry)
        m.record_pipeline_duration(3.14)

        # Histogram count should be 1
        val = registry.get_sample_value(
            "agent_framework_pipeline_duration_seconds_count",
        )
        assert val == 1.0

    def test_retry_counter(self):
        registry = CollectorRegistry()
        m = AgentMetrics(registry=registry)
        m.record_retry("agent_g")
        m.record_retry("agent_g")

        val = registry.get_sample_value(
            "agent_framework_retry_total",
            {"agent_id": "agent_g"},
        )
        assert val == 2.0


# ================================================================== #
# 2. AgentTracer (no-op when OTel not installed)
# ================================================================== #

class TestAgentTracer:

    def test_noop_when_exporter_is_none(self):
        tracer = AgentTracer(exporter="none")
        assert tracer.enabled is False

        msg = MagicMock()
        msg.trace_id = "abc"
        msg.metadata = MagicMock()
        msg.metadata.source_agent = "test"
        msg.metadata.message_type = "test.in"

        with tracer.span("my_agent", msg) as span:
            span.set_attribute("key", "value")  # no-op
            span.add_event("something")  # no-op

    def test_noop_span_does_not_raise(self):
        tracer = AgentTracer(exporter="none")
        msg = MagicMock()
        with tracer.span("agent_x", msg) as span:
            span.record_exception(ValueError("test"))
            span.set_status("ERROR", "test error")


# ================================================================== #
# 3. DeadLetterStore
# ================================================================== #

class TestDeadLetterStore:

    def test_push_and_list(self):
        dlq = DeadLetterStore(max_size=100)
        msg = MagicMock()
        msg.trace_id = "trace-1"
        msg.metadata = MagicMock()
        msg.metadata.message_type = "test.msg"
        msg.payload = {"key": "value"}

        dlq.push(msg, source_agent="pii_scrubber", error="timed out")

        entries = dlq.list_entries()
        assert len(entries) == 1
        assert entries[0]["trace_id"] == "trace-1"
        assert entries[0]["source_agent"] == "pii_scrubber"
        assert entries[0]["error"] == "timed out"

    def test_count(self):
        dlq = DeadLetterStore()
        assert dlq.count() == 0

        msg = MagicMock()
        msg.trace_id = "t1"
        msg.metadata = MagicMock()
        msg.metadata.message_type = "x"
        msg.payload = {}

        dlq.push(msg, "agent_a")
        dlq.push(msg, "agent_b")
        assert dlq.count() == 2

    def test_clear(self):
        dlq = DeadLetterStore()
        msg = MagicMock()
        msg.trace_id = "t1"
        msg.metadata = MagicMock()
        msg.metadata.message_type = "x"
        msg.payload = {}

        dlq.push(msg, "agent_a")
        assert dlq.count() == 1
        dlq.clear()
        assert dlq.count() == 0

    def test_ring_buffer_eviction(self):
        dlq = DeadLetterStore(max_size=3)
        msg = MagicMock()
        msg.metadata = MagicMock()
        msg.metadata.message_type = "x"
        msg.payload = {}

        for i in range(5):
            msg.trace_id = f"trace-{i}"
            dlq.push(msg, "agent_a")

        assert dlq.count() == 3
        entries = dlq.list_entries()
        # Should have the 3 most recent (2, 3, 4)
        trace_ids = [e["trace_id"] for e in entries]
        assert "trace-4" in trace_ids
        assert "trace-3" in trace_ids
        assert "trace-0" not in trace_ids

    def test_list_respects_limit(self):
        dlq = DeadLetterStore(max_size=100)
        msg = MagicMock()
        msg.metadata = MagicMock()
        msg.metadata.message_type = "x"
        msg.payload = {}
        msg.trace_id = "t"

        for _ in range(10):
            dlq.push(msg, "agent")

        assert len(dlq.list_entries(limit=3)) == 3


# ================================================================== #
# 4. TraceLogAdapter
# ================================================================== #

class TestTraceLogAdapter:

    def test_injects_trace_context(self):
        logger = logging.getLogger("test.trace.adapter")
        adapter = TraceLogAdapter(
            logger,
            trace_id="trace-xyz",
            correlation_id="corr-123",
            agent_id="pii_scrubber",
        )

        msg, kwargs = adapter.process("test message", {"extra": {}})
        assert msg == "test message"
        assert kwargs["extra"]["trace_id"] == "trace-xyz"
        assert kwargs["extra"]["correlation_id"] == "corr-123"
        assert kwargs["extra"]["agent_id"] == "pii_scrubber"

    def test_creates_extra_if_missing(self):
        logger = logging.getLogger("test.trace.adapter2")
        adapter = TraceLogAdapter(logger, trace_id="t", correlation_id="c")

        msg, kwargs = adapter.process("msg", {})
        assert "trace_id" in kwargs["extra"]


# ================================================================== #
# 5. Orchestrator integration — metrics fire during dispatch
# ================================================================== #

# Stub agents for orchestrator tests
class _MetricsPassAgent(BaseAgent):
    agent_id = "metrics_pass"
    version = "1.0.0"
    config_schema: Dict[str, Any] = {"type": "object", "additionalProperties": True}

    async def initialize(self, config):
        await self._base_initialize(config)

    async def handle(self, message: Message) -> AsyncIterator[Message]:
        yield Message.create(
            payload=message.payload,
            metadata=MessageMetadata(
                source_agent=self.agent_id,
                message_type="metrics_pass.done",
                correlation_id=message.metadata.correlation_id,
                request_id=message.metadata.request_id,
            ),
            trace_id=message.trace_id,
        )

    async def health_check(self):
        return HealthStatus.ok(self.agent_id, self.version)

    async def shutdown(self, graceful=True):
        self._initialized = False


class _MetricsFailAgent(BaseAgent):
    agent_id = "metrics_fail"
    version = "1.0.0"
    config_schema: Dict[str, Any] = {"type": "object", "additionalProperties": True}

    async def initialize(self, config):
        await self._base_initialize(config)

    async def handle(self, message: Message) -> AsyncIterator[Message]:
        raise RuntimeError("Intentional failure for metrics test")
        yield  # make it a generator

    async def health_check(self):
        return HealthStatus.ok(self.agent_id, self.version)

    async def shutdown(self, graceful=True):
        self._initialized = False


def _make_config(agents_cfg, routes):
    """Build a minimal AgentSystemConfig for testing."""
    return AgentSystemConfig(
        system=SystemConfig(name="metrics-test", version="1.0.0"),
        infrastructure=InfrastructureConfig(
            database=DatabaseConfig(url="sqlite:///:memory:", pool_size=1, max_overflow=0),
            redis=RedisConfig(url="redis://localhost:6379/0"),
            llm=LLMConfig(provider="openai", temperature=0.0, max_tokens=1000),
            embedding=EmbeddingConfig(provider="gemma", model="gemma-2b", device="cpu"),
        ),
        agents=agents_cfg,
        routing=routes,
        observability=ObservabilityConfig(
            metrics_port=9090,
            trace_exporter="none",
            log_format="json",
        ),
        error_handling=ErrorHandlingConfig(
            dead_letter=DeadLetterConfig(backend="memory", key_prefix="dlq:", ttl_seconds=3600),
            alerting=AlertingConfig(),
        ),
    )


class TestOrchestratorMetrics:

    @pytest.fixture(autouse=True)
    def _clean_registry(self):
        AgentRegistry.clear()
        AgentRegistry.register(_MetricsPassAgent)
        AgentRegistry.register(_MetricsFailAgent)
        yield
        AgentRegistry.clear()

    @pytest.mark.asyncio
    async def test_success_increments_metrics(self):
        prom_registry = CollectorRegistry()
        metrics = AgentMetrics(registry=prom_registry)

        config = _make_config(
            agents_cfg=[
                AgentConfig(id="metrics_pass", type="metrics_pass", enabled=True,
                            retry=RetryConfig(), config={}),
            ],
            routes=[
                RouteConfig.model_validate({"from": "__entry__", "to": "metrics_pass"}),
                RouteConfig.model_validate({"from": "metrics_pass", "to": "__sink__"}),
            ],
        )

        orch = Orchestrator(config, metrics=metrics)
        await orch.start()

        result = await orch.process(
            payload={"request_id": "r", "correlation_id": "c"},
            timeout_s=5,
        )

        assert result.metadata.message_type == "metrics_pass.done"

        # Check Prometheus counter
        val = prom_registry.get_sample_value(
            "agent_framework_messages_total",
            {"agent_id": "metrics_pass", "status": "success"},
        )
        assert val == 1.0

        # Pipeline duration should be recorded
        dur_count = prom_registry.get_sample_value(
            "agent_framework_pipeline_duration_seconds_count",
        )
        assert dur_count == 1.0

        await orch.shutdown()

    @pytest.mark.asyncio
    async def test_failure_updates_dead_letter_store(self):
        prom_registry = CollectorRegistry()
        metrics = AgentMetrics(registry=prom_registry)

        config = _make_config(
            agents_cfg=[
                AgentConfig(id="metrics_fail", type="metrics_fail", enabled=True,
                            retry=RetryConfig(max_attempts=1), config={}),
            ],
            routes=[
                RouteConfig.model_validate({"from": "__entry__", "to": "metrics_fail"}),
                RouteConfig.model_validate({"from": "metrics_fail", "to": "__sink__"}),
            ],
        )

        orch = Orchestrator(config, metrics=metrics)
        await orch.start()

        with pytest.raises(RuntimeError, match="dead-lettered"):
            await orch.process(
                payload={"request_id": "r", "correlation_id": "c"},
                timeout_s=5,
            )

        # Dead-letter store should have an entry
        assert orch.dead_letter_store.count() == 1

        # Prometheus dead-letter counter
        dlq_val = prom_registry.get_sample_value(
            "agent_framework_dead_letter_total",
            {"agent_id": "metrics_fail"},
        )
        assert dlq_val == 1.0

        await orch.shutdown()

    @pytest.mark.asyncio
    async def test_health_updates_gauges(self):
        prom_registry = CollectorRegistry()
        metrics = AgentMetrics(registry=prom_registry)

        config = _make_config(
            agents_cfg=[
                AgentConfig(id="metrics_pass", type="metrics_pass", enabled=True,
                            retry=RetryConfig(), config={}),
            ],
            routes=[
                RouteConfig.model_validate({"from": "__entry__", "to": "metrics_pass"}),
                RouteConfig.model_validate({"from": "metrics_pass", "to": "__sink__"}),
            ],
        )

        orch = Orchestrator(config, metrics=metrics)
        await orch.start()

        health = await orch.get_health()
        assert health["status"] == "ok"

        # Agent state gauge should be 1.0 (ok)
        state_val = prom_registry.get_sample_value(
            "agent_framework_agent_state",
            {"agent_id": "metrics_pass"},
        )
        assert state_val == 1.0

        await orch.shutdown()
