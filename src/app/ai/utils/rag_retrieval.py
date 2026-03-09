"""RAG Retrieval Agent - Hybrid search (BM25 + Vector) with RRF."""

import logging
import numpy as np
from typing import Any, Dict, List, Optional
import os
import sqlalchemy as sa
from sqlalchemy import text, type_coerce, literal
from app.ai.utils.base import BaseAgent
from app.ai.utils.models import EmbeddingResult, RAGCandidate


class RAGRetrievalAgent(BaseAgent):
    """Retrieve candidates using hybrid (BM25 + Vector) search."""
    
    def __init__(self, db_connection=None, logger: Optional[logging.Logger] = None):
        super().__init__("rag_retrieval", logger)
        self.db = db_connection
        
        from app.settings import settings
        self.settings = settings
        self.similarity_threshold = settings.rag_similarity_threshold
        self.max_results = 100
        self.vector_dim = 768
        
        # Weighted fusion parameters
        self.weight_bm25 = float(os.getenv("HYBRID_BM25_WEIGHT", "0.5"))
        self.weight_vector = float(os.getenv("HYBRID_VECTOR_WEIGHT", "0.5"))
        
        # JD component weights (for vector search)
        self.weight_mandatory = settings.weight_mandatory_skills
        self.weight_preferred = settings.weight_preferred_skills
        self.weight_jd_level = settings.weight_jd_text
        self.weight_certification = settings.weight_certification
        
        self.total_vector_weight = (
            self.weight_mandatory + 
            self.weight_preferred + 
            self.weight_jd_level + 
            self.weight_certification
        )
        if self.total_vector_weight == 0:
            self.total_vector_weight = 1.0
    
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
        Execute hybrid search with SPEC-001 formula and hard filters.
        
        Formula: HybridScore = (SkillBoost * 0.40) + (PreferredBoost * 0.20) + 
                                (VectorSimilarity * 0.25) + (SelectionBase * 0.15)
        """
        if not self.db:
            return []
        
        try:
            # Phase 0 Selection - Multi-vector search with hard gating filters
            candidates = self._query_vector_and_filter(
                embedding_result, 
                filter_ids, 
                mandatory_ids, 
                preferred_ids, 
                min_experience_months
            )
            
            self.logger.info(
                f"Phase 0 selection completed: {len(candidates)} candidates qualified for Pool"
            )
            
            # Sort by hybrid score and take top 40 as per SPEC-001
            candidates.sort(key=lambda c: c.final_similarity, reverse=True)
            return candidates[:40]
            
        except Exception as e:
            self.logger.error(f"Hybrid retrieval failed: {str(e)}", exc_info=True)
            return []

    def _query_vector_and_filter(
        self, 
        embedding_result: EmbeddingResult, 
        filter_ids: Optional[List[str]],
        mandatory_ids: List[str],
        preferred_ids: List[str],
        min_months: Optional[int]
    ) -> List[RAGCandidate]:
        """Query using pgvector and apply Hard Filters + SPEC-001 Hybrid Score."""
        from app.db.models.models import TeamMember, TeamMemberEmbedding, TeamMemberSkill
        from pgvector.sqlalchemy import Vector
        from sqlalchemy import func
        
        mandatory_vec = embedding_result.mandatory_vector.tolist()
        preferred_vec = embedding_result.preferred_vector.tolist()
        jd_level_vec = embedding_result.jd_level_vector.tolist()
        
        # Subquery for mandatory skill match counts
        m_count_sq = self.db.query(
            TeamMemberSkill.team_member_id,
            func.count(TeamMemberSkill.skill_id).label('m_count')
        ).filter(TeamMemberSkill.skill_id.in_(mandatory_ids)).group_by(TeamMemberSkill.team_member_id).subquery()
        
        # Subquery for preferred skill match counts
        p_count_sq = self.db.query(
            TeamMemberSkill.team_member_id,
            func.count(TeamMemberSkill.skill_id).label('p_count')
        ).filter(TeamMemberSkill.skill_id.in_(preferred_ids)).group_by(TeamMemberSkill.team_member_id).subquery()
        
        query = self.db.query(
            TeamMember.team_member_id,
            TeamMember.experience_in_months,
            TeamMemberEmbedding.embedding,
            func.coalesce(m_count_sq.c.m_count, 0).label('m_count'),
            func.coalesce(p_count_sq.c.p_count, 0).label('p_count'),
            (1 - type_coerce(TeamMemberEmbedding.embedding, Vector(self.vector_dim)).cosine_distance(mandatory_vec)).label('mandatory_sim'),
            (1 - type_coerce(TeamMemberEmbedding.embedding, Vector(self.vector_dim)).cosine_distance(preferred_vec)).label('preferred_sim'),
            (1 - type_coerce(TeamMemberEmbedding.embedding, Vector(self.vector_dim)).cosine_distance(jd_level_vec)).label('jd_level_sim')
        ).join(
            TeamMemberEmbedding, TeamMember.team_member_id == TeamMemberEmbedding.team_member_id
        ).outerjoin(
            m_count_sq, TeamMember.team_member_id == m_count_sq.c.team_member_id
        ).outerjoin(
            p_count_sq, TeamMember.team_member_id == p_count_sq.c.team_member_id
        )
        
        if embedding_result.certification_vector is not None:
            cert_vec = embedding_result.certification_vector.tolist()
            query = query.add_columns(
                (1 - type_coerce(TeamMemberEmbedding.embedding, Vector(self.vector_dim)).cosine_distance(cert_vec)).label('cert_sim')
            )
        else:
            query = query.add_columns(sa.literal(0.0).label('cert_sim'))

        # TASK-02: Hard Filters (Fail-fast gating)
        # 1. is_active != true -> FAIL
        query = query.filter(TeamMember.is_active == True)
        
        # Ensure IDs are strings for VARCHAR columns
        mandatory_ids = [str(i) for i in mandatory_ids]
        preferred_ids = [str(i) for i in preferred_ids]

        
        # 2. experience < min_months -> FAIL
        if min_months is not None:
            query = query.filter(TeamMember.experience_in_months >= min_months)


        
        # 3. no mandatory OR preferred skill match -> FAIL
        query = query.filter(sa.or_(m_count_sq.c.team_member_id != None, p_count_sq.c.team_member_id != None))







        if filter_ids:
            query = query.filter(TeamMember.team_member_id.in_(filter_ids))

        rows = query.all()
        
        candidates = []
        total_m = len(mandatory_ids)
        total_p = len(preferred_ids)
        
        for row in rows:
            # TASK-03: Hybrid Search Score Function (SPEC-001)
            # Normalize each component to [0,1]
            skill_boost = float(row.m_count) / total_m if total_m > 0 else 1.0
            preferred_boost = float(row.p_count) / total_p if total_p > 0 else 1.0
            
            vector_similarity = self._compute_weighted_similarity(
                row.mandatory_sim, row.preferred_sim, row.jd_level_sim, row.cert_sim
            )
            
            selection_base = 1.0 # Base for all qualified in pool
            
            # HybridScore = (SkillBoost * 0.40) + (PreferredBoost * 0.20) + (VectorSimilarity * 0.25) + (SelectionBase * 0.15)
            # SelectionBase * 0.15 = 0.15
            hybrid_score = (
                (skill_boost * 0.40) + 
                (preferred_boost * 0.20) + 
                (vector_similarity * 0.25) + 
                (0.15)
            )
            
            breakdown = {
                "skill_boost": round(skill_boost, 4),
                "preferred_boost": round(preferred_boost, 4),
                "vector_similarity": round(float(vector_similarity), 4),
                "selection_base": 0.15,
                "hybrid_score": round(hybrid_score, 4)
            }
            
            candidates.append(RAGCandidate(
                team_member_id=row.team_member_id,
                final_similarity=float(hybrid_score),
                mandatory_similarity=float(row.mandatory_sim),
                preferred_similarity=float(row.preferred_sim),
                jd_level_similarity=float(row.jd_level_sim),
                certification_similarity=float(row.cert_sim),
                phase0_score_breakdown=breakdown
            ))
            
        return candidates

    def _compute_weighted_similarity(self, m, p, j, c=0.0) -> float:
        m = m if m is not None and not np.isnan(m) else 0.0
        p = p if p is not None and not np.isnan(p) else 0.0
        j = j if j is not None and not np.isnan(j) else 0.0
        c = c if c is not None and not np.isnan(c) else 0.0
        
        return (
            (self.weight_mandatory * m) +
            (self.weight_preferred * p) +
            (self.weight_jd_level * j) +
            (self.weight_certification * c)
        ) / self.total_vector_weight
    
    def validate_input(self, input_data: Any) -> bool:
        return isinstance(input_data, EmbeddingResult)
    
    def format_output(self, result: List[RAGCandidate]) -> List[RAGCandidate]:
        return result

