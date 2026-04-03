"""
Unit tests for the Orchestrator and RoutingEngine.

All tests use in-process stub agents — no DB, no LLM, no real infrastructure.

Run:
    pytest tests/unit/test_orchestrator.py -v --noconftest --asyncio-mode=auto
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Dict, List, Optional
from unittest.mock import AsyncMock

import pytest

from app.agent_framework.base_agent import BaseAgent
from app.agent_framework.config_loader import (
    AgentConfig,
    AgentSystemConfig,
    DatabaseConfig,
    EmbeddingConfig,
    ErrorHandlingConfig,
    InfrastructureConfig,
    LLMConfig,
    ObservabilityConfig,
    RedisConfig,
    RetryConfig,
    RouteConfig,
    SystemConfig,
)
from app.agent_framework.health import HealthStatus
from app.agent_framework.message import Message, MessageMetadata
from app.agent_framework.orchestrator import Orchestrator
from app.agent_framework.registry import AgentRegistry
from app.agent_framework.router import RoutingEngine, RoutingError


# ------------------------------------------------------------------ #
# Stub agents for testing
# ------------------------------------------------------------------ #

class PassThroughAgent(BaseAgent):
    """Forwards input payload unchanged, changing only message_type."""
    agent_id = "pass_through"
    version = "1.0.0"

    async def initialize(self, config):
        await self._base_initialize(config)
        self.output_type = config.get("output_type", "pass.out")

    async def handle(self, message: Message) -> AsyncIterator[Message]:
        self._assert_initialized()
        yield Message.create(
            payload=message.payload,
            metadata=MessageMetadata(
                source_agent=self.agent_id,
                message_type=self.output_type,
            ),
            trace_id=message.trace_id,
        )

    async def health_check(self) -> HealthStatus:
        return HealthStatus.ok(self.agent_id, self.version)

    async def shutdown(self, graceful=True):
        self._initialized = False


class SinkAgent(BaseAgent):
    """Collects received messages for test assertions."""
    agent_id = "sink_agent"
    version = "1.0.0"
    received: List[Message] = []

    async def initialize(self, config):
        await self._base_initialize(config)
        SinkAgent.received = []

    async def handle(self, message: Message) -> AsyncIterator[Message]:
        self._assert_initialized()
        SinkAgent.received.append(message)
        yield Message.create(
            payload=message.payload,
            metadata=MessageMetadata(
                source_agent=self.agent_id,
                message_type="sink.done",
            ),
            trace_id=message.trace_id,
        )

    async def health_check(self) -> HealthStatus:
        return HealthStatus.ok(self.agent_id, self.version)

    async def shutdown(self, graceful=True):
        self._initialized = False


class FailingAgent(BaseAgent):
    """Always raises an exception (for dead-letter tests)."""
    agent_id = "failing_agent"
    version = "1.0.0"

    async def initialize(self, config):
        await self._base_initialize(config)

    async def handle(self, message: Message) -> AsyncIterator[Message]:
        self._assert_initialized()
        raise RuntimeError("Intentional failure for test")
        yield  # make it an AsyncIterator

    async def health_check(self) -> HealthStatus:
        return HealthStatus.unavailable(self.agent_id, self.version, "always broken")

    async def shutdown(self, graceful=True):
        self._initialized = False


class SlowAgent(BaseAgent):
    """Takes longer than its timeout (for timeout tests)."""
    agent_id = "slow_agent"
    version = "1.0.0"

    async def initialize(self, config):
        await self._base_initialize(config)
        self.sleep_s = config.get("sleep_s", 10)

    async def handle(self, message: Message) -> AsyncIterator[Message]:
        self._assert_initialized()
        await asyncio.sleep(self.sleep_s)
        yield Message.create(
            payload=message.payload,
            metadata=MessageMetadata(
                source_agent=self.agent_id,
                message_type="slow.done",
            ),
            trace_id=message.trace_id,
        )

    async def health_check(self) -> HealthStatus:
        return HealthStatus.ok(self.agent_id, self.version)

    async def shutdown(self, graceful=True):
        self._initialized = False


# ------------------------------------------------------------------ #
# Config builders
# ------------------------------------------------------------------ #

def _infra() -> InfrastructureConfig:
    return InfrastructureConfig(
        database=DatabaseConfig(url="postgresql+asyncpg://u:p@localhost/db"),
        redis=RedisConfig(url="redis://localhost:6379/0"),
        llm=LLMConfig(
            provider="openai",
            openai_api_key="sk-test",
            openai_model="gpt-4o-mini",
        ),
        embedding=EmbeddingConfig(provider="google", model="models/text-embedding-004"),
    )


def _agent_cfg(agent_id: str, **kwargs) -> AgentConfig:
    defaults = dict(
        id=agent_id,
        type=agent_id,
        enabled=True,
        config={},
        retry=RetryConfig(max_attempts=1, backoff="fixed", backoff_ms=0),
        timeout_ms=5000,
    )
    defaults.update(kwargs)
    return AgentConfig(**defaults)


def _route(from_: str, to: str, condition: str | None = None) -> RouteConfig:
    return RouteConfig.model_validate({"from": from_, "to": to, "condition": condition})


def _system_config(agents, routes) -> AgentSystemConfig:
    return AgentSystemConfig(
        system=SystemConfig(name="test"),
        infrastructure=_infra(),
        agents=agents,
        routing=routes,
        observability=ObservabilityConfig(
            metrics_port=9090, trace_exporter="none", log_format="json"
        ),
        error_handling=ErrorHandlingConfig(),
    )


# ------------------------------------------------------------------ #
# Fixtures
# ------------------------------------------------------------------ #

@pytest.fixture(autouse=True)
def register_stubs():
    """Register stub agents before each test, clean up after."""
    AgentRegistry.clear()
    for cls in [PassThroughAgent, SinkAgent, FailingAgent, SlowAgent]:
        AgentRegistry.register(cls)
    yield
    AgentRegistry.clear()


# ------------------------------------------------------------------ #
# Routing Engine tests
# ------------------------------------------------------------------ #

class TestRoutingEngine:
    def _engine(self, routes):
        return RoutingEngine([_route(*r) if isinstance(r, tuple) else r for r in routes])

    def _msg(self, source: str, msg_type: str) -> Message:
        return Message.create(
            payload={},
            metadata=MessageMetadata(source_agent=source, message_type=msg_type),
        )

    def test_simple_route_resolves(self):
        engine = RoutingEngine([_route("__entry__", "pass_through")])
        msg = self._msg("__entry__", "req.submitted")
        assert engine.resolve(msg) == ["pass_through"]

    def test_conditional_route_matching(self):
        routes = [
            _route("pass_through", "sink_agent",
                   "$.metadata.message_type == 'pass.out'"),
            _route("pass_through", "__dead_letter__",
                   "$.metadata.message_type == 'pass.blocked'"),
        ]
        engine = RoutingEngine(routes)
        msg = self._msg("pass_through", "pass.out")
        assert engine.resolve(msg) == ["sink_agent"]

    def test_conditional_route_non_matching(self):
        routes = [
            _route("pass_through", "sink_agent",
                   "$.metadata.message_type == 'pass.out'"),
        ]
        engine = RoutingEngine(routes)
        msg = self._msg("pass_through", "pass.OTHER")
        assert engine.resolve(msg) == []

    def test_no_matching_route_returns_empty(self):
        engine = RoutingEngine([_route("__entry__", "pass_through")])
        msg = self._msg("unknown_source", "foo.bar")
        assert engine.resolve(msg) == []

    def test_wildcard_from(self):
        routes = [_route("*", "__sink__")]
        engine = RoutingEngine(routes)
        msg = self._msg("anyone", "anything")
        assert engine.resolve(msg) == ["__sink__"]

    def test_validate_unknown_agent_raises(self):
        engine = RoutingEngine([
            _route("__entry__", "ghost"),
        ])
        with pytest.raises(RoutingError, match="ghost"):
            engine.validate({"pass_through"})

    def test_validate_unreachable_agent_raises(self):
        engine = RoutingEngine([
            _route("__entry__", "pass_through"),
            _route("pass_through", "__sink__"),
        ])
        with pytest.raises(RoutingError, match="sink_agent"):
            engine.validate({"pass_through", "sink_agent"})

    def test_validate_correct_graph_passes(self):
        engine = RoutingEngine([
            _route("__entry__", "pass_through"),
            _route("pass_through", "sink_agent"),
            _route("sink_agent", "__sink__"),
        ])
        engine.validate({"pass_through", "sink_agent"})  # no exception


# ------------------------------------------------------------------ #
# Orchestrator lifecycle tests
# ------------------------------------------------------------------ #

class TestOrchestratorLifecycle:
    @pytest.mark.asyncio
    async def test_start_and_shutdown(self):
        cfg = _system_config(
            agents=[_agent_cfg("pass_through")],
            routes=[
                _route("__entry__", "pass_through"),
                _route("pass_through", "__sink__"),
            ],
        )
        orch = Orchestrator(cfg)
        await orch.start()
        assert orch._started
        assert "pass_through" in orch._slots
        await orch.shutdown()
        assert not orch._started

    @pytest.mark.asyncio
    async def test_double_start_raises(self):
        cfg = _system_config(
            agents=[_agent_cfg("pass_through")],
            routes=[
                _route("__entry__", "pass_through"),
                _route("pass_through", "__sink__"),
            ],
        )
        orch = Orchestrator(cfg)
        await orch.start()
        with pytest.raises(RuntimeError, match="more than once"):
            await orch.start()
        await orch.shutdown()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        cfg = _system_config(
            agents=[_agent_cfg("pass_through")],
            routes=[
                _route("__entry__", "pass_through"),
                _route("pass_through", "__sink__"),
            ],
        )
        async with Orchestrator(cfg) as orch:
            assert orch._started
        assert not orch._started

    @pytest.mark.asyncio
    async def test_disabled_agent_not_instantiated(self):
        cfg = _system_config(
            agents=[
                _agent_cfg("pass_through", enabled=False),
                _agent_cfg("sink_agent"),
            ],
            routes=[
                _route("__entry__", "sink_agent"),
                _route("sink_agent", "__sink__"),
            ],
        )
        async with Orchestrator(cfg) as orch:
            assert "pass_through" not in orch._slots
            assert "sink_agent" in orch._slots


# ------------------------------------------------------------------ #
# Orchestrator message routing tests
# ------------------------------------------------------------------ #

class TestOrchestratorRouting:
    @pytest.mark.asyncio
    async def test_process_single_agent_pipeline(self):
        cfg = _system_config(
            agents=[_agent_cfg("pass_through", config={"output_type": "pass.done"})],
            routes=[
                _route("__entry__", "pass_through"),
                _route("pass_through", "__sink__"),
            ],
        )
        async with Orchestrator(cfg) as orch:
            result = await orch.process(
                {"job": "engineer"},
                correlation_id="corr-1",
                timeout_s=5.0,
            )
        assert result.payload == {"job": "engineer"}
        assert result.metadata.message_type == "pass.done"

    @pytest.mark.asyncio
    async def test_trace_id_propagated_through_pipeline(self):
        cfg = _system_config(
            agents=[_agent_cfg("pass_through")],
            routes=[
                _route("__entry__", "pass_through"),
                _route("pass_through", "__sink__"),
            ],
        )
        async with Orchestrator(cfg) as orch:
            result = await orch.process(
                {"data": "x"},
                trace_id="fixed-trace-id",
                timeout_s=5.0,
            )
        assert result.trace_id == "fixed-trace-id"

    @pytest.mark.asyncio
    async def test_conditional_routing_pii_gate(self):
        """Simulates the PII gate: 'scrubbed' goes to parsing, 'blocked' goes to DLQ."""

        class PIIStubAgent(BaseAgent):
            agent_id = "pii_stub"
            version = "1.0.0"
            async def initialize(self, config): await self._base_initialize(config)
            async def handle(self, message):
                # Emit 'scrubbed' if payload has key 'safe', else 'blocked'
                msg_type = (
                    "requisition.scrubbed"
                    if message.payload.get("safe")
                    else "requisition.pii_blocked"
                )
                yield Message.create(
                    payload=message.payload,
                    metadata=MessageMetadata(
                        source_agent=self.agent_id, message_type=msg_type
                    ),
                    trace_id=message.trace_id,
                )
            async def health_check(self): return HealthStatus.ok(self.agent_id, self.version)
            async def shutdown(self, graceful=True): self._initialized = False

        AgentRegistry.register(PIIStubAgent)

        cfg = _system_config(
            agents=[
                _agent_cfg("pii_stub"),
                _agent_cfg("pass_through", config={"output_type": "parsed.done"}),
            ],
            routes=[
                _route("__entry__", "pii_stub"),
                _route("pii_stub", "pass_through",
                       "$.metadata.message_type == 'requisition.scrubbed'"),
                _route("pii_stub", "__dead_letter__",
                       "$.metadata.message_type == 'requisition.pii_blocked'"),
                _route("pass_through", "__sink__"),
            ],
        )
        async with Orchestrator(cfg) as orch:
            # Safe payload → reaches sink
            result = await orch.process({"safe": True}, timeout_s=5.0)
            assert result.metadata.message_type == "parsed.done"

    @pytest.mark.asyncio
    async def test_dead_letter_fails_future(self):
        """A blocked message should cause the caller's Future to raise."""

        class BlockingAgent(BaseAgent):
            agent_id = "blocking_agent"
            version = "1.0.0"
            async def initialize(self, config): await self._base_initialize(config)
            async def handle(self, message):
                yield Message.create(
                    payload=message.payload,
                    metadata=MessageMetadata(
                        source_agent=self.agent_id,
                        message_type="blocked",
                    ),
                    trace_id=message.trace_id,
                )
            async def health_check(self): return HealthStatus.ok(self.agent_id, self.version)
            async def shutdown(self, graceful=True): self._initialized = False

        AgentRegistry.register(BlockingAgent)

        cfg = _system_config(
            agents=[_agent_cfg("blocking_agent")],
            routes=[
                _route("__entry__", "blocking_agent"),
                _route("blocking_agent", "__dead_letter__",
                       "$.metadata.message_type == 'blocked'"),
            ],
        )
        async with Orchestrator(cfg) as orch:
            with pytest.raises(RuntimeError, match="dead-lettered"):
                await orch.process({"data": "x"}, timeout_s=5.0)


