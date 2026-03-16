"""Embedding Agent - Generate 768-dimensional embeddings for JD components using Gemma."""

import logging
import numpy as np
from typing import Any, Dict, Optional
import os
from app.ai.utils.base import BaseAgent
from app.ai.utils.models import NormalizedRequisition, EmbeddingResult


class EmbeddingAgent(BaseAgent):
    """Generate embeddings for JD components using Google Gemini or local Gemma."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        super().__init__("embedding", logger)
        from app.settings import settings
        
        self.model_name = settings.embedding_model or settings.embedding_model_name
        self.device = settings.embedding_device
        
        if "gemini" in self.model_name.lower():
            import google.generativeai as genai
            api_key = settings.google_api_key
            if not api_key:
                # Try env fallback if settings doesn't have it
                api_key = os.getenv("GOOGLE_API_KEY")
            
            if not api_key:
                self.logger.error("GOOGLE_API_KEY not found in settings or environment")
                raise ValueError("GOOGLE_API_KEY is required for Gemini embeddings")
                
            genai.configure(api_key=api_key)
            self.model_type = "gemini"
            self.logger.info(f"Initializing Gemini EmbeddingAgent with model={self.model_name}")
        else:
            from app.ai.utils.gemma_embedding import GemmaEmbeddingAgent
            self.model_type = "gemma"
            self.logger.info(f"Initializing local Gemma EmbeddingAgent with model={self.model_name}, device={self.device}")
            self.gemma_agent = GemmaEmbeddingAgent(device=self.device, model_name=self.model_name)
    
    def execute(self, normalized_requisition: NormalizedRequisition) -> EmbeddingResult:
        """
        Generate embeddings for all JD components.
        
        Args:
            normalized_requisition: Normalized requisition data
            
        Returns:
            EmbeddingResult with all vectors
        """
        # Prepare texts to embed
        m_skills = normalized_requisition.original_mandatory_skills
        p_skills = normalized_requisition.original_preferred_skills
        jd_level = getattr(normalized_requisition.original_requisition, 'jd_level', None)
        cert_names = normalized_requisition.normalized_certifications or normalized_requisition.original_certifications
        enriched_certs = normalized_requisition.expanded_certification_terms
        
        # Build texts only if content exists
        jd_level_text = f"Job level: {jd_level}" if jd_level else None
        mandatory_text = f"Required skills: {', '.join(m_skills)}" if m_skills else None
        preferred_text = f"Preferred skills: {', '.join(p_skills)}" if p_skills else None
        
        certification_text = None
        if cert_names or enriched_certs:
            certification_text = f"Certifications: {', '.join(cert_names)}"
            if enriched_certs:
                certification_text += f". Related concepts: {', '.join(enriched_certs)}"
        
        # Generate embeddings
        jd_level_vec = self.embed_text(jd_level_text) if jd_level_text else None
        mandatory_vec = self.embed_text(mandatory_text) if mandatory_text else None
        preferred_vec = self.embed_text(preferred_text) if preferred_text else None
        certification_vec = self.embed_text(certification_text) if certification_text else None
        
        result = EmbeddingResult(
            jd_level_vector=jd_level_vec,
            mandatory_vector=mandatory_vec,
            preferred_vector=preferred_vec,
            certification_vector=certification_vec,
            model=self.model_name
        )
        
        return result
    
    def embed_text(self, text_input: str) -> np.ndarray:
        """
        Generate embedding for a text string.
        
        Returns:
            768-dimensional embedding vector
        """
        if not text_input or text_input.strip() == "":
            return np.zeros(768).astype(np.float32)

        try:
            if self.model_type == "gemini":
                import google.generativeai as genai
                result = genai.embed_content(
                    model=self.model_name,
                    content=text_input,
                    task_type="retrieval_query"
                )
                return np.array(result['embedding']).astype(np.float32)
            else:
                return self.gemma_agent.embed_text(text_input)
        except Exception as e:
            self.logger.error(f"Failed to embed text with {self.model_type}: {str(e)}", exc_info=True)
            # Fallback to random if absolutely necessary, but we want to know it failed
            return np.random.randn(768).astype(np.float32)
    
    def validate_input(self, input_data: Any) -> bool:
        """Validate that input is NormalizedRequisition."""
        if not isinstance(input_data, NormalizedRequisition):
            self.logger.warning(f"Input must be NormalizedRequisition, got {type(input_data)}")
            return False
        return True
    
    def format_output(self, result: EmbeddingResult) -> EmbeddingResult:
        """Format output."""
        return result


# ---------------------------------------------------------------------------
# CR-EMB-002: Model factory (TASK-EMB-015)
# ---------------------------------------------------------------------------

def get_embedding_agent(model_name: str | None = None):
    """
    Return the correct embedding agent based on settings.embedding_model_name.

    Routing:
      "embedding-gemma-300m" → GemmaEmbeddingAgent (local transformer)
      "gemini-*" / any other → existing EmbeddingAgent (Google GenAI)

    This factory enables A/B testing (R1) by swapping agents via env var
    EMBEDDING_MODEL_NAME without code changes.

    Args:
        model_name: Override; if None, reads from settings.

    Returns:
        An agent with an embed_text(str) -> np.ndarray method.
    """
    from app.settings import settings

    name = model_name or settings.embedding_model or settings.embedding_model_name

    if name == "embedding-gemma-300m":
        from app.ai.utils.gemma_embedding import GemmaEmbeddingAgent
        return GemmaEmbeddingAgent(device=settings.embedding_device)

    # Gemini / OpenAI / legacy path
    return EmbeddingAgent()
