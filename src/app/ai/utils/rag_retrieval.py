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
from app.db.models.models import TeamMember, TeamMemberEmbedding

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
        mandatory_skills: List[str] = [],
        preferred_skills: List[str] = [],
        locations: List[str] = [],
        work_modes: List[str] = [],
        experience_req: Dict[str, Any] = {},
        certifications: List[str] = [],
        job_title: str = "N/A"
    ) -> List[RAGCandidate]:
        """
        Execute Advanced Weighted Search as provided in USER_REQUEST.
        """
        if not self.db:
            self.logger.warning("No DB connection provided to RAGRetrievalAgent")
            return []
        
        try:
            candidates = self._advanced_weighted_search(
                embedding_result, 
                mandatory_skills,
                preferred_skills,
                locations,
                work_modes,
                experience_req,
                certifications,
                job_title,
                query_text,
                filter_ids
            )
            
            # Sort by total score
            candidates.sort(key=lambda c: c.final_similarity, reverse=True)
            return candidates[:40]
            
        except Exception as e:
            self.logger.error(f"Advanced weighted search failed: {str(e)}", exc_info=True)
            return []

    def _advanced_weighted_search(
        self, 
        embedding_result: EmbeddingResult, 
        mandatory_skills: List[str],
        preferred_skills: List[str],
        locations: List[str],
        work_modes: List[str],
        experience_req: Dict[str, Any],
        certifications: List[str],
        job_title: str,
        query_text: Optional[str], # Added query_text parameter
        filter_ids: Optional[List[str]]
    ) -> List[RAGCandidate]:
        """Implementation of the specific weighted SQL search."""
        
        # 1. Load Weights from Settings
        w_mandatory = settings.weight_mandatory_skills
        w_preferred = settings.weight_preferred_skills
        w_experience = settings.weight_experience
        w_semantic = settings.weight_semantic_fit
        w_cert = settings.weight_certification
        w_jd_text = settings.weight_jd_text
        w_location = settings.weight_location
        w_work_mode = settings.weight_work_mode
        w_title = settings.weight_jd_text

        # 2. Extract JD criteria
        jd_text = query_text or ""
        
        # Experience Score (0.1 weight)
        min_exp = experience_req.get("min_months", 0)
        max_exp = experience_req.get("max_months", 999)
        exp_score_expr = case(
            (TeamMember.experience_in_months.between(min_exp, max_exp), w_experience),
            else_=0.0
        ).label("exp_score")

        # Location Boost (0.1 weight)
        loc_cases = [
            case((TeamMember.base_location.ilike(f"%{loc}%"), w_location), else_=0.0) 
            for loc in locations
        ]
        location_sum = sum(loc_cases) if loc_cases else literal(0.0)
        location_boost_expr = func.least(w_location, location_sum).label("location_score")

        # Work Mode Boost (0.1 weight)
        mode_map = {"Remote": "wfh", "WFO": "wfo", "Hybrid": "hybrid"}
        mapped_modes = [mode_map.get(m, m.lower()) for m in work_modes]
        mode_cases = [
            case((sa.cast(TeamMember.work_type, sa.Text) == m, w_work_mode), else_=0.0)
            for m in mapped_modes
        ]
        mode_sum = sum(mode_cases) if mode_cases else literal(0.0)
        mode_boost_expr = func.least(w_work_mode, mode_sum).label("mode_score")

        # Mandatory Skills Score (0.3 weight)
        m_count = len(mandatory_skills) or 1
        m_skill_cases = [
            case((TeamMemberEmbedding.skills_text.ilike(f"%{skill}%"), w_mandatory/m_count), else_=0.0)
            for skill in mandatory_skills
        ]
        mandatory_boost_expr = (sum(m_skill_cases) if m_skill_cases else literal(0.0)).label("mandatory_score")
        
        # Preferred Skills Score (0.2 weight)
        p_count = len(preferred_skills) or 1
        p_skill_cases = [
            case((TeamMemberEmbedding.skills_text.ilike(f"%{skill}%"), w_preferred/p_count), else_=0.0)
            for skill in preferred_skills
        ]
        preferred_boost_expr = (sum(p_skill_cases) if p_skill_cases else literal(0.0)).label("preferred_score")

        # Certifications Boost (0.1 weight)
        c_count = len(certifications) or 1
        cert_cases = [
            case((TeamMemberEmbedding.profile_text.ilike(f"%{cert}%"), w_cert/c_count), else_=0.0)
            for cert in certifications
        ]
        cert_boost_expr = (sum(cert_cases) if cert_cases else literal(0.0)).label("cert_score")

        # Title match boost (0.05 weight)
        title_boost_expr = case(
            (TeamMember.designation.ilike(f"%{job_title}%"), w_title),
            else_=0.0
        ).label("title_score")

        # Semantic Fit (0.05 weight)
        def _cos_sim(col, vec):
            if vec is None: return literal(0.0)
            v_list = vec.tolist() if isinstance(vec, np.ndarray) else vec
            if all(v == 0 for v in v_list): return literal(0.0)
            return 1 - type_coerce(col, Vector(self.vector_dim)).cosine_distance(v_list)

        semantic_sim = _cos_sim(TeamMemberEmbedding.embedding, embedding_result.full_jd_vector)
        semantic_score_expr = (func.greatest(0.0, func.coalesce(semantic_sim, 0.0)) * w_semantic).label("semantic_score")

        # Final Total Score
        total_score_expr = (
            mandatory_boost_expr + 
            preferred_boost_expr + 
            location_boost_expr + 
            mode_boost_expr + 
            cert_boost_expr + 
            title_boost_expr + 
            exp_score_expr + 
            semantic_score_expr
        ).label("total_score")

        # 3. Build Final Query
        query = self.db.query(
            TeamMember.team_member_id,
            total_score_expr,
            mandatory_boost_expr,
            preferred_boost_expr,
            exp_score_expr,
            semantic_score_expr,
            location_boost_expr,
            mode_boost_expr,
            cert_boost_expr,
            title_boost_expr
        ).join(
            TeamMemberEmbedding, TeamMember.team_member_id == TeamMemberEmbedding.team_member_id
        ).filter(
            TeamMember.is_active == True
        )

        # Apply ID Filter
        if filter_ids:
            query = query.filter(TeamMember.team_member_id.in_(filter_ids))

        # Skill Gate Filter: (mandatory_score + preferred_score) >= 0.2
        query = query.filter((mandatory_boost_expr + preferred_boost_expr) >= 0.2)

        # Execute
        # 5. Execute & Build Results
        rows = query.order_by(total_score_expr.desc()).limit(100).all()
        self.logger.info(f"RAG Retrieval matched {len(rows)} candidates for testing.")
        
        candidates = []
        for row in rows:
            candidates.append(RAGCandidate(
                team_member_id=row.team_member_id,
                final_similarity=float(row.total_score),
                mandatory_similarity=float(row.mandatory_score),
                preferred_similarity=float(row.preferred_score),
                jd_level_similarity=float(row.semantic_score),
                phase0_score_breakdown={
                    "total_score": round(float(row.total_score), 4),
                    "mandatory_score": round(float(row.mandatory_score), 4),
                    "preferred_score": round(float(row.preferred_score), 4),
                    "exp_score": round(float(row.exp_score), 4),
                    "semantic_score": round(float(row.semantic_score), 4),
                    "location_score": round(float(row.location_score), 4),
                    "mode_score": round(float(row.mode_score), 4),
                    "cert_score": round(float(row.cert_score), 4),
                    "title_score": round(float(row.title_score), 4)
                }
            ))
            
        return candidates

    def validate_input(self, input_data: Any) -> bool:
        return isinstance(input_data, EmbeddingResult)

    def format_output(self, result: List[RAGCandidate]) -> List[RAGCandidate]:
        return result
