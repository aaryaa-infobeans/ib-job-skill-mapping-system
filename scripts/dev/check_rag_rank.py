"""
RAG rank checker — shows BM25 and semantic ranks for a given JD.

Uses the SAME 5-vector composite semantic query as the actual pipeline
(full_jd*0.25 + level*0.35 + mandatory*0.20 + preferred*0.10 + cert*0.10)
so results here predict exactly what the pipeline will retrieve.

Edit scripts/dev/check_rag_rank_input.json and run:
    python scripts/dev/check_rag_rank.py
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from sqlalchemy import text
from app.db.session import SessionLocal
from app.ai.utils.embedding import get_embedding_agent
from app.settings import settings

INPUT_FILE = os.path.join(os.path.dirname(__file__), 'check_rag_rank_input.json')

# Same weights as pipeline settings
W_FULL_JD    = settings.rag_weight_full_jd            # 0.25
W_LEVEL      = settings.rag_weight_level               # 0.35
W_MANDATORY  = settings.rag_weight_skills_mandatory    # 0.20
W_PREFERRED  = settings.rag_weight_skills_preferred    # 0.10
W_CERT       = settings.rag_weight_cert                # 0.10


def embed(agent, text_input: str) -> list:
    """Embed text and return as list for SQL binding."""
    import numpy as np
    if not text_input or not text_input.strip():
        return np.zeros(768).astype(float).tolist()
    return agent.embed_text(text_input).tolist()


def build_bm25_query(mandatory: list, preferred: list, certifications: list) -> str:
    """Same logic as pipeline's _build_keyword_strings."""
    def phrase(k):
        k = k.strip()
        return f'"{k}"' if ' ' in k else k

    all_terms = [phrase(k) for k in mandatory + preferred + certifications if k.strip()]
    return ' OR '.join(all_terms)


def run_bm25(db, bm25_query: str, top: int) -> list:
    if not bm25_query.strip():
        return []
    rows = db.execute(text('''
        SELECT
            e.team_member_id,
            COALESCE(tm.designation, '') AS designation,
            paradedb.score(e.id)         AS bm25_score
        FROM team_member_embeddings e
        JOIN team_member tm ON tm.team_member_id = e.team_member_id
        WHERE e @@@ paradedb.parse(:bm25_query)
          AND tm.is_active = true
          AND e.embedding IS NOT NULL
        ORDER BY paradedb.score(e.id) DESC
        LIMIT :top
    '''), {'bm25_query': bm25_query, 'top': top}).fetchall()
    return rows


def run_semantic_composite(db, vecs: dict, top: int, main_embedding_only: bool = False) -> list:
    """
    5-vector composite semantic query.

    main_embedding_only=False (current pipeline):
        Uses specialized embeddings where available:
          level     -> resume_embedding   (COALESCE fallback to embedding)
          mandatory -> skills_embedding   (COALESCE fallback to embedding)
          preferred -> skills_embedding   (COALESCE fallback to embedding)
          cert      -> certifications_embedding (COALESCE fallback to embedding)

    main_embedding_only=True (proposed change):
        Uses e.embedding for all 5 vector comparisons.
        Avoids penalising candidates whose resume/skills/cert sub-embeddings
        don't encode seniority or specialist signals well.
    """
    if main_embedding_only:
        level_expr    = 'e.embedding'
        mand_expr     = 'e.embedding'
        preferred_expr = 'e.embedding'
        cert_expr     = 'e.embedding'
        label = 'PROPOSED (main embedding only)'
    else:
        level_expr    = 'COALESCE(e.resume_embedding, e.embedding)'
        mand_expr     = 'COALESCE(e.skills_embedding, e.embedding)'
        preferred_expr = 'COALESCE(e.skills_embedding, e.embedding)'
        cert_expr     = 'COALESCE(e.certifications_embedding, e.embedding)'
        label = 'CURRENT (specialized embeddings)'

    rows = db.execute(text(f'''
        SELECT
            e.team_member_id,
            COALESCE(tm.designation, '')                                         AS designation,
            (
                (e.embedding <=> CAST(:full_jd_vector AS vector))                * {W_FULL_JD} +
                ({level_expr} <=> CAST(:jd_level_vector AS vector))              * {W_LEVEL} +
                ({mand_expr}  <=> CAST(:mandatory_vector AS vector))             * {W_MANDATORY} +
                ({preferred_expr} <=> CAST(:preferred_vector AS vector))         * {W_PREFERRED} +
                ({cert_expr}  <=> CAST(:cert_vector AS vector))                  * {W_CERT}
            ) AS composite_distance
        FROM team_member_embeddings e
        JOIN team_member tm ON tm.team_member_id = e.team_member_id
        WHERE tm.is_active = true
          AND e.embedding IS NOT NULL
        ORDER BY composite_distance ASC
        LIMIT :top
    '''), {**vecs, 'top': top}).fetchall()
    return rows, label


