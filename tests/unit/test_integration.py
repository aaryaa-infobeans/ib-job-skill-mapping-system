"""
Phase 9 — Integration validation test.

End-to-end test: load agents.yaml, boot orchestrator, process a full
requisition through the 7-agent pipeline with mocked brownfield functions,
and verify the final result arrives at __sink__.

This is the "smoke test" that proves the entire config → registry →
orchestrator → routing → agent dispatch → sink pipeline works.
"""

from __future__ import annotations

import asyncio
import sys
import types
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
from app.agent_framework.health import HealthStatus
from app.agent_framework.message import Message, MessageMetadata
from app.agent_framework.observability import AgentMetrics
from app.agent_framework.orchestrator import Orchestrator
from app.agent_framework.registry import AgentRegistry


# ------------------------------------------------------------------ #
# Mock brownfield modules (same approach as test_migration_agents.py)
# ------------------------------------------------------------------ #

def _ensure_mock_module(dotted_path: str) -> types.ModuleType:
    if dotted_path in sys.modules:
        return sys.modules[dotted_path]
    mod = types.ModuleType(dotted_path)
    mod.__package__ = dotted_path.rsplit(".", 1)[0] if "." in dotted_path else dotted_path
    sys.modules[dotted_path] = mod
    if "." in dotted_path:
        parent_path, child_name = dotted_path.rsplit(".", 1)
        if parent_path in sys.modules:
            setattr(sys.modules[parent_path], child_name, mod)
    return mod

for _pkg in ["app.pii", "app.pii.scrubber", "app.pii.config",
             "app.ai", "app.ai.agents", "app.ai.results_cache",
             "app.ai.agents.requisition_parsing",
             "app.ai.agents.skill_normalization",
             "app.ai.agents.embedding",
             "app.ai.agents.rag_retrieval",
             "app.ai.agents.matching_scoring",
             "app.ai.agents.explanation_generation",
             "app.ai.agents.result_aggregation"]:
    _ensure_mock_module(_pkg)

sys.modules["app.ai.agents.requisition_parsing"].parse_requisition_with_llm = MagicMock()
sys.modules["app.ai.agents.requisition_parsing"].requisition_parsing_node = MagicMock()
sys.modules["app.ai.agents.skill_normalization"].skill_normalization_node = MagicMock()
sys.modules["app.ai.agents.embedding"].embedding_node = MagicMock()
sys.modules["app.ai.agents.rag_retrieval"].rag_retrieval_node = MagicMock()
sys.modules["app.ai.agents.matching_scoring"].matching_scoring_node = MagicMock()
sys.modules["app.ai.agents.explanation_generation"].explanation_generation_node = MagicMock()
sys.modules["app.ai.agents.result_aggregation"].result_aggregation_node = MagicMock()
sys.modules["app.ai.results_cache"].store_results = MagicMock()
sys.modules["app.pii.scrubber"].PIIScrubber = MagicMock()
sys.modules["app.pii.config"].PIIConfig = MagicMock()

def _register_all_agents():
    """Import agent wrappers so they register themselves."""
    import app.agent_framework.agents.pii_scrubber_agent  # noqa
    import app.agent_framework.agents.requisition_parsing_agent  # noqa
    import app.agent_framework.agents.skill_normalization_agent  # noqa
    import app.agent_framework.agents.candidate_search_agent  # noqa
    import app.agent_framework.agents.matching_scoring_agent  # noqa
    import app.agent_framework.agents.explanation_agent  # noqa
    import app.agent_framework.agents.result_aggregation_agent  # noqa

    # Re-register since modules may already be cached
    from app.agent_framework.agents.pii_scrubber_agent import PIIScrubberAgent
    from app.agent_framework.agents.requisition_parsing_agent import RequisitionParsingAgent
    from app.agent_framework.agents.skill_normalization_agent import SkillNormalizationAgent
    from app.agent_framework.agents.candidate_search_agent import CandidateSearchAgent
    from app.agent_framework.agents.matching_scoring_agent import MatchingScoringAgent
    from app.agent_framework.agents.explanation_agent import ExplanationAgent
    from app.agent_framework.agents.result_aggregation_agent import ResultAggregationAgent
    for cls in [PIIScrubberAgent, RequisitionParsingAgent, SkillNormalizationAgent,
                CandidateSearchAgent, MatchingScoringAgent, ExplanationAgent,
                ResultAggregationAgent]:
        try:
            AgentRegistry.register(cls)
        except ValueError:
            pass  # already registered


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _route(from_: str, to: str, condition=None) -> RouteConfig:
    return RouteConfig.model_validate({"from": from_, "to": to, "condition": condition})


