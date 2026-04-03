"""
Agent Framework — plug-and-play multi-agent runtime for the IB Job Skill Mapping System.

Public surface:
    BaseAgent        — ABC every agent must implement
    Message          — typed envelope for all inter-agent communication
    HealthStatus     — standardised health report
    AgentRegistry    — maps agent_id → agent class; supports dynamic loading
    Orchestrator     — manages lifecycle, routing, backpressure, shutdown
    RoutingEngine    — data-driven message routing
    load_and_validate_config — load + validate agents.yaml at startup
"""

from .base_agent import BaseAgent
from .message import Message, MessageMetadata
from .health import HealthStatus, HealthState
from .registry import AgentRegistry
from .router import RoutingEngine, RoutingError
from .orchestrator import Orchestrator
from .config_loader import load_and_validate_config, ConfigError
from .observability import AgentMetrics, AgentTracer, DeadLetterStore, TraceLogAdapter

__all__ = [
    "BaseAgent",
    "Message",
    "MessageMetadata",
    "HealthStatus",
    "HealthState",
    "AgentRegistry",
    "RoutingEngine",
    "RoutingError",
    "Orchestrator",
    "load_and_validate_config",
    "ConfigError",
    "AgentMetrics",
    "AgentTracer",
    "DeadLetterStore",
    "TraceLogAdapter",
]
