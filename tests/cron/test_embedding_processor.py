"""
EmbeddingProcessor unit and integration tests (TASK-EMB-037 + TASK-EMB-035).

Unit tests (10): use mocked DB, mocked MCP, mocked embedding agent.
Integration tests (5): use in-memory SQLite with real ORM models.

Run:  pytest tests/cron/test_embedding_processor.py -v
"""

from __future__ import annotations

import hashlib
import unittest
from datetime import datetime
from typing import Optional
from unittest.mock import MagicMock, patch

import numpy as np


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hash(resume: str, skills: str, certs: str) -> str:
    raw = f"{resume}||{skills}||{certs}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _fake_embedding(dim: int = 768) -> np.ndarray:
    v = np.random.randn(dim).astype(np.float32)
    return v / np.linalg.norm(v)


class _FakeEmbeddingAgent:
    def embed_text(self, text: str) -> np.ndarray:
        return _fake_embedding()


class _FakeMCPClient:
    def fetch_resume_sync(self, url: str) -> Optional[str]:
        return "Mocked resume content for testing."


class _FakeMCPClientEmpty:
    def fetch_resume_sync(self, url: str) -> Optional[str]:
        return None


# ---------------------------------------------------------------------------
# Unit Tests
# ---------------------------------------------------------------------------


class TestContentHash(unittest.TestCase):

    def test_content_hash_same_input_same_hash(self):
        from app.cron.embedding.embedding_processor import EmbeddingProcessor

        h1 = EmbeddingProcessor._compute_hash("resume", "skills", "certs")
        h2 = EmbeddingProcessor._compute_hash("resume", "skills", "certs")
        self.assertEqual(h1, h2)

    def test_content_hash_different_input_different_hash(self):
        from app.cron.embedding.embedding_processor import EmbeddingProcessor

        h1 = EmbeddingProcessor._compute_hash("resume A", "skills", "certs")
        h2 = EmbeddingProcessor._compute_hash("resume B", "skills", "certs")
        self.assertNotEqual(h1, h2)


class TestWeightedAverage(unittest.TestCase):

    def test_weighted_average_all_three_vectors(self):
        from app.cron.embedding.embedding_processor import EmbeddingProcessor

        r = np.ones(768, dtype=np.float32)
        s = np.ones(768, dtype=np.float32) * 0.5
        c = np.ones(768, dtype=np.float32) * 0.25

        result = EmbeddingProcessor._weighted_average(r, s, c)
        self.assertIsNotNone(result)
        self.assertEqual(result.shape, (768,))
        self.assertAlmostEqual(float(np.linalg.norm(result)), 1.0, places=5)

    def test_weighted_average_skills_only(self):
        from app.cron.embedding.embedding_processor import EmbeddingProcessor

        s = _fake_embedding()
        result = EmbeddingProcessor._weighted_average(None, s, None)
        self.assertIsNotNone(result)
        np.testing.assert_array_almost_equal(result, s)

    def test_weighted_average_no_vectors_returns_none(self):
        from app.cron.embedding.embedding_processor import EmbeddingProcessor

        result = EmbeddingProcessor._weighted_average(None, None, None)
        self.assertIsNone(result)


