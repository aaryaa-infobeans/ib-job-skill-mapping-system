"""
Unit tests for the agent framework interfaces.

These tests exercise BaseAgent, Message, HealthStatus, and AgentRegistry
WITHOUT any real app dependencies (no DB, no LLM, no PII model).

Run:
    pytest tests/unit/test_agent_framework.py -v
"""

from __future__ import annotations

import pytest
import asyncio
from typing import Any, AsyncIterator, Dict

from app.agent_framework.base_agent import BaseAgent
from app.agent_framework.health import HealthState, HealthStatus
from app.agent_framework.message import Message, MessageMetadata
from app.agent_framework.registry import AgentRegistry, _satisfies


# ------------------------------------------------------------------ #
# Minimal concrete agent for testing
# ------------------------------------------------------------------ #

class EchoAgent(BaseAgent):
    """Returns the payload unchanged — useful as a no-op stub."""

    agent_id = "echo"
    version = "1.0.0"
    config_schema = {
        "type": "object",
        "properties": {"echo_prefix": {"type": "string"}},
        "additionalProperties": False,
    }

    async def initialize(self, config: Dict[str, Any]) -> None:
        await self._base_initialize(config)
        self._prefix = config.get("echo_prefix", "")

    async def handle(self, message: Message) -> AsyncIterator[Message]:
        self._assert_initialized()
        yield Message.create(
            payload={"echo": self._prefix + str(message.payload)},
            metadata=MessageMetadata(
                source_agent=self.agent_id,
                message_type="echo.response",
            ),
            trace_id=message.trace_id,
        )

    async def health_check(self) -> HealthStatus:
        return HealthStatus.ok(self.agent_id, self.version)

    async def shutdown(self, graceful: bool = True) -> None:
        self._initialized = False


class VersionedEchoAgent(EchoAgent):
    """Same agent, newer version — for registry resolution tests."""
    version = "2.1.0"


# ------------------------------------------------------------------ #
# Message tests
# ------------------------------------------------------------------ #

class TestMessage:
    def test_create_generates_trace_id(self):
        msg = Message.create(
            payload={"foo": "bar"},
            metadata=MessageMetadata(
                source_agent="test",
                message_type="test.event",
            ),
        )
        assert msg.trace_id
        assert len(msg.trace_id) == 36  # UUID4

    def test_trace_id_propagates(self):
        original = Message.create(
            payload="hello",
            metadata=MessageMetadata(source_agent="a", message_type="a.out"),
        )
        downstream = Message.create(
            payload="world",
            metadata=MessageMetadata(source_agent="b", message_type="b.out"),
            trace_id=original.trace_id,
        )
        assert downstream.trace_id == original.trace_id

    def test_immutability(self):
        msg = Message.create(
            payload="x",
            metadata=MessageMetadata(source_agent="a", message_type="a.x"),
        )
        with pytest.raises(Exception):  # pydantic frozen raises ValidationError
            msg.trace_id = "tampered"

    def test_input_size_bytes(self):
        msg = Message.create(
            payload={"key": "value"},
            metadata=MessageMetadata(source_agent="a", message_type="a.x"),
        )
        assert msg.input_size_bytes > 0


# ------------------------------------------------------------------ #
# HealthStatus tests
# ------------------------------------------------------------------ #

class TestHealthStatus:
    def test_ok_prometheus_gauge(self):
        s = HealthStatus.ok("a", "1.0.0")
        assert s.prometheus_gauge == 1
        assert s.state == HealthState.OK

    def test_degraded_prometheus_gauge(self):
        s = HealthStatus.degraded("a", "1.0.0", "slow db")
        assert s.prometheus_gauge == 0
        assert s.state == HealthState.DEGRADED

    def test_unavailable_prometheus_gauge(self):
        s = HealthStatus.unavailable("a", "1.0.0", "db down")
        assert s.prometheus_gauge == 0
        assert s.state == HealthState.UNAVAILABLE


# ------------------------------------------------------------------ #
# BaseAgent contract tests
# ------------------------------------------------------------------ #

