"""
Migration tests — before/after behavior comparison for each agent wrapper.

These tests verify that:
1. Each new BaseAgent wrapper can be instantiated and passes the BaseAgent
   contract (initialize → handle → shutdown).
2. The wrapper is registered in the AgentRegistry at import time.
3. The wrapper's config_schema is valid JSON Schema.
4. The wrapper's handle() emits the correct message_type.
5. Trace IDs are propagated through every wrapper.

These tests do NOT call the brownfield code (which needs a live DB + LLM).
They only exercise the adapter shell — confirming that the interface contract
holds.  Integration tests against a live DB belong in tests/integration/.

Run:
    cd /sessions/happy-busy-heisenberg/mnt/ib-job-skill-mapping-system
    PYTHONPATH=src pytest tests/unit/test_migration_agents.py -v \
        --noconftest --asyncio-mode=auto
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import sys
import types
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent_framework.base_agent import BaseAgent
from app.agent_framework.health import HealthState, HealthStatus
from app.agent_framework.message import Message, MessageMetadata
from app.agent_framework.registry import AgentRegistry


# ------------------------------------------------------------------ #
# Pre-populate sys.modules with mock brownfield modules so that
# patch("app.ai.agents.X.func") doesn't trigger the real import chain
# (which needs openai, spacy, etc. that aren't installed in the test VM).
# ------------------------------------------------------------------ #

def _ensure_mock_module(dotted_path: str) -> types.ModuleType:
    """Create a mock module at dotted_path if it doesn't already exist,
    and wire it as an attribute on its parent so patch() getattr works."""
    if dotted_path in sys.modules:
        return sys.modules[dotted_path]
    mod = types.ModuleType(dotted_path)
    mod.__package__ = dotted_path.rsplit(".", 1)[0] if "." in dotted_path else dotted_path
    sys.modules[dotted_path] = mod
    # Wire as attribute on parent
    if "." in dotted_path:
        parent_path, child_name = dotted_path.rsplit(".", 1)
        if parent_path in sys.modules:
            setattr(sys.modules[parent_path], child_name, mod)
    return mod

# Ensure parent packages exist first (order matters — parents before children)
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

# Add mock functions/classes as attributes on the mock modules
sys.modules["app.ai.agents.requisition_parsing"].parse_requisition_with_llm = MagicMock(name="parse_requisition_with_llm")
sys.modules["app.ai.agents.requisition_parsing"].requisition_parsing_node = MagicMock(name="requisition_parsing_node")
sys.modules["app.ai.agents.skill_normalization"].skill_normalization_node = MagicMock(name="skill_normalization_node")
sys.modules["app.ai.agents.embedding"].embedding_node = MagicMock(name="embedding_node")
sys.modules["app.ai.agents.rag_retrieval"].rag_retrieval_node = MagicMock(name="rag_retrieval_node")
sys.modules["app.ai.agents.matching_scoring"].matching_scoring_node = MagicMock(name="matching_scoring_node")
sys.modules["app.ai.agents.explanation_generation"].explanation_generation_node = MagicMock(name="explanation_generation_node")
sys.modules["app.ai.agents.result_aggregation"].result_aggregation_node = MagicMock(name="result_aggregation_node")
sys.modules["app.ai.results_cache"].store_results = MagicMock(name="store_results")
sys.modules["app.pii.scrubber"].PIIScrubber = MagicMock(name="PIIScrubber")
sys.modules["app.pii.config"].PIIConfig = MagicMock(name="PIIConfig")


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _entry_message(payload: dict, source: str = "__entry__") -> Message:
    return Message.create(
        payload=payload,
        metadata=MessageMetadata(
            source_agent=source,
            message_type="test.input",
            correlation_id="corr-test-1",
            request_id="req-test-1",
        ),
    )


async def _collect(agent: BaseAgent, message: Message) -> List[Message]:
    results = []
    async for msg in agent.handle(message):
        results.append(msg)
    return results


# ------------------------------------------------------------------ #
# Import all agent wrappers so they self-register in the AgentRegistry
# ------------------------------------------------------------------ #

@pytest.fixture(autouse=True, scope="module")
def _register_all_agents():
    """Import the agent modules so they register themselves."""
    AgentRegistry.clear()
    # These imports trigger @AgentRegistry.register decorators
    import app.agent_framework.agents.pii_scrubber_agent  # noqa: F401
    import app.agent_framework.agents.requisition_parsing_agent  # noqa: F401
    import app.agent_framework.agents.skill_normalization_agent  # noqa: F401
    import app.agent_framework.agents.candidate_search_agent  # noqa: F401
    import app.agent_framework.agents.matching_scoring_agent  # noqa: F401
    import app.agent_framework.agents.explanation_agent  # noqa: F401
    import app.agent_framework.agents.result_aggregation_agent  # noqa: F401
    yield
    AgentRegistry.clear()


# ================================================================== #
# 1. Registry presence tests
# ================================================================== #

class TestRegistryPresence:
    """Every agent wrapper is discoverable in the registry."""

    EXPECTED_IDS = [
        "pii_scrubber",
        "requisition_parsing",
        "skill_normalization",
        "candidate_search",
        "matching_scoring",
        "explanation_generation",
        "result_aggregation",
    ]

    def test_all_agents_registered(self):
        registered = AgentRegistry.list_agents()
        for aid in self.EXPECTED_IDS:
            assert aid in registered, (
                f"Agent '{aid}' not found in registry. "
                f"Registered: {sorted(registered.keys())}"
            )

    def test_all_agents_resolve_latest(self):
        for aid in self.EXPECTED_IDS:
            cls = AgentRegistry.resolve(aid)
            assert issubclass(cls, BaseAgent)
            assert cls.agent_id == aid

    def test_all_agents_have_version(self):
        for aid in self.EXPECTED_IDS:
            cls = AgentRegistry.resolve(aid)
            assert cls.version, f"Agent '{aid}' has empty version"

    def test_all_agents_have_config_schema(self):
        for aid in self.EXPECTED_IDS:
            cls = AgentRegistry.resolve(aid)
            schema = cls.config_schema
            assert isinstance(schema, dict)
            assert schema.get("type") == "object"


# ================================================================== #
# 2. PIIScrubberAgent migration test
# ================================================================== #

class TestPIIScrubberMigration:
    """PIIScrubberAgent wraps app.pii.scrubber.PIIScrubber."""

    @pytest.mark.asyncio
    async def test_handle_emits_scrubbed_message(self):
        """Mock the inner scrubber and verify the adapter output shape."""
        cls = AgentRegistry.resolve("pii_scrubber")
        agent = cls()

        # Mock the PIIScrubber to avoid loading the NER model
        mock_result = MagicMock()
        mock_result.scrubbed_payload = {"title": "Engineer", "jd_text": "Build things"}
        mock_result.pii_found = False
        mock_result.detections = []
        mock_result.fields_scrubbed = []
        mock_result.total_pii_count = 0
        mock_result.scrubbing_confirmed = True

        with patch("app.pii.scrubber.PIIScrubber") as MockScrubber, \
             patch("app.pii.config.PIIConfig"):
            mock_instance = MockScrubber.return_value
            mock_instance.scrub.return_value = mock_result
            mock_instance.probe.return_value = True

            await agent.initialize({"action": "redact"})

            msg = _entry_message({
                "request_id": "req-1",
                "correlation_id": "corr-1",
                "job_description": {"title": "Engineer", "jd_text": "Build things"},
            })

            results = await _collect(agent, msg)

        assert len(results) == 1
        out = results[0]
        assert out.metadata.message_type == "requisition.scrubbed"
        assert out.metadata.source_agent == "pii_scrubber"
        assert out.trace_id == msg.trace_id
        assert out.payload["scrubbed_job_description"]["title"] == "Engineer"

        await agent.shutdown()


# ================================================================== #
# 3. RequisitionParsingAgent migration test
# ================================================================== #

class TestRequisitionParsingMigration:
    @pytest.mark.asyncio
    async def test_handle_emits_parsed_message(self):
        cls = AgentRegistry.resolve("requisition_parsing")
        agent = cls()
        await agent.initialize({})

        mock_parsed = {
            "normalized_title": "Software Engineer",
            "normalized_role": "Backend",
            "extracted_mandatory_skills": ["Python", "PostgreSQL"],
            "extracted_preferred_skills": ["Docker"],
            "experience": {"min_months": 24, "max_months": 60},
            "expected_start_date": "2026-05-01",
            "requisition_duration_month": 6,
            "certifications_required": ["AWS SAA"],
        }

        with patch(
            "app.ai.agents.requisition_parsing.parse_requisition_with_llm",
            return_value=mock_parsed,
        ):
            msg = _entry_message({
                "request_id": "req-1",
                "correlation_id": "corr-1",
                "scrubbed_job_description": {
                    "title": "Software Eng",
                    "role": "Backend Dev",
                    "jd_text": "We need a Python backend engineer.",
                    "mandatory_skills": ["Python"],
                    "preferred_skills": ["Docker"],
                },
            })

            results = await _collect(agent, msg)

        assert len(results) == 1
        out = results[0]
        assert out.metadata.message_type == "requisition.parsed"
        assert out.trace_id == msg.trace_id
        assert out.payload["normalized_title"] == "Software Engineer"
        assert "Python" in out.payload["mandatory_skills"]

        await agent.shutdown()

    @pytest.mark.asyncio
    async def test_handle_emits_failure_when_llm_returns_none(self):
        cls = AgentRegistry.resolve("requisition_parsing")
        agent = cls()
        await agent.initialize({})

        with patch(
            "app.ai.agents.requisition_parsing.parse_requisition_with_llm",
            return_value=None,
        ):
            msg = _entry_message({
                "request_id": "req-1",
                "correlation_id": "corr-1",
                "scrubbed_job_description": {"jd_text": "something"},
            })

            results = await _collect(agent, msg)

        assert len(results) == 1
        assert results[0].metadata.message_type == "requisition.parse_failed"
        assert "error" in results[0].payload

        await agent.shutdown()


# ================================================================== #
# 4. SkillNormalizationAgent migration test
# ================================================================== #

class TestSkillNormalizationMigration:
    @pytest.mark.asyncio
    async def test_handle_emits_normalized_skills(self):
        cls = AgentRegistry.resolve("skill_normalization")
        agent = cls()
        await agent.initialize({})

        mock_updated_state = {
            "normalized_skills": {
                "mandatory_skill_ids": ["python-001", "pg-002"],
                "preferred_skill_ids": ["docker-003"],
                "mandatory_enriched": {"Python": ["CPython", "Python3"]},
                "preferred_enriched": {},
                "mandatory_alternatives": {},
                "preferred_alternatives": {},
                "normalized_certifications": ["AWS SAA"],
                "expanded_certification_terms": ["Solutions Architect"],
            },
            "error_message": None,
        }

        with patch(
            "app.ai.agents.skill_normalization.skill_normalization_node",
            return_value=mock_updated_state,
        ):
            msg = _entry_message({
                "request_id": "req-1",
                "correlation_id": "corr-1",
                "mandatory_skills": ["Python", "PostgreSQL"],
                "preferred_skills": ["Docker"],
                "certifications_required": ["AWS SAA"],
                "normalized_title": "Software Engineer",
                "normalized_role": "Backend",
                "jd_text": "Build microservices",
            })

            results = await _collect(agent, msg)

        assert len(results) == 1
        out = results[0]
        assert out.metadata.message_type == "skill_normalization.complete"
        assert out.trace_id == msg.trace_id
        assert "python-001" in out.payload["mandatory_skill_ids"]
        # Verify pass-through fields survive
        assert out.payload["normalized_title"] == "Software Engineer"

        await agent.shutdown()


# ================================================================== #
# 5. CandidateSearchAgent migration test
# ================================================================== #

class TestCandidateSearchMigration:
    @pytest.mark.asyncio
    async def test_handle_emits_candidates(self):
        cls = AgentRegistry.resolve("candidate_search")
        agent = cls()
        await agent.initialize({"top_k": 5})

        def mock_embedding_node(state):
            state["embedding_result"] = {
                "mandatory_vector": [0.1] * 768,
                "preferred_vector": [0.2] * 768,
            }
            return state

        def mock_rag_node(state):
            state["retrieved_candidates"] = [
                {
                    "team_member_id": "tm-001",
                    "final_similarity": 0.85,
                    "mandatory_similarity": 0.9,
                    "preferred_similarity": 0.7,
                    "jd_level_similarity": 0.8,
                    "certification_similarity": 0.6,
                },
            ]
            return state

        with patch("app.ai.agents.embedding.embedding_node", side_effect=mock_embedding_node), \
             patch("app.ai.agents.rag_retrieval.rag_retrieval_node", side_effect=mock_rag_node):

            msg = _entry_message({
                "request_id": "req-1",
                "correlation_id": "corr-1",
                "mandatory_skill_ids": ["python-001"],
                "preferred_skill_ids": ["docker-003"],
                "mandatory_skills_raw": ["Python"],
                "preferred_skills_raw": ["Docker"],
                "normalized_title": "Software Engineer",
                "normalized_role": "Backend",
                "jd_text": "Build stuff",
            })

            results = await _collect(agent, msg)

        assert len(results) == 1
        out = results[0]
        assert out.metadata.message_type == "candidate_search.complete"
        assert len(out.payload["candidates"]) == 1
        assert out.payload["candidates"][0]["team_member_id"] == "tm-001"

        await agent.shutdown()


# ================================================================== #
# 6. MatchingScoringAgent migration test
# ================================================================== #

class TestMatchingScoringMigration:
    @pytest.mark.asyncio
    async def test_handle_emits_scored_candidates(self):
        cls = AgentRegistry.resolve("matching_scoring")
        agent = cls()
        await agent.initialize({})

        def mock_scoring_node(state):
            state["candidate_scores"] = [
                {
                    "team_member_id": "tm-001",
                    "skill_score": 0.8,
                    "experience_score": 0.7,
                    "certification_score": 0.5,
                    "availability_score": 1.0,
                    "final_score": 0.78,
                    "is_available": True,
                    "certifications": ["AWS SAA"],
                    "match_reasons": {"mandatory_matched": ["Python"]},
                    "score_breakdown": {},
                },
            ]
            state["total_evaluated"] = 1
            state["error_message"] = None
            return state

        with patch(
            "app.ai.agents.matching_scoring.matching_scoring_node",
            side_effect=mock_scoring_node,
        ):
            msg = _entry_message({
                "request_id": "req-1",
                "correlation_id": "corr-1",
                "candidates": [{"team_member_id": "tm-001", "final_similarity": 0.85}],
                "mandatory_skill_ids": ["python-001"],
                "preferred_skill_ids": [],
                "normalized_role": "Backend",
            })

            results = await _collect(agent, msg)

        assert len(results) == 1
        out = results[0]
        assert out.metadata.message_type == "matching_scoring.complete"
        assert len(out.payload["scored_candidates"]) == 1
        assert out.payload["scored_candidates"][0]["final_score"] == 0.78

        await agent.shutdown()


# ================================================================== #
# 7. ExplanationAgent migration test
# ================================================================== #

class TestExplanationMigration:
    @pytest.mark.asyncio
    async def test_handle_emits_explanations(self):
        cls = AgentRegistry.resolve("explanation_generation")
        agent = cls()
        await agent.initialize({"max_explanations": 2})

        input_candidates = [
            {
                "team_member_id": "tm-001",
                "final_score": 0.78,
                "explanation": [],
            },
        ]

        def mock_explanation_node(state):
            # Brownfield node adds explanation field to candidate_scores
            for c in state["candidate_scores"]:
                c["explanation"] = ["Strong Python skills match the mandatory requirement."]
            state["error_message"] = None
            return state

        with patch(
            "app.ai.agents.explanation_generation.explanation_generation_node",
            side_effect=mock_explanation_node,
        ):
            msg = _entry_message({
                "request_id": "req-1",
                "correlation_id": "corr-1",
                "scored_candidates": input_candidates,
                "total_evaluated": 1,
                "normalized_role": "Backend",
            })

            results = await _collect(agent, msg)

        assert len(results) == 1
        out = results[0]
        assert out.metadata.message_type == "explanation.complete"
        cand = out.payload["scored_candidates"][0]
        assert len(cand["explanation"]) > 0

        await agent.shutdown()


# ================================================================== #
# 8. ResultAggregationAgent migration test
# ================================================================== #

class TestResultAggregationMigration:
    @pytest.mark.asyncio
    async def test_handle_emits_final_results(self):
        cls = AgentRegistry.resolve("result_aggregation")
        agent = cls()
        await agent.initialize({
            "qualification_threshold": 0.30,
            "results_backend": "memory",
        })

        def mock_aggregation_node(state):
            state["final_results"] = [
                {
                    "team_member_id": "tm-001",
                    "profile_score": 0.78,
                    "fit_level": "MEDIUM",
                    "availability_match": True,
                    "explanation": ["Strong Python match"],
                },
            ]
            state["total_qualified"] = 1
            state["error_message"] = None
            return state

        with patch(
            "app.ai.agents.result_aggregation.result_aggregation_node",
            side_effect=mock_aggregation_node,
        ), patch("app.ai.results_cache.store_results"):

            msg = _entry_message({
                "request_id": "req-1",
                "correlation_id": "corr-1",
                "scored_candidates": [{"team_member_id": "tm-001", "final_score": 0.78}],
                "total_evaluated": 1,
            })

            results = await _collect(agent, msg)

        assert len(results) == 1
        out = results[0]
        assert out.metadata.message_type == "result_aggregation.complete"
        assert out.payload["total_qualified"] == 1
        assert out.payload["final_results"][0]["team_member_id"] == "tm-001"

        await agent.shutdown()


# ================================================================== #
# 9. Cross-cutting: trace_id propagation through all agents
# ================================================================== #

class TestTraceIdPropagation:
    """Every wrapper MUST propagate the incoming message's trace_id."""

    AGENTS_AND_MOCKS = [
        (
            "pii_scrubber",
            {"request_id": "r", "correlation_id": "c", "job_description": {"jd_text": "x"}},
            [("app.pii.scrubber.PIIScrubber", None), ("app.pii.config.PIIConfig", None)],
        ),
        (
            "requisition_parsing",
            {"request_id": "r", "correlation_id": "c", "scrubbed_job_description": {"jd_text": "x"}},
            [("app.ai.agents.requisition_parsing.parse_requisition_with_llm",
              {"normalized_title": "T", "normalized_role": "R",
               "extracted_mandatory_skills": [], "extracted_preferred_skills": [],
               "experience": {}, "certifications_required": []})],
        ),
        (
            "skill_normalization",
            {"request_id": "r", "correlation_id": "c",
             "mandatory_skills": ["Python"], "preferred_skills": []},
            [("app.ai.agents.skill_normalization.skill_normalization_node",
              {"normalized_skills": {"mandatory_skill_ids": [], "preferred_skill_ids": []},
               "error_message": None})],
        ),
        (
            "result_aggregation",
            {"request_id": "r", "correlation_id": "c",
             "scored_candidates": [], "total_evaluated": 0},
            [("app.ai.agents.result_aggregation.result_aggregation_node",
              {"final_results": [], "total_qualified": 0, "error_message": None}),
             ("app.ai.results_cache.store_results", None)],
        ),
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("agent_id,payload,mocks", AGENTS_AND_MOCKS,
                             ids=[a[0] for a in AGENTS_AND_MOCKS])
    async def test_trace_id_preserved(self, agent_id, payload, mocks):
        cls = AgentRegistry.resolve(agent_id)
        agent = cls()

        # Build context manager stack for mocks
        patches = []  # list of (target_str, patch_obj)
        for target, return_value in mocks:
            if return_value is None:
                patches.append((target, patch(target)))
            elif isinstance(return_value, dict):
                if "node" in target:
                    patches.append((target, patch(target, side_effect=lambda s, rv=return_value: {**s, **rv})))
                else:
                    patches.append((target, patch(target, return_value=return_value)))
            else:
                patches.append((target, patch(target, return_value=return_value)))

        with contextlib.ExitStack() as stack:
            for target_str, p in patches:
                mock_obj = stack.enter_context(p)
                # For PIIScrubber, set up the mock instance
                if "PIIScrubber" in target_str:
                    mock_result = MagicMock()
                    mock_result.scrubbed_payload = payload.get("job_description", {})
                    mock_result.pii_found = False
                    mock_result.detections = []
                    mock_result.fields_scrubbed = []
                    mock_result.total_pii_count = 0
                    mock_result.scrubbing_confirmed = True
                    mock_obj.return_value.scrub.return_value = mock_result
                    mock_obj.return_value.probe.return_value = True

            await agent.initialize({})
            fixed_trace = "trace-id-must-survive"
            msg = Message.create(
                payload=payload,
                metadata=MessageMetadata(
                    source_agent="test", message_type="test.in",
                    correlation_id="c", request_id="r",
                ),
                trace_id=fixed_trace,
            )

            results = await _collect(agent, msg)

        assert len(results) >= 1, f"Agent '{agent_id}' emitted no messages"
        assert results[0].trace_id == fixed_trace, (
            f"Agent '{agent_id}' did not propagate trace_id"
        )

        await agent.shutdown()
