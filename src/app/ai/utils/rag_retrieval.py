"""RAG Retrieval Agent - Multi-Vector Hybrid search (BM25 + pgvector) supporting Gemma embeddings."""

import logging
import numpy as np
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import text

from app.ai.utils.base import BaseAgent
from app.ai.utils.models import EmbeddingResult, RAGCandidate
from app.settings import settings

# Terms that indicate "no fixed location" — not physical places, so skip the location filter
# rather than searching for candidates whose base_location contains e.g. "Remote".
_VIRTUAL_LOCATION_TERMS: frozenset = frozenset({
    "remote", "wfh", "work from home", "work-from-home", "work_from_home",
    "anywhere", "global", "worldwide", "virtual", "online",
    "n/a", "na", "not specified", "none", "any",
})

# Canonical mapping from any JD work-mode string → DB work_type value.
# Unknown entries are skipped (no filter added) rather than causing a zero-result query.
_WORK_MODE_ALIASES: Dict[str, str] = {
    "remote":           "wfh",
    "wfh":              "wfh",
    "work from home":   "wfh",
    "work-from-home":   "wfh",
    "work_from_home":   "wfh",
    "wfo":              "wfo",
    "office":           "wfo",
    "onsite":           "wfo",
    "on-site":          "wfo",
    "on site":          "wfo",
    "in-office":        "wfo",
    "in office":        "wfo",
    "hybrid":           "hybrid",
    "flexible":         "hybrid",
    "mixed":            "hybrid",
}

