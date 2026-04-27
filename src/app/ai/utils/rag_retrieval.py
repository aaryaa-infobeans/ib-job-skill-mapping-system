"""RAG Retrieval Agent - Hybrid search (BM25 + Multi-Vector) supporting Gemma embeddings."""

import logging
import numpy as np
import os
from typing import Any, Dict, List, Optional
import sqlalchemy as sa
from sqlalchemy import func, text, type_coerce, case, literal, desc
from pgvector.sqlalchemy import Vector

from app.ai.utils.base import BaseAgent
from app.ai.utils.models import EmbeddingResult, RAGCandidate
from app.settings import settings
from app.db.models.models import TeamMember, TeamMemberEmbedding

class RAGRetrievalAgent(BaseAgent):
    """Retrieve candidates using Hybrid Search (BM25 + Semantic) logic."""

    def __init__(self, db_connection=None, logger: Optional[logging.Logger] = None):
        super().__init__("rag_retrieval", logger)
        self.db = db_connection
        self.vector_dim = 768

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
        Execute Hybrid Search (BM25 + Semantic) logic.
        """
        if not self.db:
            self.logger.warning("No DB connection provided to RAGRetrievalAgent")
            return []
        
        try:
            # 1. Prepare components for SQL
            vector_literal = embedding_result.full_jd_vector.tolist() if isinstance(embedding_result.full_jd_vector, np.ndarray) else embedding_result.full_jd_vector
            
            kw_list = mandatory_skills + preferred_skills + certifications
            keywords = []
            for k in kw_list:
                k = k.strip()
                if not k: continue
                keywords.append(f'"{k}"' if " " in k else k)
            keyword_query_str = " OR ".join(keywords) if keywords else ""

            # 2. Build SQL Filters (Refined for Hybrid Search)
            filters = ["e.embedding IS NOT NULL", "tm.is_active = true"]
            params = {"vector": vector_literal, "kw_query": keyword_query_str}

            if locations:
                loc_filters = []
                for i, loc in enumerate(locations):
                    key = f"loc_{i}"
                    loc_filters.append(f"tm.base_location ILIKE :{key}")
                    params[key] = f"%{loc}%"
                filters.append("(" + " OR ".join(loc_filters) + ")")

            sql = text(f"""
                SELECT
                    e.team_member_id,
                    COALESCE(tm.designation, '') AS role,
                    COALESCE(e.skills_text, '') AS skills,
                    COALESCE(e.certifications_text, '') AS certifications_text,
                    tm.experience_in_months,
                    COALESCE(tm.base_location, '') AS base_location,
                    COALESCE(CAST(tm.work_type AS text), 'hybrid') AS work_type,
                    e.embedding <-> CAST(:vector AS vector) AS similarity_score,
                    ts_rank(
                        to_tsvector('english', 
                            coalesce(e.skills_text, '') || ' ' || 
                            coalesce(e.certifications_text, '') || ' ' || 
                            coalesce(e.profile_text, '')
                        ),
                        websearch_to_tsquery('english', :kw_query)
                    ) AS keyword_score
                FROM team_member_embeddings e
                LEFT JOIN team_member tm ON tm.team_member_id = e.team_member_id
                WHERE {" AND ".join(filters)}
                ORDER BY similarity_score ASC
                LIMIT 10
            """)

            result_set = self.db.execute(sql, params).fetchall()
            
            # 3. Process results and calculate weighted scores
            candidates = []
            for row in result_set:
                candidate = self._build_structured_candidate(row, mandatory_skills, preferred_skills, certifications, locations, work_modes, experience_req)
                if candidate:
                    candidates.append(candidate)

            # 4. Final Sorting and Filtering
            final_candidates = [c for c in candidates if c.final_similarity > 0.30]
            final_candidates.sort(key=lambda x: x.final_similarity, reverse=True)

            self.logger.info(f"RAG Retrieval matched {len(final_candidates)} candidates above 30% threshold")
            return final_candidates[:10]

        except Exception as e:
            self.logger.error(f"Hybrid search execute failed: {str(e)}", exc_info=True)
            return []

    def _build_structured_candidate(self, row, mandatory_skills, preferred_skills, certifications, locations, work_modes, experience_req) -> RAGCandidate:
        try:
            (
                team_member_id,
                role,
                skills_text,
                certifications_text,
                experience_in_months,
                base_location,
                work_type,
                distance,
                keyword_score,
            ) = row

            # Score components as per embed_search.py logic
            def _filter_keyword_matches(text, keywords):
                if not text or not keywords: return []
                t = text.lower()
                return [kw for kw in keywords if kw.lower() in t]

            combined_text = " ".join([str(skills_text or ""), str(role or "")]).lower()
            mandatory_matches = _filter_keyword_matches(combined_text, mandatory_skills)
            preferred_matches = _filter_keyword_matches(combined_text, preferred_skills)
            certification_matches = _filter_keyword_matches(str(certifications_text or ""), certifications)

            # Experience relevance
            def _exp_relevance(cand_m, req):
                if not req or cand_m is None: return 1.0
                min_m = req.get("min_months", 0)
                max_m = req.get("max_months", 9999)
                if min_m <= cand_m <= max_m: return 1.0
                diff = min_m - cand_m if cand_m < min_m else cand_m - max_m
                return max(0.0, 1.0 - min(diff / max(12, min_m or 12), 1.0))

            experience_relevance = _exp_relevance(experience_in_months, experience_req)
            
            # Compatibility
            location_comp = any(loc.lower() in str(base_location).lower() for loc in locations) if locations else True
            mode_comp = any(mode.lower() in str(work_type).lower() for mode in work_modes) if work_modes else True

            # Normalized scores
            semantic_fit = 1.0 / (1.0 + float(distance)) if distance is not None else 0.0
            kw_norm = round(float(keyword_score) / (0.03 + float(keyword_score)), 4) if float(keyword_score) > 0 else 0.0
            
            m_score = len(mandatory_matches) / max(len(mandatory_skills), 1) if mandatory_skills else 1.0
            p_score = len(preferred_matches) / max(len(preferred_skills), 1) if preferred_skills else 1.0
            c_score = len(certification_matches) / max(len(certifications), 1) if certifications else 1.0

            # Weights
            weights = {
                "semantic": 0.30, "keyword": 0.20, "mandatory": 0.30, 
                "preferred": 0.05, "experience": 0.05, "certification": 0.05,
                "location": 0.025, "work_mode": 0.025,
            }

            total_score = (
                semantic_fit * weights["semantic"] +
                kw_norm * weights["keyword"] +
                m_score * weights["mandatory"] +
                p_score * weights["preferred"] +
                experience_relevance * weights["experience"] +
                c_score * weights["certification"] +
                (1.0 if location_comp else 0.0) * weights["location"] +
                (1.0 if mode_comp else 0.0) * weights["work_mode"]
            )

            # Mandatory Match Penalty
            if mandatory_skills and not mandatory_matches:
                total_score *= 0.6

            return RAGCandidate(
                team_member_id=team_member_id,
                final_similarity=round(total_score, 4),
                mandatory_similarity=round(m_score, 4),
                preferred_similarity=round(p_score, 4),
                jd_level_similarity=round(semantic_fit, 4),
                certification_similarity=round(c_score, 4),
                experience_in_months=experience_in_months,
                phase0_score_breakdown={
                    "total_score": round(total_score, 4),
                    "semantic_fit": round(semantic_fit, 4),
                    "keyword_score": round(kw_norm, 4),
                    "mandatory_score": round(m_score, 4),
                    "preferred_score": round(p_score, 4),
                    "experience_relevance": round(experience_relevance, 4),
                    "certification_score": round(c_score, 4),
                    "location_compatibility": location_comp,
                    "work_mode_compatibility": mode_comp,
                    "mandatory_penalty_assigned": mandatory_skills and not mandatory_matches
                }
            )
        except Exception as e:
            logging.getLogger(__name__).error(f"Error building structured candidate: {str(e)}")
            return None

    def validate_input(self, input_data: Any) -> bool:
        """Validate input data."""
        return isinstance(input_data, EmbeddingResult)

    def format_output(self, result: List[RAGCandidate]) -> List[RAGCandidate]:
        """Format output."""
        return result