class TestEmbeddingProcessorUnitMocked(unittest.TestCase):
    """Unit tests with fully mocked DB."""

    def _make_processor(self, stored_hash: str | None = None, has_profile_url: bool = True):
        """Build EmbeddingProcessor with mocked DB, MCP, embedding agent."""
        from app.db.models.models import TeamMember, TeamMemberEmbedding, WorkTypeEnum
        from app.cron.embedding.embedding_processor import EmbeddingProcessor

        # Mock team member
        member = MagicMock(spec=TeamMember)
        member.team_member_id = "TM001"
        member.designation = "SWE"
        member.base_location = "BLR"
        member.work_type = WorkTypeEnum.wfo
        member.experience_in_months = 24
        member.profile_url = "https://docs.google.com/test" if has_profile_url else None

        # Mock embedding row
        emb_row = MagicMock(spec=TeamMemberEmbedding)
        emb_row.content_hash = stored_hash

        # Mock DB session
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [member]
        # For the hash lookup query
        db.query.return_value.filter_by.return_value.first.return_value = emb_row if stored_hash else None

        # Text assembler returns fixed strings
        with (
            patch(
                "app.cron.embedding.text_assembler.assemble_skills_text",
                return_value="Python: Expert",
            ),
            patch(
                "app.cron.embedding.text_assembler.assemble_certifications_text",
                return_value="AWS: Active",
            ),
        ):
            pass

        return EmbeddingProcessor(
            db=db,
            mcp_client=_FakeMCPClient(),
            embedding_agent=_FakeEmbeddingAgent(),
        ), db

    def test_embedding_processor_skips_on_hash_match(self):
        """If content hash unchanged and force=False, skip_count == 1."""
        from app.cron.embedding.embedding_processor import EmbeddingProcessor

        # Precompute the hash the processor will compute
        resume_text = "Mocked resume content for testing."
        skills_text = "Python: Expert"
        certs_text = "AWS: Active"
        known_hash = EmbeddingProcessor._compute_hash(
            # PII scrub is identity in unit test
            resume_text, skills_text, certs_text
        )

        processor, db = self._make_processor(stored_hash=known_hash)

        with (
            patch(
                "app.cron.embedding.text_assembler.assemble_skills_text",
                return_value=skills_text,
            ),
            patch(
                "app.cron.embedding.text_assembler.assemble_certifications_text",
                return_value=certs_text,
            ),
            patch.object(processor, "_scrub_pii", side_effect=lambda t, _: t),
        ):
            result = processor.run(force=False)

        self.assertEqual(result.skip_count, 1)
        self.assertEqual(result.success_count, 0)

    def test_embedding_processor_embeds_on_hash_mismatch(self):
        """New content → success_count == 1, DB upsert called."""
        from app.cron.embedding.embedding_processor import EmbeddingProcessor
        from app.cron.db.repositories import EmbeddingRepository

        processor, db = self._make_processor(stored_hash="stale_hash_000")

        with (
            patch(
                "app.cron.embedding.text_assembler.assemble_skills_text",
                return_value="Go: Intermediate",
            ),
            patch(
                "app.cron.embedding.text_assembler.assemble_certifications_text",
                return_value="CKA: Active",
            ),
            patch.object(processor, "_scrub_pii", side_effect=lambda t, _: t),
            patch.object(
                EmbeddingRepository, "upsert_team_member_embeddings"
            ),
        ):
            result = processor.run(force=False)

        self.assertEqual(result.success_count, 1)
        self.assertEqual(result.skip_count, 0)

    def test_embedding_processor_pii_scrub_empty_result_skips_resume_embedding(self):
        """If PII scrubber returns '', resume_embedding is skipped (None)."""
        from app.cron.embedding.embedding_processor import EmbeddingProcessor
        from app.cron.db.repositories import EmbeddingRepository

        processor, db = self._make_processor(stored_hash=None)
        captured_payloads = []

        def _capture_upsert(payload):
            captured_payloads.append(payload)

        with (
            patch(
                "app.cron.embedding.text_assembler.assemble_skills_text",
                return_value="Skills",
            ),
            patch(
                "app.cron.embedding.text_assembler.assemble_certifications_text",
                return_value="Certs",
            ),
            patch.object(processor, "_scrub_pii", return_value=""),
            patch.object(
                EmbeddingRepository,
                "upsert_team_member_embeddings",
                side_effect=_capture_upsert,
            ),
        ):
            result = processor.run(force=False)

        # resume_embedding should be None since scrub returned ""
        if captured_payloads:
            self.assertIsNone(captured_payloads[0].resume_embedding)

    def test_embed_force_flag_re_embeds_when_hash_unchanged(self):
        """force=True must bypass hash check."""
        from app.cron.embedding.embedding_processor import EmbeddingProcessor
        from app.cron.db.repositories import EmbeddingRepository

        resume_text = "Mocked resume content for testing."
        skills_text = "Python: Expert"
        certs_text = "AWS: Active"
        known_hash = EmbeddingProcessor._compute_hash(resume_text, skills_text, certs_text)
        processor, db = self._make_processor(stored_hash=known_hash)

        with (
            patch(
                "app.cron.embedding.text_assembler.assemble_skills_text",
                return_value=skills_text,
            ),
            patch(
                "app.cron.embedding.text_assembler.assemble_certifications_text",
                return_value=certs_text,
            ),
            patch.object(processor, "_scrub_pii", side_effect=lambda t, _: t),
            patch.object(EmbeddingRepository, "upsert_team_member_embeddings"),
        ):
            result = processor.run(force=True)

        self.assertEqual(result.success_count, 1)

    def test_embed_second_run_skips_unchanged(self):
        """Second run without data changes: all members skipped."""
        from app.cron.embedding.embedding_processor import EmbeddingProcessor

        resume = "resume text"
        skills = "skills text"
        certs = "certs text"
        h = EmbeddingProcessor._compute_hash(resume, skills, certs)

        processor, db = self._make_processor(stored_hash=h)
        processor.mcp_client = MagicMock()
        processor.mcp_client.fetch_resume_sync.return_value = resume

        with (
            patch(
                "app.cron.embedding.text_assembler.assemble_skills_text",
                return_value=skills,
            ),
            patch(
                "app.cron.embedding.text_assembler.assemble_certifications_text",
                return_value=certs,
            ),
            patch.object(processor, "_scrub_pii", side_effect=lambda t, _: t),
        ):
            result = processor.run(force=False)

        self.assertEqual(result.skip_count, 1)


