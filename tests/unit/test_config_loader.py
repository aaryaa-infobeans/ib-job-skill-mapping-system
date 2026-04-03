"""
Unit tests for the config loader and validator.

Tests validate that:
- A well-formed config loads successfully.
- Every class of misconfiguration produces a clear error message.
- Environment variable substitution works correctly.
- Missing required env vars are caught before any agent initialises.
- Routing graph violations (unknown agents, unreachable agents,
  duplicate routes) are all caught.
- ALL violations are reported together (not just the first one).

Run:
    pytest tests/unit/test_config_loader.py -v --noconftest
"""

from __future__ import annotations

import os
import textwrap
from pathlib import Path

import pytest
import yaml

from app.agent_framework.config_loader import (
    AgentSystemConfig,
    ConfigError,
    _substitute_env_vars,
    _validate_routing,
    load_and_validate_config,
)
from app.agent_framework.config_loader import RouteConfig


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _write_config(tmp_path: Path, data: dict) -> Path:
    """Write a dict as YAML to a temp file and return the path."""
    p = tmp_path / "agents.yaml"
    p.write_text(yaml.dump(data, default_flow_style=False))
    return p


def _minimal_config(overrides: dict | None = None) -> dict:
    """
    Return a minimal VALID config dict.

    Passes all validators.  Use overrides to break specific parts.
    """
    base = {
        "system": {
            "name": "test-system",
            "log_level": "INFO",
            "tracing": False,
        },
        "infrastructure": {
            "database": {"url": "postgresql+asyncpg://u:p@localhost/db"},
            "redis": {"url": "redis://localhost:6379/0"},
            "llm": {
                "provider": "openai",
                "openai_api_key": "sk-test-key",
                "openai_model": "gpt-4o-mini",
                "temperature": 0.1,
                "max_tokens": 1024,
            },
            "embedding": {
                "provider": "google",
                "model": "models/text-embedding-004",
                "google_api_key": "gkey-test",
            },
        },
        "agents": [
            {
                "id": "pii_scrubber",
                "type": "pii_scrubber",
                "enabled": True,
                "config": {"action": "redact"},
                "retry": {"max_attempts": 1, "backoff": "fixed", "backoff_ms": 0},
                "timeout_ms": 500,
            },
        ],
        "routing": [
            {"from": "__entry__", "to": "pii_scrubber"},
            {"from": "pii_scrubber", "to": "__sink__"},
        ],
        "observability": {
            "metrics_port": 9090,
            "trace_exporter": "none",
            "log_format": "json",
        },
    }
    if overrides:
        # Deep merge one level
        for k, v in overrides.items():
            if isinstance(v, dict) and k in base:
                base[k].update(v)
            else:
                base[k] = v
    return base


# ------------------------------------------------------------------ #
# Happy path
# ------------------------------------------------------------------ #

class TestHappyPath:
    def test_minimal_valid_config_loads(self, tmp_path):
        p = _write_config(tmp_path, _minimal_config())
        cfg = load_and_validate_config(p)
        assert isinstance(cfg, AgentSystemConfig)
        assert cfg.system.name == "test-system"
        assert len(cfg.agents) == 1
        assert cfg.agents[0].id == "pii_scrubber"

    def test_disabled_agent_is_accepted(self, tmp_path):
        data = _minimal_config()
        data["agents"][0]["enabled"] = False
        # Add a second ENABLED agent and route only through it (disabled agent
        # must NOT appear in routing — the validator correctly rejects routes
        # referencing disabled agents).
        data["agents"].append({
            "id": "result_aggregation",
            "type": "result_aggregation",
            "enabled": True,
            "config": {},
            "retry": {"max_attempts": 1, "backoff": "fixed", "backoff_ms": 0},
            "timeout_ms": 1000,
        })
        # Replace routing entirely — don't route through the disabled pii_scrubber
        data["routing"] = [
            {"from": "__entry__", "to": "result_aggregation"},
            {"from": "result_aggregation", "to": "__sink__"},
        ]
        p = _write_config(tmp_path, data)
        cfg = load_and_validate_config(p)
        assert cfg.agents[0].enabled is False

    def test_multiple_agents_linear_pipeline(self, tmp_path):
        data = _minimal_config()
        data["agents"].append({
            "id": "requisition_parsing",
            "type": "requisition_parsing",
            "enabled": True,
            "config": {},
            "retry": {"max_attempts": 1, "backoff": "fixed", "backoff_ms": 0},
            "timeout_ms": 5000,
        })
        # Fix routing to connect both agents
        data["routing"] = [
            {"from": "__entry__", "to": "pii_scrubber"},
            {"from": "pii_scrubber", "to": "requisition_parsing"},
            {"from": "requisition_parsing", "to": "__sink__"},
        ]
        p = _write_config(tmp_path, data)
        cfg = load_and_validate_config(p)
        assert len(cfg.agents) == 2


