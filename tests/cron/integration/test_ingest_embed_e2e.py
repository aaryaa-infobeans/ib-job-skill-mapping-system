"""
End-to-end integration tests for the CR-EMB-002 ingest → embed pipeline.

These tests use an in-memory SQLite database and mock every external call
(MCP server, Google Drive, PII scrubber, embedding model). They verify the
full data path: team-member rows seeded by the ingest phase → EmbeddingProcessor
→ TeamMemberEmbedding rows with correct vectors, texts, and hashes.

Test matrix
-----------
E2E-001  Single member — resume + skills + certs → all three embeddings stored
E2E-002  Multi-member batch (3 members) — mixed profile states → correct counts
E2E-003  Idempotency — second run, unchanged data → all members skipped
E2E-004  Force flag — re-embeds even on hash match
E2E-005  PII scrubber in pipeline — scrubbed text stored, not raw text
E2E-006  Resume-only member (no skills, no certs) → single embedding + legacy
E2E-007  Skills+certs-only member (no profile_url) → no resume fetch
E2E-008  Phase isolation — embed crash does NOT roll back ingested TeamMember rows
E2E-009  Weighted-average dimensions and L2-norm ≈ 1.0
E2E-010  Hash persisted in DB and equals recomputed hash

AC refs: AC-1, AC-5, AC-6, AC-7, AC-14, AC-15
Plan §7.2-7.5 | CR §3.6 | TASK-EMB-030..040

Run:
    pytest tests/cron/integration/test_ingest_embed_e2e.py -v
"""

from __future__ import annotations

import hashlib
import json
import unittest
from datetime import date, timedelta
from typing import Optional
from unittest.mock import MagicMock, patch

import numpy as np


# ---------------------------------------------------------------------------
# Shared fakes
# ---------------------------------------------------------------------------


def _unit_vec(dim: int = 768) -> np.ndarray:
    v = np.ones(dim, dtype=np.float32)
    return v / np.linalg.norm(v)


class _FakeEmbeddingAgent:
    """Deterministic embedding: all-ones unit vector for any text."""

    def embed_text(self, text: str) -> np.ndarray:
        return _unit_vec()


class _FakeMCPClient:
    """Returns a fixed resume string for any URL."""

    RESUME_TEXT = "Jane Doe — Senior Software Engineer, 7 years Python."

    def fetch_resume_sync(self, url: str) -> Optional[str]:
        return self.RESUME_TEXT


class _FakeMCPClientEmpty:
    """Simulates MCP returning nothing (doc not found / no profile_url)."""

    def fetch_resume_sync(self, url: str) -> Optional[str]:
        return None


def _expected_hash(resume: str, skills: str, certs: str) -> str:
    raw = f"{resume}||{skills}||{certs}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------------------------
# DB bootstrap
# ---------------------------------------------------------------------------


