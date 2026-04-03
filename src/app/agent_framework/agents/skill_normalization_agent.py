"""
SkillNormalizationAgent — strangler-fig wrapper around the brownfield
skill_normalization_node (app.ai.agents.skill_normalization).

Anti-corruption layer
---------------------
The brownfield node receives a full GraphState dict and writes back into
it.  This wrapper extracts only the fields the agent needs, calls the
existing helper functions, and adapts the output to the new Message
contract — without modifying any brownfield logic.

TODO(agent-migration): The brownfield node creates a SessionLocal()
internally.  Replace with an injected async session once the DB
injection pattern is agreed in Phase 5 follow-up work.  Tracked in
TASK-MIGRATE-003.

TODO(agent-migration): The skill_normalization_node hardcodes OpenAI
via `from openai import OpenAI` regardless of settings.llm_provider.
Redirect through LLMClient in Phase 7 cleanup.  Tracked in
TASK-MIGRATE-004.
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Dict, List, Optional

from pydantic import BaseModel, Field

from app.agent_framework.base_agent import BaseAgent
from app.agent_framework.health import HealthStatus
from app.agent_framework.message import Message, MessageMetadata
from app.agent_framework.registry import AgentRegistry


# ------------------------------------------------------------------ #
# I/O schemas
# ------------------------------------------------------------------ #

class SkillNormalizationInput(BaseModel):
    request_id: str
    correlation_id: str
    mandatory_skills: List[str]
    preferred_skills: List[str]
    certifications_required: List[str] = Field(default_factory=list)
    # Pass-through fields needed by downstream agents
    normalized_title: str = ""
    normalized_role: str = ""
    experience: Optional[Dict[str, Any]] = None
    expected_start_date: Optional[str] = None
    duration_months: Optional[int] = None
    priority: Optional[str] = None
    location: List[str] = Field(default_factory=list)
    work_mode: List[str] = Field(default_factory=list)
    jd_text: str = ""
    client_name: Optional[str] = None


class SkillNormalizationOutput(BaseModel):
    request_id: str
    correlation_id: str
    mandatory_skill_ids: List[str] = Field(default_factory=list)
    preferred_skill_ids: List[str] = Field(default_factory=list)
    mandatory_enriched: Dict[str, List[str]] = Field(default_factory=dict)
    preferred_enriched: Dict[str, List[str]] = Field(default_factory=dict)
    mandatory_alternatives: Dict[str, List[str]] = Field(default_factory=dict)
    preferred_alternatives: Dict[str, List[str]] = Field(default_factory=dict)
    normalized_certifications: List[str] = Field(default_factory=list)
    expanded_certification_terms: List[str] = Field(default_factory=list)
    # Pass-through fields from upstream
    normalized_title: str = ""
    normalized_role: str = ""
    mandatory_skills_raw: List[str] = Field(default_factory=list)
    preferred_skills_raw: List[str] = Field(default_factory=list)
    experience: Optional[Dict[str, Any]] = None
    expected_start_date: Optional[str] = None
    duration_months: Optional[int] = None
    location: List[str] = Field(default_factory=list)
    work_mode: List[str] = Field(default_factory=list)
    jd_text: str = ""
    client_name: Optional[str] = None


# ------------------------------------------------------------------ #
# Anti-corruption layer: GraphState ↔ Message adapter
# ------------------------------------------------------------------ #

def _build_graph_state_fragment(inp: SkillNormalizationInput) -> dict:
    """Build the minimal GraphState-shaped dict the brownfield node expects."""
    return {
        "requisition_input": {
            "request_id": inp.request_id,
            "correlation_id": inp.correlation_id,
            "job_description": {
                "mandatory_skills": inp.mandatory_skills,
                "preferred_skills": inp.preferred_skills,
                "certifications": inp.certifications_required,
            },
        },
        "parsed_jd": {
            "normalized_title": inp.normalized_title,
            "normalized_role": inp.normalized_role,
            "extracted_mandatory_skills": inp.mandatory_skills,
            "extracted_preferred_skills": inp.preferred_skills,
            "certifications_required": inp.certifications_required,
            "experience": inp.experience,
            "expected_start_date": inp.expected_start_date,
            "requisition_duration_month": inp.duration_months,
            "location": inp.location,
            "work_mode": inp.work_mode,
            "jd_text": inp.jd_text,
            "client_name": inp.client_name,
        },
        "error_message": None,
    }


def _extract_normalized_skills(state: dict) -> dict:
    """Extract normalized_skills sub-dict from a returned GraphState."""
    return state.get("normalized_skills") or {}


# ------------------------------------------------------------------ #
# Agent
# ------------------------------------------------------------------ #

@AgentRegistry.register
class SkillNormalizationAgent(BaseAgent):
    """
    Maps raw skill strings to canonical skill_master IDs and expands
    ontology terms.

    Wraps the existing  skill_normalization_node()  function unchanged
    (strangler-fig step 1).
    """

    agent_id = "skill_normalization"
    version = "1.0.0"

    config_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "llm_model":          {"type": ["string", "null"]},
            "temperature":        {"type": "number"},
            "max_tokens":         {"type": "integer"},
            "db_lookup":          {"type": "boolean"},
            "ontology_expansion": {"type": "boolean"},
        },
        "additionalProperties": True,
    }

    async def initialize(self, config: Dict[str, Any]) -> None:
        await self._base_initialize(config)
        # TODO(agent-migration): replace SessionLocal() inside brownfield
        # node with injected db_url from config["db_url"].
        # Tracked in TASK-MIGRATE-003.
        self._log.info("SkillNormalizationAgent ready (using legacy SessionLocal)")

    async def handle(self, message: Message) -> AsyncIterator[Message]:
        self._assert_initialized()

        inp = SkillNormalizationInput.model_validate(message.payload)

        # ── Anti-corruption: build the brownfield state shape ─────────
        state_fragment = _build_graph_state_fragment(inp)

        # ── Delegate to brownfield node ───────────────────────────────
        from app.ai.agents.skill_normalization import skill_normalization_node
        updated_state = skill_normalization_node(state_fragment)

        if updated_state.get("error_message"):
            self._log.error(
                "Skill normalization failed: %s",
                updated_state["error_message"],
                extra={"trace_id": message.trace_id},
            )
            yield Message.create(
                payload={
                    "request_id": inp.request_id,
                    "correlation_id": inp.correlation_id,
                    "error": updated_state["error_message"],
                },
                metadata=MessageMetadata(
                    source_agent=self.agent_id,
                    message_type="skill_normalization.failed",
                    correlation_id=inp.correlation_id,
                    request_id=inp.request_id,
                ),
                trace_id=message.trace_id,
            )
            return

        ns = _extract_normalized_skills(updated_state)

        output = SkillNormalizationOutput(
            request_id=inp.request_id,
            correlation_id=inp.correlation_id,
            mandatory_skill_ids=ns.get("mandatory_skill_ids", []),
            preferred_skill_ids=ns.get("preferred_skill_ids", []),
            mandatory_enriched=ns.get("mandatory_enriched") or {},
            preferred_enriched=ns.get("preferred_enriched") or {},
            mandatory_alternatives=ns.get("mandatory_alternatives") or {},
            preferred_alternatives=ns.get("preferred_alternatives") or {},
            normalized_certifications=ns.get("normalized_certifications") or [],
            expanded_certification_terms=ns.get("expanded_certification_terms") or [],
            # Pass-through
            normalized_title=inp.normalized_title,
            normalized_role=inp.normalized_role,
            mandatory_skills_raw=inp.mandatory_skills,
            preferred_skills_raw=inp.preferred_skills,
            experience=inp.experience,
            expected_start_date=inp.expected_start_date,
            duration_months=inp.duration_months,
            location=inp.location,
            work_mode=inp.work_mode,
            jd_text=inp.jd_text,
            client_name=inp.client_name,
        )

        yield Message.create(
            payload=output.model_dump(),
            metadata=MessageMetadata(
                source_agent=self.agent_id,
                message_type="skill_normalization.complete",
                correlation_id=inp.correlation_id,
                request_id=inp.request_id,
            ),
            trace_id=message.trace_id,
        )

    async def health_check(self) -> HealthStatus:
        if not self._initialized:
            return HealthStatus.unavailable(self.agent_id, self.version, "Not initialized")
        # Probe DB reachability via a quick count query
        try:
            from app.db.session import SessionLocal
            from app.db.models import SkillMaster
            with SessionLocal() as db:
                count = db.query(SkillMaster).limit(1).count()
            return HealthStatus.ok(self.agent_id, self.version,
                                   uptime_s=round(self.uptime_seconds, 1),
                                   skill_master_reachable=True)
        except Exception as exc:
            return HealthStatus.degraded(
                self.agent_id, self.version,
                f"DB probe failed: {exc}",
                skill_master_reachable=False,
            )

    async def shutdown(self, graceful: bool = True) -> None:
        self._initialized = False
