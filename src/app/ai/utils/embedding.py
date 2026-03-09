"""Embedding Agent - Generate 768-dimensional embeddings for JD components using Gemma."""

import logging
import numpy as np
from typing import Any, Dict, Optional
import os
from app.ai.utils.base import BaseAgent
from app.ai.utils.models import NormalizedRequisition, EmbeddingResult


class EmbeddingAgent(BaseAgent):
    """Generate embeddings for JD components using Google Generative AI (Gemma)."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        super().__init__("embedding", logger)
        # Fallback to gemini-embedding-001 as embedding-gemma-300m is not in the list
        self.model = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001") 
        self.genai_client = None
        self._init_genai()
    
    def _init_genai(self):
        """Initialize Google Generative AI client."""
        try:
            from google import genai
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not api_key:
                self.logger.warning("GOOGLE_API_KEY not set, using mock embeddings")
                return
            self.genai_client = genai.Client(api_key=api_key)
        except ImportError:
            self.logger.warning("google-genai library not installed, using mock embeddings")
    
    def execute(self, normalized_requisition: NormalizedRequisition) -> EmbeddingResult:
        """
        Generate embeddings for all JD components.
        
        Args:
            normalized_requisition: Normalized requisition data
            
        Returns:
            EmbeddingResult with all vectors
        """
        # Prepare texts to embed
        jd_level_text = f"Job level: {getattr(normalized_requisition.original_requisition, 'jd_level', 'N/A')}"
        mandatory_text = f"Required skills: {', '.join(normalized_requisition.original_mandatory_skills)}"
        preferred_text = f"Preferred skills: {', '.join(normalized_requisition.original_preferred_skills)}"
        
        # Build certification text
        cert_names = normalized_requisition.normalized_certifications or normalized_requisition.original_certifications
        enriched_certs = normalized_requisition.expanded_certification_terms
        certification_text = f"Certifications: {', '.join(cert_names)}"
        if enriched_certs:
            certification_text += f". Related concepts: {', '.join(enriched_certs)}"
        
        # Generate embeddings
        jd_level_vec = self.embed_text(jd_level_text)
        mandatory_vec = self.embed_text(mandatory_text)
        preferred_vec = self.embed_text(preferred_text)
        certification_vec = self.embed_text(certification_text) if certification_text else None
        
        result = EmbeddingResult(
            jd_level_vector=jd_level_vec,
            mandatory_vector=mandatory_vec,
            preferred_vector=preferred_vec,
            certification_vector=certification_vec,
            model=self.model
        )
        
        return result
    
    def embed_text(self, text_input: str) -> np.ndarray:
        """
        Generate embedding for a text string using Google's embedding model.
        
        Returns:
            768-dimensional embedding vector (default for text-embedding-004)
        """
        dimension = 768
        if not self.genai_client:
            # Return mock embedding for testing
            return np.random.randn(dimension).astype(np.float32)
        
        try:
            # New google.genai client syntax
            # Note: text-embedding-004 default dimension is 768
            response = self.genai_client.models.embed_content(
                model=self.model,
                contents=text_input,
                config={
                    "task_type": "RETRIEVAL_QUERY"
                }
            )
            embedding = response.embeddings[0].values
            return np.array(embedding, dtype=np.float32)[:dimension]
        except Exception as e:
            self.logger.error(f"Failed to embed text with Google API: {str(e)}", exc_info=True)
            return np.random.randn(dimension).astype(np.float32)
    
    def validate_input(self, input_data: Any) -> bool:
        """Validate that input is NormalizedRequisition."""
        if not isinstance(input_data, NormalizedRequisition):
            self.logger.warning(f"Input must be NormalizedRequisition, got {type(input_data)}")
            return False
        return True
    
    def format_output(self, result: EmbeddingResult) -> EmbeddingResult:
        """Format output."""
        return result