def _build_test_db():
    """In-memory SQLite with all ORM tables."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.db.base import Base
    from app.db.models import models  # noqa: F401

    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


# ---------------------------------------------------------------------------
# Base test class with setUp/tearDown
# ---------------------------------------------------------------------------


class _E2EBase(unittest.TestCase):

    def setUp(self):
        from sqlalchemy.orm import Session

        self.engine = _build_test_db()
        self.db = Session(self.engine)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    # -- seed helpers --------------------------------------------------------

    def _seed_member(
        self,
        member_id: str,
        profile_url: Optional[str] = None,
        designation: str = "Engineer",
        experience_months: int = 24,
    ):
        from app.db.models.models import TeamMember

        m = TeamMember(
            team_member_id=member_id,
            designation=designation,
            is_active=True,
            experience_in_months=experience_months,
            profile_url=profile_url,
        )
        self.db.add(m)
        self.db.commit()
        return m

    def _seed_skill(self, member_id: str, skill_name: str, category: str, rating: int):
        from app.db.models.models import (
            TeamMemberSkill, SkillMaster, CategoryMaster,
        )

        # Derive a deterministic skill_id from the name (SkillMaster PK is String(50))
        skill_id = skill_name.lower().replace(" ", "_")[:50]

        # category
        cat = (
            self.db.query(CategoryMaster)
            .filter_by(category_name=category)
            .first()
        )
        if not cat:
            cat = CategoryMaster(category_name=category)
            self.db.add(cat)
            self.db.flush()

        # skill
        skill = (
            self.db.query(SkillMaster)
            .filter_by(skill_id=skill_id)
            .first()
        )
        if not skill:
            skill = SkillMaster(
                skill_id=skill_id,
                skill_name=skill_name,
                category_id=cat.category_id,
            )
            self.db.add(skill)
            self.db.flush()

        tms = TeamMemberSkill(
            team_member_id=member_id,
            skill_id=skill.skill_id,
            rating=rating,
            is_deleted=False,
        )
        self.db.add(tms)
        self.db.commit()

    def _seed_cert(
        self,
        member_id: str,
        skill_name: str,
        cert_name: str,
        issuer: str,
        valid_till: Optional[date] = None,
    ):
        from app.db.models.models import (
            TeamMemberSkill, SkillMaster, CategoryMaster,
            TeamMemberSkillCertification,
        )

        skill_id = skill_name.lower().replace(" ", "_")[:50]

        skill = (
            self.db.query(SkillMaster).filter_by(skill_id=skill_id).first()
        )
        if not skill:
            cat = CategoryMaster(category_name="General")
            self.db.add(cat)
            self.db.flush()
            skill = SkillMaster(
                skill_id=skill_id,
                skill_name=skill_name,
                category_id=cat.category_id,
            )
            self.db.add(skill)
            self.db.flush()

        tms = (
            self.db.query(TeamMemberSkill)
            .filter_by(team_member_id=member_id, skill_id=skill.skill_id)
            .first()
        )
        if not tms:
            tms = TeamMemberSkill(
                team_member_id=member_id,
                skill_id=skill.skill_id,
                rating=5,
                is_deleted=False,
            )
            self.db.add(tms)
            self.db.flush()

        cert = TeamMemberSkillCertification(
            team_member_id=member_id,
            skill_id=skill.skill_id,
            certificate=cert_name,
            issuer=issuer,
            valid_till=valid_till,
        )
        self.db.add(cert)
        self.db.commit()

    # -- processor factory ---------------------------------------------------

    def _make_processor(self, mcp_client=None, embedding_agent=None):
        from app.cron.embedding.embedding_processor import EmbeddingProcessor

        return EmbeddingProcessor(
            db=self.db,
            mcp_client=mcp_client or _FakeMCPClientEmpty(),
            embedding_agent=embedding_agent or _FakeEmbeddingAgent(),
        )

    # -- assertion helpers ---------------------------------------------------

    def _get_embedding_row(self, member_id: str):
        from app.db.models.models import TeamMemberEmbedding

        return (
            self.db.query(TeamMemberEmbedding)
            .filter_by(team_member_id=member_id)
            .first()
        )


# ===========================================================================
# E2E-001: Single member — resume + skills + certs → all three embeddings
# ===========================================================================


class TestE2E001SingleMemberFullPipeline(_E2EBase):

    def test_all_three_embeddings_stored_in_db(self):
        """
        AC-1 / AC-5: After a full pipeline run, team_member_embeddings must
        contain resume_embedding, skills_embedding, certifications_embedding,
        and the weighted-average legacy embedding.
        """
        mid = "E2E_001"
        self._seed_member(mid, profile_url="https://docs.google.com/d/fakeid1")
        self._seed_skill(mid, "Python", "Programming", 9)
        self._seed_cert(
            mid, "Python", "AWS SA", "Amazon",
            valid_till=date.today() + timedelta(days=365),
        )

        processor = self._make_processor(mcp_client=_FakeMCPClient())
        with patch.object(processor, "_scrub_pii", side_effect=lambda t, _: t):
            result = processor.run(force=True)

        self.assertEqual(result.success_count, 1)
        self.assertEqual(result.error_count, 0)

        row = self._get_embedding_row(mid)
        self.assertIsNotNone(row, "Embedding row must be inserted")
        self.assertIsNotNone(row.resume_embedding, "resume_embedding must be set")
        self.assertIsNotNone(row.skills_embedding, "skills_embedding must be set")
        self.assertIsNotNone(row.certifications_embedding, "certifications_embedding must be set")
        self.assertIsNotNone(row.embedding, "legacy weighted-average embedding must be set")

    def test_resume_text_and_skills_text_stored(self):
        """resume_text and skills_text must be written to the DB row."""
        mid = "E2E_001b"
        self._seed_member(mid, profile_url="https://docs.google.com/d/fakeid1b")
        self._seed_skill(mid, "Java", "Programming", 7)

        processor = self._make_processor(mcp_client=_FakeMCPClient())
        with patch.object(processor, "_scrub_pii", side_effect=lambda t, _: t):
            processor.run(force=True)

        row = self._get_embedding_row(mid)
        self.assertIsNotNone(row.resume_text)
        self.assertIn("Jane Doe", row.resume_text)
        self.assertIsNotNone(row.skills_text)
        self.assertIn("Java", row.skills_text)


# ===========================================================================
# E2E-002: Multi-member batch — mixed profile states
# ===========================================================================


class TestE2E002MultimemberBatch(_E2EBase):

    def test_batch_processes_three_members_with_mixed_profiles(self):
        """
        Three members:
          - TM_A: has profile_url → resume fetch succeeds
          - TM_B: has profile_url → MCP returns None (no doc)
          - TM_C: no profile_url → no MCP call at all
        All should succeed (success_count == 3).
        """

        class _SelectiveMCP:
            """Returns resume only for TM_A's URL."""

            def fetch_resume_sync(self, url: str) -> Optional[str]:
                if "TM_A" in url:
                    return "Resume for member A."
                return None

        self._seed_member("TM_A", profile_url="https://docs.google.com/d/TM_A_id")
        self._seed_skill("TM_A", "Go", "Backend", 8)
        self._seed_member("TM_B", profile_url="https://docs.google.com/d/TM_B_id")
        self._seed_skill("TM_B", "Rust", "Systems", 6)
        self._seed_member("TM_C", profile_url=None)
        self._seed_skill("TM_C", "SQL", "Database", 9)

        processor = self._make_processor(mcp_client=_SelectiveMCP())
        with patch.object(processor, "_scrub_pii", side_effect=lambda t, _: t):
            result = processor.run(force=True)

        self.assertEqual(result.success_count, 3)
        self.assertEqual(result.error_count, 0)

        # TM_A has resume; TM_B and TM_C do not
        row_a = self._get_embedding_row("TM_A")
        row_b = self._get_embedding_row("TM_B")
        row_c = self._get_embedding_row("TM_C")

        self.assertIsNotNone(row_a.resume_embedding)
        self.assertIsNone(row_b.resume_embedding)
        self.assertIsNone(row_c.resume_embedding)

        # All three have skills embeddings
        self.assertIsNotNone(row_a.skills_embedding)
        self.assertIsNotNone(row_b.skills_embedding)
        self.assertIsNotNone(row_c.skills_embedding)