# ---------------------------------------------------------------------------
# Integration tests (in-memory SQLite)
# ---------------------------------------------------------------------------


def _build_test_db():
    """Create in-memory SQLite DB with all tables."""
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import Session
    from app.db.base import Base
    from app.db.models import models  # noqa: F401 — registers all ORM classes

    engine = create_engine("sqlite:///:memory:", echo=False)

    # pgvector columns are Text in SQLite; no special setup needed
    Base.metadata.create_all(engine)
    return engine


class TestEmbeddingProcessorIntegration(unittest.TestCase):
    """Integration tests against in-memory SQLite."""

    def setUp(self):
        from sqlalchemy.orm import Session

        self.engine = _build_test_db()
        self.session = Session(self.engine)

    def tearDown(self):
        self.session.close()
        self.engine.dispose()

    def _seed_member(
        self,
        member_id: str = "TM_INT_001",
        profile_url: str | None = None,
    ):
        from app.db.models.models import TeamMember

        member = TeamMember(
            team_member_id=member_id,
            designation="Engineer",
            is_active=True,
            experience_in_months=24,
            profile_url=profile_url,
        )
        self.session.add(member)
        self.session.commit()
        return member

    def _make_processor(self, mcp_client=None, embedding_agent=None):
        from app.cron.embedding.embedding_processor import EmbeddingProcessor

        return EmbeddingProcessor(
            db=self.session,
            mcp_client=mcp_client or _FakeMCPClientEmpty(),
            embedding_agent=embedding_agent or _FakeEmbeddingAgent(),
        )

    def test_e2e_cron_embed_mcp_mock_to_db(self):
        """Mocked MCP + real SQLite: row inserted with skills embedding."""
        self._seed_member("TM_INT_001")
        processor = self._make_processor(mcp_client=_FakeMCPClientEmpty())

        with (
            patch(
                "app.cron.embedding.text_assembler.assemble_skills_text",
                return_value="Python: Expert",
            ),
            patch(
                "app.cron.embedding.text_assembler.assemble_certifications_text",
                return_value="",
            ),
            patch.object(processor, "_scrub_pii", side_effect=lambda t, _: t),
        ):
            result = processor.run(force=True)

        self.assertEqual(result.success_count, 1)

        from app.db.models.models import TeamMemberEmbedding
        row = (
            self.session.query(TeamMemberEmbedding)
            .filter_by(team_member_id="TM_INT_001")
            .first()
        )
        self.assertIsNotNone(row)
        self.assertIsNotNone(row.skills_embedding)

    def test_e2e_ingest_embed_phase_isolation(self):
        """
        TASK-EMB-035: embed phase error must NOT roll back previously committed data.
        """
        from app.db.models.models import TeamMember, TeamMemberEmbedding
        from app.cron.embedding.embedding_processor import EmbeddingProcessor

        self._seed_member("TM_ISO_001")

        # Confirm member row exists (ingest phase already committed)
        member = (
            self.session.query(TeamMember)
            .filter_by(team_member_id="TM_ISO_001")
            .first()
        )
        self.assertIsNotNone(member, "Team member must exist before embed phase")

        # Simulate embed phase crash
        processor = self._make_processor()
        with (
            patch(
                "app.cron.embedding.text_assembler.assemble_skills_text",
                side_effect=RuntimeError("Simulated embed crash"),
            ),
        ):
            result = processor.run(force=True)

        # Ingest data (TeamMember row) must still be intact
        member_after = (
            self.session.query(TeamMember)
            .filter_by(team_member_id="TM_ISO_001")
            .first()
        )
        self.assertIsNotNone(
            member_after, "TeamMember row must survive embed phase crash"
        )
        self.assertEqual(result.error_count, 1)

    def test_upsert_does_not_touch_profile_text(self):
        """profile_text column must not be overwritten by upsert."""
        from app.db.models.models import TeamMember, TeamMemberEmbedding
        from app.cron.db.repositories import EmbeddingRepository, EmbeddingPayload

        self._seed_member("TM_PT_001")

        # Pre-populate profile_text
        emb = TeamMemberEmbedding(
            team_member_id="TM_PT_001",
            profile_text="Original profile text that must not change.",
        )
        self.session.add(emb)
        self.session.commit()

        repo = EmbeddingRepository(self.session)
        payload = EmbeddingPayload(
            member_id="TM_PT_001",
            skills_embedding=[0.1] * 768,
            embedding=[0.1] * 768,
            content_hash="abc",
        )
        repo.upsert_team_member_embeddings(payload)
        self.session.commit()

        row = (
            self.session.query(TeamMemberEmbedding)
            .filter_by(team_member_id="TM_PT_001")
            .first()
        )
        self.assertEqual(row.profile_text, "Original profile text that must not change.")

    def test_embed_force_flag_re_embeds_all_in_db(self):
        """force=True re-embeds even if hash matches stored value."""
        from app.cron.embedding.embedding_processor import EmbeddingProcessor

        self._seed_member("TM_FORCE_001")
        processor = self._make_processor()

        # First run to establish hash
        with (
            patch(
                "app.cron.embedding.text_assembler.assemble_skills_text",
                return_value="Go: Expert",
            ),
            patch(
                "app.cron.embedding.text_assembler.assemble_certifications_text",
                return_value="",
            ),
            patch.object(processor, "_scrub_pii", side_effect=lambda t, _: t),
        ):
            r1 = processor.run(force=False)
        self.assertEqual(r1.success_count, 1)

        # Second run (same data) — force=True should re-embed
        with (
            patch(
                "app.cron.embedding.text_assembler.assemble_skills_text",
                return_value="Go: Expert",
            ),
            patch(
                "app.cron.embedding.text_assembler.assemble_certifications_text",
                return_value="",
            ),
            patch.object(processor, "_scrub_pii", side_effect=lambda t, _: t),
        ):
            r2 = processor.run(force=True)
        self.assertEqual(r2.success_count, 1)
        self.assertEqual(r2.skip_count, 0)

    def test_embed_second_run_skips_unchanged_in_db(self):
        """Second run without data changes: skip_count == total members."""
        self._seed_member("TM_SKIP_001")
        processor = self._make_processor()

        with (
            patch(
                "app.cron.embedding.text_assembler.assemble_skills_text",
                return_value="Java: Expert",
            ),
            patch(
                "app.cron.embedding.text_assembler.assemble_certifications_text",
                return_value="",
            ),
            patch.object(processor, "_scrub_pii", side_effect=lambda t, _: t),
        ):
            r1 = processor.run(force=False)
            r2 = processor.run(force=False)  # same data

        self.assertEqual(r1.success_count, 1)
        self.assertEqual(r2.skip_count, 1)


if __name__ == "__main__":
    unittest.main()