# ------------------------------------------------------------------ #
# Backpressure and retry tests
# ------------------------------------------------------------------ #

class TestOrchestratorRetry:
    @pytest.mark.asyncio
    async def test_agent_timeout_dead_letters_message(self):
        """SlowAgent times out → message is dead-lettered → caller gets error."""
        cfg = _system_config(
            agents=[
                _agent_cfg(
                    "slow_agent",
                    config={"sleep_s": 30},
                    retry=RetryConfig(max_attempts=1, backoff="fixed", backoff_ms=0),
                    timeout_ms=100,   # 100ms timeout, agent sleeps 30s
                ),
            ],
            routes=[
                _route("__entry__", "slow_agent"),
                _route("slow_agent", "__sink__"),
            ],
        )
        async with Orchestrator(cfg) as orch:
            with pytest.raises((RuntimeError, asyncio.TimeoutError)):
                await orch.process({"data": "x"}, timeout_s=2.0)


# ------------------------------------------------------------------ #
# Health aggregation tests
# ------------------------------------------------------------------ #

class TestOrchestratorHealth:
    @pytest.mark.asyncio
    async def test_all_healthy_returns_ok(self):
        cfg = _system_config(
            agents=[_agent_cfg("pass_through"), _agent_cfg("sink_agent")],
            routes=[
                _route("__entry__", "pass_through"),
                _route("pass_through", "sink_agent"),
                _route("sink_agent", "__sink__"),
            ],
        )
        async with Orchestrator(cfg) as orch:
            health = await orch.get_health()

        assert health["status"] == "ok"
        assert "pass_through" in health["agents"]
        assert "sink_agent" in health["agents"]

    @pytest.mark.asyncio
    async def test_unavailable_agent_returns_unavailable(self):
        cfg = _system_config(
            agents=[_agent_cfg("failing_agent")],
            routes=[
                _route("__entry__", "failing_agent"),
                _route("failing_agent", "__sink__"),
            ],
        )
        async with Orchestrator(cfg) as orch:
            health = await orch.get_health()

        assert health["status"] == "unavailable"
        assert health["agents"]["failing_agent"]["state"] == "unavailable"

    @pytest.mark.asyncio
    async def test_queue_depths_reported(self):
        cfg = _system_config(
            agents=[_agent_cfg("pass_through")],
            routes=[
                _route("__entry__", "pass_through"),
                _route("pass_through", "__sink__"),
            ],
        )
        async with Orchestrator(cfg) as orch:
            health = await orch.get_health()

        assert "pass_through" in health["queue_depths"]
        assert isinstance(health["queue_depths"]["pass_through"], int)

    @pytest.mark.asyncio
    async def test_process_before_start_raises(self):
        cfg = _system_config(
            agents=[_agent_cfg("pass_through")],
            routes=[
                _route("__entry__", "pass_through"),
                _route("pass_through", "__sink__"),
            ],
        )
        orch = Orchestrator(cfg)
        with pytest.raises(RuntimeError, match="not been started"):
            await orch.process({"data": "x"})
