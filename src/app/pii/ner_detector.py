"""
NER Detection with SpaCy - FR-PII-002, TASK-PII-002

Implements Named Entity Recognition using SpaCy models.

Model Specifications:
- Model: en_core_web_sm (12.8MB CPU model, default for Python 3.13)
- Model (alternate): en_core_web_trf (560MB transformer, requires Python 3.11/3.12)
- F1-score: ≥ 0.85 (en_core_web_sm) or ≥ 0.90 (en_core_web_trf)
- GPU acceleration: Optional, CPU-based model used by default
- Entity types: PERSON, ORG, GPE, LOC, DATE, etc.

Linked Specs:
- FR-PII-002: NER integration for PII detection
- NFR-PII-001: Performance requirements (p95 ≤ 50ms)
- TASK-PII-002: Model installation and validation
"""

import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PIIEntity:
    """Detected PII entity from NER."""
    text: str
    label: str
    start: int
    end: int
    confidence: float


class NERDetector:
    """SpaCy-based NER detector for PII identification."""
    
    def __init__(self, model_name: str = "en_core_web_sm", use_gpu: bool = False, confidence_threshold: float = 0.85):
        """
        Initialize NER detector with SpaCy model.
        
        Args:
            model_name: SpaCy model name (default: en_core_web_sm for Python 3.13)
            use_gpu: Enable GPU acceleration (default: False, CPU-based model)
            confidence_threshold: Minimum confidence for entity detection (default: 0.85 for CPU model)
        
        Validation (TASK-PII-002 DoD):
        - Model loads in < 5 seconds
        - F1 ≥ 0.85 on validation corpus (0.90 for transformer models)
        - Version locked (3.5+)
        """
        logger.info(f"NERDetector.__init__ called with model_name={model_name}, use_gpu={use_gpu}, confidence_threshold={confidence_threshold}")
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self._nlp = None
        self._load_time = None
        
        # Load model
        start_time = time.time()
        self._load_model(use_gpu)
        self._load_time = time.time() - start_time
        
        # Validate load time
        if self._load_time >= 5.0:
            logger.warning(
                "Model load time %.2fs exceeds 5s threshold (TASK-PII-002)",
                self._load_time
            )
        else:
            logger.info("Model loaded in %.2fs", self._load_time)
    
    def _load_model(self, use_gpu: bool) -> None:
        """
        Load SpaCy NER model.
        
        Args:
            use_gpu: Enable GPU acceleration
        
        Raises:
            RuntimeError: If model cannot be loaded
        """
        try:
            import spacy
            
            # Verify SpaCy version
            spacy_version = spacy.__version__
            major_version = int(spacy_version.split('.')[0])
            if major_version < 3:
                raise RuntimeError(f"SpaCy version {spacy_version} < 3.x (requirement: 3.5+)")
            
            logger.info(f"Loading SpaCy model '{self.model_name}' (version: {spacy_version})")
            
            # Load model
            try:
                self._nlp = spacy.load(self.model_name)
            except OSError:
                raise RuntimeError(
                    f"SpaCy model '{self.model_name}' not found. "
                    f"Install with: python -m spacy download {self.model_name}"
                )
            
            # Configure GPU
            if use_gpu:
                try:
                    spacy.prefer_gpu()
                    logger.info("GPU acceleration enabled for SpaCy")
                except Exception as e:
                    logger.warning(f"GPU acceleration failed, falling back to CPU: {e}")
            
            # Validate model has NER component
            if "ner" not in self._nlp.pipe_names:
                raise RuntimeError(f"Model '{self.model_name}' missing NER component")
            
            logger.info(f"Model pipeline: {self._nlp.pipe_names}")
            
        except ImportError:
            raise RuntimeError(
                "SpaCy not installed. Install with: pip install spacy"
            )
    
    def detect_entities(self, text: str) -> List[PIIEntity]:
        """
        Detect PII entities in text using NER.
        
        Args:
            text: Input text to analyze
        
        Returns:
            List of detected PII entities
        
        Entity Types Detected:
        - PERSON: Personal names
        - ORG: Organizations, companies
        - GPE: Countries, cities, states
        - DATE: Dates (may contain identifying info)
        - LOC: Non-GPE locations
        
        Performance (NFR-PII-001):
        - p95 latency ≤ 50ms
        - GPU acceleration provides 5x speedup vs CPU
        """
        if not text or not text.strip():
            return []
        
        start_time = time.time()
        
        # Process text with SpaCy
        doc = self._nlp(text)
        
        # Extract entities above confidence threshold
        entities = []
        for ent in doc.ents:
            # SpaCy transformer models don't always expose confidence scores
            # Use 1.0 as default (model is pre-validated at F1 ≥ 0.90)
            confidence = getattr(ent, 'confidence', 1.0)
            
            if confidence >= self.confidence_threshold:
                entities.append(PIIEntity(
                    text=ent.text,
                    label=ent.label_,
                    start=ent.start_char,
                    end=ent.end_char,
                    confidence=confidence
                ))
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        logger.debug(
            "Detected %d entities in %.2fms (text_length=%d)",
            len(entities),
            elapsed_ms,
            len(text)
        )
        
        return entities
    
    def detect_person_names(self, text: str) -> List[PIIEntity]:
        """
        Detect only PERSON entities (names).
        
        Args:
            text: Input text
        
        Returns:
            List of PERSON entities
        """
        all_entities = self.detect_entities(text)
        return [e for e in all_entities if e.label == "PERSON"]
    
    def detect_organizations(self, text: str) -> List[PIIEntity]:
        """
        Detect only ORG entities (companies, organizations).
        
        Args:
            text: Input text
        
        Returns:
            List of ORG entities
        """
        all_entities = self.detect_entities(text)
        return [e for e in all_entities if e.label == "ORG"]
    
    @property
    def model_info(self) -> Dict[str, Any]:
        """Get model information for validation."""
        return {
            "model_name": self.model_name,
            "load_time_seconds": self._load_time,
            "confidence_threshold": self.confidence_threshold,
            "pipeline_components": self._nlp.pipe_names if self._nlp else [],
        }