def print_results(rows, score_label: str, member_id: str, top: int):
    found = False
    for i, r in enumerate(rows, 1):
        is_target = str(r[0]) == str(member_id) if member_id else False
        if is_target:
            found = True
        if i <= top or is_target:
            marker = '  <---' if is_target else ''
            print(f'  Rank {i:>4}: id={r[0]:<8} {score_label}={float(r[2]):.4f}  [{r[1]}]{marker}')

    if member_id and not found:
        print(f'  Member {member_id} not found in top {len(rows)} results')


def print_bm25(db, mandatory, preferred, certifications, member_id, top, pool):
    bm25_query = build_bm25_query(mandatory, preferred, certifications)
    print('=' * 60)
    print(f'BM25 query: {bm25_query}')
    print(f'(includes {len(mandatory)} mandatory, {len(preferred)} preferred, {len(certifications)} cert terms)')
    print('=' * 60)
    if not bm25_query:
        print('No skills provided — BM25 skipped')
        return []
    rows = run_bm25(db, bm25_query, pool)
    print(f'BM25 pool size: {len(rows)}')
    print_results(rows, 'score', member_id, top)
    return rows


def print_semantic(db, vecs: dict, member_id, top, pool, main_embedding_only: bool = False):
    rows, label = run_semantic_composite(db, vecs, pool, main_embedding_only=main_embedding_only)
    print()
    print('=' * 60)
    print(f'Semantic [{label}]')
    print(f'  weights: full_jd={W_FULL_JD} level={W_LEVEL} mandatory={W_MANDATORY} preferred={W_PREFERRED} cert={W_CERT}')
    print('=' * 60)
    print(f'Semantic pool size: {len(rows)}')
    print_results(rows, 'dist ', member_id, top)
    return rows


def print_rrf(bm25_rows, semantic_rows, member_id, top):
    print()
    print('=' * 60)
    print('RRF combined rank (k=60) — matches pipeline _filter_and_rank()')
    print('=' * 60)
    k = 60
    scores, desig = {}, {}
    for i, r in enumerate(semantic_rows, 1):
        scores[r[0]] = scores.get(r[0], 0.0) + 1.0 / (k + i)
        desig[r[0]]  = r[1]
    for i, r in enumerate(bm25_rows, 1):
        scores[r[0]] = scores.get(r[0], 0.0) + 1.0 / (k + i)
        desig.setdefault(r[0], r[1])

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    found  = False
    for i, (mid, rrf) in enumerate(ranked, 1):
        is_target = str(mid) == str(member_id) if member_id else False
        if is_target:
            found = True
        if i <= top or is_target:
            marker = '  <---' if is_target else ''
            print(f'  Rank {i:>4}: id={mid:<8} rrf={rrf:.6f}  [{desig.get(mid, "")}]{marker}')
    if member_id and not found:
        print(f'  Member {member_id} not in merged pool of {len(ranked)}')

    rag_cap = settings.rag_final_candidates
    print(f'\n  Pipeline cap: top {rag_cap} by RRF reach Node 5 scoring')
    if member_id:
        rank_in_merged = next((i+1 for i, (mid, _) in enumerate(ranked) if str(mid) == str(member_id)), None)
        if rank_in_merged:
            if rank_in_merged <= rag_cap:
                print(f'  Member {member_id} at RRF rank {rank_in_merged} -> WILL reach scoring (within top {rag_cap})')
            else:
                print(f'  Member {member_id} at RRF rank {rank_in_merged} -> WILL NOT reach scoring organically (cap={rag_cap}), needs target_member_ids force-injection')


