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
    """Retrieve candidates using 70/30 Hybrid Search (BM25 + Multi-Vector)."""

    def __init__(self, db_connection=None, logger: Optional[logging.Logger] = None):
        super().__init__("rag_retrieval", logger)
        self.db = db_connection
        self.vector_dim = 768

        # Hybrid Search Ratios
        self.ratio_bm25 = float(os.getenv("HYBRID_SEARCH_RATIO_BM25", "0.7"))
        self.ratio_vector = float(os.getenv("HYBRID_SEARCH_RATIO_VECTOR", "0.3"))
        # Default threshold 0.5 (50%)
        self.threshold = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.5"))
        self.logger.info(f"RAGRetrievalAgent initialized with BM25:{self.ratio_bm25}, Vector:{self.ratio_vector}, threshold={self.threshold}")

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
            
            # Sort by final similarity (already sorted in query, but ensure consistency)
            candidates.sort(key=lambda c: c.final_similarity, reverse=True)
            return candidates[:40]  # Return top 40 as per original implementation
            
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
        """Implementation of hybrid BM25 + Multi-Vector search with proper weighting."""
        
        # 1. Load Weights from Settings based on seniority level
        seniority = self._determine_seniority_level(experience_req)
        weights = self._get_weights_for_seniority(seniority)
        
        # 2. Extract JD criteria
        jd_text = query_text or ""
        
        # 3. Build BM25 scoring using PostgreSQL full-text search
        bm25_score_expr = self._build_bm25_score(jd_text, mandatory_skills, preferred_skills)
        
        # 4. Build Vector similarity scoring
        vector_score_expr = self._build_vector_score(embedding_result)
        
        # Get raw vector similarity (before greatest/coalesce processing)
        def _raw_cos_sim(col, vec):
            if vec is None: return literal(0.0)
            v_list = vec.tolist() if isinstance(vec, np.ndarray) else vec
            if all(v == 0 for v in v_list): return literal(0.0)
            return 1 - type_coerce(col, Vector(self.vector_dim)).cosine_distance(v_list)
        
        raw_vector_sim_expr = _raw_cos_sim(TeamMemberEmbedding.embedding, embedding_result.full_jd_vector)
        raw_vector_sim_expr = func.coalesce(raw_vector_sim_expr, 0.0).label("raw_vector_sim")
        
        # 5. Build Boost expressions (skills, location, etc.)
        boost_score_expr = self._build_boost_scores(
            mandatory_skills, preferred_skills, locations, work_modes, 
            experience_req, certifications, job_title, weights
        )
        
        # 6. Combine scores: Hybrid = (BM25 * ratio_bm25) + (Vector * ratio_vector) + Boosts
        hybrid_score_expr = (
            (bm25_score_expr * self.ratio_bm25) + 
            (vector_score_expr * self.ratio_vector) + 
            boost_score_expr
        ).label("hybrid_score")
        
        # 7. Build Final Query
        query = self.db.query(
            TeamMember.team_member_id,
            hybrid_score_expr,
            bm25_score_expr.label("bm25_score"),
            vector_score_expr.label("vector_score"),
            raw_vector_sim_expr.label("raw_vector_sim"),
            boost_score_expr.label("boost_score")
        ).join(
            TeamMemberEmbedding, TeamMember.team_member_id == TeamMemberEmbedding.team_member_id
        ).filter(
            TeamMember.is_active == True
        )

        # Apply ID Filter
        if filter_ids:
            query = query.filter(TeamMember.team_member_id.in_(filter_ids))

        # Experience, location, and work mode are handled via boost scores, not hard filters.
        # This prevents 0 match scenarios where candidates are slightly outside the range.

        # Apply Skill Gate Filter: minimum combined skill matching
        skill_gate_threshold = self._get_skill_gate_threshold(seniority)
        mandatory_boost = self._build_skill_boost(mandatory_skills, weights['mandatory'])
        preferred_boost = self._build_skill_boost(preferred_skills, weights['preferred'])
        # Use full gate; with updated settings, this is lenient enough but still avoids full scan
        query = query.filter((mandatory_boost + preferred_boost) >= skill_gate_threshold)

        # Execute query and get top candidates
        rows = query.order_by(desc(hybrid_score_expr)).limit(100).all()
        self.logger.info(f"RAG Retrieval matched {len(rows)} candidates (Hybrid BM25:{self.ratio_bm25}+Vector:{self.ratio_vector})")
        
        candidates = []
        for row in rows:
            # Calculate final similarity as weighted combination
            final_score = float(row.hybrid_score)
            
            candidates.append(RAGCandidate(
                team_member_id=row.team_member_id,
                final_similarity=final_score,
                mandatory_similarity=float(row.boost_score),  # Boost score includes skill matching
                preferred_similarity=0.0,  # Will be calculated in matching_scoring
                jd_level_similarity=float(row.vector_score),
                certification_similarity=0.0,  # Will be calculated in matching_scoring
                phase0_score_breakdown={
                    "total_score": round(final_score, 4),
                    "bm25_component": round(float(row.bm25_score), 4),
                    "raw_bm25_norm": round(float(row.bm25_score), 4),  # BM25 is already normalized
                    "vector_component": round(float(row.vector_score), 4),
                    "raw_vector_sim": round(float(row.raw_vector_sim), 4),
                    "boost_component": round(float(row.boost_score), 4),
                    "bm25_weight": self.ratio_bm25,
                    "vector_weight": self.ratio_vector,
                    "seniority_level": seniority
                }
            ))
            
        return candidates

    def _determine_seniority_level(self, experience_req: Dict[str, Any]) -> str:
        """Determine seniority level based on experience requirements."""
        min_months = experience_req.get("min_months", 0)
        
        if min_months >= settings.senior_exp_threshold:
            return "senior"
        elif min_months <= settings.junior_exp_threshold:
            return "junior"
        else:
            return "mid"

    def _get_weights_for_seniority(self, seniority: str) -> Dict[str, float]:
        """Get weights based on seniority level."""
        if seniority == "senior":
            return {
                'mandatory': settings.weight_mandatory_senior,
                'preferred': settings.weight_preferred_senior,
                'semantic': settings.weight_semantic_senior,
                'experience': settings.weight_experience,
                'certification': settings.weight_certification,
                'location': settings.weight_location,
                'work_mode': settings.weight_work_mode,
                'title': settings.weight_jd_text
            }
        elif seniority == "junior":
            return {
                'mandatory': settings.weight_mandatory_junior,
                'preferred': settings.weight_preferred_junior,
                'semantic': settings.weight_semantic_junior,
                'experience': settings.weight_experience,
                'certification': settings.weight_certification,
                'location': settings.weight_location,
                'work_mode': settings.weight_work_mode,
                'title': settings.weight_jd_text
            }
        else:  # mid
            return {
                'mandatory': settings.weight_mandatory_mid,
                'preferred': settings.weight_preferred_mid,
                'semantic': settings.weight_semantic_mid,
                'experience': settings.weight_experience,
                'certification': settings.weight_certification,
                'location': settings.weight_location,
                'work_mode': settings.weight_work_mode,
                'title': settings.weight_jd_text
            }

    def _build_bm25_score(self, query_text: str, mandatory_skills: List[str], preferred_skills: List[str]) -> sa.sql.expression.Label:
        """Build BM25 score using PostgreSQL full-text search."""
        # Process query terms - split multi-word phrases and clean
        all_terms = []
        
        if query_text:
            # Split on spaces and punctuation, filter out short words
            words = [word.strip() for word in query_text.replace(',', ' ').replace('.', ' ').split() if len(word.strip()) > 2]
            all_terms.extend(words)
        
        # Process skills - split multi-word skills
        for skill in mandatory_skills + preferred_skills:
            if ' ' in skill:
                # Split multi-word skills
                skill_words = [word.strip() for word in skill.split() if len(word.strip()) > 1]
                all_terms.extend(skill_words)
            else:
                all_terms.append(skill)
        
        # Remove duplicates and filter
        unique_terms = list(set(term.lower() for term in all_terms if term and len(term) > 1))
        
        if not unique_terms:
            return literal(0.0).label("bm25_score")
        
        # Create search string for plainto_tsquery
        search_str = ' '.join(unique_terms)
        
        try:
            # Use plainto_tsquery which handles multi-word queries better
            bm25_skills = func.ts_rank(
                func.to_tsvector('english', TeamMemberEmbedding.skills_text), 
                func.plainto_tsquery('english', search_str)
            )
            
            bm25_profile = func.ts_rank(
                func.to_tsvector('english', TeamMemberEmbedding.profile_text), 
                func.plainto_tsquery('english', search_str)
            )
            
            # Combine skills and profile BM25 scores (take the higher one)
            bm25_score = func.greatest(bm25_skills, bm25_profile)
        except Exception:
            # Fallback if tsquery fails
            self.logger.warning(f"BM25 tsquery failed for terms: {unique_terms}, using fallback")
            bm25_score = literal(0.0)
        
        return bm25_score.label("bm25_score")

    def _build_vector_score(self, embedding_result: EmbeddingResult) -> sa.sql.expression.Label:
        """Build vector similarity score."""
        def _cos_sim(col, vec):
            if vec is None: return literal(0.0)
            v_list = vec.tolist() if isinstance(vec, np.ndarray) else vec
            if all(v == 0 for v in v_list): return literal(0.0)
            return 1 - type_coerce(col, Vector(self.vector_dim)).cosine_distance(v_list)

        # Use full_jd_vector for overall semantic similarity
        vector_sim = _cos_sim(TeamMemberEmbedding.embedding, embedding_result.full_jd_vector)
        vector_score = func.greatest(0.0, func.coalesce(vector_sim, 0.0))
        
        return vector_score.label("vector_score")

    def _build_boost_scores(self, mandatory_skills: List[str], preferred_skills: List[str], 
                           locations: List[str], work_modes: List[str], experience_req: Dict[str, Any],
                           certifications: List[str], job_title: str, weights: Dict[str, float]) -> sa.sql.expression.Label:
        """Build all boost scores combined."""
        
        # Mandatory skills boost
        mandatory_boost = self._build_skill_boost(mandatory_skills, weights['mandatory'])
        
        # Preferred skills boost  
        preferred_boost = self._build_skill_boost(preferred_skills, weights['preferred'])
        
        # Experience boost
        min_exp = experience_req.get("min_months", 0)
        max_exp = experience_req.get("max_months", 999)
        exp_boost = case(
            (TeamMember.experience_in_months.between(min_exp, max_exp), weights['experience']),
            else_=0.0
        )
        
        # Location boost
        loc_cases = [
            case((TeamMember.base_location.ilike(f"%{loc}%"), weights['location']), else_=0.0) 
            for loc in locations
        ]
        location_boost = func.least(weights['location'], sum(loc_cases) if loc_cases else literal(0.0))
        
        # Work mode boost
        mode_map = {"Remote": "wfh", "WFO": "wfo", "Hybrid": "hybrid"}
        mapped_modes = [mode_map.get(m, m.lower()) for m in work_modes]
        mode_cases = [
            case((sa.cast(TeamMember.work_type, sa.Text) == m, weights['work_mode']), else_=0.0)
            for m in mapped_modes
        ]
        mode_boost = func.least(weights['work_mode'], sum(mode_cases) if mode_cases else literal(0.0))
        
        # Certifications boost
        cert_cases = [
            case((TeamMemberEmbedding.profile_text.ilike(f"%{cert}%"), weights['certification']/max(1, len(certifications))), else_=0.0)
            for cert in certifications
        ]
        cert_boost = sum(cert_cases) if cert_cases else literal(0.0)
        
        # Title boost
        title_boost = case(
            (TeamMember.designation.ilike(f"%{job_title}%"), weights['title']),
            else_=0.0
        )
        
        # Combine all boosts
        total_boost = (
            mandatory_boost + preferred_boost + exp_boost + 
            location_boost + mode_boost + cert_boost + title_boost
        )
        
        return total_boost.label("boost_score")

    def _build_skill_boost(self, skills: List[str], weight: float) -> sa.sql.expression.ColumnElement:
        """Build skill matching boost score."""
        if not skills:
            return literal(0.0)
        
        # Map skill variations to common names for better matching
        skill_variations = {
            "Apache Spark": ["spark", "apache spark"],
            "Spark": ["spark", "apache spark"],
            "ETL Pipeline": ["etl", "pipeline", "data pipeline"],
            "ETL": ["etl", "pipeline", "data pipeline"],
            "Apache Airflow": ["airflow", "apache airflow"],
            "Airflow": ["airflow", "apache airflow"],
            "Hadoop": ["hadoop", "hdfs"],
            "Scala": ["scala"],
            "AWS": ["aws", "amazon web services"],
            "GCP": ["gcp", "google cloud"],
            "Azure": ["azure", "microsoft azure"]
        }
        
        skill_cases = []
        per_skill_weight = weight / len(skills)
        
        for skill in skills:
            # Get variations for this skill
            variations = skill_variations.get(skill, [skill.lower()])
            
            # Build OR condition for all variations of this skill
            skill_condition = None
            for variation in variations:
                match_expr = TeamMemberEmbedding.skills_text.ilike(f"%{variation}%")
                if skill_condition is None:
                    skill_condition = match_expr
                else:
                    skill_condition = skill_condition | match_expr
            
            # Add case for this skill
            skill_cases.append(
                case((skill_condition, per_skill_weight), else_=0.0)
            )
        
        return func.least(weight, sum(skill_cases))

    def _get_skill_gate_threshold(self, seniority: str) -> float:
        """Get skill gate threshold based on seniority."""
        if seniority == "senior":
            return settings.min_skill_weighted_senior
        elif seniority == "junior":
            return settings.min_skill_weighted_junior
        else:  # mid
            return settings.min_skill_weighted_mid

    def validate_input(self, input_data: Any) -> bool:
        """Validate input data for RAG retrieval."""
        return isinstance(input_data, EmbeddingResult)

    def format_output(self, result: List[RAGCandidate]) -> List[RAGCandidate]:
        """Format output for RAG retrieval."""
        return result