# ===========================================================================
# E2E-003: Idempotency — second run, unchanged data → all skipped
# ===========================================================================


class TestE2E003Idempotency(_E2EBase):

    def test_second_run_skips_all_members(self):
        """AC-6: second run with same data must skip all (hash unchanged)."""
        mid = "E2E_003"
        self._seed_member(mid)
        self._seed_skill(mid, "TypeScript", "Frontend", 7)

        processor = self._make_processor()
        skills_text = "Skills:\nTypeScript (Frontend): Intermediate"

        with (
            patch(
                "app.cron.embedding.text_assembler.assemble_skills_text",
                return_value=skills_text,
            ),
            patch(
                "app.cron.embedding.text_assembler.assemble_certifications_text",
                return_value="",
            ),
            patch.object(processor, "_scrub_pii", side_effect=lambda t, _: t),
        ):
            r1 = processor.run(force=False)
            r2 = processor.run(force=False)

        self.assertEqual(r1.success_count, 1)
        self.assertEqual(r1.skip_count, 0)
        self.assertEqual(r2.success_count, 0)
        self.assertEqual(r2.skip_count, 1, "Unchanged data: member must be skipped on second run")


# ===========================================================================
# E2E-004: Force flag — re-embeds even on hash match
# ===========================================================================


class TestE2E004ForceFlag(_E2EBase):

    def test_force_flag_re_embeds_on_identical_data(self):
        """AC-6 inverse: force=True bypasses hash check and re-embeds."""
        mid = "E2E_004"
        self._seed_member(mid)
        self._seed_skill(mid, "Kotlin", "Mobile", 8)

        processor = self._make_processor()
        fixed_skills = "Skills:\nKotlin (Mobile): Expert"

        with (
            patch(
                "app.cron.embedding.text_assembler.assemble_skills_text",
                return_value=fixed_skills,
            ),
            patch(
                "app.cron.embedding.text_assembler.assemble_certifications_text",
                return_value="",
            ),
            patch.object(processor, "_scrub_pii", side_effect=lambda t, _: t),
        ):
            r1 = processor.run(force=False)  # first run — store hash
            r2 = processor.run(force=True)   # force — must re-embed

        self.assertEqual(r1.success_count, 1)
        self.assertEqual(r2.success_count, 1, "force=True must re-embed even when hash unchanged")
        self.assertEqual(r2.skip_count, 0)


