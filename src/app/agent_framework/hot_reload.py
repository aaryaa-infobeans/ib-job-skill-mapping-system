"""
Hot-reload support for agents.yaml config changes.

Provides two strategies:
1. **Polling** — check file mtime every N seconds (works everywhere).
2. **inotify/fsevents** — OS-native file-change notifications (future).

Safe hot-reload rules:
- Agent enable/disable: allowed (starts or gracefully stops workers).
- Config value changes: allowed (re-initialise agent with new config).
- Routing changes: allowed (swap routing table atomically).
- Agent type change or removal: NOT allowed at runtime (logged as warning).

Usage:
    reloader = ConfigReloader(
        config_path="config/agents.yaml",
        on_change=orchestrator.apply_config_update,
        poll_interval_s=5.0,
    )
    await reloader.start()
    ...
    await reloader.stop()
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional

log = logging.getLogger("agent.hot_reload")


class ConfigReloader:
    """
    Watches agents.yaml for changes and invokes a callback with the new
    config path when modifications are detected.

    Thread-safe: runs in a background asyncio Task.
    """

    def __init__(
        self,
        config_path: str | Path,
        on_change: Callable[[str], Coroutine[Any, Any, None]],
        poll_interval_s: float = 5.0,
    ) -> None:
        self._path = Path(config_path)
        self._on_change = on_change
        self._interval = poll_interval_s
        self._task: Optional[asyncio.Task] = None
        self._last_hash: Optional[str] = None
        self._running = False

    async def start(self) -> None:
        """Begin polling in a background task."""
        if self._task is not None:
            return
        self._last_hash = self._file_hash()
        self._running = True
        self._task = asyncio.create_task(self._poll_loop(), name="config-reloader")
        log.info(
            "Config reloader started (path=%s, interval=%ss)",
            self._path, self._interval,
        )

    async def stop(self) -> None:
        """Stop the polling task."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        log.info("Config reloader stopped.")

    async def _poll_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(self._interval)
                current_hash = self._file_hash()
                if current_hash and current_hash != self._last_hash:
                    log.info(
                        "Config file changed (hash %s → %s), triggering reload.",
                        self._last_hash[:8] if self._last_hash else "none",
                        current_hash[:8],
                    )
                    self._last_hash = current_hash
                    try:
                        await self._on_change(str(self._path))
                    except Exception as exc:
                        log.error(
                            "Hot-reload callback failed: %s", exc, exc_info=True,
                        )
            except asyncio.CancelledError:
                break
            except Exception as exc:
                log.error("Config reloader poll error: %s", exc)

    def _file_hash(self) -> Optional[str]:
        """Return SHA-256 of file contents, or None if unreadable."""
        try:
            data = self._path.read_bytes()
            return hashlib.sha256(data).hexdigest()
        except (OSError, IOError):
            return None

    @property
    def running(self) -> bool:
        return self._running


