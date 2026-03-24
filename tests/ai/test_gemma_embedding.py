"""
GemmaEmbeddingAgent unit tests (TASK-EMB-016) + RG-R6 memory gate (TASK-EMB-017).

Run:  pytest tests/ai/test_gemma_embedding.py -v
No real model download required — AutoModel/AutoTokenizer are mocked.
"""

import time
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
import torch


# ---------------------------------------------------------------------------
# Helpers: build fake model/tokenizer outputs
# ---------------------------------------------------------------------------

def _make_fake_tokenizer(seq_len: int = 8):
    """Return a mock tokenizer that produces fixed-length token tensors."""
    tok = MagicMock()

    def _call(texts, padding=True, truncation=True, max_length=2048, return_tensors="pt"):
        batch = len(texts) if isinstance(texts, list) else 1
        ids = torch.ones(batch, seq_len, dtype=torch.long)
        mask = torch.ones(batch, seq_len, dtype=torch.long)
        return {"input_ids": ids, "attention_mask": mask}

    tok.side_effect = _call
    tok.__call__ = _call
    return tok


def _make_fake_model(hidden: int = 768, seq_len: int = 8):
    """Return a mock model whose forward pass returns fixed last_hidden_state."""
    model = MagicMock()
    model.eval.return_value = model
    model.to.return_value = model

    def _forward(**kwargs):
        batch = kwargs["input_ids"].shape[0]
        output = MagicMock()
        output.last_hidden_state = torch.randn(batch, seq_len, hidden)
        return output

    model.side_effect = _forward
    model.__call__ = _forward
    return model


# ---------------------------------------------------------------------------
# Unit Tests
# ---------------------------------------------------------------------------

class TestGemmaEmbeddingAgent(unittest.TestCase):

    def _patched_agent(self, device: str = "cpu"):
        """Return a GemmaEmbeddingAgent with mocked model + tokenizer."""
        with (
            patch(
                "transformers.AutoTokenizer.from_pretrained",
                return_value=_make_fake_tokenizer(),
            ),
            patch(
                "transformers.AutoModel.from_pretrained",
                return_value=_make_fake_model(),
            ),
        ):
            from app.ai.utils.gemma_embedding import GemmaEmbeddingAgent
            return GemmaEmbeddingAgent(device=device)

    def test_gemma_agent_embed_text_returns_768_dim_unit_vector(self):
        """embed_text() must return (768,) ndarray with L2 norm ≈ 1.0."""
        agent = self._patched_agent()
        vec = agent.embed_text("Software engineer with 5 years experience")
        self.assertIsInstance(vec, np.ndarray)
        self.assertEqual(vec.shape, (768,))
        norm = np.linalg.norm(vec)
        self.assertAlmostEqual(float(norm), 1.0, places=5)

    def test_gemma_agent_embed_batch_returns_list(self):
        """embed_batch() returns a list of (768,) unit vectors."""
        agent = self._patched_agent()
        texts = ["Python developer", "DevOps engineer", "Data scientist"]
        results = agent.embed_batch(texts)
        self.assertEqual(len(results), 3)
        for vec in results:
            self.assertEqual(vec.shape, (768,))
            self.assertAlmostEqual(float(np.linalg.norm(vec)), 1.0, places=5)

    def test_gemma_agent_model_name_constant(self):
        """MODEL_NAME must be google/embeddinggemma-300m."""
        from app.ai.utils.gemma_embedding import GemmaEmbeddingAgent
        self.assertEqual(GemmaEmbeddingAgent.MODEL_NAME, "google/embeddinggemma-300m")

    def test_gemma_agent_fp16_on_non_cpu_device(self):
        """FP16 dtype selected when device != 'cpu' (R6 mitigation)."""
        captured = {}

        def fake_from_pretrained(model_id, torch_dtype=None, **kw):
            captured["dtype"] = torch_dtype
            return _make_fake_model()

        with (
            patch(
                "transformers.AutoTokenizer.from_pretrained",
                return_value=_make_fake_tokenizer(),
            ),
            patch(
                "transformers.AutoModel.from_pretrained",
                side_effect=fake_from_pretrained,
            ),
        ):
            from app.ai.utils.gemma_embedding import GemmaEmbeddingAgent

            GemmaEmbeddingAgent(device="cuda")

        self.assertEqual(captured["dtype"], torch.float16)

    def test_gemma_agent_fp32_on_cpu_device(self):
        """FP32 dtype selected when device == 'cpu'."""
        captured = {}

        def fake_from_pretrained(model_id, torch_dtype=None, **kw):
            captured["dtype"] = torch_dtype
            return _make_fake_model()

        with (
            patch(
                "transformers.AutoTokenizer.from_pretrained",
                return_value=_make_fake_tokenizer(),
            ),
            patch(
                "transformers.AutoModel.from_pretrained",
                side_effect=fake_from_pretrained,
            ),
        ):
            from app.ai.utils.gemma_embedding import GemmaEmbeddingAgent

            GemmaEmbeddingAgent(device="cpu")

        self.assertEqual(captured["dtype"], torch.float32)

    # ------------------------------------------------------------------
    # Throughput test — RG-R3 / AC-11
    # ------------------------------------------------------------------

    def test_throughput_100_texts(self):
        """
        100 embed_text() calls must complete in < 60s on CPU (≥100/min).
        RG-R3 gate.
        """
        agent = self._patched_agent()
        texts = [f"Team member {i} profile text for embedding." for i in range(100)]

        start = time.perf_counter()
        for t in texts:
            agent.embed_text(t)
        elapsed = time.perf_counter() - start

        self.assertLess(
            elapsed,
            60.0,
            f"Throughput gate failed: 100 texts took {elapsed:.1f}s (> 60s limit)",
        )


# ---------------------------------------------------------------------------
# RG-R6: Memory footprint check (TASK-EMB-017)
# Measured against the mocked model — verifies the check harness works.
# Real measurement must be done in Phase 3 with actual model weights loaded.
# ---------------------------------------------------------------------------

class TestRGR6MemoryGate(unittest.TestCase):

    def test_rg_r6_rss_increase_recorded(self):
        """
        RG-R6: RSS increase from GemmaEmbeddingAgent() load must be < 2 GB.
        This test uses mocked weights so actual RSS delta is near-zero.
        In Phase 3 the gate must be re-run with real model weights.
        """
        import psutil
        import os

        process = psutil.Process(os.getpid())
        rss_before = process.memory_info().rss

        with (
            patch(
                "transformers.AutoTokenizer.from_pretrained",
                return_value=_make_fake_tokenizer(),
            ),
            patch(
                "transformers.AutoModel.from_pretrained",
                return_value=_make_fake_model(),
            ),
        ):
            from app.ai.utils.gemma_embedding import GemmaEmbeddingAgent
            _ = GemmaEmbeddingAgent(device="cpu")

        rss_after = process.memory_info().rss
        delta_bytes = rss_after - rss_before
        delta_mb = delta_bytes / (1024 * 1024)

        print(f"\nRG-R6: RSS delta = {delta_mb:.1f} MB (limit 2000 MB)")

        # With mocked model the delta should be < 50 MB
        self.assertLess(
            delta_bytes,
            2_000_000_000,
            f"RG-R6 FAIL: RSS increase {delta_mb:.0f} MB exceeds 2 GB limit",
        )


if __name__ == "__main__":
    unittest.main()
