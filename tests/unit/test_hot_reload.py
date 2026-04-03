"""
Phase 8 — Hot-Reload and Plug-and-Play tests.

Tests:
1. ConfigReloader — polling, hash change detection, callback invocation
2. HotSwapManager — enable/disable agents, config updates, routing swaps
3. Feature flag (enabled toggle) — runtime agent kill-switch
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent_framework.base_agent import BaseAgent
from app.agent_framework.config_loader import (
    AgentConfig, AgentSystemConfig, DatabaseConfig,
    DeadLetterConfig, ErrorHandlingConfig, InfrastructureConfig,
    LLMConfig, EmbeddingConfig, ObservabilityConfig, RedisConfig,
    RetryConfig, RouteConfig, SystemConfig, AlertingConfig,
)
from app.agent_framework.health import HealthStatus
from app.agent_framework.hot_reload import ConfigReloader, HotSwapManager
from app.agent_framework.message import Message, MessageMetadata
from app.agent_framework.observability import AgentMetrics
from app.agent_framework.orchestrator import Orchestrator
from app.agent_framework.registry import AgentRegistry

from prometheus_client import CollectorRegistry


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _route(from_: str, to: str, condition=None) -> RouteConfig:
    return RouteConfig.model_validate({"from": from_, "to": to, "condition": condition})


def _make_config(agents_cfg, routes):
    return AgentSystemConfig(
        system=SystemConfig(name="reload-test", version="1.0.0"),
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


class _ToggleAgent(BaseAgent):
    agent_id = "toggle_agent"
    version = "1.0.0"
    config_schema: Dict[str, Any] = {"type": "object", "additionalProperties": True}

    async def initialize(self, config):
        await self._base_initialize(config)
        self.last_config = config

    async def handle(self, message: Message) -> AsyncIterator[Message]:
        yield Message.create(
            payload=message.payload,
            metadata=MessageMetadata(
                source_agent=self.agent_id,
                message_type="toggle.done",
                correlation_id=message.metadata.correlation_id,
                request_id=message.metadata.request_id,
            ),
            trace_id=message.trace_id,
        )

    async def health_check(self):
        return HealthStatus.ok(self.agent_id, self.version)

    async def shutdown(self, graceful=True):
        self._initialized = False


class _SecondAgent(BaseAgent):
    agent_id = "second_agent"
    version = "1.0.0"
    config_schema: Dict[str, Any] = {"type": "object", "additionalProperties": True}

    async def initialize(self, config):
        await self._base_initialize(config)

    async def handle(self, message: Message) -> AsyncIterator[Message]:
        yield Message.create(
            payload=message.payload,
            metadata=MessageMetadata(
                source_agent=self.agent_id,
                message_type="second.done",
                correlation_id=message.metadata.correlation_id,
                request_id=message.metadata.request_id,
            ),
            trace_id=message.trace_id,
        )

    async def health_check(self):
        return HealthStatus.ok(self.agent_id, self.version)

    async def shutdown(self, graceful=True):
        self._initialized = False


@pytest.fixture(autouse=True)
def _clean_registry():
    AgentRegistry.clear()
    AgentRegistry.register(_ToggleAgent)
    AgentRegistry.register(_SecondAgent)
    yield
    AgentRegistry.clear()


# ================================================================== #
# 1. ConfigReloader tests
# ================================================================== #

class TestConfigReloader:

    @pytest.mark.asyncio
    async def test_detects_file_change(self):
        """Reloader fires callback when file hash changes."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("version: 1")
            f.flush()
            path = f.name

        callback = AsyncMock()
        reloader = ConfigReloader(
            config_path=path,
            on_change=callback,
            poll_interval_s=0.1,
        )

        await reloader.start()
        assert reloader.running

        # Modify file
        await asyncio.sleep(0.05)
        Path(path).write_text("version: 2")

        # Wait for poll to detect
        await asyncio.sleep(0.3)

        await reloader.stop()
        assert not reloader.running

        callback.assert_called_once_with(path)
        os.unlink(path)

    @pytest.mark.asyncio
    async def test_no_callback_if_unchanged(self):
        """Reloader does NOT fire callback if file hasn't changed."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("version: 1")
            f.flush()
            path = f.name

        callback = AsyncMock()
        reloader = ConfigReloader(
            config_path=path,
            on_change=callback,
            poll_interval_s=0.1,
        )

        await reloader.start()
        await asyncio.sleep(0.3)
        await reloader.stop()

        callback.assert_not_called()
        os.unlink(path)

    @pytest.mark.asyncio
    async def test_handles_missing_file_gracefully(self):
        """Reloader doesn't crash if config file disappears."""
        callback = AsyncMock()
        reloader = ConfigReloader(
            config_path="/nonexistent/agents.yaml",
            on_change=callback,
            poll_interval_s=0.1,
        )

        await reloader.start()
        await asyncio.sleep(0.2)
        await reloader.stop()

        callback.assert_not_called()


# ================================================================== #
# 2. HotSwapManager tests
# ================================================================== #