# ===========================================================================
# E2E-005: PII scrubber in pipeline
# ===========================================================================


class TestE2E005PIIScrubInPipeline(_E2EBase):

    def test_scrubbed_text_stored_not_raw(self):
        """
        PII scrubber must run before DB write.
        The stored resume_text must equal the scrubbed version.
        """
        mid = "E2E_005"
        raw_resume = "John Smith, SSN: 123-45-6789, DOB: 1990-01-01. Python expert."
        scrubbed_resume = "John Smith, SSN: [REDACTED], DOB: [REDACTED]. Python expert."

        self._seed_member(mid, profile_url="https://docs.google.com/d/pii_test")
        self._seed_skill(mid, "Python", "Programming", 9)

        class _PIIMCPClient:
            def fetch_resume_sync(self, url: str) -> Optional[str]:
                return raw_resume

        processor = self._make_processor(mcp_client=_PIIMCPClient())
        # Simulate a scrubber that replaces SSN and DOB patterns
        with patch.object(
            processor, "_scrub_pii", return_value=scrubbed_resume
        ):
            result = processor.run(force=True)

        self.assertEqual(result.success_count, 1)
        row = self._get_embedding_row(mid)
        self.assertIsNotNone(row)
        self.assertEqual(
            row.resume_text,
            scrubbed_resume,
            "Stored resume_text must be the PII-scrubbed version",
        )
        self.assertNotIn("123-45-6789", row.resume_text or "")

    def test_pii_scrub_failure_falls_back_to_original(self):
        """
        If PIIScrubber raises at runtime, the pipeline must fall back to the
        original text (not crash). The member should still be embedded.
        The catch lives inside EmbeddingProcessor._scrub_pii.
        """
        mid = "E2E_005b"
        raw_resume = "Alice Engineer, plain resume, no PII."
        self._seed_member(mid, profile_url="https://docs.google.com/d/fallback")
        self._seed_skill(mid, "C++", "Systems", 7)

        class _MCPClient:
            def fetch_resume_sync(self, url: str) -> Optional[str]:
                return raw_resume

        processor = self._make_processor(mcp_client=_MCPClient())
        # Patch PIIScrubber to raise during instantiation.
        # EmbeddingProcessor._scrub_pii has a try/except that catches this and
        # returns the original text, so the pipeline must still succeed.
        with patch("app.pii.scrubber.PIIScrubber", side_effect=RuntimeError("scrubber down")):
            result = processor.run(force=True)

        # Pipeline should still succeed — _scrub_pii catches all exceptions
        self.assertEqual(result.error_count, 0)
        row = self._get_embedding_row(mid)
        self.assertIsNotNone(row, "Embedding row must exist despite scrubber failure")
        # Fallback: stored resume_text should equal the raw (un-scrubbed) text
        self.assertEqual(row.resume_text, raw_resume)


