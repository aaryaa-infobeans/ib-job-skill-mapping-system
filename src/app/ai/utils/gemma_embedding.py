"""
GemmaEmbeddingAgent — local transformer-based 768-dim embeddings.

Model: google/embeddinggemma-300m
Dimension: 768
Max tokens: 2048 (Gemma context window)

The model uses the sentence-transformers pipeline (1_Pooling → 2_Dense → 3_Dense).
Inference delegates to SentenceTransformer.encode() so all projection layers
are applied correctly. Requires HF_TOKEN env var (model is gated).

TASK-EMB-014 | Plan §5.1-5.3 | CR §3.3 | AC-4 | R6
"""

from __future__ import annotations

import logging
from typing import List

import numpy as np

logger = logging.getLogger(__name__)


class GemmaEmbeddingAgent:
    """
    Wraps google/embeddinggemma-300m via SentenceTransformer for correct
    end-to-end embeddings including the Dense projection layers.

    Model loading is deliberately separated from inference so memory profiling
    (RG-R6) can measure RSS before/after __init__().
    """

    MODEL_NAME: str = "google/embeddinggemma-300m"
    DIMENSION: int = 768
    MAX_TOKENS: int = 2048

    def __init__(self, device: str = "cpu", model_name: str = None) -> None:
        """
        Load the SentenceTransformer pipeline.

        Args:
            device: "cpu", "cuda", or "mps".
            model_name: Override model ID or local path. Defaults to MODEL_NAME.
        """
        from sentence_transformers import SentenceTransformer

        self.device = device
        model_id = model_name or self.MODEL_NAME

        logger.info("Loading SentenceTransformer from %s (device=%s)", model_id, device)
        self._st_model = SentenceTransformer(model_id, device=device)
        # Expose tokenizer for safe_max_length checks (TD-001 guard kept for safety)
        self.tokenizer = self._st_model.tokenizer

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def embed_text(self, text: str) -> np.ndarray:
        """
        Embed a single text string.

        Returns:
            np.ndarray of shape (768,) with L2 norm ≈ 1.0.
        """
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Embed a list of strings via the full sentence-transformers pipeline
        (pooling + Dense projection layers).

        Returns:
            List of np.ndarray, each shape (768,), L2-normalized.
        """
        if not texts:
            return []

        # TD-001 guard: clamp to model's actual token limit regardless of checkpoint.
        # sentence-transformers v3+ requires max_seq_length on the model object,
        # not as an encode() argument.
        safe_max_length = min(self.MAX_TOKENS, self.tokenizer.model_max_length)
        self._st_model.max_seq_length = safe_max_length

        embeddings = self._st_model.encode(
            texts,
            batch_size=len(texts),
            normalize_embeddings=True,
            convert_to_numpy=True,
        )  # shape (batch, 768), already L2-normalized

        return [embeddings[i] for i in range(len(texts))]
