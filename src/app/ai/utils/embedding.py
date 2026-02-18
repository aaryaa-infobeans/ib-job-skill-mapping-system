"""Embedding Agent - Generate 3072-dimensional embeddings for JD components."""

import logging
import numpy as np
from typing import Any, Dict, Optional
import os
from app.ai.utils.base import BaseAgent
from app.ai.utils.models import NormalizedRequisition, EmbeddingResult


from app.settings import settings

class EmbeddingAgent(BaseAgent):
    """Generate embeddings for JD components using configured Provider (OpenAI or Google)."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        super().__init__("embedding", logger)
        self.provider = settings.embedding_provider.lower()
        self.target_dim = getattr(settings, "pgvector_dimension", 3072)
        
        self.openai_client = None
        self.google_embeddings = None
        
        if self.provider == "google":
            self._init_google()
        else:
            self._init_openai()
    
    def _init_google(self):
        """Initialize Google Generative AI embeddings."""
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            api_key = settings.google_api_key or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                self.logger.warning("GOOGLE_API_KEY not set, using mock embeddings")
                return
            
            self.google_embeddings = GoogleGenerativeAIEmbeddings(
                model=settings.google_embedding_model,
                google_api_key=api_key
            )
            self.model = settings.google_embedding_model
            self.logger.info(f"✅ Initialized Google Embeddings: {self.model}")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Google embeddings: {str(e)}")
    
    def _init_openai(self):
        """Initialize OpenAI client."""
        try:
            from openai import OpenAI
            api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                self.logger.warning("OPENAI_API_KEY not set, using mock embeddings")
                return
            self.openai_client = OpenAI(api_key=api_key)
            self.model = settings.openai_embedding_model
            self.logger.info(f"✅ Initialized OpenAI Embeddings: {self.model}")
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
        mandatory_text = f"Required skills: {', '.join(normalized_requisition.original_mandatory_skills)}"
        preferred_text = f"Preferred skills: {', '.join(normalized_requisition.original_preferred_skills)}"
        
        # Build certification text using both original names and enriched terms
        cert_names = normalized_requisition.normalized_certifications or normalized_requisition.original_certifications
        enriched_certs = normalized_requisition.expanded_certification_terms
        certification_text = f"Certifications: {', '.join(cert_names)}"
        if enriched_certs:
            certification_text += f". Related concepts: {', '.join(enriched_certs)}"
        
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
        Generate embedding for a text string using configured provider.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector (padded to target_dim if necessary)
        """
        # Try Google first if configured
        if self.provider == "google" and self.google_embeddings:
            try:
                embedding = self.google_embeddings.embed_query(text)
                vector = np.array(embedding, dtype=np.float32)
                
                # Zero-padding for dimension mismatch (e.g., 768 -> 3072)
                if len(vector) < self.target_dim:
                    vector = np.pad(vector, (0, self.target_dim - len(vector)), mode='constant')
                
                return vector[:self.target_dim]
            except Exception as e:
                self.logger.error(f"Failed to embed text with Google: {str(e)}")
                # Continue to fallback or mock
        
        # Try OpenAI
        if self.openai_client:
            try:
                response = self.openai_client.embeddings.create(
                    model=self.model,
                    input=text
                )
                embedding = response.data[0].embedding
                vector = np.array(embedding, dtype=np.float32)

                if len(vector) < self.target_dim:
                    vector = np.pad(vector, (0, self.target_dim - len(vector)), mode='constant')
                
                return vector[:self.target_dim]
            except Exception as e:
                self.logger.error(f"Failed to embed text with OpenAI: {str(e)}", exc_info=True)
        
        # Fallback to mock embedding
        return np.random.randn(self.target_dim).astype(np.float32)
    
    def validate_input(self, input_data: Any) -> bool:
        """Validate that input is NormalizedRequisition."""
        if not isinstance(input_data, NormalizedRequisition):
            self.logger.warning(f"Input must be NormalizedRequisition, got {type(input_data)}")
            return False
        return True
    
    def format_output(self, result: EmbeddingResult) -> EmbeddingResult:
        """Format output - already in correct format."""
        return result
