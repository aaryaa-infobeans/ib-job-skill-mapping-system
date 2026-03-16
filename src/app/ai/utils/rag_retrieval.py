"""RAG Retrieval Agent - Hybrid search (BM25 + Multi-Vector) supporting Gemma embeddings."""

import logging
import numpy as np
import os
from typing import Any, Dict, List, Optional
import sqlalchemy as sa
from sqlalchemy import func, text, type_coerce, case, literal
from pgvector.sqlalchemy import Vector

from app.ai.utils.base import BaseAgent
from app.ai.utils.models import EmbeddingResult, RAGCandidate
from app.settings import settings

class RAGRetrievalAgent(BaseAgent):
    """Retrieve candidates using 70/30 Hybrid Search (BM25 + Multi-Vector)."""
    
    def __init__(self, db_connection=None, logger: Optional[logging.Logger] = None):
        super().__init__("rag_retrieval", logger)
        self.db = db_connection
        self.vector_dim = 768
        
        # New Ratios from USER_REQUEST
        self.ratio_bm25 = float(os.getenv("HYBRID_SEARCH_RATIO_BM25", "0.7"))
        self.ratio_vector = float(os.getenv("HYBRID_SEARCH_RATIO_VECTOR", "0.3"))
        # Default threshold 0.5 (50%)
        self.threshold = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.5"))
        self.logger.info(f"RAGRetrievalAgent initialized with threshold={self.threshold}")

    def execute(
        self, 
        embedding_result: EmbeddingResult, 
        query_text: Optional[str] = None, 
        filter_ids: Optional[List[str]] = None,
        mandatory_ids: List[str] = [],
        preferred_ids: List[str] = [],
        min_experience_months: Optional[int] = None
    ) -> List[RAGCandidate]:
        """
        Execute Hybrid Search with 70% BM25 and 30% Multi-Vector.
        Retains top 40 candidates.
        """
        if not self.db:
            self.logger.warning("No DB connection provided to RAGRetrievalAgent")
            return []
        
        try:
            candidates = self._query_vector_and_filter(
                embedding_result, 
                query_text,
                filter_ids, 
                mandatory_ids, 
                preferred_ids, 
                min_experience_months
            )
            
            # Additional sorting by hybrid score and return top 40 (As requested: out of ~39)
            candidates.sort(key=lambda c: c.final_similarity, reverse=True)
            return candidates[:40]
            
        except Exception as e:
            self.logger.error(f"Hybrid retrieval execution failed: {str(e)}", exc_info=True)
            return []

    def _query_vector_and_filter(
        self, 
        embedding_result: EmbeddingResult, 
        query_text: str,
        filter_ids: Optional[List[str]],
        mandatory_ids: List[str],
        preferred_ids: List[str],
        min_months: Optional[int]
    ) -> List[RAGCandidate]:
        """Core SQL Logic for Hybrid (BM25 + 3-Vector) search."""
        from app.db.models.models import TeamMember, TeamMemberEmbedding
        
        # 1. Prepare Vector Similarity Utility
        def _cos_sim(col, vec):
            if vec is None:
                return literal(0.0)
            
            # Handle both numpy arrays and lists
            v_list = vec.tolist() if isinstance(vec, np.ndarray) else vec
            
            # Check for zero vector which results in NaN cosine distance
            if all(v == 0 for v in v_list):
                return literal(0.0)
                
            # Cosine Sim = 1 - Cosine Distance
            return 1 - type_coerce(col, Vector(self.vector_dim)).cosine_distance(v_list)

        # 2. Build multi-stage vector expressions
        # Skills Vector (Mandatory + Preferred weighting)
        m_sim = case(
            (TeamMemberEmbedding.skills_embedding != None, _cos_sim(TeamMemberEmbedding.skills_embedding, embedding_result.mandatory_vector)),
            else_=_cos_sim(TeamMemberEmbedding.embedding, embedding_result.mandatory_vector)
        )
        p_sim = case(
            (TeamMemberEmbedding.skills_embedding != None, _cos_sim(TeamMemberEmbedding.skills_embedding, embedding_result.preferred_vector)),
            else_=_cos_sim(TeamMemberEmbedding.embedding, embedding_result.preferred_vector)
        )
        
        # Resume/Experience Vector (JD Level)
        r_sim = case(
            (TeamMemberEmbedding.resume_embedding != None, _cos_sim(TeamMemberEmbedding.resume_embedding, embedding_result.jd_level_vector)),
            else_=_cos_sim(TeamMemberEmbedding.embedding, embedding_result.jd_level_vector)
        )
        
        # Certification Vector
        c_sim = case(
            (TeamMemberEmbedding.certifications_embedding != None, _cos_sim(TeamMemberEmbedding.certifications_embedding, embedding_result.certification_vector)),
            else_=literal(0.0)
        )

        # Aggregate Vector Score (Weighted 40/20/30/10)
        v_sim_raw = (
            func.coalesce(m_sim, 0.0) * 0.4 + 
            func.coalesce(p_sim, 0.0) * 0.2 + 
            func.coalesce(r_sim, 0.0) * 0.3 + 
            func.coalesce(c_sim, 0.0) * 0.1
        )
        
        # Prevent negative scores (from floating point or opposite vectors)
        v_sim_final = case((v_sim_raw < 0, 0.0), else_=v_sim_raw).label("v_sim")

        # 3. BM25 Keyword Rank Expression
        # Concatenate text fields with Coalesce to handle NULLs
        search_text = (
            func.coalesce(TeamMemberEmbedding.profile_text, "") + " " + 
            func.coalesce(TeamMemberEmbedding.skills_text, "") + " " + 
            func.coalesce(TeamMemberEmbedding.resume_text, "")
        )
        # Use plainto_tsquery for natural language, or websearch_to_tsquery for query features
        ts_query = func.plainto_tsquery('english', query_text or " ")
        bm25_raw = func.ts_rank_cd(func.to_tsvector('english', search_text), ts_query).label("b_score")

        # Normalize BM25 to 0-1 range using logistic squashing
        norm_bm25 = (bm25_raw / (1.0 + bm25_raw)).label("bm25_sim")

        # 4. Final Hybrid Score
        hybrid_score_expr = (self.ratio_bm25 * norm_bm25 + self.ratio_vector * v_sim_final).label("hybrid_score")

        # 5. Build Final Query
        query = self.db.query(
            TeamMember.team_member_id,
            v_sim_final,
            norm_bm25,
            hybrid_score_expr
        ).join(
            TeamMemberEmbedding, TeamMember.team_member_id == TeamMemberEmbedding.team_member_id
        ).filter(
            TeamMember.is_active == True
        )

        # Apply Hard Filters
        if filter_ids:
            query = query.filter(TeamMember.team_member_id.in_(filter_ids))
        if min_months is not None:
            query = query.filter(TeamMember.experience_in_months >= min_months)

        # Apply Global Threshold
        if self.threshold > 0:
            query = query.filter(hybrid_score_expr >= self.threshold)

        # Execute and format
        from sqlalchemy.dialects import postgresql
        try:
            compiled = query.statement.compile(dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True})
            self.logger.warning(f"DEBUG SQL QUERY: {str(compiled)}")
        except Exception as e:
            self.logger.warning(f"DEBUG SQL QUERY COMPILE FAILED: {str(e)}")

        rows = query.order_by(hybrid_score_expr.desc()).limit(100).all()
        self.logger.warning(f"DEBUG SQL: Found {len(rows)} rows from DB query for query='{query_text}'")
        if len(rows) == 0:
            # Check if any active members exist at all in this session
            active_count = self.db.query(TeamMember).filter(TeamMember.is_active == True).count()
            self.logger.warning(f"DEBUG SQL: Total active members in DB: {active_count}")
        
        candidates = []
        for row in rows:
            candidates.append(RAGCandidate(
                team_member_id=row.team_member_id,
                final_similarity=float(row.hybrid_score),
                mandatory_similarity=float(row.v_sim), # Combined vector sim
                preferred_similarity=float(row.v_sim),
                jd_level_similarity=float(row.v_sim),
                phase0_score_breakdown={
                    "bm25_component": round(float(row.bm25_sim) * self.ratio_bm25, 4),
                    "vector_component": round(float(row.v_sim) * self.ratio_vector, 4),
                    "raw_bm25_norm": round(float(row.bm25_sim), 4),
                    "raw_vector_sim": round(float(row.v_sim), 4),
                    "hybrid_score": round(float(row.hybrid_score), 4)
                }
            ))
            
        if candidates:
            self.logger.info(f"Hybrid RAG fetched {len(candidates)} candidates. Top score: {candidates[0].final_similarity:.4f}")
        else:
            self.logger.info(f"Hybrid RAG fetched 0 candidates for query: '{query_text}'")
            
        return candidates

    def validate_input(self, input_data: Any) -> bool:
        return isinstance(input_data, EmbeddingResult)

    def format_output(self, result: List[RAGCandidate]) -> List[RAGCandidate]:
        return result
