"""
Config loader and validator for the agent system.

Responsibilities
----------------
1. Load agents.yaml (with environment variable substitution).
2. Validate the top-level schema (system, infrastructure, agents, routing,
   observability, error_handling sections).
3. For each enabled agent, validate its agent-specific `config` block
   against the agent's own `config_schema` using jsonschema.
4. Validate the routing graph:
   - All `from` / `to` agent IDs exist in the agents list or are reserved
     (__entry__, __sink__, __dead_letter__).
   - No unreachable agents (every enabled agent is reachable from __entry__).
   - No duplicate route definitions.
5. FAIL FAST — raise ConfigError with a human-readable, structured message
   listing ALL violations found (not just the first one).

Usage
-----
    from app.agent_framework.config_loader import load_and_validate_config
    config = load_and_validate_config("config/agents.yaml")
    # config is a validated AgentSystemConfig object

The function raises ConfigError on any misconfiguration.
It is designed to be called once at application startup, before any agent
is instantiated.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

try:
    import jsonschema
    _JSONSCHEMA_AVAILABLE = True
except ImportError:
    _JSONSCHEMA_AVAILABLE = False


# ------------------------------------------------------------------ #
# Errors
# ------------------------------------------------------------------ #

class ConfigError(Exception):
    """
    Raised when the agent system config is invalid.

    The message contains a numbered list of ALL violations found,
    not just the first one.  This lets operators fix everything in
    one pass.
    """
    def __init__(self, violations: List[str]) -> None:
        self.violations = violations
        bullet_list = "\n".join(f"  [{i+1}] {v}" for i, v in enumerate(violations))
        super().__init__(
            f"Agent system config is invalid ({len(violations)} violation(s)):\n"
            f"{bullet_list}"
        )


# ------------------------------------------------------------------ #
# Pydantic config models
# ------------------------------------------------------------------ #

class RetryConfig(BaseModel):
    max_attempts: int = Field(ge=1, default=3)
    backoff: str = Field(default="exponential")
    backoff_ms: int = Field(ge=0, default=500)

    @field_validator("backoff")
    @classmethod
    def _valid_backoff(cls, v: str) -> str:
        allowed = {"exponential", "linear", "fixed"}
        if v not in allowed:
            raise ValueError(f"backoff must be one of {allowed}, got '{v}'")
        return v


class AgentConfig(BaseModel):
    id: str
    type: str
    enabled: bool = True
    version: Optional[str] = None
    replicas: int = Field(ge=1, default=1)
    config: Dict[str, Any] = Field(default_factory=dict)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    timeout_ms: int = Field(ge=100, default=30_000)


class RouteConfig(BaseModel):
    from_: str = Field(alias="from")
    to: str
    condition: Optional[str] = None
    transform: Optional[str] = None

    model_config = {"populate_by_name": True}


class DatabaseConfig(BaseModel):
    url: str
    pool_size: int = Field(ge=1, default=10)
    max_overflow: int = Field(ge=0, default=5)
    pool_timeout_s: int = Field(ge=1, default=30)


class RedisConfig(BaseModel):
    url: str
    socket_timeout_s: int = Field(ge=1, default=5)
    max_connections: int = Field(ge=1, default=20)


class LLMConfig(BaseModel):
    provider: str
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_input_rate: float = 0.0
    openai_output_rate: float = 0.0
    groq_api_key: Optional[str] = None
    groq_model: str = "llama3-70b-8192"
    google_api_key: Optional[str] = None
    google_model: str = "gemini-2.0-flash"
    temperature: float = Field(ge=0.0, le=2.0, default=0.1)
    max_tokens: int = Field(ge=1, default=4096)

    @field_validator("provider")
    @classmethod
    def _valid_provider(cls, v: str) -> str:
        allowed = {"openai", "groq", "google"}
        if v not in allowed:
            raise ValueError(f"LLM provider must be one of {allowed}, got '{v}'")
        return v


class EmbeddingConfig(BaseModel):
    provider: str = "google"
    model: str = "models/text-embedding-004"
    gemma_model_path: Optional[str] = None
    device: str = "cpu"

    @field_validator("provider")
    @classmethod
    def _valid_provider(cls, v: str) -> str:
        allowed = {"google", "gemma"}
        if v not in allowed:
            raise ValueError(f"Embedding provider must be one of {allowed}, got '{v}'")
        return v


class InfrastructureConfig(BaseModel):
    database: DatabaseConfig
    redis: RedisConfig
    llm: LLMConfig
    embedding: EmbeddingConfig


class SystemConfig(BaseModel):
    name: str
    log_level: str = "INFO"
    tracing: bool = True
    plugins_dir: str = "plugins/"

    @field_validator("log_level")
    @classmethod
    def _valid_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARN", "WARNING", "ERROR"}
        if v.upper() not in allowed:
            raise ValueError(f"log_level must be one of {allowed}, got '{v}'")
        return v.upper()


class ObservabilityConfig(BaseModel):
    metrics_port: int = Field(ge=1024, le=65535, default=9090)
    trace_exporter: str = "otlp"
    otlp_endpoint: Optional[str] = None
    log_format: str = "json"
    agent_log_levels: Dict[str, str] = Field(default_factory=dict)

    @field_validator("trace_exporter")
    @classmethod
    def _valid_exporter(cls, v: str) -> str:
        allowed = {"otlp", "stdout", "none"}
        if v not in allowed:
            raise ValueError(f"trace_exporter must be one of {allowed}, got '{v}'")
        return v

    @field_validator("log_format")
    @classmethod
    def _valid_format(cls, v: str) -> str:
        allowed = {"json", "text"}
        if v not in allowed:
            raise ValueError(f"log_format must be one of {allowed}, got '{v}'")
        return v


class DeadLetterConfig(BaseModel):
    backend: str = "redis"
    key_prefix: str = "dlq:agent:"
    ttl_s: int = Field(ge=60, default=86400)


class AlertingConfig(BaseModel):
    enabled: bool = False
    webhook_url: Optional[str] = None
    on_events: List[str] = Field(default_factory=list)


class ErrorHandlingConfig(BaseModel):
    dead_letter: DeadLetterConfig = Field(default_factory=DeadLetterConfig)
    alerting: AlertingConfig = Field(default_factory=AlertingConfig)


class AgentSystemConfig(BaseModel):
    """Top-level validated config object returned by load_and_validate_config()."""
    system: SystemConfig
    infrastructure: InfrastructureConfig
    agents: List[AgentConfig]
    routing: List[RouteConfig]
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    error_handling: ErrorHandlingConfig = Field(default_factory=ErrorHandlingConfig)


# ------------------------------------------------------------------ #
# Environment variable substitution
# ------------------------------------------------------------------ #

_ENV_VAR_RE = re.compile(r"^\$([A-Za-z_][A-Za-z0-9_]*)$")


def _substitute_env_vars(obj: Any, path: str = "") -> tuple[Any, List[str]]:
    """
    Recursively walk the parsed YAML and replace $VAR_NAME strings with
    their env var values.

    Returns (substituted_obj, list_of_missing_var_errors).
    Missing vars produce an error message but do NOT crash immediately —
    we collect all of them so the operator sees everything at once.
    """
    errors: List[str] = []

    if isinstance(obj, str):
        m = _ENV_VAR_RE.match(obj.strip())
        if m:
            var_name = m.group(1)
            value = os.environ.get(var_name)
            if value is None:
                errors.append(
                    f"Environment variable '${var_name}' referenced at "
                    f"config path '{path}' is not set."
                )
                return obj, errors   # keep placeholder so schema errors are clear
            return value, errors
        return obj, errors

    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            substituted, errs = _substitute_env_vars(v, path=f"{path}.{k}")
            result[k] = substituted
            errors.extend(errs)
        return result, errors

    if isinstance(obj, list):
        result = []
        for i, item in enumerate(obj):
            substituted, errs = _substitute_env_vars(item, path=f"{path}[{i}]")
            result.append(substituted)
            errors.extend(errs)
        return result, errors

    return obj, errors


# ------------------------------------------------------------------ #
# Routing graph validator
# ------------------------------------------------------------------ #

_RESERVED_NODES = {"__entry__", "__sink__", "__dead_letter__"}


def _validate_routing(
    routes: List[RouteConfig],
    enabled_agent_ids: Set[str],
) -> List[str]:
    """
    Check routing graph for structural problems.

    Returns a list of human-readable violation strings (empty = OK).
    """
    errors: List[str] = []
    valid_ids = enabled_agent_ids | _RESERVED_NODES

    # All referenced agent IDs must exist
    for i, route in enumerate(routes):
        for field_name, node_id in [("from", route.from_), ("to", route.to)]:
            # `to` can be a comma-separated list (multi-cast future extension)
            for nid in node_id.split(","):
                nid = nid.strip()
                if nid not in valid_ids:
                    errors.append(
                        f"routing[{i}]: '{field_name}' references unknown "
                        f"agent '{nid}'.  Known IDs: {sorted(valid_ids)}"
                    )

    # No duplicate (from, condition) pairs
    seen: Set[tuple] = set()
    for i, route in enumerate(routes):
        key = (route.from_, route.condition)
        if key in seen:
            errors.append(
                f"routing[{i}]: Duplicate route from='{route.from_}' "
                f"condition='{route.condition}'.  Routes must be unique."
            )
        seen.add(key)

    # Every enabled agent must be reachable from __entry__
    reachable: Set[str] = {"__entry__"}
    changed = True
    while changed:
        changed = False
        for route in routes:
            if route.from_ in reachable:
                for nid in route.to.split(","):
                    nid = nid.strip()
                    if nid not in reachable:
                        reachable.add(nid)
                        changed = True

    for agent_id in sorted(enabled_agent_ids):
        if agent_id not in reachable:
            errors.append(
                f"Agent '{agent_id}' is enabled but unreachable from "
                f"'__entry__'.  Add a routing rule that leads to it."
            )

    return errors


# ------------------------------------------------------------------ #
# Per-agent config schema validation
# ------------------------------------------------------------------ #

def _validate_agent_config_schemas(
    agents: List[AgentConfig],
) -> List[str]:
    """
    For each enabled agent, if its class is registered, validate the
    agent-specific `config` block against the agent's `config_schema`.

    Silently skips agents whose class is not yet in the registry
    (allows partial registration during migration).
    """
    errors: List[str] = []
    if not _JSONSCHEMA_AVAILABLE:
        return ["jsonschema package not installed — agent config schema "
                "validation is DISABLED.  Run: pip install jsonschema"]

    from app.agent_framework.registry import AgentRegistry

    for agent_cfg in agents:
        if not agent_cfg.enabled:
            continue
        try:
            cls = AgentRegistry.resolve(
                agent_cfg.id,
                version_constraint=agent_cfg.version,
            )
        except (KeyError, LookupError):
            # Agent not registered yet — skip schema validation for now.
            continue

        schema = getattr(cls, "config_schema", None)
        if not schema:
            continue

        try:
            jsonschema.validate(instance=agent_cfg.config, schema=schema)
        except jsonschema.ValidationError as exc:
            errors.append(
                f"agents[id={agent_cfg.id}].config failed schema validation: "
                f"{exc.message} (path: {'.'.join(str(p) for p in exc.path)})"
            )
    return errors


# ------------------------------------------------------------------ #
# Cross-field business rules
# ------------------------------------------------------------------ #

def _validate_business_rules(config: AgentSystemConfig) -> List[str]:
    """
    Validate rules that span multiple config sections and cannot be
    expressed in Pydantic field validators alone.
    """
    errors: List[str] = []

    llm = config.infrastructure.llm

    # LLM provider API key must be present
    if llm.provider == "openai" and not llm.openai_api_key:
        errors.append(
            "infrastructure.llm.provider is 'openai' but "
            "OPENAI_API_KEY is not set."
        )
    if llm.provider == "groq" and not llm.groq_api_key:
        errors.append(
            "infrastructure.llm.provider is 'groq' but "
            "GROQ_API_KEY is not set."
        )
    if llm.provider == "google" and not llm.google_api_key:
        errors.append(
            "infrastructure.llm.provider is 'google' but "
            "GOOGLE_API_KEY is not set."
        )

    # Gemma embedding requires a model path
    emb = config.infrastructure.embedding
    if emb.provider == "gemma" and not emb.gemma_model_path:
        errors.append(
            "infrastructure.embedding.provider is 'gemma' but "
            "GEMMA_MODEL_PATH is not set."
        )

    # OTLP exporter requires an endpoint
    obs = config.observability
    if obs.trace_exporter == "otlp" and not obs.otlp_endpoint:
        errors.append(
            "observability.trace_exporter is 'otlp' but "
            "OTLP_ENDPOINT is not set."
        )

    # Alerting webhook required when enabled
    if config.error_handling.alerting.enabled:
        if not config.error_handling.alerting.webhook_url:
            errors.append(
                "error_handling.alerting.enabled is true but "
                "ALERT_WEBHOOK_URL is not set."
            )

    # At least one agent must be enabled
    enabled = [a for a in config.agents if a.enabled]
    if not enabled:
        errors.append("No agents are enabled.  At least one must have enabled: true.")

    # Warn (as error) if results_backend=redis but Redis URL looks empty
    for a in config.agents:
        if (
            a.enabled
            and a.id == "result_aggregation"
            and a.config.get("results_backend") == "redis"
            and not config.infrastructure.redis.url.startswith("redis")
        ):
            errors.append(
                "agents[id=result_aggregation].config.results_backend is "
                "'redis' but infrastructure.redis.url does not look like "
                "a valid Redis URL."
            )

    return errors


# ------------------------------------------------------------------ #
# Public API
# ------------------------------------------------------------------ #

def load_and_validate_config(config_path: str | Path) -> AgentSystemConfig:
    """
    Load, substitute env vars, and validate the agent system config.

    Parameters
    ----------
    config_path:
        Path to the YAML config file (e.g. "config/agents.yaml").

    Returns
    -------
    AgentSystemConfig
        Fully validated config object, ready for the orchestrator.

    Raises
    ------
    FileNotFoundError
        If the config file does not exist.
    ConfigError
        If any validation violations are found.  The exception message
        lists ALL violations, not just the first one.
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Agent config file not found: {path.resolve()}\n"
            f"Copy config/agents.yaml to this path and populate it."
        )

    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):
        raise ConfigError(["Config file did not parse as a YAML mapping."])

    # ── Step 1: env var substitution ────────────────────────────────
    raw, env_errors = _substitute_env_vars(raw)

    # ── Step 2: top-level schema (Pydantic) ─────────────────────────
    pydantic_errors: List[str] = []
    config: Optional[AgentSystemConfig] = None
    try:
        config = AgentSystemConfig.model_validate(raw)
    except Exception as exc:
        # Pydantic v2 ValidationError has a list of errors
        if hasattr(exc, "errors"):
            for e in exc.errors():
                loc = ".".join(str(x) for x in e.get("loc", []))
                pydantic_errors.append(f"{loc}: {e['msg']}")
        else:
            pydantic_errors.append(str(exc))

    # Collect everything before raising
    all_errors = env_errors + pydantic_errors

    # ── Steps 3-5 only if basic structure is valid ───────────────────
    if config is not None:
        enabled_ids = {a.id for a in config.agents if a.enabled}

        routing_errors = _validate_routing(config.routing, enabled_ids)
        schema_errors = _validate_agent_config_schemas(config.agents)
        biz_errors = _validate_business_rules(config)

        all_errors += routing_errors + schema_errors + biz_errors

    if all_errors:
        raise ConfigError(all_errors)

    return config


def load_config_or_exit(config_path: str | Path) -> AgentSystemConfig:
    """
    Same as load_and_validate_config but prints errors and calls sys.exit(1)
    instead of raising.  Convenient for use in __main__ entry points.
    """
    import sys
    try:
        return load_and_validate_config(config_path)
    except FileNotFoundError as exc:
        print(f"\n❌  {exc}\n")
        sys.exit(1)
    except ConfigError as exc:
        print(f"\n❌  {exc}\n")
        sys.exit(1)
