"""
PII Scrubber Module - CR-PII-001

Implements deterministic, idempotent PII scrubbing for RAG pipeline.

Key Components:
- scrubber.py: Core scrubbing engine (FR-PII-001)
- tokenizer.py: Hash-based tokenization (FR-PII-003)
- ner_detector.py: SpaCy NER integration (FR-PII-002)
- audit_logger.py: Immutable audit logging (NFR-PII-003)
- config.py: Configuration and GPU detection (TASK-PII-001)
"""

from .scrubber import PIIScrubber
from .config import PIIConfig

__all__ = ["PIIScrubber", "PIIConfig"]