# ===========================================================================
# E2E-006: Resume-only member (no skills, no certs)
# ===========================================================================


class TestE2E006ResumeOnlyMember(_E2EBase):

    def test_resume_only_member_stored_with_legacy_embedding(self):
        """
        Member with profile_url but no skills/certs:
          - resume_embedding set
          - skills_embedding = None
          - certifications_embedding = None
          - legacy embedding = normalized resume_embedding
        """
        mid = "E2E_006"
        self._seed_member(mid, profile_url="https://docs.google.com/d/resume_only")
        # No skills, no certs seeded

        processor = self._make_processor(mcp_client=_FakeMCPClient())
        with patch.object(processor, "_scrub_pii", side_effect=lambda t, _: t):
            result = processor.run(force=True)

        self.assertEqual(result.success_count, 1)
        row = self._get_embedding_row(mid)
        self.assertIsNotNone(row.resume_embedding)
        self.assertIsNone(row.skills_embedding)
        self.assertIsNone(row.certifications_embedding)
        self.assertIsNotNone(row.embedding, "Legacy embedding must exist even for resume-only")


# ===========================================================================
# E2E-007: Skills+certs-only member (no profile_url)
# ===========================================================================


class TestE2E007SkillsCertsOnlyMember(_E2EBase):

    def test_no_mcp_call_when_profile_url_is_none(self):
        """
        Member without profile_url: MCP must NOT be called, resume_embedding = None,
        skills + certs embeddings are stored.
        AC-7: no unnecessary MCP calls.
        """
        mid = "E2E_007"
        self._seed_member(mid, profile_url=None)
        self._seed_skill(mid, "Terraform", "DevOps", 8)
        self._seed_cert(
            mid, "Terraform", "HashiCorp Terraform Associate", "HashiCorp", None
        )

        mcp_spy = MagicMock(wraps=_FakeMCPClientEmpty())
        processor = self._make_processor(mcp_client=mcp_spy)
        with patch.object(processor, "_scrub_pii", side_effect=lambda t, _: t):
            result = processor.run(force=True)

        mcp_spy.fetch_resume_sync.assert_not_called()
        self.assertEqual(result.success_count, 1)
        row = self._get_embedding_row(mid)
        self.assertIsNone(row.resume_embedding)
        self.assertIsNotNone(row.skills_embedding)
        self.assertIsNotNone(row.certifications_embedding)


# ===========================================================================
# E2E-008: Phase isolation — embed crash does not roll back ingested rows
# ===========================================================================


class TestE2E008PhaseIsolation(_E2EBase):

    def test_embed_crash_preserves_team_member_rows(self):
        """
        AC-15: Embed phase crash must NOT roll back previously committed
        TeamMember rows (ingest phase is a separate transaction).
        """
        from app.db.models.models import TeamMember

        mid = "E2E_008"
        self._seed_member(mid)

        # Verify the member is in the DB (simulating ingest committed)
        member = (
            self.db.query(TeamMember).filter_by(team_member_id=mid).first()
        )
        self.assertIsNotNone(member, "TeamMember must exist before embed phase")

        # Simulate embed phase crash in the text assembler
        processor = self._make_processor()
        with patch(
            "app.cron.embedding.text_assembler.assemble_skills_text",
            side_effect=RuntimeError("embed crash"),
        ):
            result = processor.run(force=True)

        self.assertEqual(result.error_count, 1)

        # TeamMember row must still exist after embed phase crash
        member_after = (
            self.db.query(TeamMember).filter_by(team_member_id=mid).first()
        )
        self.assertIsNotNone(
            member_after,
            "TeamMember row must survive an embed phase crash (phase isolation)",
        )

        # No embedding row should have been written
        emb_row = self._get_embedding_row(mid)
        self.assertIsNone(
            emb_row, "No embedding row should be written after a crash"
        )


# ===========================================================================
# E2E-009: Weighted-average vector — correct dimensions and L2-norm ≈ 1.0
# ===========================================================================


