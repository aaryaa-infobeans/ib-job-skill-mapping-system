"""RAG Retrieval Agent - Multi-Vector Hybrid search (BM25 + pgvector) supporting Gemma embeddings."""

import logging
import numpy as np
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import text

from app.ai.utils.base import BaseAgent
from app.ai.utils.models import EmbeddingResult, RAGCandidate
from app.settings import settings


class RAGRetrievalAgent(BaseAgent):
    """Retrieve candidates using Multi-Vector Hybrid Search (BM25 + pgvector)."""

    def __init__(self, db_connection=None, logger: Optional[logging.Logger] = None):
        super().__init__("rag_retrieval", logger)
        self.db = db_connection
        self.vector_dim = 768

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

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
        """Execute Multi-Vector Hybrid Search (BM25 + pgvector)."""
        if not self.db:
            self.logger.warning("No DB connection provided to RAGRetrievalAgent")
            return []

        try:
            vectors = self._extract_vectors(embedding_result)
            keyword_query_str, mandatory_query_str = self._build_keyword_strings(
                mandatory_skills, preferred_skills, certifications
            )
            filters, params = self._build_filters(
                locations, work_modes, experience_req,
                mandatory_query_str, vectors, keyword_query_str
            )

            sql = self._build_sql(filters)
            result_set = self.db.execute(sql, params).fetchall()
            self.logger.info(
                f"RAG SQL returned {len(result_set)} rows | "
                f"filters={[f.strip() for f in filters]} | "
                f"kw_query={params.get('kw_query', '')!r} | "
                f"m_query={params.get('m_query', '')!r}"
            )

            candidates = [
                self._build_structured_candidate(
                    row, mandatory_skills, preferred_skills,
                    certifications, locations, work_modes, experience_req
                )
                for row in result_set
            ]

            return self._filter_and_rank(candidates)

        except Exception as e:
            self.logger.error(f"Hybrid search execute failed: {str(e)}", exc_info=True)
            return []

    def validate_input(self, input_data: Any) -> bool:
        return isinstance(input_data, EmbeddingResult)

    def format_output(self, result: List[RAGCandidate]) -> List[RAGCandidate]:
        return result

    # ------------------------------------------------------------------
    # Vector and keyword preparation
    # ------------------------------------------------------------------

    def _extract_vectors(self, embedding_result: EmbeddingResult) -> Dict[str, Any]:
        """Convert EmbeddingResult vectors to lists; fall back to full_jd for missing."""
        def _to_list(vec):
            return vec.tolist() if isinstance(vec, np.ndarray) else vec

        full_jd = _to_list(embedding_result.full_jd_vector)
        return {
            "full_jd_vector":   full_jd,
            "jd_level_vector":  _to_list(embedding_result.jd_level_vector)       or full_jd,
            "mandatory_vector": _to_list(embedding_result.mandatory_vector)       or full_jd,
            "preferred_vector": _to_list(embedding_result.preferred_vector)       or full_jd,
            "cert_vector":      _to_list(embedding_result.certification_vector)   or full_jd,
        }

    def _build_keyword_strings(
        self,
        mandatory_skills: List[str],
        preferred_skills: List[str],
        certifications: List[str],
    ) -> Tuple[str, str]:
        """Build websearch_to_tsquery-compatible OR strings for BM25."""
        def _phrase(k: str) -> str:
            k = k.strip()
            return f'"{k}"' if " " in k else k

        all_kw = [_phrase(k) for k in (mandatory_skills or []) + (preferred_skills or []) + (certifications or []) if k.strip()]
        mandatory_kw = [_phrase(k) for k in (mandatory_skills or []) if k.strip()]

        return (
            " OR ".join(all_kw),
            " OR ".join(mandatory_kw),
        )

    # ------------------------------------------------------------------
    # SQL construction
    # ------------------------------------------------------------------

    def _build_filters(
        self,
        locations: List[str],
        work_modes: List[str],
        experience_req: Dict[str, Any],
        mandatory_query_str: str,
        vectors: Dict[str, Any],
        keyword_query_str: str,
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Build WHERE clause fragments and the full params dict."""
        filters = ["e.embedding IS NOT NULL", "tm.is_active = true"]
        params: Dict[str, Any] = {
            **vectors,
            "kw_query":  keyword_query_str,
            "sql_limit": settings.rag_sql_limit,
        }

        if mandatory_query_str:
            filters.append("""
                to_tsvector('english',
                    coalesce(e.skills_text, '') || ' ' ||
                    coalesce(e.certifications_text, '') || ' ' ||
                    coalesce(e.profile_text, '')
                ) @@ websearch_to_tsquery('english', :m_query)
            """)
            params["m_query"] = mandatory_query_str

        self._add_location_filters(filters, params, locations)
        self._add_work_mode_filters(filters, params, work_modes)
        self._add_experience_filters(filters, params, experience_req)

        return filters, params

    def _add_location_filters(self, filters: List[str], params: Dict, locations: List[str]) -> None:
        if not locations:
            return
        loc_clauses = []
        for i, loc in enumerate(locations):
            key = f"loc_{i}"
            loc_clauses.append(f"tm.base_location ILIKE :{key}")
            params[key] = f"%{loc}%"
        filters.append("(" + " OR ".join(loc_clauses) + ")")

    def _add_work_mode_filters(self, filters: List[str], params: Dict, work_modes: List[str]) -> None:
        if not work_modes:
            return
        mode_map = {"Remote": "wfh", "WFO": "wfo", "Hybrid": "hybrid"}
        mode_clauses = []
        for i, mode in enumerate(work_modes):
            mapped = mode_map.get(mode, mode.lower())
            key = f"mode_{i}"
            mode_clauses.append(f"CAST(tm.work_type AS text) ILIKE :{key}")
            params[key] = f"%{mapped}%"
        filters.append("(" + " OR ".join(mode_clauses) + ")")

    def _add_experience_filters(self, filters: List[str], params: Dict, experience_req: Dict) -> None:
        if not experience_req:
            return
        min_m = experience_req.get("min_months")
        max_m = experience_req.get("max_months")
        if min_m is not None and max_m is not None:
            filters.append("tm.experience_in_months BETWEEN :min_m AND :max_m")
            params["min_m"] = min_m
            params["max_m"] = max_m
        elif min_m is not None:
            filters.append("tm.experience_in_months >= :min_m")
            params["min_m"] = min_m
        elif max_m is not None:
            filters.append("tm.experience_in_months <= :max_m")
            params["max_m"] = max_m

    def _build_sql(self, filters: List[str]):
        return text(f"""
            SELECT
                e.team_member_id,
                COALESCE(tm.designation, '')                                         AS role,
                COALESCE(e.skills_text, '')                                          AS skills,
                COALESCE(e.certifications_text, '')                                  AS certifications_text,
                tm.experience_in_months,
                COALESCE(tm.base_location, '')                                       AS base_location,
                COALESCE(CAST(tm.work_type AS text), 'hybrid')                       AS work_type,

                e.embedding <-> CAST(:full_jd_vector AS vector)                      AS full_jd_distance,

                COALESCE(e.resume_embedding, e.embedding)
                    <-> CAST(:jd_level_vector AS vector)                             AS level_distance,

                COALESCE(e.skills_embedding, e.embedding)
                    <-> CAST(:mandatory_vector AS vector)                            AS mandatory_skills_distance,

                COALESCE(e.skills_embedding, e.embedding)
                    <-> CAST(:preferred_vector AS vector)                            AS preferred_skills_distance,

                COALESCE(e.certifications_embedding, e.embedding)
                    <-> CAST(:cert_vector AS vector)                                 AS cert_distance,

                ts_rank(
                    to_tsvector('english',
                        coalesce(e.skills_text, '') || ' ' ||
                        coalesce(e.certifications_text, '') || ' ' ||
                        coalesce(e.profile_text, '')
                    ),
                    websearch_to_tsquery('english', :kw_query)
                )                                                                    AS keyword_score

            FROM team_member_embeddings e
            LEFT JOIN team_member tm ON tm.team_member_id = e.team_member_id
            WHERE {" AND ".join(filters)}
            ORDER BY full_jd_distance ASC
            LIMIT :sql_limit
        """)

    # ------------------------------------------------------------------
    # Candidate scoring
    # ------------------------------------------------------------------

    def _filter_and_rank(self, candidates: List[RAGCandidate]) -> List[RAGCandidate]:
        threshold = settings.rag_similarity_threshold
        qualified = [c for c in candidates if c.final_similarity > threshold]
        qualified.sort(key=lambda x: x.final_similarity, reverse=True)
        result = qualified[:settings.rag_final_candidates]
        self.logger.info(
            f"RAG Retrieval matched {len(result)} candidates above "
            f"{threshold} threshold (Multi-Vector Hybrid BM25+pgvector)"
        )
        return result

    @staticmethod
    def _dist_to_sim(d) -> float:
        """Convert L2 distance to 0-1 similarity."""
        return 1.0 / (1.0 + float(d)) if d is not None else 0.0

    @staticmethod
    def _exp_relevance(cand_m, req: Dict) -> float:
        """Partial credit for candidates outside the experience range."""
        if not req or cand_m is None:
            return 1.0
        min_m = req.get("min_months") or 0
        max_m = req.get("max_months") or 9999
        if min_m <= cand_m <= max_m:
            return 1.0
        diff = min_m - cand_m if cand_m < min_m else cand_m - max_m
        return max(0.0, 1.0 - min(diff / max(12, min_m or 12), 1.0))

    @staticmethod
    def _keyword_matches(haystack: str, keywords: List[str]) -> List[str]:
        if not haystack or not keywords:
            return []
        t = haystack.lower()
        return [kw for kw in keywords if kw.lower() in t]

    def _build_structured_candidate(
        self, row,
        mandatory_skills, preferred_skills,
        certifications, locations, work_modes, experience_req
    ) -> RAGCandidate:
        (
            team_member_id, role, skills_text, certifications_text,
            experience_in_months, base_location, work_type,
            full_jd_distance, level_distance,
            mandatory_skills_distance, preferred_skills_distance,
            cert_distance, keyword_score,
        ) = row

        combined_text = f"{skills_text or ''} {role or ''}".lower()
        mandatory_matches     = self._keyword_matches(combined_text, mandatory_skills)
        preferred_matches     = self._keyword_matches(combined_text, preferred_skills)
        cert_matches          = self._keyword_matches(str(certifications_text or ""), certifications)

        location_comp = any(loc.lower() in str(base_location).lower() for loc in locations) if locations else True
        _mode_map = {"remote": "wfh", "wfh": "remote"}
        _wt = str(work_type).lower()
        _wt_aliases = {_wt, _mode_map.get(_wt, _wt)}
        mode_comp = any(
            mode.lower() in _wt_aliases or _mode_map.get(mode.lower(), mode.lower()) in _wt_aliases
            for mode in work_modes
        ) if work_modes else True

        experience_relevance  = self._exp_relevance(experience_in_months, experience_req)

        # Per-vector similarities
        full_jd_sim       = self._dist_to_sim(full_jd_distance)
        level_sim         = self._dist_to_sim(level_distance)
        mandatory_vec_sim = self._dist_to_sim(mandatory_skills_distance)
        preferred_vec_sim = self._dist_to_sim(preferred_skills_distance)
        cert_vec_sim      = self._dist_to_sim(cert_distance)

        kw_norm = round(float(keyword_score) / (0.03 + float(keyword_score)), 4) if float(keyword_score) > 0 else 0.0
        m_score = len(mandatory_matches) / max(len(mandatory_skills), 1) if mandatory_skills else 1.0
        p_score = len(preferred_matches) / max(len(preferred_skills), 1) if preferred_skills else 1.0
        c_score = len(cert_matches)       / max(len(certifications), 1)   if certifications   else 1.0

        total_score = self._compute_total_score(
            full_jd_sim, level_sim, mandatory_vec_sim, preferred_vec_sim, cert_vec_sim,
            kw_norm, m_score, p_score, c_score,
            experience_relevance, location_comp, mode_comp,
            mandatory_skills, mandatory_matches,
        )

        jd_level_sim_value = level_sim if settings.rag_use_level_vector else full_jd_sim

        vector_sims = {
            "full_jd":    full_jd_sim,
            "level":      level_sim,
            "mandatory":  mandatory_vec_sim,
            "preferred":  preferred_vec_sim,
            "cert":       cert_vec_sim,
        }

        return RAGCandidate(
            team_member_id=team_member_id,
            final_similarity=round(total_score, 4),
            mandatory_similarity=round(m_score, 4),
            preferred_similarity=round(p_score, 4),
            jd_level_similarity=round(jd_level_sim_value, 4),
            certification_similarity=round(c_score, 4),
            full_jd_similarity=round(full_jd_sim, 4),
            phase0_score_breakdown=self._build_breakdown(
                total_score, kw_norm, m_score, p_score, c_score,
                experience_relevance, location_comp, mode_comp,
                bool(mandatory_skills and not mandatory_matches),
                vector_sims,
            )
        )

    def _compute_total_score(
        self,
        full_jd_sim, level_sim, mandatory_vec_sim, preferred_vec_sim, cert_vec_sim,
        kw_norm, m_score, p_score, c_score,
        experience_relevance, location_comp, mode_comp,
        mandatory_skills, mandatory_matches,
    ) -> float:
        multi_vec_semantic = (
            full_jd_sim       * settings.rag_weight_full_jd +
            level_sim         * settings.rag_weight_level +
            mandatory_vec_sim * settings.rag_weight_skills_mandatory +
            preferred_vec_sim * settings.rag_weight_skills_preferred +
            cert_vec_sim      * settings.rag_weight_cert
        )

        # Split semantic+keyword 0.50 budget by hybrid_ratio settings
        vec_w = 0.50 * settings.hybrid_ratio_vector
        kw_w  = 0.50 * settings.hybrid_ratio_bm25

        score = (
            multi_vec_semantic   * vec_w +
            kw_norm              * kw_w  +
            m_score              * 0.30  +
            p_score              * 0.05  +
            experience_relevance * 0.05  +
            c_score              * 0.05  +
            (1.0 if location_comp else 0.0) * 0.025 +
            (1.0 if mode_comp     else 0.0) * 0.025
        )

        if mandatory_skills and not mandatory_matches:
            score *= 0.6

        return score

    @staticmethod
    def _build_breakdown(
        total_score, kw_norm, m_score, p_score, c_score,
        experience_relevance, location_comp, mode_comp, penalty_assigned,
        vector_sims: Dict[str, float],
    ) -> Dict:
        multi_vec_semantic = (
            vector_sims["full_jd"]   * settings.rag_weight_full_jd +
            vector_sims["level"]     * settings.rag_weight_level +
            vector_sims["mandatory"] * settings.rag_weight_skills_mandatory +
            vector_sims["preferred"] * settings.rag_weight_skills_preferred
        )
        return {
            # Existing keys — unchanged semantics
            "total_score":              round(total_score, 4),
            "semantic_fit":             round(multi_vec_semantic, 4),
            "keyword_score":            round(kw_norm, 4),
            "mandatory_score":          round(m_score, 4),
            "preferred_score":          round(p_score, 4),
            "experience_relevance":     round(experience_relevance, 4),
            "certification_score":      round(c_score, 4),
            "location_compatibility":   location_comp,
            "work_mode_compatibility":  mode_comp,
            "mandatory_penalty_assigned": penalty_assigned,
            # New audit fields — visible in detailed_breakdown.phase0_ledger
            "full_jd_vector_sim":           round(vector_sims["full_jd"],   4),
            "level_vector_sim":             round(vector_sims["level"],     4),
            "mandatory_skills_vector_sim":  round(vector_sims["mandatory"], 4),
            "preferred_skills_vector_sim":  round(vector_sims["preferred"], 4),
            "cert_vector_sim":              round(vector_sims["cert"],      4),
        }