def _make_full_config():
    """Build a config that mirrors the real agents.yaml 7-agent pipeline."""
    return AgentSystemConfig(
        system=SystemConfig(name="integration-test", version="1.0.0"),
        infrastructure=InfrastructureConfig(
            database=DatabaseConfig(url="sqlite:///:memory:", pool_size=1, max_overflow=0),
            redis=RedisConfig(url="redis://localhost:6379/0"),
            llm=LLMConfig(provider="openai", temperature=0.0, max_tokens=1000),
            embedding=EmbeddingConfig(provider="gemma", model="gemma-2b", device="cpu"),
        ),
        agents=[
            AgentConfig(id="pii_scrubber", type="pii_scrubber", enabled=True,
                        retry=RetryConfig(), config={"action": "redact"}),
            AgentConfig(id="requisition_parsing", type="requisition_parsing", enabled=True,
                        retry=RetryConfig(), config={}),
            AgentConfig(id="skill_normalization", type="skill_normalization", enabled=True,
                        retry=RetryConfig(), config={}),
            AgentConfig(id="candidate_search", type="candidate_search", enabled=True,
                        retry=RetryConfig(), config={"top_k": 10}),
            AgentConfig(id="matching_scoring", type="matching_scoring", enabled=True,
                        retry=RetryConfig(), config={}),
            AgentConfig(id="explanation_generation", type="explanation_generation", enabled=True,
                        retry=RetryConfig(), config={"max_explanations": 2}),
            AgentConfig(id="result_aggregation", type="result_aggregation", enabled=True,
                        retry=RetryConfig(), config={"results_backend": "memory"}),
        ],
        routing=[
            _route("__entry__", "pii_scrubber"),
            _route("pii_scrubber", "requisition_parsing",
                   "$.metadata.message_type == 'requisition.scrubbed'"),
            _route("pii_scrubber", "__dead_letter__",
                   "$.metadata.message_type == 'requisition.pii_blocked'"),
            _route("requisition_parsing", "skill_normalization"),
            _route("skill_normalization", "candidate_search"),
            _route("candidate_search", "matching_scoring"),
            _route("matching_scoring", "explanation_generation"),
            _route("explanation_generation", "result_aggregation"),
            _route("result_aggregation", "__sink__"),
        ],
        observability=ObservabilityConfig(
            metrics_port=9090, trace_exporter="none", log_format="json",
        ),
        error_handling=ErrorHandlingConfig(
            dead_letter=DeadLetterConfig(backend="memory", key_prefix="dlq:", ttl_seconds=3600),
            alerting=AlertingConfig(),
        ),
    )


# ================================================================== #
# Integration tests
# ================================================================== #