# ------------------------------------------------------------------ #
# File handling
# ------------------------------------------------------------------ #

class TestFileHandling:
    def test_missing_file_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="not found"):
            load_and_validate_config(tmp_path / "nonexistent.yaml")

    def test_non_mapping_yaml_raises_config_error(self, tmp_path):
        p = tmp_path / "bad.yaml"
        p.write_text("- just a list\n- not a dict\n")
        with pytest.raises(ConfigError, match="mapping"):
            load_and_validate_config(p)


# ------------------------------------------------------------------ #
# Environment variable substitution
# ------------------------------------------------------------------ #

class TestEnvSubstitution:
    def test_env_var_substituted(self, monkeypatch):
        monkeypatch.setenv("MY_DB_URL", "postgresql://user:pass@host/db")
        result, errors = _substitute_env_vars({"url": "$MY_DB_URL"})
        assert errors == []
        assert result["url"] == "postgresql://user:pass@host/db"

    def test_missing_env_var_produces_error(self, monkeypatch):
        monkeypatch.delenv("MISSING_VAR", raising=False)
        _, errors = _substitute_env_vars({"key": "$MISSING_VAR"})
        assert len(errors) == 1
        assert "MISSING_VAR" in errors[0]

    def test_non_env_string_unchanged(self):
        result, errors = _substitute_env_vars({"url": "literal-value"})
        assert errors == []
        assert result["url"] == "literal-value"

    def test_nested_substitution(self, monkeypatch):
        monkeypatch.setenv("INNER_KEY", "secret")
        obj = {"outer": {"inner": "$INNER_KEY"}}
        result, errors = _substitute_env_vars(obj)
        assert errors == []
        assert result["outer"]["inner"] == "secret"

    def test_list_substitution(self, monkeypatch):
        monkeypatch.setenv("ITEM", "hello")
        obj = ["$ITEM", "literal"]
        result, errors = _substitute_env_vars(obj)
        assert errors == []
        assert result == ["hello", "literal"]

    def test_all_missing_vars_reported_together(self, monkeypatch, tmp_path):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("DATABASE_URL", raising=False)
        data = _minimal_config()
        data["infrastructure"]["database"]["url"] = "$DATABASE_URL"
        data["infrastructure"]["llm"]["openai_api_key"] = "$OPENAI_API_KEY"
        p = _write_config(tmp_path, data)
        with pytest.raises(ConfigError) as exc_info:
            load_and_validate_config(p)
        violations = exc_info.value.violations
        var_errors = [v for v in violations if "is not set" in v or "not set" in v]
        assert len(var_errors) >= 2, f"Expected ≥2 missing-var errors; got: {violations}"


# ------------------------------------------------------------------ #
# Schema validation errors
# ------------------------------------------------------------------ #

class TestSchemaValidation:
    def test_invalid_log_level(self, tmp_path):
        data = _minimal_config()
        data["system"]["log_level"] = "VERBOSE"
        p = _write_config(tmp_path, data)
        with pytest.raises(ConfigError, match="log_level"):
            load_and_validate_config(p)

    def test_invalid_backoff_strategy(self, tmp_path):
        data = _minimal_config()
        data["agents"][0]["retry"]["backoff"] = "magical"
        p = _write_config(tmp_path, data)
        with pytest.raises(ConfigError, match="backoff"):
            load_and_validate_config(p)

    def test_agent_replicas_below_one(self, tmp_path):
        data = _minimal_config()
        data["agents"][0]["replicas"] = 0
        p = _write_config(tmp_path, data)
        with pytest.raises(ConfigError):
            load_and_validate_config(p)

    def test_timeout_below_minimum(self, tmp_path):
        data = _minimal_config()
        data["agents"][0]["timeout_ms"] = 50
        p = _write_config(tmp_path, data)
        with pytest.raises(ConfigError):
            load_and_validate_config(p)

    def test_invalid_trace_exporter(self, tmp_path):
        data = _minimal_config()
        data["observability"] = {
            "metrics_port": 9090,
            "trace_exporter": "datadog",
            "log_format": "json",
        }
        p = _write_config(tmp_path, data)
        with pytest.raises(ConfigError, match="trace_exporter"):
            load_and_validate_config(p)

    def test_invalid_llm_provider(self, tmp_path):
        data = _minimal_config()
        data["infrastructure"]["llm"]["provider"] = "anthropic"
        p = _write_config(tmp_path, data)
        with pytest.raises(ConfigError, match="provider"):
            load_and_validate_config(p)