class TestHotSwapManager:

    @pytest.mark.asyncio
    async def test_disable_running_agent(self):
        """Disabling an agent via hot-swap stops its worker."""
        prom_registry = CollectorRegistry()
        metrics = AgentMetrics(registry=prom_registry)

        config = _make_config(
            agents_cfg=[
                AgentConfig(id="toggle_agent", type="toggle_agent", enabled=True,
                            retry=RetryConfig(), config={}),
            ],
            routes=[
                _route("__entry__", "toggle_agent"),
                _route("toggle_agent", "__sink__"),
            ],
        )

        orch = Orchestrator(config, metrics=metrics)
        await orch.start()
        assert "toggle_agent" in orch._slots

        manager = HotSwapManager(orch)
        await manager._disable_agent("toggle_agent")

        assert "toggle_agent" not in orch._slots
        await orch.shutdown()

    @pytest.mark.asyncio
    async def test_enable_previously_disabled_agent(self):
        """Enabling a disabled agent starts it at runtime."""
        prom_registry = CollectorRegistry()
        metrics = AgentMetrics(registry=prom_registry)

        config = _make_config(
            agents_cfg=[
                AgentConfig(id="toggle_agent", type="toggle_agent", enabled=True,
                            retry=RetryConfig(), config={}),
            ],
            routes=[
                _route("__entry__", "toggle_agent"),
                _route("toggle_agent", "__sink__"),
            ],
        )

        orch = Orchestrator(config, metrics=metrics)
        await orch.start()

        manager = HotSwapManager(orch)

        # Disable first
        await manager._disable_agent("toggle_agent")
        assert "toggle_agent" not in orch._slots

        # Re-enable
        new_cfg = AgentConfig(
            id="toggle_agent", type="toggle_agent", enabled=True,
            retry=RetryConfig(), config={},
        )
        await manager._enable_agent("toggle_agent", new_cfg)
        assert "toggle_agent" in orch._slots

        await orch.shutdown()

    @pytest.mark.asyncio
    async def test_reconfigure_updates_agent_config(self):
        """Reconfiguring an agent re-initializes with new config."""
        prom_registry = CollectorRegistry()
        metrics = AgentMetrics(registry=prom_registry)

        config = _make_config(
            agents_cfg=[
                AgentConfig(id="toggle_agent", type="toggle_agent", enabled=True,
                            retry=RetryConfig(), config={"threshold": 0.5}),
            ],
            routes=[
                _route("__entry__", "toggle_agent"),
                _route("toggle_agent", "__sink__"),
            ],
        )

        orch = Orchestrator(config, metrics=metrics)
        await orch.start()

        manager = HotSwapManager(orch)

        new_cfg = AgentConfig(
            id="toggle_agent", type="toggle_agent", enabled=True,
            retry=RetryConfig(), config={"threshold": 0.9},
        )
        await manager._reconfigure_agent("toggle_agent", new_cfg)

        # Agent should have been re-initialized with new config
        slot = orch._slots["toggle_agent"]
        assert slot.agent.last_config.get("threshold") == 0.9

        await orch.shutdown()


# ================================================================== #
# 3. Feature flag (enabled toggle) integration test
# ================================================================== #

class TestFeatureFlagToggle:

    @pytest.mark.asyncio
    async def test_disabled_agent_skipped_at_startup(self):
        """Agent with enabled=false is not instantiated."""
        prom_registry = CollectorRegistry()
        metrics = AgentMetrics(registry=prom_registry)

        config = _make_config(
            agents_cfg=[
                AgentConfig(id="toggle_agent", type="toggle_agent", enabled=False,
                            retry=RetryConfig(), config={}),
                AgentConfig(id="second_agent", type="second_agent", enabled=True,
                            retry=RetryConfig(), config={}),
            ],
            routes=[
                _route("__entry__", "second_agent"),
                _route("second_agent", "__sink__"),
            ],
        )

        orch = Orchestrator(config, metrics=metrics)
        await orch.start()

        assert "toggle_agent" not in orch._slots
        assert "second_agent" in orch._slots

        await orch.shutdown()

    @pytest.mark.asyncio
    async def test_runtime_disable_then_process(self):
        """After hot-disabling an agent, the remaining pipeline still works."""
        prom_registry = CollectorRegistry()
        metrics = AgentMetrics(registry=prom_registry)

        config = _make_config(
            agents_cfg=[
                AgentConfig(id="toggle_agent", type="toggle_agent", enabled=True,
                            retry=RetryConfig(), config={}),
                AgentConfig(id="second_agent", type="second_agent", enabled=True,
                            retry=RetryConfig(), config={}),
            ],
            routes=[
                _route("__entry__", "toggle_agent"),
                _route("toggle_agent", "second_agent"),
                _route("second_agent", "__sink__"),
            ],
        )

        orch = Orchestrator(config, metrics=metrics)
        await orch.start()
        assert "toggle_agent" in orch._slots

        # Disable toggle_agent at runtime
        manager = HotSwapManager(orch)
        await manager._disable_agent("toggle_agent")
        assert "toggle_agent" not in orch._slots

        # Update routing to bypass disabled agent
        from app.agent_framework.router import RoutingEngine
        new_routes = [
            _route("__entry__", "second_agent"),
            _route("second_agent", "__sink__"),
        ]
        orch._router = RoutingEngine(new_routes)
        orch._router.validate(set(orch._slots.keys()))

        # Pipeline should still work through second_agent
        result = await orch.process(
            payload={"request_id": "r", "correlation_id": "c"},
            timeout_s=5,
        )
        assert result.metadata.message_type == "second.done"

        await orch.shutdown()
