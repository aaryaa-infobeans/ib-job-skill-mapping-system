"""RAG Retrieval Agent - Weighted multi-vector retrieval from pgvector."""

import logging
import numpy as np
from typing import Any, List, Optional
import os
import sqlalchemy as sa
from sqlalchemy import text
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
        Query database for candidate embeddings using weighted multi-vector search.
        """
        from app.db.models.models import TeamMemberEmbedding
        
        # Multi-vector weighted search:
        # We compute similarity for each JD component against the single candidate embedding.
        
        mandatory_vec = embedding_result.mandatory_vector.tolist()
        preferred_vec = embedding_result.preferred_vector.tolist()
        jd_level_vec = embedding_result.jd_level_vector.tolist()
        
        query = self.db.query(
            TeamMemberEmbedding.team_member_id,
            (1 - TeamMemberEmbedding.embedding.cosine_distance(mandatory_vec)).label('mandatory_sim'),
            (1 - TeamMemberEmbedding.embedding.cosine_distance(preferred_vec)).label('preferred_sim'),
            (1 - TeamMemberEmbedding.embedding.cosine_distance(jd_level_vec)).label('jd_level_sim')
        )
        
        if embedding_result.certification_vector is not None:
            cert_vec = embedding_result.certification_vector.tolist()
            query = query.add_columns(
                (1 - TeamMemberEmbedding.embedding.cosine_distance(cert_vec)).label('cert_sim')
            )
        else:
            query = query.add_columns(sa.literal(0.0).label('cert_sim'))

        rows = query.all()
        
        candidates = []
        for i, row in enumerate(rows):
            final_sim = self._compute_weighted_similarity(
                row.mandatory_sim,
                row.preferred_sim,
                row.jd_level_sim,
                row.cert_sim
            )
            
            if final_sim >= self.similarity_threshold:
                candidates.append(RAGCandidate(
                    team_member_id=row.team_member_id,
                    final_similarity=float(final_sim),
                    mandatory_similarity=float(row.mandatory_sim),
                    preferred_similarity=float(row.preferred_sim),
                    jd_level_similarity=float(row.jd_level_sim),
                    certification_similarity=float(row.cert_sim)
                ))
        
        return candidates
    
    def _compute_weighted_similarity(
        self,
        mandatory_sim: float,
        preferred_sim: float,
        jd_level_sim: float,
        certification_sim: float = 0.0
    ) -> float:
        """Compute weighted final similarity."""
        # Handle None values from DB
        m = mandatory_sim or 0.0
        p = preferred_sim or 0.0
        j = jd_level_sim or 0.0
        c = certification_sim or 0.0
        
        final_similarity = (
            (self.weight_mandatory * m) +
            (self.weight_preferred * p) +
            (self.weight_jd_level * j) +
            (self.weight_certification * c)
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
