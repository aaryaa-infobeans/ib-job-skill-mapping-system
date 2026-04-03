#!/usr/bin/env python3
"""
Demo Runner — Process a sample job requisition through the 7-agent pipeline.

This script lets trial users see the agent framework in action without needing
a live database, LLM API keys, or any external services. All brownfield
functions are replaced with realistic mock data.

Usage:
    # Quick demo (default config)
    python scripts/demo_agent_pipeline.py

    # Custom config
    python scripts/demo_agent_pipeline.py --config config/agents.demo.yaml

    # Verbose output
    python scripts/demo_agent_pipeline.py --verbose

    # Custom job description
    python scripts/demo_agent_pipeline.py --title "Senior Data Engineer" \
        --skills "Python,Spark,Airflow,SQL"

What it demonstrates:
    1. Config loading and 5-stage validation
    2. Agent registry with semver resolution
    3. Orchestrator lifecycle (start → process → shutdown)
    4. 7-agent pipeline with message routing
    5. Conditional PII gate (scrubbed → parsing, blocked → dead-letter)
    6. Trace ID propagation across all agents
    7. Prometheus metrics collection
    8. Dead-letter store inspection
    9. Health endpoint aggregation
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import types
from pathlib import Path
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))


# ---------------------------------------------------------------------------
# Mock brownfield modules (avoids needing openai, spacy, torch, etc.)
# ---------------------------------------------------------------------------

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


def setup_demo_mocks(title: str, skills: list[str]):
    """Install mock brownfield modules with realistic demo data."""

    for pkg in [
        "app.pii", "app.pii.scrubber", "app.pii.config",
        "app.ai", "app.ai.agents", "app.ai.results_cache",
        "app.ai.agents.requisition_parsing",
        "app.ai.agents.skill_normalization",
        "app.ai.agents.embedding",
        "app.ai.agents.rag_retrieval",
        "app.ai.agents.matching_scoring",
        "app.ai.agents.explanation_generation",
        "app.ai.agents.result_aggregation",
    ]:
        _ensure_mock_module(pkg)

    # -- PII Scrubber mock --
    mock_scrub_result = MagicMock()
    mock_scrub_result.scrubbed_payload = {
        "title": title,
        "jd_text": f"We are looking for a {title} with expertise in {', '.join(skills)}.",
        "mandatory_skills": skills[:3],
        "preferred_skills": skills[3:] if len(skills) > 3 else ["Docker", "Kubernetes"],
    }
    mock_scrub_result.pii_found = False
    mock_scrub_result.detections = []
    mock_scrub_result.fields_scrubbed = []
    mock_scrub_result.total_pii_count = 0
    mock_scrub_result.scrubbing_confirmed = True

    mock_scrubber = MagicMock()
    mock_scrubber.scrub.return_value = mock_scrub_result
    mock_scrubber.probe.return_value = True

    sys.modules["app.pii.scrubber"].PIIScrubber = MagicMock(return_value=mock_scrubber)
    sys.modules["app.pii.config"].PIIConfig = MagicMock()

    # -- Requisition Parsing mock --
    sys.modules["app.ai.agents.requisition_parsing"].parse_requisition_with_llm = MagicMock(
        return_value={
            "normalized_title": title,
            "normalized_role": "Backend" if "backend" in title.lower() else "Full Stack",
            "extracted_mandatory_skills": skills[:3],
            "extracted_preferred_skills": skills[3:] if len(skills) > 3 else ["Docker"],
            "experience": {"min_months": 24, "max_months": 72},
            "expected_start_date": "2026-06-01",
            "requisition_duration_month": 12,
            "certifications_required": ["AWS SAA"] if "cloud" in " ".join(skills).lower() else [],
        }
    )
    sys.modules["app.ai.agents.requisition_parsing"].requisition_parsing_node = MagicMock()

    # -- Skill Normalization mock --
    def mock_skill_norm(state):
        state["normalized_skills"] = {
            "mandatory_skill_ids": [f"{s.lower().replace(' ', '-')}-001" for s in skills[:3]],
            "preferred_skill_ids": [f"{s.lower().replace(' ', '-')}-002" for s in (skills[3:] or ["docker"])],
            "mandatory_enriched": {skills[0]: [f"{skills[0]}3", f"Advanced {skills[0]}"]},
            "preferred_enriched": {},
            "mandatory_alternatives": {},
            "preferred_alternatives": {},
            "normalized_certifications": [],
            "expanded_certification_terms": [],
        }
        state["error_message"] = None
        return state
    sys.modules["app.ai.agents.skill_normalization"].skill_normalization_node = MagicMock(side_effect=mock_skill_norm)

    # -- Embedding mock --
    def mock_embed(state):
        state["embedding_result"] = {
            "mandatory_vector": [0.1] * 768,
            "preferred_vector": [0.2] * 768,
        }
        return state
    sys.modules["app.ai.agents.embedding"].embedding_node = MagicMock(side_effect=mock_embed)

    # -- RAG Retrieval mock --
    def mock_rag(state):
        state["retrieved_candidates"] = [
            {"team_member_id": "TM-1001", "final_similarity": 0.92,
             "mandatory_similarity": 0.95, "preferred_similarity": 0.85,
             "jd_level_similarity": 0.88, "certification_similarity": 0.70},
            {"team_member_id": "TM-1042", "final_similarity": 0.84,
             "mandatory_similarity": 0.88, "preferred_similarity": 0.72,
             "jd_level_similarity": 0.80, "certification_similarity": 0.60},
            {"team_member_id": "TM-1087", "final_similarity": 0.76,
             "mandatory_similarity": 0.80, "preferred_similarity": 0.65,
             "jd_level_similarity": 0.72, "certification_similarity": 0.55},
            {"team_member_id": "TM-1103", "final_similarity": 0.68,
             "mandatory_similarity": 0.70, "preferred_similarity": 0.55,
             "jd_level_similarity": 0.65, "certification_similarity": 0.40},
            {"team_member_id": "TM-1200", "final_similarity": 0.51,
             "mandatory_similarity": 0.52, "preferred_similarity": 0.40,
             "jd_level_similarity": 0.48, "certification_similarity": 0.30},
        ]
        return state
    sys.modules["app.ai.agents.rag_retrieval"].rag_retrieval_node = MagicMock(side_effect=mock_rag)

    # -- Matching & Scoring mock --
    def mock_scoring(state):
        candidates = state.get("retrieved_candidates", [])
        state["candidate_scores"] = []
        for i, c in enumerate(candidates):
            score = round(0.90 - (i * 0.12), 2)
            state["candidate_scores"].append({
                "team_member_id": c["team_member_id"],
                "skill_score": round(score + 0.05, 2),
                "experience_score": round(score - 0.05, 2),
                "certification_score": round(score - 0.10, 2),
                "availability_score": 1.0 if i < 3 else 0.5,
                "final_score": score,
                "is_available": i < 3,
                "certifications": ["AWS SAA"] if i == 0 else [],
                "match_reasons": {"mandatory_matched": skills[:2]},
                "score_breakdown": {},
            })
        state["total_evaluated"] = len(candidates)
        state["error_message"] = None
        return state
    sys.modules["app.ai.agents.matching_scoring"].matching_scoring_node = MagicMock(side_effect=mock_scoring)

    # -- Explanation Generation mock --
    def mock_explanation(state):
        explanations = [
            f"Strong alignment with mandatory {skills[0]} requirement. Deep experience in related technologies.",
            f"Solid match across {skills[0]} and {skills[1] if len(skills) > 1 else 'core'} skills. Availability confirmed.",
            f"Partial match — meets {skills[0]} requirement but lacks depth in preferred skills.",
            "Below threshold on preferred skills. Limited availability in the requested timeframe.",
            "Weak overall match. Consider for future requisitions with lower skill requirements.",
        ]
        for i, c in enumerate(state.get("candidate_scores", [])):
            c["explanation"] = [explanations[min(i, len(explanations) - 1)]]
        state["error_message"] = None
        return state
    sys.modules["app.ai.agents.explanation_generation"].explanation_generation_node = MagicMock(side_effect=mock_explanation)

    # -- Result Aggregation mock --
    def mock_aggregation(state):
        fit_levels = ["STRONG_FIT", "STRONG_FIT", "GOOD_FIT", "PARTIAL_FIT", "PARTIAL_FIT"]
        state["final_results"] = []
        for i, c in enumerate(state.get("candidate_scores", [])):
            if c["final_score"] >= 0.30:
                state["final_results"].append({
                    "team_member_id": c["team_member_id"],
                    "profile_score": c["final_score"],
                    "fit_level": fit_levels[min(i, len(fit_levels) - 1)],
                    "availability_match": c["is_available"],
                    "explanation": c.get("explanation", []),
                })
        state["total_qualified"] = len(state["final_results"])
        state["error_message"] = None
        return state
    sys.modules["app.ai.agents.result_aggregation"].result_aggregation_node = MagicMock(side_effect=mock_aggregation)
    sys.modules["app.ai.results_cache"].store_results = MagicMock()


# ---------------------------------------------------------------------------
# Pretty printers
# ---------------------------------------------------------------------------

CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def banner(text: str):
    width = 70
    print(f"\n{CYAN}{'═' * width}")
    print(f"  {BOLD}{text}{RESET}{CYAN}")
    print(f"{'═' * width}{RESET}\n")


def section(text: str):
    print(f"\n{YELLOW}▸ {text}{RESET}")


def kv(key: str, value, indent: int = 2):
    pad = " " * indent
    print(f"{pad}{DIM}{key}:{RESET} {value}")


def print_candidate(rank: int, c: dict):
    fit = c.get("fit_level", "UNKNOWN")
    color = GREEN if "STRONG" in fit else YELLOW if "GOOD" in fit else RED
    avail = "✓" if c.get("availability_match") else "✗"
    print(f"  {BOLD}#{rank}{RESET}  {c['team_member_id']}  "
          f"Score: {BOLD}{c['profile_score']:.2f}{RESET}  "
          f"Fit: {color}{fit}{RESET}  "
          f"Available: {avail}")
    for exp in c.get("explanation", []):
        print(f"      {DIM}→ {exp}{RESET}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run_demo(config_path: str, title: str, skills: list[str], verbose: bool):
    """Boot the orchestrator, process a requisition, print results."""

    from prometheus_client import CollectorRegistry
    from app.agent_framework.config_loader import load_and_validate_config
    from app.agent_framework.observability import AgentMetrics
    from app.agent_framework.orchestrator import Orchestrator
    from app.agent_framework.registry import AgentRegistry

    # Import agent wrappers (triggers registration)
    import app.agent_framework.agents.pii_scrubber_agent       # noqa
    import app.agent_framework.agents.requisition_parsing_agent # noqa
    import app.agent_framework.agents.skill_normalization_agent # noqa
    import app.agent_framework.agents.candidate_search_agent    # noqa
    import app.agent_framework.agents.matching_scoring_agent    # noqa
    import app.agent_framework.agents.explanation_agent         # noqa
    import app.agent_framework.agents.result_aggregation_agent  # noqa

    banner("Agent Framework Demo")
    print(f"  Config:  {config_path}")
    print(f"  Title:   {title}")
    print(f"  Skills:  {', '.join(skills)}")

    # ── Step 1: Load and validate config ──
    section("Step 1 — Loading and validating config (5-stage pipeline)")
    config = load_and_validate_config(config_path)
    kv("System", config.system.name)
    kv("Agents", f"{len([a for a in config.agents if a.enabled])} enabled")
    kv("Routes", f"{len(config.routing)} rules")
    kv("Trace exporter", config.observability.trace_exporter)
    print(f"  {GREEN}✓ Config valid{RESET}")

    # ── Step 2: Show registry ──
    section("Step 2 — Agent Registry (semver resolution)")
    registered = AgentRegistry.list_agents()
    for aid, versions in sorted(registered.items()):
        kv(aid, f"v{versions[-1]}" if versions else "unknown")

    # ── Step 3: Boot orchestrator ──
    section("Step 3 — Starting Orchestrator (per-agent workers + bounded queues)")
    prom_registry = CollectorRegistry()
    metrics = AgentMetrics(registry=prom_registry)

    t_start = time.monotonic()
    orch = Orchestrator(config, metrics=metrics)
    await orch.start()
    boot_ms = (time.monotonic() - t_start) * 1000
    kv("Boot time", f"{boot_ms:.0f} ms")
    kv("Workers", f"{len(orch._slots)} running")
    print(f"  {GREEN}✓ All agents initialized{RESET}")

    # ── Step 4: Process requisition ──
    section("Step 4 — Processing requisition through 7-agent pipeline")
    payload = {
        "request_id": "demo-req-001",
        "correlation_id": "demo-corr-001",
        "job_description": {
            "title": title,
            "jd_text": f"We are looking for a {title} with expertise in {', '.join(skills)}.",
            "mandatory_skills": skills[:3],
            "preferred_skills": skills[3:] if len(skills) > 3 else ["Docker", "Kubernetes"],
        },
    }

    pipeline_start = time.monotonic()
    result = await orch.process(
        payload=payload,
        trace_id="demo-trace-001",
        correlation_id="demo-corr-001",
        request_id="demo-req-001",
        timeout_s=30,
    )
    pipeline_ms = (time.monotonic() - pipeline_start) * 1000

    kv("Pipeline time", f"{pipeline_ms:.0f} ms")
    kv("Trace ID", result.trace_id)
    kv("Final message type", result.metadata.message_type)
    kv("Source agent", result.metadata.source_agent)

    # ── Step 5: Display results ──
    section("Step 5 — Ranked Candidate Results")
    candidates = result.payload.get("final_results", [])
    kv("Total qualified", result.payload.get("total_qualified", 0))
    print()

    for i, c in enumerate(candidates, 1):
        print_candidate(i, c)

    # ── Step 6: Health check ──
    section("Step 6 — Health Check (all agents)")
    health = await orch.get_health()
    status_color = GREEN if health["status"] == "ok" else YELLOW if health["status"] == "degraded" else RED
    kv("Overall status", f"{status_color}{health['status'].upper()}{RESET}")
    for aid, agent_health in health["agents"].items():
        state = agent_health.get("state", "unknown")
        s_color = GREEN if state == "ok" else YELLOW
        kv(aid, f"{s_color}{state}{RESET}", indent=4)

    # ── Step 7: Metrics summary ──
    section("Step 7 — Prometheus Metrics Summary")
    for agent_id in ["pii_scrubber", "requisition_parsing", "skill_normalization",
                     "candidate_search", "matching_scoring", "explanation_generation",
                     "result_aggregation"]:
        success = prom_registry.get_sample_value(
            "agent_framework_messages_total",
            {"agent_id": agent_id, "status": "success"},
        ) or 0
        dur_sum = prom_registry.get_sample_value(
            "agent_framework_message_duration_seconds_sum",
            {"agent_id": agent_id},
        ) or 0
        kv(agent_id, f"success={int(success)}  duration={dur_sum*1000:.1f}ms", indent=4)

    pipeline_dur = prom_registry.get_sample_value(
        "agent_framework_pipeline_duration_seconds_sum",
    ) or 0
    kv("Pipeline total", f"{pipeline_dur*1000:.1f}ms")

    # ── Step 8: Dead-letter store ──
    section("Step 8 — Dead-Letter Store")
    kv("Entries", orch.dead_letter_store.count())
    if orch.dead_letter_store.count() > 0:
        for entry in orch.dead_letter_store.list_entries(limit=5):
            kv(entry["trace_id"], f"{entry['source_agent']} → {entry['error']}", indent=4)
    else:
        print(f"  {GREEN}✓ No failed messages{RESET}")

    # ── Shutdown ──
    section("Shutting down orchestrator")
    await orch.shutdown()
    print(f"  {GREEN}✓ Graceful shutdown complete{RESET}")

    banner("Demo Complete!")
    print(f"  {BOLD}What you just saw:{RESET}")
    print(f"  • Config loaded and validated (5-stage pipeline)")
    print(f"  • 7 agents resolved from registry (semver constraints)")
    print(f"  • Orchestrator booted with per-agent asyncio workers")
    print(f"  • Job requisition processed through the full pipeline")
    print(f"  • Conditional routing (PII gate → parsing)")
    print(f"  • Trace ID propagated end-to-end: {result.trace_id}")
    print(f"  • Prometheus metrics collected for every agent")
    print(f"  • Dead-letter store inspected (0 failures)")
    print(f"  • Health endpoint aggregated all agent statuses")
    print()
    print(f"  {DIM}Next steps:{RESET}")
    print(f"  • Edit config/agents.demo.yaml to toggle agents on/off")
    print(f"  • Set enabled: false on any agent to see the feature flag")
    print(f"  • Add your own agent: see docs/AGENT_AUTHORING_GUIDE.md")
    print(f"  • Run the test suite: make test-agents")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Demo the agent framework pipeline with mock data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/demo_agent_pipeline.py
  python scripts/demo_agent_pipeline.py --title "Senior Data Engineer" --skills "Python,Spark,SQL,Airflow"
  python scripts/demo_agent_pipeline.py --verbose
        """,
    )
    parser.add_argument(
        "--config", default=str(PROJECT_ROOT / "config" / "agents.demo.yaml"),
        help="Path to agents YAML config (default: config/agents.demo.yaml)",
    )
    parser.add_argument(
        "--title", default="Senior Backend Engineer",
        help="Job title for the demo requisition",
    )
    parser.add_argument(
        "--skills", default="Python,PostgreSQL,FastAPI,Docker",
        help="Comma-separated list of required skills",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable verbose logging output",
    )
    args = parser.parse_args()

    skills = [s.strip() for s in args.skills.split(",") if s.strip()]

    # Set up mocks before any framework imports
    setup_demo_mocks(args.title, skills)

    if not args.verbose:
        import logging
        logging.basicConfig(level=logging.WARNING)
    else:
        import logging
        logging.basicConfig(level=logging.DEBUG, format="%(name)s %(levelname)s %(message)s")

    asyncio.run(run_demo(args.config, args.title, skills, args.verbose))


if __name__ == "__main__":
    main()