# ------------------------------------------------------------------ #
# Routing graph validator
# ------------------------------------------------------------------ #

class TestRoutingValidator:
    def _routes(self, raw: list) -> list[RouteConfig]:
        return [RouteConfig.model_validate(r) for r in raw]

    def test_unknown_from_agent(self):
        routes = self._routes([
            {"from": "__entry__", "to": "pii_scrubber"},
            {"from": "ghost_agent", "to": "__sink__"},   # unknown
        ])
        errors = _validate_routing(routes, {"pii_scrubber"})
        assert any("ghost_agent" in e for e in errors)

    def test_unknown_to_agent(self):
        routes = self._routes([
            {"from": "__entry__", "to": "pii_scrubber"},
            {"from": "pii_scrubber", "to": "nonexistent"},   # unknown
        ])
        errors = _validate_routing(routes, {"pii_scrubber"})
        assert any("nonexistent" in e for e in errors)

    def test_unreachable_agent_detected(self):
        routes = self._routes([
            {"from": "__entry__", "to": "pii_scrubber"},
            {"from": "pii_scrubber", "to": "__sink__"},
            # skill_normalization is enabled but has no route leading to it
        ])
        errors = _validate_routing(
            routes, {"pii_scrubber", "skill_normalization"}
        )
        assert any("skill_normalization" in e for e in errors)

    def test_duplicate_route_detected(self):
        routes = self._routes([
            {"from": "__entry__", "to": "pii_scrubber"},
            {"from": "__entry__", "to": "pii_scrubber"},   # duplicate
            {"from": "pii_scrubber", "to": "__sink__"},
        ])
        errors = _validate_routing(routes, {"pii_scrubber"})
        assert any("Duplicate" in e for e in errors)

    def test_valid_routing_no_errors(self):
        routes = self._routes([
            {"from": "__entry__", "to": "pii_scrubber"},
            {
                "from": "pii_scrubber",
                "to": "requisition_parsing",
                "condition": "$.metadata.message_type == 'requisition.scrubbed'",
            },
            {
                "from": "pii_scrubber",
                "to": "__dead_letter__",
                "condition": "$.metadata.message_type == 'requisition.pii_blocked'",
            },
            {"from": "requisition_parsing", "to": "__sink__"},
        ])
        errors = _validate_routing(
            routes, {"pii_scrubber", "requisition_parsing"}
        )
        assert errors == []


# ------------------------------------------------------------------ #
# Business rule validation
# ------------------------------------------------------------------ #

class TestBusinessRules:
    def test_no_enabled_agents_fails(self, tmp_path):
        data = _minimal_config()
        data["agents"][0]["enabled"] = False
        p = _write_config(tmp_path, data)
        with pytest.raises(ConfigError, match="No agents are enabled"):
            load_and_validate_config(p)

    def test_missing_groq_key_when_provider_is_groq(self, tmp_path):
        data = _minimal_config()
        data["infrastructure"]["llm"]["provider"] = "groq"
        data["infrastructure"]["llm"]["groq_api_key"] = None
        p = _write_config(tmp_path, data)
        with pytest.raises(ConfigError, match="GROQ_API_KEY"):
            load_and_validate_config(p)

    def test_missing_google_key_when_provider_is_google(self, tmp_path):
        data = _minimal_config()
        data["infrastructure"]["llm"]["provider"] = "google"
        data["infrastructure"]["llm"]["google_api_key"] = None
        p = _write_config(tmp_path, data)
        with pytest.raises(ConfigError, match="GOOGLE_API_KEY"):
            load_and_validate_config(p)

    def test_otlp_without_endpoint_fails(self, tmp_path):
        data = _minimal_config()
        data["observability"] = {
            "metrics_port": 9090,
            "trace_exporter": "otlp",
            "log_format": "json",
            # otlp_endpoint intentionally absent
        }
        p = _write_config(tmp_path, data)
        with pytest.raises(ConfigError, match="OTLP_ENDPOINT"):
            load_and_validate_config(p)

    def test_all_violations_reported_in_one_error(self, tmp_path):
        """
        Ensures ALL violations are reported together, not just the first.
        """
        data = _minimal_config()
        data["system"]["log_level"] = "INVALID"          # violation 1
        data["agents"][0]["retry"]["backoff"] = "magic"  # violation 2
        p = _write_config(tmp_path, data)
        with pytest.raises(ConfigError) as exc_info:
            load_and_validate_config(p)
        # Should be a multi-violation error
        assert len(exc_info.value.violations) >= 2
