"""
AgentRegistry — maps agent_id → agent class with versioning and plugin support.

Discovery order (first match wins)
-----------------------------------
1. Built-in agents registered via  AgentRegistry.register()  at import time.
2. Plugin agents discovered from the  plugins/  directory (Python .py files
   that export a subclass of BaseAgent with agent_id set).
3. Remote agents (future extension point — see TODO below).

Version resolution
------------------
If the config specifies  version: ">=1.2.0"  the registry resolves the
best available version using semver rules.  If no version constraint is
given, the latest registered version is used.

Thread safety
-------------
The registry is a module-level singleton.  Reads are safe.  Writes
(register / load_plugins) should only happen at startup before any agent
is instantiated.
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import logging
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple, Type

log = logging.getLogger("agent.registry")


# We import BaseAgent lazily inside methods to avoid circular imports.
def _base_agent_class():
    from .base_agent import BaseAgent
    return BaseAgent


# ------------------------------------------------------------------ #
# Semver helpers (no external dependency)
# ------------------------------------------------------------------ #

def _parse_semver(v: str) -> Tuple[int, int, int]:
    """Parse 'MAJOR.MINOR.PATCH' into a sortable tuple."""
    parts = v.lstrip("v").split(".")
    try:
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except (IndexError, ValueError):
        return (0, 0, 0)


def _satisfies(version: str, constraint: Optional[str]) -> bool:
    """
    Evaluate a simple semver constraint against a version string.

    Supported operators: >=, <=, >, <, ==, =, (none → exact match).
    Examples: ">=1.2.0", "==2.0.0", "2.1.3"
    """
    if not constraint:
        return True
    constraint = constraint.strip()
    for op in (">=", "<=", ">", "<", "==", "="):
        if constraint.startswith(op):
            required = _parse_semver(constraint[len(op):])
            actual = _parse_semver(version)
            if op == ">=":
                return actual >= required
            if op == "<=":
                return actual <= required
            if op == ">":
                return actual > required
            if op == "<":
                return actual < required
            if op in ("==", "="):
                return actual == required
    # No operator → exact match
    return _parse_semver(version) == _parse_semver(constraint)


# ------------------------------------------------------------------ #
# Registry
# ------------------------------------------------------------------ #

class AgentRegistry:
    """
    Central registry for all agent classes.

    Usage
    -----
    # At module level (built-ins):
    from app.agent_framework import AgentRegistry
    AgentRegistry.register(PIIScrubberAgent)

    # In orchestrator:
    cls = AgentRegistry.resolve("pii_scrubber", version_constraint=">=1.0.0")
    agent = cls()
    await agent.initialize(config)
    """

    # { agent_id: { version_str: agent_class } }
    _store: Dict[str, Dict[str, Type]] = {}

    # ------------------------------------------------------------------ #
    # Registration
    # ------------------------------------------------------------------ #
    @classmethod
    def register(cls, agent_class: Type) -> Type:
        """
        Register an agent class.

        Can be used as a decorator:

            @AgentRegistry.register
            class PIIScrubberAgent(BaseAgent):
                agent_id = "pii_scrubber"
                version  = "1.0.0"

        Or called directly:

            AgentRegistry.register(PIIScrubberAgent)
        """
        BaseAgent = _base_agent_class()
        if not (inspect.isclass(agent_class) and issubclass(agent_class, BaseAgent)):
            raise TypeError(
                f"AgentRegistry.register expects a BaseAgent subclass, "
                f"got {agent_class!r}"
            )
        aid = getattr(agent_class, "agent_id", "")
        ver = getattr(agent_class, "version", "0.0.0")
        if not aid:
            raise ValueError(
                f"Agent class {agent_class.__name__} must set agent_id."
            )
        cls._store.setdefault(aid, {})[ver] = agent_class
        log.debug("Registered agent %s v%s", aid, ver)
        return agent_class  # allow use as decorator

    # ------------------------------------------------------------------ #
    # Resolution
    # ------------------------------------------------------------------ #
    @classmethod
    def resolve(
        cls,
        agent_id: str,
        version_constraint: Optional[str] = None,
    ) -> Type:
        """
        Return the best matching agent class.

        Parameters
        ----------
        agent_id:
            The stable identifier, e.g. "pii_scrubber".
        version_constraint:
            Optional semver constraint, e.g. ">=1.2.0".
            If None, the latest registered version is returned.

        Raises
        ------
        KeyError
            If agent_id is not registered at all.
        LookupError
            If agent_id is registered but no version satisfies the constraint.
        """
        if agent_id not in cls._store:
            raise KeyError(
                f"Agent '{agent_id}' is not registered.  "
                f"Available: {sorted(cls._store.keys())}"
            )
        candidates = {
            ver: klass
            for ver, klass in cls._store[agent_id].items()
            if _satisfies(ver, version_constraint)
        }
        if not candidates:
            available = sorted(cls._store[agent_id].keys())
            raise LookupError(
                f"No version of agent '{agent_id}' satisfies constraint "
                f"'{version_constraint}'.  Available: {available}"
            )
        # Pick the highest semver among candidates
        best_ver = max(candidates, key=_parse_semver)
        return candidates[best_ver]

    # ------------------------------------------------------------------ #
    # Plugin discovery
    # ------------------------------------------------------------------ #
    @classmethod
    def load_plugins(cls, plugins_dir: Path) -> int:
        """
        Discover and register agents from .py files in plugins_dir.

        Each plugin file must export exactly one BaseAgent subclass with
        agent_id set.  Files that fail to import are logged and skipped
        (no crash — bad plugins should not take down the system).

        Returns the number of agents successfully loaded.
        """
        if not plugins_dir.exists():
            log.debug("Plugin directory %s does not exist; skipping.", plugins_dir)
            return 0

        loaded = 0
        for py_file in sorted(plugins_dir.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            module_name = f"_plugin_{py_file.stem}"
            try:
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                BaseAgent = _base_agent_class()
                for _, obj in inspect.getmembers(module, inspect.isclass):
                    if (
                        issubclass(obj, BaseAgent)
                        and obj is not BaseAgent
                        and getattr(obj, "agent_id", "")
                    ):
                        cls.register(obj)
                        loaded += 1
            except Exception as exc:
                log.error(
                    "Failed to load plugin %s: %s",
                    py_file,
                    exc,
                    exc_info=True,
                )
        log.info("Loaded %d agent(s) from plugin directory %s", loaded, plugins_dir)
        return loaded

    # ------------------------------------------------------------------ #
    # Introspection
    # ------------------------------------------------------------------ #
    @classmethod
    def list_agents(cls) -> Dict[str, list]:
        """Return {agent_id: [versions]} for all registered agents."""
        return {aid: sorted(versions.keys()) for aid, versions in cls._store.items()}

    @classmethod
    def clear(cls) -> None:
        """Reset the registry (useful in tests)."""
        cls._store.clear()
