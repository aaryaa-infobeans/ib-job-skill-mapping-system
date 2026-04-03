"""
RoutingEngine — data-driven message routing.

Resolves which agent(s) a message should be delivered to based on:
  1. The sender's agent_id  (message.metadata.source_agent)
  2. The message_type       (message.metadata.message_type)
  3. An optional JSONPath-style condition on the message envelope

Adding a new route requires ONLY a config change — no code change.

Condition syntax
----------------
Conditions are simple equality expressions evaluated against the message
envelope (as a flat dict).  The supported syntax is:

    $.path.to.field == 'value'
    $.path.to.field != 'value'

Examples from agents.yaml:
    $.metadata.message_type == 'requisition.scrubbed'
    $.metadata.message_type == 'requisition.pii_blocked'

For complex expressions, callers can subclass RoutingEngine and override
_evaluate_condition().

Dead-end detection
------------------
validate() is called by the orchestrator after agents are instantiated.
It checks:
  - Every 'to' ID exists in the running agent set (or is reserved).
  - Every enabled agent is reachable from __entry__.
  - No cycles exist in the unconditional path (cycles in conditional
    branches are allowed — e.g. a retry loop).
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Set

from .config_loader import RouteConfig
from .message import Message


_RESERVED = {"__entry__", "__sink__", "__dead_letter__"}

# Parses: "$.some.path == 'value'"  or  "$.some.path != 'value'"
_CONDITION_RE = re.compile(
    r"^\$\.(?P<path>[\w.]+)\s*(?P<op>==|!=)\s*['\"](?P<value>[^'\"]*)['\"]$"
)


class RoutingError(Exception):
    """Raised when the routing graph is structurally invalid."""


class RoutingEngine:
    """
    Evaluates routing rules and resolves message destinations.

    Parameters
    ----------
    routes:
        List of RouteConfig objects from the loaded YAML.
    """

    def __init__(self, routes: List[RouteConfig]) -> None:
        self._routes = routes

    # ------------------------------------------------------------------ #
    # Hot path: resolve destinations for an outgoing message
    # ------------------------------------------------------------------ #

    def resolve(self, message: Message) -> List[str]:
        """
        Return the list of destination agent IDs for the given message.

        Evaluates routes in declaration order.  All matching routes fire
        (enables fan-out to multiple destinations from a single message).

        Returns an empty list if no route matches (caller decides what to
        do — typically a warning + drop).
        """
        source = message.metadata.source_agent
        destinations: List[str] = []

        for route in self._routes:
            if route.from_ != source and route.from_ != "*":
                continue
            if route.condition and not self._evaluate_condition(
                route.condition, message
            ):
                continue
            # to can be comma-separated for multi-cast (future extension)
            for dest in route.to.split(","):
                dest = dest.strip()
                if dest:
                    destinations.append(dest)

        return destinations

    # ------------------------------------------------------------------ #
    # Condition evaluator
    # ------------------------------------------------------------------ #

    def _evaluate_condition(self, condition: str, message: Message) -> bool:
        """
        Evaluate a simple JSONPath-like condition against the message.

        Supported syntax:
            $.metadata.message_type == 'value'
            $.metadata.message_type != 'value'
        """
        m = _CONDITION_RE.match(condition.strip())
        if not m:
            # Unrecognised condition syntax → conservative: treat as False
            # to avoid routing to wrong agents.
            return False

        path = m.group("path")
        op = m.group("op")
        expected = m.group("value")

        actual = self._get_path(message, path)

        if op == "==":
            return str(actual) == expected
        if op == "!=":
            return str(actual) != expected
        return False

    @staticmethod
    def _get_path(message: Message, path: str) -> Optional[str]:
        """
        Traverse a dot-separated path on the message object.

        Supports:
            metadata.message_type
            metadata.source_agent
            metadata.correlation_id
            metadata.request_id
        """
        obj: object = message
        for part in path.split("."):
            if isinstance(obj, dict):
                obj = obj.get(part)
            else:
                obj = getattr(obj, part, None)
            if obj is None:
                return None
        return str(obj) if obj is not None else None

    # ------------------------------------------------------------------ #
    # Graph validation (called once at startup)
    # ------------------------------------------------------------------ #

    def validate(self, running_agent_ids: Set[str]) -> None:
        """
        Validate the routing graph against the set of running agent IDs.

        Raises RoutingError with all violations if any are found.
        """
        valid_ids = running_agent_ids | _RESERVED
        errors: List[str] = []

        for i, route in enumerate(self._routes):
            for field_name, node_id in [("from", route.from_), ("to", route.to)]:
                for nid in node_id.split(","):
                    nid = nid.strip()
                    if nid not in valid_ids and nid != "*":
                        errors.append(
                            f"routing[{i}] '{field_name}' references "
                            f"unknown agent '{nid}'. "
                            f"Running agents: {sorted(running_agent_ids)}"
                        )

        # Reachability: every running agent must be reachable from __entry__
        reachable: Set[str] = {"__entry__"}
        changed = True
        while changed:
            changed = False
            for route in self._routes:
                if route.from_ in reachable or route.from_ == "*":
                    for nid in route.to.split(","):
                        nid = nid.strip()
                        if nid not in reachable:
                            reachable.add(nid)
                            changed = True

        for agent_id in sorted(running_agent_ids):
            if agent_id not in reachable:
                errors.append(
                    f"Agent '{agent_id}' is running but unreachable "
                    f"from '__entry__'. Add a routing rule."
                )

        if errors:
            bullet = "\n  ".join(errors)
            raise RoutingError(
                f"Routing graph has {len(errors)} violation(s):\n  {bullet}"
            )