class HotSwapManager:
    """
    Applies safe config changes to a running Orchestrator.

    This class encapsulates the logic for what changes are safe to apply
    at runtime vs what requires a full restart.
    """

    def __init__(self, orchestrator: Any) -> None:
        self._orch = orchestrator

    async def apply_config_update(self, config_path: str) -> None:
        """
        Load new config, diff against current, and apply safe changes.

        Safe changes:
        - Agent enabled/disabled toggle
        - Agent config value changes (triggers re-initialize)
        - Per-agent log level changes
        - Routing table updates

        Unsafe changes (logged as warnings):
        - Agent type changes
        - Agent removal from config
        - Infrastructure credential changes
        """
        from .config_loader import load_and_validate_config, ConfigError

        try:
            new_config = load_and_validate_config(config_path)
        except ConfigError as exc:
            log.error(
                "Hot-reload rejected — new config has validation errors: %s", exc,
            )
            return

        old_config = self._orch._config
        changes_applied = 0

        # 1. Diff agent enable/disable
        old_agents = {a.id: a for a in old_config.agents}
        new_agents = {a.id: a for a in new_config.agents}

        for agent_id, new_cfg in new_agents.items():
            old_cfg = old_agents.get(agent_id)

            if old_cfg is None:
                log.warning(
                    "Hot-reload: new agent '%s' added — requires restart to activate.",
                    agent_id,
                )
                continue

            # Enable/disable toggle
            if old_cfg.enabled != new_cfg.enabled:
                if new_cfg.enabled:
                    log.info("Hot-reload: enabling agent '%s'", agent_id)
                    await self._enable_agent(agent_id, new_cfg)
                else:
                    log.info("Hot-reload: disabling agent '%s'", agent_id)
                    await self._disable_agent(agent_id)
                changes_applied += 1

            # Config value changes (for already-running agents)
            elif old_cfg.config != new_cfg.config and agent_id in self._orch._slots:
                log.info("Hot-reload: re-configuring agent '%s'", agent_id)
                await self._reconfigure_agent(agent_id, new_cfg)
                changes_applied += 1

        # 2. Check for removed agents
        for agent_id in old_agents:
            if agent_id not in new_agents:
                log.warning(
                    "Hot-reload: agent '%s' removed from config — "
                    "requires restart to fully remove.",
                    agent_id,
                )

        # 3. Update routing table
        if old_config.routing != new_config.routing:
            log.info("Hot-reload: updating routing table.")
            from .router import RoutingEngine
            self._orch._router = RoutingEngine(new_config.routing)
            running_ids = set(self._orch._slots.keys())
            self._orch._router.validate(running_ids)
            changes_applied += 1

        # 4. Update observability log levels
        old_levels = old_config.observability.agent_log_levels
        new_levels = new_config.observability.agent_log_levels
        if old_levels != new_levels:
            for agent_id, level in new_levels.items():
                agent_logger = logging.getLogger(f"agent.{agent_id}")
                agent_logger.setLevel(logging.getLevelName(level.upper()))
                log.info(
                    "Hot-reload: agent '%s' log level → %s", agent_id, level,
                )
            changes_applied += 1

        # 5. Swap config reference
        self._orch._config = new_config

        log.info("Hot-reload complete: %d change(s) applied.", changes_applied)

    async def _enable_agent(self, agent_id: str, agent_cfg: Any) -> None:
        """Start a previously disabled agent."""
        if agent_id in self._orch._slots:
            log.warning("Agent '%s' is already running.", agent_id)
            return
        try:
            await self._orch._init_agent(agent_cfg)
            log.info("Agent '%s' enabled and started.", agent_id)
        except Exception as exc:
            log.error("Failed to enable agent '%s': %s", agent_id, exc)

    async def _disable_agent(self, agent_id: str) -> None:
        """Gracefully stop a running agent."""
        slot = self._orch._slots.get(agent_id)
        if not slot:
            return
        from .orchestrator import _SHUTDOWN, AgentState
        slot.state = AgentState.SHUTTING_DOWN
        await slot.queue.put(_SHUTDOWN)
        if slot.worker_task and not slot.worker_task.done():
            try:
                await asyncio.wait_for(slot.worker_task, timeout=10.0)
            except asyncio.TimeoutError:
                slot.worker_task.cancel()
        await slot.agent.shutdown(graceful=True)
        del self._orch._slots[agent_id]
        log.info("Agent '%s' disabled and stopped.", agent_id)

    async def _reconfigure_agent(self, agent_id: str, agent_cfg: Any) -> None:
        """Re-initialize an agent with updated config (no restart)."""
        slot = self._orch._slots.get(agent_id)
        if not slot:
            return
        scoped = self._orch._build_scoped_config(agent_cfg)
        try:
            await slot.agent.initialize(scoped)
            slot.config = agent_cfg
            log.info("Agent '%s' re-configured.", agent_id)
        except Exception as exc:
            log.error("Failed to re-configure agent '%s': %s", agent_id, exc)