# Experience bounds that are treated as "no real constraint" and skipped.
# Controlled via EXP_MAX_PLAUSIBLE_MONTHS in .env (fallback: 600 months / 50 years).
from app.settings import settings as _settings
_EXP_MAX_PLAUSIBLE_MONTHS: int = _settings.exp_max_plausible_months


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

            self.logger.debug(
                "skill_ontology expansion input | "
                f"mandatory={mandatory_skills!r} | preferred={preferred_skills!r}"
            )
            expanded_mandatory = self._expand_skills_via_ontology(mandatory_skills)
            expanded_preferred = self._expand_skills_via_ontology(preferred_skills)
            self.logger.debug(
                "skill_ontology expansion output | "
                f"mandatory={expanded_mandatory!r} | preferred={expanded_preferred!r}"
            )

            expanded_mandatory_flat = [t for terms in expanded_mandatory.values() for t in terms]
            expanded_preferred_flat = [t for terms in expanded_preferred.values() for t in terms]

            keyword_query_str, _ = self._build_keyword_strings(
                expanded_mandatory_flat, expanded_preferred_flat, certifications
            ) # second parameter is mandatory_query_str which is not used reason for unnaming
            filters, params = self._build_filters(
                locations, work_modes, experience_req,
                vectors, keyword_query_str
            )

            mode = (settings.rag_retrieval_mode or "hybrid").strip().lower()
            run_semantic = mode in ("hybrid", "semantic")
            run_keyword = mode in ("hybrid", "bm25")
            self.logger.info(f"RAG retrieval mode: {mode}")

            # Semantic path: composite vector-ordered top-N
            # bm25_score is embedded via LEFT JOIN subquery (col 14) for accurate scoring
            semantic_rows: list = []
            if run_semantic:
                sql = self._build_sql(filters, keyword_query_str)
                semantic_rows = self.db.execute(sql, params).fetchall()
                self.logger.info(
                    f"RAG SQL (semantic) returned {len(semantic_rows)} rows"
                )

            # Keyword path: pg_bm25 index — BM25 drives retrieval, not a boolean pre-filter
            keyword_rows: list = []
            if run_keyword and keyword_query_str.strip():
                try:
                    kw_sql = self._build_keyword_sql(filters)
                    keyword_rows = self.db.execute(kw_sql, params).fetchall()
                    self.logger.info(
                        f"RAG SQL (keyword/pg_bm25) returned {len(keyword_rows)} rows "
                        f"(cap={settings.rag_keyword_fetch_limit})"
                    )
                except Exception as kw_err:
                    self.logger.warning(f"pg_bm25 keyword SQL failed, skipping keyword path: {kw_err}")
            elif run_keyword and not keyword_query_str.strip():
                self.logger.warning(
                    "RAG retrieval mode requires BM25 but keyword query is empty — no keyword rows"
                )

            # Build rank maps for RRF: {team_member_id: 1-based rank}
            semantic_rank_map: Dict[str, int] = {row[0]: i + 1 for i, row in enumerate(semantic_rows)}
            bm25_rank_map:     Dict[str, int] = {row[0]: i + 1 for i, row in enumerate(keyword_rows)}

            merged_rows = self._merge_result_sets(semantic_rows, keyword_rows)
            self.logger.info(
                f"Merged pool: {len(merged_rows)} unique candidates "
                f"(semantic={len(semantic_rows)}, keyword={len(keyword_rows)}, "
                f"keyword-only={len(merged_rows) - len(semantic_rows)})"
            )

            candidates = [
                self._build_structured_candidate(
                    row,
                    semantic_rank_map, bm25_rank_map,
                    mandatory_skills, preferred_skills,
                    certifications, locations, work_modes, experience_req,
                    expanded_mandatory, expanded_preferred,
                )
                for row in merged_rows
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

    def _expand_skills_via_ontology(self, skill_names: List[str]) -> Dict[str, List[str]]:
        """Return a per-skill synonym map from skill_ontology; falls back to identity map.

        Bidirectional: matches rows where the input skill is the core_skill OR appears
        inside enriched_terms, so a JD skill like 'React.js' still resolves to the full
        synonym set even when the canonical entry is 'ReactJS'.
        """
        skill_names = skill_names or []
        result: Dict[str, List[str]] = {s: [s] for s in skill_names}
        if not skill_names or self.db is None:
            return result
        lower_to_original = {s.lower(): s for s in skill_names}
        lower_names = list(lower_to_original.keys())
        rows = self.db.execute(
            text(
                "SELECT core_skill, enriched_terms "
                "FROM skill_ontology "
                "WHERE LOWER(core_skill) = ANY(:names) "
                "   OR EXISTS (SELECT 1 FROM unnest(enriched_terms) AS term WHERE LOWER(term) = ANY(:names))"
            ),
            {"names": lower_names},
        ).fetchall()
        for core_skill, enriched_terms in rows:
            synonyms = [core_skill] + list(enriched_terms or [])
            for lower_name, original_name in lower_to_original.items():
                if lower_name == core_skill.lower() or lower_name in [t.lower() for t in (enriched_terms or [])]:
                    result[original_name] = synonyms
        return result

    # ------------------------------------------------------------------
    # SQL construction
    # ------------------------------------------------------------------

    def _build_filters(
        self,
        locations: List[str],
        work_modes: List[str],
        experience_req: Dict[str, Any],
        vectors: Dict[str, Any],
        keyword_query_str: str,
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Build WHERE clause fragments and the full params dict."""
        filters = ["e.embedding IS NOT NULL", "tm.is_active = true"]
        params: Dict[str, Any] = {
            **vectors,
            "bm25_query":          keyword_query_str,
            "sql_limit":           settings.rag_sql_limit,
            "keyword_fetch_limit": settings.rag_keyword_fetch_limit,
        }

        # Hard pre-filters applied to both SQL paths.
        # Location: only applied when the JD does NOT accept remote/WFH.
        # Work mode: removed as a hard SQL filter — candidates are not excluded by work_type.
        #   Fit is a scoring concern handled downstream, not a binary retrieval gate.
        jd_accepts_remote = any(
            _WORK_MODE_ALIASES.get(m.strip().lower()) == "wfh"
            for m in work_modes
        ) or any(
            loc.strip().lower() in _VIRTUAL_LOCATION_TERMS
            for loc in locations
        )
        if not jd_accepts_remote:
            self._add_location_filters(filters, params, locations)
        self._add_experience_filters(filters, params, experience_req)

        return filters, params

    def _add_location_filters(self, filters: List[str], params: Dict, locations: List[str]) -> None:
        if not locations:
            return
        # Drop virtual/work-mode terms — not physical places, would match nothing in base_location.
        physical = [loc for loc in locations if loc.strip() and loc.strip().lower() not in _VIRTUAL_LOCATION_TERMS]
        if not physical:
            return  # all entries were virtual — skip filter rather than returning zero rows
        loc_clauses = []
        for i, loc in enumerate(physical):
            key = f"loc_{i}"
            loc_clauses.append(f"tm.base_location ILIKE :{key}")
            params[key] = f"%{loc}%"
        filters.append("(" + " OR ".join(loc_clauses) + ")")

    def _add_work_mode_filters(self, filters: List[str], params: Dict, work_modes: List[str]) -> None:
        if not work_modes:
            return
        mapped_modes = {_WORK_MODE_ALIASES[m.strip().lower()] for m in work_modes if m.strip().lower() in _WORK_MODE_ALIASES}
        if not mapped_modes:
            return  # all entries unmappable — skip rather than filtering to zero rows

        # If the JD accepts WFH, every candidate can fulfil it (a WFO candidate can work
        # remotely when the role allows). Only filter when the JD demands physical presence.
        if "wfh" in mapped_modes:
            return

        # JD requires physical presence (WFO-only or Hybrid-only).
        # WFH-only candidates cannot fulfil office requirements — exclude them.
        # Allow wfo and hybrid candidates (hybrid implies they can do in-office days).
        filters.append("CAST(tm.work_type AS text) NOT ILIKE :wfh_exclude")
        params["wfh_exclude"] = "wfh"

    def _add_experience_filters(self, filters: List[str], params: Dict, experience_req: Dict) -> None:
        if not experience_req:
            return
        min_m = experience_req.get("min_months")
        max_m = experience_req.get("max_months")

        # Discard values outside any plausible real-world range
        if min_m is not None and (min_m < 0 or min_m > _EXP_MAX_PLAUSIBLE_MONTHS):
            min_m = None
        if max_m is not None and (max_m < 0 or max_m > _EXP_MAX_PLAUSIBLE_MONTHS):
            max_m = None

        # min=0 is a no-op lower bound — skip it
        if min_m == 0:
            min_m = None

        # Experience is not used as a hard SQL filter — the scoring layer handles this.

    def _build_sql(self, filters: List[str], keyword_query_str: str = ""):
        if keyword_query_str.strip():
            bm25_join = """
            LEFT JOIN (
                SELECT e2.id, paradedb.score(e2.id) AS bm25_score
                FROM team_member_embeddings e2
                WHERE e2 @@@ paradedb.parse(:bm25_query)
            ) bm25_sub ON bm25_sub.id = e.id"""
            bm25_col = "COALESCE(bm25_sub.bm25_score, 0.0)                              AS bm25_score"
        else:
            bm25_join = ""
            bm25_col = "0.0::float                                                       AS bm25_score"

        return text(f"""
            SELECT
                e.team_member_id,
                COALESCE(tm.designation, '')                                         AS role,
                COALESCE(e.skills_text, '')                                          AS skills,
                COALESCE(e.certifications_text, '')                                  AS certifications_text,
                tm.experience_in_months,
                COALESCE(tm.base_location, '')                                       AS base_location,
                COALESCE(CAST(tm.work_type AS text), 'hybrid')                       AS work_type,

                e.embedding <=> CAST(:full_jd_vector AS vector)                      AS full_jd_distance,

                COALESCE(e.resume_embedding, e.embedding)
                    <=> CAST(:jd_level_vector AS vector)                             AS level_distance,

                COALESCE(e.skills_embedding, e.embedding)
                    <=> CAST(:mandatory_vector AS vector)                            AS mandatory_skills_distance,

                COALESCE(e.skills_embedding, e.embedding)
                    <=> CAST(:preferred_vector AS vector)                            AS preferred_skills_distance,

                COALESCE(e.certifications_embedding, e.embedding)
                    <=> CAST(:cert_vector AS vector)                                 AS cert_distance,

                COALESCE(e.profile_text, '')                                         AS profile_text,

                {bm25_col}

            FROM team_member_embeddings e
            LEFT JOIN team_member tm ON tm.team_member_id = e.team_member_id{bm25_join}
            WHERE {" AND ".join(filters)}
            ORDER BY (
                (e.embedding <=> CAST(:full_jd_vector AS vector))
                    * {settings.rag_weight_full_jd} +
                (COALESCE(e.resume_embedding, e.embedding) <=> CAST(:jd_level_vector AS vector))
                    * {settings.rag_weight_level} +
                (COALESCE(e.skills_embedding, e.embedding) <=> CAST(:mandatory_vector AS vector))
                    * {settings.rag_weight_skills_mandatory} +
                (COALESCE(e.skills_embedding, e.embedding) <=> CAST(:preferred_vector AS vector))
                    * {settings.rag_weight_skills_preferred} +
                (COALESCE(e.certifications_embedding, e.embedding) <=> CAST(:cert_vector AS vector))
                    * {settings.rag_weight_cert}
            ) ASC
            LIMIT :sql_limit
        """)

    def _build_keyword_sql(self, filters: List[str]):
        """SQL #2: pg_bm25 keyword retrieval path using ParadeDB @@@ operator.

        Returns 14 columns: same 13 as _build_sql() + bm25_score as col 14.
        Ordered by BM25 score DESC so the strongest keyword matches come first.
        Uses the same filters list as _build_sql() so that enabling business constraint
        pre-filters in _build_filters() automatically applies to both SQL paths.
        """
        return text(f"""
            SELECT
                e.team_member_id,
                COALESCE(tm.designation, '')                                         AS role,
                COALESCE(e.skills_text, '')                                          AS skills,
                COALESCE(e.certifications_text, '')                                  AS certifications_text,
                tm.experience_in_months,
                COALESCE(tm.base_location, '')                                       AS base_location,
                COALESCE(CAST(tm.work_type AS text), 'hybrid')                       AS work_type,

                e.embedding <=> CAST(:full_jd_vector AS vector)                      AS full_jd_distance,

                COALESCE(e.resume_embedding, e.embedding)
                    <=> CAST(:jd_level_vector AS vector)                             AS level_distance,

                COALESCE(e.skills_embedding, e.embedding)
                    <=> CAST(:mandatory_vector AS vector)                            AS mandatory_skills_distance,

                COALESCE(e.skills_embedding, e.embedding)
                    <=> CAST(:preferred_vector AS vector)                            AS preferred_skills_distance,

                COALESCE(e.certifications_embedding, e.embedding)
                    <=> CAST(:cert_vector AS vector)                                 AS cert_distance,

                COALESCE(e.profile_text, '')                                         AS profile_text,

                paradedb.score(e.id)                                                 AS bm25_score

            FROM team_member_embeddings e
            LEFT JOIN team_member tm ON tm.team_member_id = e.team_member_id
            WHERE e @@@ paradedb.parse(:bm25_query)
              AND {" AND ".join(filters)}
            ORDER BY paradedb.score(e.id) DESC
            LIMIT :keyword_fetch_limit
        """)

    @staticmethod
    def _merge_result_sets(semantic_rows: list, keyword_rows: list) -> list:
        """Union semantic and keyword rows, deduplicating by team_member_id (col 0).

        Semantic rows take priority for duplicates. Keyword-only rows are appended after.
        """
        seen: set = set()
        merged = []
        for row in semantic_rows:
            tm_id = row[0]
            if tm_id not in seen:
                seen.add(tm_id)
                merged.append(row)
        for row in keyword_rows:
            tm_id = row[0]
            if tm_id not in seen:
                seen.add(tm_id)
                merged.append(row)
        return merged

    # ------------------------------------------------------------------
    # Candidate scoring
    # ------------------------------------------------------------------

    def _filter_and_rank(self, candidates: List[RAGCandidate]) -> List[RAGCandidate]:
        candidates.sort(key=lambda x: x.final_similarity, reverse=True)
        result = candidates[:settings.rag_final_candidates]
        self.logger.info(
            f"RAG Retrieval: top {len(result)} candidates by RRF score "
            f"(pool={len(candidates)}, cap={settings.rag_final_candidates})"
        )
        return result

    @staticmethod
    def _dist_to_sim(d) -> float:
        """Convert cosine distance (0=identical, 1=orthogonal) to similarity."""
        return max(0.0, 1.0 - float(d)) if d is not None else 0.0

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

    @staticmethod
    def _synonym_keyword_matches(haystack: str, skill_synonyms: Dict[str, List[str]]) -> List[str]:
        """Return original skill names whose synonym list has any hit in haystack."""
        if not haystack or not skill_synonyms:
            return []
        t = haystack.lower()
        return [skill for skill, synonyms in skill_synonyms.items() if any(syn.lower() in t for syn in synonyms)]

    def _build_structured_candidate(
        self, row,
        semantic_rank_map: Dict[str, int],
        bm25_rank_map: Dict[str, int],
        mandatory_skills, preferred_skills,
        certifications, locations, work_modes, experience_req,
        expanded_mandatory: Optional[Dict[str, List[str]]] = None,
        expanded_preferred: Optional[Dict[str, List[str]]] = None,
    ) -> RAGCandidate:
        (
            team_member_id, role, skills_text, certifications_text,
            experience_in_months, base_location, work_type,
            full_jd_distance, level_distance,
            mandatory_skills_distance, preferred_skills_distance,
            cert_distance, profile_text, bm25_score,
        ) = row

        combined_text = f"{skills_text or ''} {role or ''}".lower()
        mandatory_matches = (
            self._synonym_keyword_matches(combined_text, expanded_mandatory)
            if expanded_mandatory else self._keyword_matches(combined_text, mandatory_skills)
        )
        preferred_matches = (
            self._synonym_keyword_matches(combined_text, expanded_preferred)
            if expanded_preferred else self._keyword_matches(combined_text, preferred_skills)
        )
        cert_matches = self._keyword_matches(str(certifications_text or ""), certifications)

        location_comp = any(loc.lower() in str(base_location).lower() for loc in locations) if locations else True
        _mode_map = {"remote": "wfh", "wfh": "remote"}
        _wt = str(work_type).lower()
        _wt_aliases = {_wt, _mode_map.get(_wt, _wt)}
        mode_comp = any(
            mode.lower() in _wt_aliases or _mode_map.get(mode.lower(), mode.lower()) in _wt_aliases
            for mode in work_modes
        ) if work_modes else True

        experience_relevance = self._exp_relevance(experience_in_months, experience_req)

        # Per-vector similarities (passed to Node 5 scorer via RAGCandidate fields)
        full_jd_sim       = self._dist_to_sim(full_jd_distance)
        level_sim         = self._dist_to_sim(level_distance)
        mandatory_vec_sim = self._dist_to_sim(mandatory_skills_distance)
        preferred_vec_sim = self._dist_to_sim(preferred_skills_distance)
        cert_vec_sim      = self._dist_to_sim(cert_distance)

        bm25_score = round(float(bm25_score), 4)
        m_score = len(mandatory_matches) / max(len(mandatory_skills), 1) if mandatory_skills else 1.0
        p_score = len(preferred_matches) / max(len(preferred_skills), 1) if preferred_skills else 1.0
        c_score = len(cert_matches)       / max(len(certifications), 1)   if certifications   else 1.0

        # Phase 0 ranking: Reciprocal Rank Fusion (RRF)
        # Candidates in both paths get additive contribution from each path's rank.
        # k=60 is the standard constant used by Elasticsearch/Weaviate hybrid search.
        _k = 60
        semantic_rank = semantic_rank_map.get(team_member_id)
        bm25_rank     = bm25_rank_map.get(team_member_id)
        rrf_score = 0.0
        if semantic_rank is not None:
            rrf_score += 1.0 / (_k + semantic_rank)
        if bm25_rank is not None:
            rrf_score += 1.0 / (_k + bm25_rank)
        rrf_score = round(rrf_score, 6)

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
            final_similarity=rrf_score,
            mandatory_similarity=round(m_score, 4),
            preferred_similarity=round(p_score, 4),
            jd_level_similarity=round(jd_level_sim_value, 4),
            certification_similarity=round(c_score, 4),
            full_jd_similarity=round(full_jd_sim, 4),
            profile_text=profile_text,
            phase0_score_breakdown=self._build_breakdown(
                rrf_score, semantic_rank, bm25_rank,
                bm25_score, m_score, p_score, c_score,
                experience_relevance, location_comp, mode_comp,
                bool(mandatory_skills and not mandatory_matches),
                vector_sims,
            )
        )

    @staticmethod
    def _build_breakdown(
        rrf_score, semantic_rank, bm25_rank,
        bm25_score, m_score, p_score, c_score,
        experience_relevance, location_comp, mode_comp, penalty_assigned,
        vector_sims: Dict[str, float],
    ) -> Dict:
        return {
            # Phase 0 ranking signal
            "rrf_score":                round(rrf_score, 6),
            "semantic_rank":            semantic_rank,   # None if not in semantic path
            "bm25_rank":                bm25_rank,       # None if not in keyword path
            # Raw retrieval scores — available for Node 5 and audit
            "bm25_score":               round(bm25_score, 4),
            "mandatory_score":          round(m_score, 4),
            "preferred_score":          round(p_score, 4),
            "experience_relevance":     round(experience_relevance, 4),
            "certification_score":      round(c_score, 4),
            "location_compatibility":   location_comp,
            "work_mode_compatibility":  mode_comp,
            "mandatory_penalty_assigned": penalty_assigned,
            "full_jd_vector_sim":           round(vector_sims["full_jd"],   4),
            "level_vector_sim":             round(vector_sims["level"],     4),
            "mandatory_skills_vector_sim":  round(vector_sims["mandatory"], 4),
            "preferred_skills_vector_sim":  round(vector_sims["preferred"], 4),
            "cert_vector_sim":              round(vector_sims["cert"],      4),
        }
