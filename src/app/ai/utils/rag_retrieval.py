"""RAG Retrieval Agent - Weighted multi-vector retrieval from pgvector."""

import logging
import numpy as np
from typing import Any, List, Optional
import os
from app.ai.utils.base import BaseAgent
from app.ai.utils.models import EmbeddingResult, RAGCandidate


class RAGRetrievalAgent(BaseAgent):
    """Retrieve candidates using weighted multi-vector RAG from pgvector."""
    
    def __init__(self, db_connection=None, logger: Optional[logging.Logger] = None):
        super().__init__("rag_retrieval", logger)
        self.db = db_connection
        
        # Load weights from environment
        self.weight_mandatory = float(os.getenv("RAG_WEIGHT_MANDATORY", "0.45"))
        self.weight_preferred = float(os.getenv("RAG_WEIGHT_PREFERRED", "0.25"))
        self.weight_jd_level = float(os.getenv("RAG_WEIGHT_JD_LEVEL", "0.20"))
        self.weight_certification = float(os.getenv("RAG_WEIGHT_CERTIFICATION", "0.10"))
        self.similarity_threshold = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.0"))
        self.max_results = int(os.getenv("RAG_MAX_RESULTS", "100"))
    
    def execute(self, embedding_result: EmbeddingResult) -> List[RAGCandidate]:
        """
        Retrieve candidates using weighted multi-vector RAG.
        
        Args:
            embedding_result: Embedding vectors for JD components
            
        Returns:
            List of RAGCandidate sorted by final_similarity descending
        """
        if not self.db:
            self.logger.warning("No database connection, returning empty candidates")
            return []
        
        try:
            # Query candidates with similarity scores
            candidates = self._query_candidates(embedding_result)
            
            # Sort by final similarity
            candidates.sort(key=lambda c: c.final_similarity, reverse=True)
            
            # Limit results
            candidates = candidates[:self.max_results]
            
            self.logger.info(f"Retrieved {len(candidates)} candidates")
            return candidates
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve candidates: {str(e)}", exc_info=True)
            return []
    
    def _query_candidates(self, embedding_result: EmbeddingResult) -> List[RAGCandidate]:
        """
        Query database for candidate embeddings.
        
        Args:
            embedding_result: Embedding vectors
            
        Returns:
            List of RAGCandidate objects
        """
        candidates = []
        
        # Mock implementation - return empty list
        # In production, this would query pgvector:
        # SELECT 
        #   team_member_id,
        #   (embedding <#> mandatory_vector) as mandatory_sim,
        #   (embedding <#> preferred_vector) as preferred_sim,
        #   (embedding <#> jd_level_vector) as jd_level_sim,
        #   (embedding <#> certification_vector) as cert_sim
        # FROM team_member_embeddings
        # WHERE (weighted formula) >= threshold
        
        return candidates
    
    def _compute_weighted_similarity(
        self,
        mandatory_sim: float,
        preferred_sim: float,
        jd_level_sim: float,
        certification_sim: float = 0.0
    ) -> float:
        """
        Compute weighted final similarity.
        
        Formula: (0.45 * mandatory) + (0.25 * preferred) + (0.20 * jd_level) + (0.10 * certification)
        
        Args:
            mandatory_sim: Mandatory skills similarity
            preferred_sim: Preferred skills similarity
            jd_level_sim: JD level similarity
            certification_sim: Certification similarity
            
        Returns:
            Weighted final similarity score
        """
        final_similarity = (
            (self.weight_mandatory * mandatory_sim) +
            (self.weight_preferred * preferred_sim) +
            (self.weight_jd_level * jd_level_sim) +
            (self.weight_certification * certification_sim)
        )
        return final_similarity
    
    def validate_input(self, input_data: Any) -> bool:
        """Validate that input is EmbeddingResult."""
        if not isinstance(input_data, EmbeddingResult):
            self.logger.warning(f"Input must be EmbeddingResult, got {type(input_data)}")
            return False
        return True
    
    def format_output(self, result: List[RAGCandidate]) -> List[RAGCandidate]:
        """Format output - already in correct format."""
        return result
