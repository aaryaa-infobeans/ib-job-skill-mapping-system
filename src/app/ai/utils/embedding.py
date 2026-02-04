"""Embedding Agent - Generate 3072-dimensional embeddings for JD components."""

import logging
import numpy as np
from typing import Any, Dict, Optional
import os
from app.ai.utils.base import BaseAgent
from app.ai.utils.models import NormalizedRequisition, EmbeddingResult


class EmbeddingAgent(BaseAgent):
    """Generate embeddings for JD components using OpenAI API."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        super().__init__("embedding", logger)
        self.model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
        self.openai_client = None
        self._init_openai()
    
    def _init_openai(self):
        """Initialize OpenAI client."""
        try:
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                self.logger.warning("OPENAI_API_KEY not set, using mock embeddings")
                return
            self.openai_client = OpenAI(api_key=api_key)
        except ImportError:
            self.logger.warning("OpenAI library not installed, using mock embeddings")
    
    def execute(self, normalized_requisition: NormalizedRequisition) -> EmbeddingResult:
        """
        Generate embeddings for all JD components.
        
        Args:
            normalized_requisition: Normalized requisition data
            
        Returns:
            EmbeddingResult with all vectors
        """
        # Prepare texts to embed
        jd_level_text = f"Job level: {normalized_requisition.original_requisition.jd_level}"
        mandatory_text = f"Required skills: {', '.join(normalized_requisition.normalized_mandatory_skills)}"
        preferred_text = f"Preferred skills: {', '.join(normalized_requisition.normalized_preferred_skills)}"
        certification_text = f"Certifications: {', '.join(normalized_requisition.original_requisition.certifications or [])}"
        
        # Generate embeddings
        jd_level_vec = self._embed_text(jd_level_text)
        mandatory_vec = self._embed_text(mandatory_text)
        preferred_vec = self._embed_text(preferred_text)
        certification_vec = self._embed_text(certification_text) if certification_text else None
        
        result = EmbeddingResult(
            jd_level_vector=jd_level_vec,
            mandatory_vector=mandatory_vec,
            preferred_vector=preferred_vec,
            certification_vector=certification_vec,
            model=self.model
        )
        
        return result
    
    def _embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for a text string.
        
        Args:
            text: Text to embed
            
        Returns:
            3072-dimensional embedding vector
        """
        if not self.openai_client:
            # Return mock embedding for testing
            return np.random.randn(3072).astype(np.float32)
        
        try:
            response = self.openai_client.embeddings.create(
                model=self.model,
                input=text
            )
            embedding = response.data[0].embedding
            return np.array(embedding, dtype=np.float32)
        except Exception as e:
            self.logger.error(f"Failed to embed text: {str(e)}", exc_info=True)
            # Return mock embedding on error
            return np.random.randn(3072).astype(np.float32)
    
    def validate_input(self, input_data: Any) -> bool:
        """Validate that input is NormalizedRequisition."""
        if not isinstance(input_data, NormalizedRequisition):
            self.logger.warning(f"Input must be NormalizedRequisition, got {type(input_data)}")
            return False
        return True
    
    def format_output(self, result: EmbeddingResult) -> EmbeddingResult:
        """Format output - already in correct format."""
        return result