class TestFullPipelineIntegration:
    """End-to-end: config → orchestrator → 7-agent pipeline → result."""

    @pytest.fixture(autouse=True)
    def _ensure_registered(self):
        """Ensure all agent wrappers are registered before each test."""
        _register_all_agents()
        yield

    @pytest.fixture(autouse=True)
    def _setup_mocks(self):
        """Wire up mock brownfield functions for the full pipeline."""

        # PII scrubber mock
        mock_scrub_result = MagicMock()
        mock_scrub_result.scrubbed_payload = {
            "title": "Software Engineer",
            "jd_text": "We need a Python backend engineer.",
            "mandatory_skills": ["Python"],
            "preferred_skills": ["Docker"],
        }
        mock_scrub_result.pii_found = False
        mock_scrub_result.detections = []
        mock_scrub_result.fields_scrubbed = []
        mock_scrub_result.total_pii_count = 0
        mock_scrub_result.scrubbing_confirmed = True

        mock_scrubber = sys.modules["app.pii.scrubber"].PIIScrubber.return_value
        mock_scrubber.scrub.return_value = mock_scrub_result
        mock_scrubber.probe.return_value = True

        # Requisition parsing mock
        sys.modules["app.ai.agents.requisition_parsing"].parse_requisition_with_llm.return_value = {
            "normalized_title": "Software Engineer",
            "normalized_role": "Backend",
            "extracted_mandatory_skills": ["Python"],
            "extracted_preferred_skills": ["Docker"],
            "experience": {"min_months": 24},
            "certifications_required": [],
            "expected_start_date": "2026-05-01",
            "requisition_duration_month": 6,
        }

        # Skill normalization mock
        def mock_skill_norm(state):
            state["normalized_skills"] = {
                "mandatory_skill_ids": ["python-001"],
                "preferred_skill_ids": ["docker-002"],
                "mandatory_enriched": {},
                "preferred_enriched": {},
                "mandatory_alternatives": {},
                "preferred_alternatives": {},
                "normalized_certifications": [],
                "expanded_certification_terms": [],
            }
            state["error_message"] = None
            return state
        sys.modules["app.ai.agents.skill_normalization"].skill_normalization_node.side_effect = mock_skill_norm

        # Embedding mock
        def mock_embed(state):
            state["embedding_result"] = {"mandatory_vector": [0.1] * 768}
            return state
        sys.modules["app.ai.agents.embedding"].embedding_node.side_effect = mock_embed

        # RAG retrieval mock
        def mock_rag(state):
            state["retrieved_candidates"] = [{
                "team_member_id": "tm-001",
                "final_similarity": 0.85,
                "mandatory_similarity": 0.9,
                "preferred_similarity": 0.7,
                "jd_level_similarity": 0.8,
                "certification_similarity": 0.6,
            }]
            return state
        sys.modules["app.ai.agents.rag_retrieval"].rag_retrieval_node.side_effect = mock_rag

        # Matching/scoring mock
        def mock_scoring(state):
            state["candidate_scores"] = [{
                "team_member_id": "tm-001",
                "skill_score": 0.85,
                "experience_score": 0.7,
                "certification_score": 0.5,
                "availability_score": 1.0,
                "final_score": 0.80,
                "is_available": True,
                "certifications": [],
                "match_reasons": {},
                "score_breakdown": {},
            }]
            state["total_evaluated"] = 1
            state["error_message"] = None
            return state
        sys.modules["app.ai.agents.matching_scoring"].matching_scoring_node.side_effect = mock_scoring

        # Explanation mock
        def mock_explanation(state):
            for c in state.get("candidate_scores", []):
                c["explanation"] = ["Strong Python match"]
            state["error_message"] = None
            return state
        sys.modules["app.ai.agents.explanation_generation"].explanation_generation_node.side_effect = mock_explanation

        # Result aggregation mock
        def mock_aggregation(state):
            state["final_results"] = [{
                "team_member_id": "tm-001",
                "profile_score": 0.80,
                "fit_level": "STRONG_FIT",
                "availability_match": True,
                "explanation": ["Strong Python match"],
            }]
            state["total_qualified"] = 1
            state["error_message"] = None
            return state
        sys.modules["app.ai.agents.result_aggregation"].result_aggregation_node.side_effect = mock_aggregation

        yield

    @pytest.mark.asyncio
    async def test_full_pipeline_produces_final_results(self):
        """Process a requisition through all 7 agents and get ranked results."""
        prom_registry = CollectorRegistry()
        metrics = AgentMetrics(registry=prom_registry)
        config = _make_full_config()

        async with Orchestrator(config, metrics=metrics) as orch:
            result = await orch.process(
                payload={
                    "request_id": "req-integration-1",
                    "correlation_id": "corr-integration-1",
                    "job_description": {
                        "title": "Software Engineer",
                        "jd_text": "We need a Python backend engineer.",
                        "mandatory_skills": ["Python"],
                        "preferred_skills": ["Docker"],
                    },
                },
                timeout_s=10,
            )

        # Verify we got through the full pipeline
        assert result.metadata.message_type == "result_aggregation.complete"
        assert result.metadata.source_agent == "result_aggregation"
        assert result.payload["total_qualified"] == 1
        assert result.payload["final_results"][0]["team_member_id"] == "tm-001"
        assert result.payload["final_results"][0]["fit_level"] == "STRONG_FIT"

        # Verify metrics were collected
        success_count = prom_registry.get_sample_value(
            "agent_framework_messages_total",
            {"agent_id": "result_aggregation", "status": "success"},
        )
        assert success_count == 1.0

        pipeline_count = prom_registry.get_sample_value(
            "agent_framework_pipeline_duration_seconds_count",
        )
        assert pipeline_count == 1.0

    @pytest.mark.asyncio
    async def test_health_endpoint_all_agents_present(self):
        """After startup, all 7 agents are present in health report."""
        config = _make_full_config()

        async with Orchestrator(config) as orch:
            health = await orch.get_health()

        # All 7 agents should be reported (some may be degraded due to
        # mocked DB connections, but they should all be present)
        assert len(health["agents"]) == 7
        assert health["status"] in ("ok", "degraded", "unavailable")
        for agent_id in [
            "pii_scrubber", "requisition_parsing", "skill_normalization",
            "candidate_search", "matching_scoring", "explanation_generation",
            "result_aggregation",
        ]:
            assert agent_id in health["agents"]

    @pytest.mark.asyncio
    async def test_trace_id_survives_full_pipeline(self):
        """A fixed trace_id propagates from entry to final result."""
        config = _make_full_config()

        async with Orchestrator(config) as orch:
            result = await orch.process(
                payload={
                    "request_id": "r",
                    "correlation_id": "c",
                    "job_description": {
                        "title": "Engineer",
                        "jd_text": "Python dev",
                        "mandatory_skills": ["Python"],
                        "preferred_skills": [],
                    },
                },
                trace_id="trace-must-survive-pipeline",
                timeout_s=10,
            )

        assert result.trace_id == "trace-must-survive-pipeline"

    @pytest.mark.asyncio
    async def test_dead_letter_store_empty_on_success(self):
        """Successful pipeline leaves the dead-letter store empty."""
        config = _make_full_config()

        async with Orchestrator(config) as orch:
            await orch.process(
                payload={
                    "request_id": "r",
                    "correlation_id": "c",
                    "job_description": {
                        "title": "Engineer",
                        "jd_text": "Python dev",
                        "mandatory_skills": ["Python"],
                        "preferred_skills": [],
                    },
                },
                timeout_s=10,
            )
            assert orch.dead_letter_store.count() == 0
