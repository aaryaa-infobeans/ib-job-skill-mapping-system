"""RAG Retrieval Agent - Hybrid search (BM25 + Vector) from scratch."""

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
    """Retrieve candidates using 70/30 Hybrid Search (BM25 + Vector)."""
    
    def __init__(self, db_connection=None, logger: Optional[logging.Logger] = None):
        super().__init__("rag_retrieval", logger)
        self.db = db_connection
        self.vector_dim = 768
        
        # New Ratios from USER_REQUEST
        self.ratio_bm25 = float(os.getenv("HYBRID_SEARCH_RATIO_BM25", "0.7"))
        self.ratio_vector = float(os.getenv("HYBRID_SEARCH_RATIO_VECTOR", "0.3"))
        self.threshold = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.5"))

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
        Execute Hybrid Search with 70% BM25 and 30% Vector.
        Threshold: 0.5 (Combined Score)
        """
        if not self.db:
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
            
            # Sort by hybrid score and return top 40
            candidates.sort(key=lambda c: c.final_similarity, reverse=True)
            return candidates[:40]
            
        except Exception as e:
            self.logger.error(f"Hybrid retrieval failed: {str(e)}", exc_info=True)
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
        """Query using Hybrid (BM25 + 3-Vector) logic."""
        from app.db.models.models import TeamMember, TeamMemberEmbedding
        
        self.logger.info(f"RAG Input: Query='{query_text}', MandatoryV={embedding_result.mandatory_vector is not None}")

        # 1. Prepare Vector Expressions (0-1)
        def _cos_sim(col, vec):
            if vec is None:
                return literal(0.0)
            # Ensure vec is a list for pgvector
            v_list = vec.tolist() if isinstance(vec, np.ndarray) else vec
            return 1 - type_coerce(col, Vector(self.vector_dim)).cosine_distance(v_list)

        # Skill Similarity (Max of mandatory/preferred vs skills_embedding)
        # Fallback to legacy embedding
        m_sim = case(
            (TeamMemberEmbedding.skills_embedding != None, _cos_sim(TeamMemberEmbedding.skills_embedding, embedding_result.mandatory_vector)),
            else_=_cos_sim(TeamMemberEmbedding.embedding, embedding_result.mandatory_vector)
        )
        p_sim = case(
            (TeamMemberEmbedding.skills_embedding != None, _cos_sim(TeamMemberEmbedding.skills_embedding, embedding_result.preferred_vector)),
            else_=_cos_sim(TeamMemberEmbedding.embedding, embedding_result.preferred_vector)
        )
        
        # Resume/JD Level Similarity
        r_sim = case(
            (TeamMemberEmbedding.resume_embedding != None, _cos_sim(TeamMemberEmbedding.resume_embedding, embedding_result.jd_level_vector)),
            else_=_cos_sim(TeamMemberEmbedding.embedding, embedding_result.jd_level_vector)
        )
        
        # Certification Similarity
        c_sim = case(
            (TeamMemberEmbedding.certifications_embedding != None, _cos_sim(TeamMemberEmbedding.certifications_embedding, embedding_result.certification_vector)),
            else_=literal(0.0)
        )

        # Combine specialized vectors into a single v_sim (Simple average of present components)
        v_sim_expr = (
            func.coalesce(m_sim, 0.0) * 0.4 + 
            func.coalesce(p_sim, 0.0) * 0.2 + 
            func.coalesce(r_sim, 0.0) * 0.3 + 
            func.coalesce(c_sim, 0.0) * 0.1
        ).label("v_sim")

        # 2. BM25-like Expression (Postgres FTS Rank)
        search_text = (
            func.coalesce(TeamMemberEmbedding.profile_text, "") + " " + 
            func.coalesce(TeamMemberEmbedding.skills_text, "") + " " + 
            func.coalesce(TeamMemberEmbedding.resume_text, "")
        )
        ts_query = func.plainto_tsquery('english', query_text or " ")
        bm25_expr = func.ts_rank_cd(func.to_tsvector('english', search_text), ts_query).label("b_score")

        # 3. Hybrid Combination & Filter
        # Normalize BM25 score to [0, 1] using logistic/squashing: score / (1 + score)
        # Clip negative vector similarities at 0
        v_sim_clipped = case((v_sim_expr < 0, 0.0), else_=v_sim_expr)
        norm_bm25 = (bm25_expr / (1.0 + bm25_expr)).label("bm25_sim")
        hybrid_score_expr = (self.ratio_bm25 * norm_bm25 + self.ratio_vector * v_sim_clipped).label("hybrid_score")

        # Building Query
        query = self.db.query(
            TeamMember.team_member_id,
            v_sim_clipped.label("v_sim"),
            norm_bm25,
            hybrid_score_expr
        ).join(
            TeamMemberEmbedding, TeamMember.team_member_id == TeamMemberEmbedding.team_member_id
        ).filter(
            TeamMember.is_active == True
        )

        # Filters
        if filter_ids:
            query = query.filter(TeamMember.team_member_id.in_(filter_ids))
        if min_months is not None:
            query = query.filter(TeamMember.experience_in_months >= min_months)

        # Apply Similarity Threshold (50% and above)
        query = query.filter(hybrid_score_expr >= self.threshold)

        rows = query.order_by(hybrid_score_expr.desc()).limit(10).all()
        self.logger.info(f"DEBUG: Found {len(rows)} rows total in query")
        
        candidates = []
        for row in rows:
            breakdown = {
                "bm25_component": round(float(row.bm25_sim) * self.ratio_bm25, 4),
                "vector_component": round(float(row.v_sim) * self.ratio_vector, 4),
                "raw_bm25_norm": round(float(row.bm25_sim), 4),
                "raw_vector_sim": round(float(row.v_sim), 4),
                "hybrid_score": round(float(row.hybrid_score), 4)
            }
            
            candidates.append(RAGCandidate(
                team_member_id=row.team_member_id,
                final_similarity=float(row.hybrid_score),
                mandatory_similarity=float(row.v_sim),
                preferred_similarity=float(row.v_sim),
                jd_level_similarity=float(row.v_sim),
                phase0_score_breakdown=breakdown
            ))
            
        if candidates:
            self.logger.info(f"Hybrid RAG fetched {len(candidates)} candidates. Top score: {candidates[0].final_similarity:.4f}")
        else:
            self.logger.info("Hybrid RAG fetched 0 candidates.")
            
        return candidates

    def validate_input(self, input_data: Any) -> bool:
        return isinstance(input_data, EmbeddingResult)

    def format_output(self, result: List[RAGCandidate]) -> List[RAGCandidate]:
        return result
