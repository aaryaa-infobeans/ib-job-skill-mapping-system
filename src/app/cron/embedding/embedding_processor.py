"""
EmbeddingProcessor — orchestrates per-member embedding pipeline.

Pipeline per member (TASK-EMB-030..032):
  1. SELECT active team_members
  2. Assemble skills_text + certifications_text from DB
  3. Fetch resume_text via MCPResumeClient (if profile_url set)
  4. Scrub resume_text via PII scrubber (CR-PII-001)
  5. Compute SHA-256 content_hash
  6. Skip if hash unchanged and force=False (AC-6)
  7. Embed all three texts → compute weighted average legacy embedding
  8. upsert_team_member_embeddings() → commit per-member

Observability metrics (TASK-EMB-036) — all 8 metric names emitted as
structured log events:
  mcp_session_init_duration_seconds
  mcp_tool_call_total
  mcp_tool_call_error_total
  mcp_server_uptime_seconds
  embedding_generation_duration_seconds
  resume_fetch_success_total
  embedding_skip_total
  embedding_batch_total_duration_seconds

Alert thresholds (Plan §10):
  mcp_server_start_failed         → P1 (page immediately)
  resume_fetch_error_rate_high    → P2 (> 10% of members)
  embedding_phase_duration_exceeded → P2 (> 900s)

TASK-EMB-030 | Plan §7.2-7.5 | CR §3.6 | AC-1, AC-5, AC-6 | R7
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

import numpy as np
import structlog

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class ProcessingResult:
    success_count: int = 0
    skip_count: int = 0
    error_count: int = 0
    error_members: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# EmbeddingProcessor
# ---------------------------------------------------------------------------


class EmbeddingProcessor:
    """
    Orchestrates the embedding pipeline for all active team members.
    """

    def __init__(
        self,
        db: "Session",
        mcp_client,
        embedding_agent,
        settings=None,
    ) -> None:
        self.db = db
        self.mcp_client = mcp_client
        self.embedding_agent = embedding_agent
        self.settings = settings

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, force: bool = False) -> ProcessingResult:
        """
        Run embedding pipeline for all active team members.

        Args:
            force: If True, re-embed even if content_hash unchanged.

        Returns:
            ProcessingResult with counts.
        """
        from app.db.models.models import TeamMember, TeamMemberEmbedding
        from app.cron.embedding.text_assembler import (
            assemble_skills_text,
            assemble_certifications_text,
            assemble_resume_text,
        )
        from app.cron.db.repositories import EmbeddingRepository, EmbeddingPayload

        result = ProcessingResult()
        batch_start = time.monotonic()

        members = (
            self.db.query(TeamMember)
            .filter(TeamMember.is_active == True)  # noqa: E712
            .order_by(TeamMember.team_member_id)
            .all()
        )

        repo = EmbeddingRepository(self.db)
        total = len(members)
        fetch_errors = 0

        for member in members:
            mid = member.team_member_id
            try:
                self._process_member(
                    member=member,
                    repo=repo,
                    result=result,
                    force=force,
                    assemble_skills_text=assemble_skills_text,
                    assemble_certifications_text=assemble_certifications_text,
                    assemble_resume_text=assemble_resume_text,
                )
            except Exception as exc:
                logger.error(
                    "Unhandled error embedding member %s: %s", mid, exc, exc_info=True
                )
                result.error_count += 1
                result.error_members.append(mid)
                # Roll back the aborted transaction so the next member gets a
                # clean session — a DB error (e.g. UndefinedColumn, constraint
                # violation) leaves PostgreSQL in InFailedSqlTransaction state
                # which would cause every subsequent SELECT to fail too.
                try:
                    self.db.rollback()
                except Exception:
                    pass

        # Batch total duration metric
        elapsed = time.monotonic() - batch_start
        logger.info(
            "embedding_batch_total_duration_seconds",
            metric="embedding_batch_total_duration_seconds",
            value=round(elapsed, 2),
            total_members=total,
            success=result.success_count,
            skipped=result.skip_count,
            errors=result.error_count,
        )

        if elapsed > 900:
            logger.warning(
                "embedding_phase_duration_exceeded",
                alert="P2",
                value=round(elapsed, 2),
            )

        if total > 0 and result.error_count / total > 0.10:
            logger.warning(
                "resume_fetch_error_rate_high",
                alert="P2",
                error_rate=round(result.error_count / total, 3),
            )

        return result

    # ------------------------------------------------------------------
    # Per-member processing (step 2..8)
    # ------------------------------------------------------------------

    def _process_member(
        self,
        member,
        repo,
        result: ProcessingResult,
        force: bool,
        assemble_skills_text,
        assemble_certifications_text,
        assemble_resume_text,
    ) -> None:
        from app.db.models.models import TeamMemberEmbedding
        from app.cron.db.repositories import EmbeddingPayload

        mid = member.team_member_id

        # Fetch current stored hash
        emb_row = (
            self.db.query(TeamMemberEmbedding)
            .filter_by(team_member_id=mid)
            .first()
        )
        stored_hash = emb_row.content_hash if emb_row else None

        # 2. Assemble texts
        skills_text = assemble_skills_text(mid, self.db)
        certs_text = assemble_certifications_text(mid, self.db)

        # 3. Fetch resume via MCP
        resume_text: Optional[str] = None
        profile_url = getattr(member, "profile_url", None)
        if profile_url:
            t0 = time.monotonic()
            raw_resume = self.mcp_client.fetch_resume_sync(profile_url)
            fetch_elapsed = time.monotonic() - t0

            if raw_resume:
                # 4. PII scrub
                resume_text = self._scrub_pii(raw_resume, mid)
                logger.info(
                    "resume_fetch_success_total",
                    metric="resume_fetch_success_total",
                    status="success",
                    member_id=mid,
                )
            else:
                logger.info(
                    "resume_fetch_success_total",
                    metric="resume_fetch_success_total",
                    status="error",
                    member_id=mid,
                )

        # 5. Compute content hash
        new_hash = self._compute_hash(resume_text or "", skills_text, certs_text)

        # 6. Skip if unchanged
        if new_hash == stored_hash and not force:
            logger.info(
                "embedding_skip_total",
                metric="embedding_skip_total",
                reason="hash_match",
                member_id=mid,
            )
            result.skip_count += 1
            return

        # 7. Embed all three vectors
        resume_emb = self._embed(resume_text, "resume") if resume_text else None
        skills_emb = self._embed(skills_text, "skills") if skills_text else None
        certs_emb = self._embed(certs_text, "certifications") if certs_text else None

        if resume_emb is None and skills_emb is None and certs_emb is None:
            logger.info(
                "embedding_skip_total",
                metric="embedding_skip_total",
                reason="no_content",
                member_id=mid,
            )
            result.skip_count += 1
            return

        # Weighted average legacy embedding (TASK-EMB-032)
        legacy_emb = self._weighted_average(resume_emb, skills_emb, certs_emb)

        # 8. Upsert + commit per-member
        payload = EmbeddingPayload(
            member_id=mid,
            resume_embedding=resume_emb,
            skills_embedding=skills_emb,
            certifications_embedding=certs_emb,
            embedding=legacy_emb,
            resume_text=resume_text,
            skills_text=skills_text,
            certifications_text=certs_text,
            embedding_model="embedding-gemma-300m",
            content_hash=new_hash,
            resume_fetched_at=datetime.utcnow() if profile_url and resume_text else None,
            embedding_updated_at=datetime.utcnow(),
        )
        repo.upsert_team_member_embeddings(payload)
        self.db.commit()

        result.success_count += 1

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _scrub_pii(self, text: str, member_id: str) -> str:
        """Run PII scrubber on resume text before embedding or DB write."""
        try:
            from app.pii.scrubber import PIIScrubber
            from app.pii.config import PIIConfig

            scrubber = PIIScrubber(PIIConfig())
            scrubbed = scrubber.scrub(text)
            logger.info("pii_scrub_called", member_id=member_id)
            return scrubbed
        except Exception as exc:
            logger.warning(
                "pii_scrub_failed; returning original text",
                member_id=member_id,
                error=str(exc),
            )
            return text

    def _embed(self, text: str, embed_type: str) -> Optional[np.ndarray]:
        """Embed a single text, emit timing metric."""
        t0 = time.monotonic()
        vec = self.embedding_agent.embed_text(text)
        elapsed = time.monotonic() - t0
        logger.info(
            "embedding_generation_duration_seconds",
            metric="embedding_generation_duration_seconds",
            type=embed_type,
            value=round(elapsed, 4),
        )
        return vec

    @staticmethod
    def _compute_hash(resume_text: str, skills_text: str, certs_text: str) -> str:
        """SHA-256 of concatenated texts with || delimiter."""
        raw = f"{resume_text}||{skills_text}||{certs_text}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def _weighted_average(
        resume: Optional[np.ndarray],
        skills: Optional[np.ndarray],
        certs: Optional[np.ndarray],
    ) -> Optional[np.ndarray]:
        """
        Compute L2-normalized weighted average of available embeddings.

        Weights: resume=0.50, skills=0.30, certs=0.20.
        Re-normalized to sum=1.0 when vectors are missing.
        """
        available = []
        weights = []

        if resume is not None:
            available.append(resume)
            weights.append(0.50)
        if skills is not None:
            available.append(skills)
            weights.append(0.30)
        if certs is not None:
            available.append(certs)
            weights.append(0.20)

        if not available:
            return None

        total_w = sum(weights)
        combined = np.zeros(768, dtype=np.float32)
        for vec, w in zip(available, weights):
            combined += (w / total_w) * np.array(vec, dtype=np.float32)

        norm = np.linalg.norm(combined)
        if norm < 1e-9:
            return combined
        return combined / norm
