"""
GemmaEmbeddingAgent — local transformer-based 768-dim embeddings.

Model: google/embeddinggemma-300m
Dimension: 768
Max tokens: 2048

Usage:
    agent = GemmaEmbeddingAgent(device="cpu")
    vec = agent.embed_text("Software Engineer with Python experience")
    # vec.shape == (768,), np.linalg.norm(vec) ≈ 1.0

TASK-EMB-014 | Plan §5.1-5.3 | CR §3.3 | AC-4 | R6
"""

from __future__ import annotations

import logging
from typing import List

import numpy as np

logger = logging.getLogger(__name__)


class GemmaEmbeddingAgent:
    """
    Wraps google/embeddinggemma-300m for mean-pooling + L2-normalized embeddings.

    Model loading is deliberately separated from inference so memory profiling
    (RG-R6) can measure RSS before/after __init__().
    """

    MODEL_NAME: str = "google/embeddinggemma-300m"
    DIMENSION: int = 768
    MAX_TOKENS: int = 2048

    def __init__(self, device: str = "cpu", model_name: str = None) -> None:
        """
        Load tokenizer and model.

        Args:
            device: "cpu", "cuda", or "mps". FP16 used for non-CPU devices to
                    reduce memory footprint (R6 mitigation).
            model_name: Override model ID or local path. Defaults to MODEL_NAME.
        """
        import torch
        from transformers import AutoModel, AutoTokenizer

        self.device = device

        # Choose dtype: FP32 on CPU, FP16 elsewhere (R6)
        dtype = torch.float32 if device == "cpu" else torch.float16

        model_id = model_name or self.MODEL_NAME

        logger.info("Loading tokenizer from %s", model_id)
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)

        logger.info("Loading model from %s (dtype=%s, device=%s)", model_id, dtype, device)
        # Suppress torch_dtype deprecation warning
        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=".*torch_dtype.*deprecated.*", category=FutureWarning)
            self.model = AutoModel.from_pretrained(model_id, torch_dtype=dtype)
        self.model.to(device)
        self.model.eval()

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
        Embed a list of strings.

        Returns:
            List of np.ndarray, each shape (768,), L2-normalized.
        """
        import torch

        if not texts:
            return []

        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=self.MAX_TOKENS,
            return_tensors="pt",
        )
        encoded = {k: v.to(self.device) for k, v in encoded.items()}

        with torch.no_grad():
            outputs = self.model(**encoded)

        # Mean pooling over non-padding token positions
        last_hidden = outputs.last_hidden_state  # (batch, seq, hidden)
        attention_mask = encoded["attention_mask"]  # (batch, seq)

        # Expand mask to hidden dim
        mask_expanded = (
            attention_mask.unsqueeze(-1).expand(last_hidden.size()).float()
        )
        sum_hidden = (last_hidden.float() * mask_expanded).sum(dim=1)
        sum_mask = mask_expanded.sum(dim=1).clamp(min=1e-9)
        pooled = sum_hidden / sum_mask  # (batch, hidden)

        pooled_np = pooled.cpu().numpy()  # (batch, 768)

        # L2-normalize each vector
        norms = np.linalg.norm(pooled_np, axis=1, keepdims=True).clip(min=1e-9)
        normalized = pooled_np / norms

        return [normalized[i] for i in range(len(texts))]