class TestBaseAgent:
    @pytest.mark.asyncio
    async def test_handle_before_initialize_raises(self):
        agent = EchoAgent()
        msg = Message.create(
            payload="hi",
            metadata=MessageMetadata(source_agent="test", message_type="test.in"),
        )
        with pytest.raises(RuntimeError, match="initialize"):
            async for _ in agent.handle(msg):
                pass

    @pytest.mark.asyncio
    async def test_handle_propagates_trace_id(self):
        agent = EchoAgent()
        await agent.initialize({})
        incoming = Message.create(
            payload="hello",
            metadata=MessageMetadata(source_agent="upstream", message_type="x.in"),
        )
        results = []
        async for out_msg in agent.handle(incoming):
            results.append(out_msg)
        assert len(results) == 1
        assert results[0].trace_id == incoming.trace_id

    @pytest.mark.asyncio
    async def test_handle_does_not_mutate_input(self):
        agent = EchoAgent()
        await agent.initialize({"echo_prefix": "PRE_"})
        original_payload = "test_payload"
        incoming = Message.create(
            payload=original_payload,
            metadata=MessageMetadata(source_agent="upstream", message_type="x.in"),
        )
        async for _ in agent.handle(incoming):
            pass
        assert incoming.payload == original_payload  # unchanged

    @pytest.mark.asyncio
    async def test_uptime_increases(self):
        import asyncio
        agent = EchoAgent()
        t0 = agent.uptime_seconds
        await asyncio.sleep(0.01)
        assert agent.uptime_seconds > t0

    @pytest.mark.asyncio
    async def test_shutdown_marks_uninitialized(self):
        agent = EchoAgent()
        await agent.initialize({})
        assert agent._initialized
        await agent.shutdown()
        assert not agent._initialized


# ------------------------------------------------------------------ #
# AgentRegistry tests
# ------------------------------------------------------------------ #

class TestAgentRegistry:
    def setup_method(self):
        # Isolate each test by clearing the registry then re-registering
        # the test agents only.
        AgentRegistry.clear()
        AgentRegistry.register(EchoAgent)
        AgentRegistry.register(VersionedEchoAgent)

    def teardown_method(self):
        AgentRegistry.clear()

    def test_register_and_resolve_latest(self):
        cls = AgentRegistry.resolve("echo")
        # Should return the highest version
        assert cls.version == "2.1.0"

    def test_resolve_with_constraint(self):
        cls = AgentRegistry.resolve("echo", version_constraint=">=1.0.0")
        assert cls.version == "2.1.0"

        cls = AgentRegistry.resolve("echo", version_constraint="<2.0.0")
        assert cls.version == "1.0.0"

    def test_resolve_exact_version(self):
        cls = AgentRegistry.resolve("echo", version_constraint="==1.0.0")
        assert cls.version == "1.0.0"

    def test_resolve_unknown_agent_raises(self):
        with pytest.raises(KeyError, match="unknown_agent"):
            AgentRegistry.resolve("unknown_agent")

    def test_resolve_unsatisfiable_constraint_raises(self):
        with pytest.raises(LookupError, match="constraint"):
            AgentRegistry.resolve("echo", version_constraint=">=99.0.0")

    def test_register_as_decorator(self):
        @AgentRegistry.register
        class DecoratedAgent(EchoAgent):
            agent_id = "decorated_echo"
            version = "3.0.0"

        assert "decorated_echo" in AgentRegistry.list_agents()

    def test_register_non_agent_raises(self):
        with pytest.raises(TypeError):
            AgentRegistry.register(object)

    def test_register_no_agent_id_raises(self):
        class BadAgent(EchoAgent):
            agent_id = ""  # empty

        with pytest.raises(ValueError, match="agent_id"):
            AgentRegistry.register(BadAgent)

    def test_list_agents(self):
        agents = AgentRegistry.list_agents()
        assert "echo" in agents
        assert "1.0.0" in agents["echo"]
        assert "2.1.0" in agents["echo"]

    def test_load_plugins_missing_dir(self, tmp_path):
        missing = tmp_path / "nonexistent"
        count = AgentRegistry.load_plugins(missing)
        assert count == 0

    def test_load_plugins_from_dir(self, tmp_path):
        plugin_code = '''
from app.agent_framework.base_agent import BaseAgent
from app.agent_framework.health import HealthStatus
from app.agent_framework.message import Message
from typing import Any, AsyncIterator, Dict

class PluginAgent(BaseAgent):
    agent_id = "plugin_test"
    version = "0.1.0"
    async def initialize(self, config): await self._base_initialize(config)
    async def handle(self, message): yield message
    async def health_check(self): return HealthStatus.ok(self.agent_id, self.version)
    async def shutdown(self, graceful=True): pass
'''
        (tmp_path / "my_plugin.py").write_text(plugin_code)
        count = AgentRegistry.load_plugins(tmp_path)
        assert count == 1
        assert "plugin_test" in AgentRegistry.list_agents()


# ------------------------------------------------------------------ #
# Semver helper tests
# ------------------------------------------------------------------ #

class TestSemver:
    @pytest.mark.parametrize("ver,constraint,expected", [
        ("1.2.3", ">=1.2.0", True),
        ("1.1.9", ">=1.2.0", False),
        ("2.0.0", ">=1.2.0", True),
        ("1.2.3", "==1.2.3", True),
        ("1.2.4", "==1.2.3", False),
        ("1.0.0", "<2.0.0", True),
        ("2.0.0", "<2.0.0", False),
        ("1.2.3", None, True),  # no constraint → always True
    ])
    def test_satisfies(self, ver, constraint, expected):
        assert _satisfies(ver, constraint) == expected
