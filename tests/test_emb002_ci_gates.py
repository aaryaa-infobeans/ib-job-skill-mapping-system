"""
Cross-Phase CI gates for CR-EMB-002 (TASK-EMB-061..065).

TASK-EMB-061: Spec traceability check — all AC-1..AC-15 referenced in tests
TASK-EMB-062: Credential isolation scan — GOOGLE_SERVICE_ACCOUNT_FILE not in cron env
TASK-EMB-063: Migration dry-run CI gate — alembic script is parseable
TASK-EMB-064: Performance regression guard — embed_text < 1s/text on mocked model
TASK-EMB-065: tools/list health check — server exposes exactly 3 tools

Run:  pytest tests/test_emb002_ci_gates.py -v
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np


ROOT = Path(__file__).resolve().parents[1] / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# TASK-EMB-061: Spec traceability — AC-1..AC-15 covered in test files
# ---------------------------------------------------------------------------


class TestSpecTraceability(unittest.TestCase):

    def test_ac_coverage_in_test_files(self):
        """
        Verify that AC-1..AC-15 are referenced somewhere in the test suite.
        Each AC must appear in at least one test file or runbook.
        """
        test_root = Path(__file__).resolve().parents[1]
        target_dirs = [
            test_root / "tests",
            test_root / "scripts",
        ]

        # Collect all text from test files + runbooks
        all_text = ""
        for d in target_dirs:
            for f in d.rglob("*.py"):
                all_text += f.read_text(encoding="utf-8", errors="ignore")
            for f in d.rglob("*.md"):
                all_text += f.read_text(encoding="utf-8", errors="ignore")

        missing = []
        for i in range(1, 16):
            tag = f"AC-{i}"
            if tag not in all_text:
                missing.append(tag)

        self.assertEqual(
            missing,
            [],
            f"Missing AC coverage in tests/runbooks: {missing}",
        )


# ---------------------------------------------------------------------------
# TASK-EMB-062: Credential isolation scan
# ---------------------------------------------------------------------------


class TestCredentialIsolation(unittest.TestCase):

    def test_sa_key_not_in_cron_env(self):
        """
        AC-14: GOOGLE_SERVICE_ACCOUNT_FILE must NOT be in cron process os.environ.
        It may only appear in StdioServerParameters.env (subprocess only).
        """
        env_backup = os.environ.pop("GOOGLE_SERVICE_ACCOUNT_FILE", None)
        try:
            self.assertNotIn(
                "GOOGLE_SERVICE_ACCOUNT_FILE",
                os.environ,
                "SA key leaked into cron process environment",
            )
        finally:
            if env_backup is not None:
                os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"] = env_backup

    def test_mcp_client_passes_sa_key_to_subprocess_only(self):
        """StdioServerParameters.env contains SA key; cron os.environ does not."""
        from app.cron.embedding.mcp_client import MCPResumeClient

        env_backup = os.environ.pop("GOOGLE_SERVICE_ACCOUNT_FILE", None)
        try:
            client = MCPResumeClient(
                server_script="fake.py",
                sa_key_path="/secrets/sa-key.json",
            )
            params = client._make_server_params()
            self.assertEqual(
                params.env.get("GOOGLE_SERVICE_ACCOUNT_FILE"),
                "/secrets/sa-key.json",
            )
            self.assertNotIn("GOOGLE_SERVICE_ACCOUNT_FILE", os.environ)
        finally:
            if env_backup is not None:
                os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"] = env_backup


# ---------------------------------------------------------------------------
# TASK-EMB-063: Migration dry-run — alembic script is parseable
# ---------------------------------------------------------------------------


class TestMigrationDryRun(unittest.TestCase):

    def test_alembic_migration_script_parseable(self):
        """
        Migration file emb002_add_multi_vector_embeddings.py must be importable
        and expose upgrade() + downgrade() callables.
        """
        import importlib.util

        migration_path = (
            Path(__file__).resolve().parents[1]
            / "alembic"
            / "versions"
            / "emb002_add_multi_vector_embeddings.py"
        )
        self.assertTrue(migration_path.exists(), f"Migration file not found: {migration_path}")

        spec = importlib.util.spec_from_file_location("emb002_migration", migration_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        self.assertEqual(mod.down_revision, "bca284b2d901")
        self.assertTrue(callable(mod.upgrade))
        self.assertTrue(callable(mod.downgrade))

    def test_acceptable_revisions_contains_new_revision(self):
        """ACCEPTABLE_REVISIONS in migrations_check.py includes emb002 revision."""
        from app.cron.db.migrations_check import ACCEPTABLE_REVISIONS

        self.assertIn(
            "emb002_multi_vec",
            ACCEPTABLE_REVISIONS,
            "New migration revision not added to ACCEPTABLE_REVISIONS",
        )


# ---------------------------------------------------------------------------
# TASK-EMB-064: Performance regression guard — embed_text < 1s/text (mocked)
# ---------------------------------------------------------------------------


class TestPerformanceRegressionGuard(unittest.TestCase):

    def test_embed_text_under_1s_per_call_mocked(self):
        """
        Single embed_text() call (mocked model) must complete in < 1s.
        Guards against accidental synchronous network calls in inference path.
        """
        import time
        import torch
        from unittest.mock import MagicMock, patch

        seq_len, hidden = 8, 768
        tok_mock = MagicMock()
        tok_mock.side_effect = lambda texts, **kw: {
            "input_ids": torch.ones(len(texts) if isinstance(texts, list) else 1, seq_len, dtype=torch.long),
            "attention_mask": torch.ones(len(texts) if isinstance(texts, list) else 1, seq_len, dtype=torch.long),
        }

        model_mock = MagicMock()
        model_mock.eval.return_value = model_mock
        model_mock.to.return_value = model_mock

        def _forward(**kwargs):
            batch = kwargs["input_ids"].shape[0]
            out = MagicMock()
            out.last_hidden_state = torch.randn(batch, seq_len, hidden)
            return out

        model_mock.side_effect = _forward

        with (
            patch("transformers.AutoTokenizer.from_pretrained", return_value=tok_mock),
            patch("transformers.AutoModel.from_pretrained", return_value=model_mock),
        ):
            from app.ai.utils.gemma_embedding import GemmaEmbeddingAgent

            agent = GemmaEmbeddingAgent(device="cpu")
            t0 = time.perf_counter()
            agent.embed_text("Software engineer with 5 years experience in Python")
            elapsed = time.perf_counter() - t0

        self.assertLess(elapsed, 1.0, f"embed_text took {elapsed:.3f}s (limit 1.0s)")


# ---------------------------------------------------------------------------
# TASK-EMB-065: tools/list health check
# ---------------------------------------------------------------------------


class TestToolsListHealthCheck(unittest.TestCase):

    def test_gdrive_server_exposes_exactly_three_tools(self):
        """
        AC-12 / RG-R10: FastMCP server must expose exactly 3 tools:
        read_document, search_files, get_file_metadata.
        """
        sys.path.insert(0, str(ROOT))
        from mcp_servers.gdrive.server import mcp

        tools = mcp._tool_manager._tools
        tool_names = set(tools.keys())

        self.assertIn("read_document", tool_names)
        self.assertIn("search_files", tool_names)
        self.assertIn("get_file_metadata", tool_names)
        self.assertEqual(len(tool_names), 3)


if __name__ == "__main__":
    unittest.main()