class TestE2E009WeightedAverageNorm(_E2EBase):

    def test_legacy_embedding_is_768_dim_unit_vector(self):
        """
        The stored legacy embedding must be 768-dimensional and L2-normalised
        (norm ≈ 1.0). Stored as a JSON list in SQLite.
        """
        import json as _json

        mid = "E2E_009"
        self._seed_member(mid, profile_url="https://docs.google.com/d/norm_test")
        self._seed_skill(mid, "Scala", "JVM", 9)

        processor = self._make_processor(mcp_client=_FakeMCPClient())
        with patch.object(processor, "_scrub_pii", side_effect=lambda t, _: t):
            processor.run(force=True)

        row = self._get_embedding_row(mid)
        self.assertIsNotNone(row.embedding)

        # SQLite stores the embedding as a JSON string
        raw = row.embedding
        vec = np.array(_json.loads(raw) if isinstance(raw, str) else raw, dtype=np.float32)

        self.assertEqual(vec.shape, (768,), "Embedding must be 768-dimensional")
        norm = float(np.linalg.norm(vec))
        self.assertAlmostEqual(
            norm, 1.0, places=4,
            msg=f"Legacy embedding norm should be ≈ 1.0; got {norm:.6f}",
        )


# ===========================================================================
# E2E-010: Content hash persisted and matches recomputed hash
# ===========================================================================


class TestE2E010ContentHashConsistency(_E2EBase):

    def test_stored_hash_equals_recomputed_hash(self):
        """
        AC-6: The content_hash stored in DB must equal
        SHA-256(resume_text||skills_text||certs_text).
        """
        mid = "E2E_010"
        self._seed_member(mid, profile_url="https://docs.google.com/d/hash_test")
        self._seed_skill(mid, "Elixir", "Functional", 8)

        resume_text = _FakeMCPClient.RESUME_TEXT

        processor = self._make_processor(mcp_client=_FakeMCPClient())
        with patch.object(processor, "_scrub_pii", side_effect=lambda t, _: t):
            result = processor.run(force=True)

        self.assertEqual(result.success_count, 1)
        row = self._get_embedding_row(mid)
        self.assertIsNotNone(row.content_hash)

        # Recompute the hash from what's stored in the DB
        recomputed = _expected_hash(
            row.resume_text or "",
            row.skills_text or "",
            row.certifications_text or "",
        )
        self.assertEqual(
            row.content_hash,
            recomputed,
            "Stored content_hash must equal SHA-256(resume||skills||certs)",
        )

    def test_hash_changes_when_skills_change(self):
        """
        If skills change between runs, the hash must change and re-embedding
        must occur (success_count == 1 on second run, not skip).
        """
        mid = "E2E_010b"
        self._seed_member(mid)

        processor = self._make_processor()

        with (
            patch(
                "app.cron.embedding.text_assembler.assemble_skills_text",
                return_value="Skills:\nPython (Programming): Expert",
            ),
            patch(
                "app.cron.embedding.text_assembler.assemble_certifications_text",
                return_value="",
            ),
            patch.object(processor, "_scrub_pii", side_effect=lambda t, _: t),
        ):
            r1 = processor.run(force=False)

        hash_after_r1 = self._get_embedding_row(mid).content_hash

        with (
            patch(
                "app.cron.embedding.text_assembler.assemble_skills_text",
                return_value="Skills:\nRust (Systems): Expert",  # changed
            ),
            patch(
                "app.cron.embedding.text_assembler.assemble_certifications_text",
                return_value="",
            ),
            patch.object(processor, "_scrub_pii", side_effect=lambda t, _: t),
        ):
            r2 = processor.run(force=False)

        hash_after_r2 = self._get_embedding_row(mid).content_hash

        self.assertEqual(r1.success_count, 1)
        self.assertEqual(r2.success_count, 1, "Changed skills must trigger re-embed")
        self.assertNotEqual(
            hash_after_r1, hash_after_r2, "Hash must change when content changes"
        )


if __name__ == "__main__":
    unittest.main()