def main():
    with open(INPUT_FILE, 'r') as f:
        cfg = json.load(f)

    mandatory      = cfg.get('mandatory_skills', [])
    preferred      = cfg.get('preferred_skills', [])
    certifications = cfg.get('certifications', [])
    jd_text        = cfg.get('jd_text', '').strip()
    mandatory_text = cfg.get('mandatory_text', ' '.join(mandatory))
    preferred_text = cfg.get('preferred_text', ' '.join(preferred))
    cert_text      = cfg.get('cert_text', ' '.join(certifications))
    member_id      = str(cfg.get('member_id', '')).strip()
    top            = cfg.get('top', 15)
    pool           = cfg.get('pool', 150)

    if not mandatory and not preferred and not jd_text:
        print('ERROR: provide at least one of mandatory_skills, preferred_skills, or jd_text in the JSON')
        sys.exit(1)

    # Build text inputs exactly as EmbeddingAgent._build_texts() does in the pipeline:
    # - full_jd:   "search_query: {jd_text}"
    # - jd_level:  "Seniority: {level}. Title: {title}." (falls back to full_jd if not given)
    # - mandatory: "Required skills: {skills}"
    # - preferred: "Preferred skills: {skills}"
    # - cert:      "Certifications: {certs}"
    title        = cfg.get('title', '')
    jd_level     = cfg.get('jd_level', '')     # e.g. "MID", "SENIOR", "JUNIOR"

    full_jd_input   = f"search_query: {jd_text}" if jd_text else ""
    level_input     = (f"Seniority: {jd_level}. Title: {title}." if jd_level and title
                       else (f"Seniority: {jd_level}." if jd_level
                             else full_jd_input))  # fallback to full_jd
    mandatory_input = (f"Required skills: {', '.join(mandatory)}" if mandatory else full_jd_input)
    preferred_input = (f"Preferred skills: {', '.join(preferred)}" if preferred else full_jd_input)
    cert_input      = (f"Certifications: {', '.join(certifications)}" if certifications else full_jd_input)

    print('Generating embeddings...')
    agent = get_embedding_agent()
    vecs = {
        'full_jd_vector':   str(embed(agent, full_jd_input)),
        'jd_level_vector':  str(embed(agent, level_input)),
        'mandatory_vector': str(embed(agent, mandatory_input)),
        'preferred_vector': str(embed(agent, preferred_input)),
        'cert_vector':      str(embed(agent, cert_input)),
    }
    print(f'  full_jd:   "{full_jd_input[:70]}"')
    print(f'  level:     "{level_input[:70]}"')
    print(f'  mandatory: "{mandatory_input[:70]}"')
    print(f'  preferred: "{preferred_input[:70]}"')
    print(f'  cert:      "{cert_input[:70]}"')

    db = SessionLocal()
    bm25_rows = print_bm25(db, mandatory, preferred, certifications, member_id, top, pool)

    print('\n' + '#' * 60)
    print('# CURRENT pipeline (specialized embeddings per vector)')
    print('#' * 60)
    sem_current = print_semantic(db, vecs, member_id, top, pool, main_embedding_only=False)
    if bm25_rows or sem_current:
        print_rrf(bm25_rows, sem_current, member_id, top)

    print('\n' + '#' * 60)
    print('# PROPOSED change (main embedding for all vectors)')
    print('#' * 60)
    sem_proposed = print_semantic(db, vecs, member_id, top, pool, main_embedding_only=True)
    if bm25_rows or sem_proposed:
        print_rrf(bm25_rows, sem_proposed, member_id, top)

    db.close()


if __name__ == '__main__':
    main()
