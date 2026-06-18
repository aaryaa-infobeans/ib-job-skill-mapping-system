"""
Batch RAG rank checker — runs all candidates from tests/postman/ through
BM25 + semantic + RRF using the current pipeline weights, then reports
each candidate's rank in each layer for their Scenario A (perfect match)
and Scenario B (partial match).

Run:
    python scripts/dev/check_rag_rank_batch.py
"""

import json
import os
import sys
import glob

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import numpy as np
from sqlalchemy import text
from app.db.session import SessionLocal
from app.ai.utils.embedding import get_embedding_agent
from app.settings import settings

POSTMAN_DIR = os.path.join(
    os.path.dirname(__file__), '..', '..', 'tests', 'postman'
)
POOL = 300
TOP  = 20   # how many rows to show in tables before "..."

W_FULL_JD   = settings.rag_weight_full_jd
W_LEVEL     = settings.rag_weight_level
W_MANDATORY = settings.rag_weight_skills_mandatory
W_PREFERRED = settings.rag_weight_skills_preferred
W_CERT      = settings.rag_weight_cert


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def embed(agent, text_input: str) -> list:
    if not text_input or not text_input.strip():
        return np.zeros(768).astype(float).tolist()
    return agent.embed_text(text_input).tolist()


def build_bm25_query(mandatory: list, preferred: list, certifications: list) -> str:
    def phrase(k):
        k = k.strip()
        return f'"{k}"' if ' ' in k else k
    all_terms = [phrase(k) for k in mandatory + preferred + certifications if k.strip()]
    return ' OR '.join(all_terms)


def run_bm25(db, bm25_query: str) -> list:
    if not bm25_query.strip():
        return []
    rows = db.execute(text('''
        SELECT e.team_member_id,
               COALESCE(tm.designation, '') AS designation,
               paradedb.score(e.id)         AS bm25_score
        FROM team_member_embeddings e
        JOIN team_member tm ON tm.team_member_id = e.team_member_id
        WHERE e @@@ paradedb.parse(:q)
          AND tm.is_active = true
          AND e.embedding IS NOT NULL
        ORDER BY paradedb.score(e.id) DESC
        LIMIT :pool
    '''), {'q': bm25_query, 'pool': POOL}).fetchall()
    return rows


def run_semantic(db, vecs: dict) -> list:
    # All 5 query vectors are compared against e.embedding (full-profile) only.
    # Avoids skills_embedding/resume_embedding/certifications_embedding being
    # NULL or built from incomplete DB skill records skewing the composite.
    rows = db.execute(text(f'''
        SELECT e.team_member_id,
               COALESCE(tm.designation, '') AS designation,
               (
                   (e.embedding <=> CAST(:full_jd_vector AS vector))   * {W_FULL_JD} +
                   (e.embedding <=> CAST(:jd_level_vector AS vector))  * {W_LEVEL} +
                   (e.embedding <=> CAST(:mandatory_vector AS vector)) * {W_MANDATORY} +
                   (e.embedding <=> CAST(:preferred_vector AS vector)) * {W_PREFERRED} +
                   (e.embedding <=> CAST(:cert_vector AS vector))      * {W_CERT}
               ) AS composite_distance
        FROM team_member_embeddings e
        JOIN team_member tm ON tm.team_member_id = e.team_member_id
        WHERE tm.is_active = true
          AND e.embedding IS NOT NULL
        ORDER BY composite_distance ASC
        LIMIT :pool
    '''), {**vecs, 'pool': POOL}).fetchall()
    return rows


def compute_rrf(bm25_rows, semantic_rows, k=60) -> list:
    scores, desig = {}, {}
    for i, r in enumerate(semantic_rows, 1):
        scores[r[0]] = scores.get(r[0], 0.0) + 1.0 / (k + i)
        desig[r[0]] = r[1]
    for i, r in enumerate(bm25_rows, 1):
        scores[r[0]] = scores.get(r[0], 0.0) + 1.0 / (k + i)
        desig.setdefault(r[0], r[1])
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def find_rank(rows_or_pairs, member_id: str) -> int | None:
    """Return 1-based rank of member_id or None if not found."""
    mid = str(member_id)
    for i, row in enumerate(rows_or_pairs, 1):
        # row can be a SQLAlchemy Row (row[0]) or a tuple (mid, score)
        row_id = str(row[0])
        if row_id == mid:
            return i
    return None


def build_vecs(agent, jd_text, title, jd_level, mandatory, preferred, certifications):
    full_jd_input   = f"search_query: {jd_text}" if jd_text else ""
    level_input     = (f"Seniority: {jd_level}. Title: {title}." if jd_level and title
                       else full_jd_input)
    mandatory_input = (f"Required skills: {', '.join(mandatory)}" if mandatory else full_jd_input)
    preferred_input = (f"Preferred skills: {', '.join(preferred)}" if preferred else full_jd_input)
    cert_input      = (f"Certifications: {', '.join(certifications)}" if certifications else full_jd_input)
    return {
        'full_jd_vector':   str(embed(agent, full_jd_input)),
        'jd_level_vector':  str(embed(agent, level_input)),
        'mandatory_vector': str(embed(agent, mandatory_input)),
        'preferred_vector': str(embed(agent, preferred_input)),
        'cert_vector':      str(embed(agent, cert_input)),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    cap = settings.rag_final_candidates

    print(f"\nRAG Batch Rank Check")
    print(f"Weights: full_jd={W_FULL_JD}  level={W_LEVEL}  mandatory={W_MANDATORY}  preferred={W_PREFERRED}  cert={W_CERT}")
    print(f"Pool={POOL}  RAG cap={cap}")
    print("=" * 80)

    agent = get_embedding_agent()
    db    = SessionLocal()

    pattern = os.path.join(POSTMAN_DIR, 'candidate_*.json')
    files   = sorted(glob.glob(pattern))

    if not files:
        print(f"No candidate_*.json found in {POSTMAN_DIR}")
        sys.exit(1)

    summary_rows = []  # (member_id, scenario, bm25_rank, sem_rank, rrf_rank, reaches_scoring)

    for fpath in files:
        fname      = os.path.basename(fpath)
        member_id  = fname.replace('candidate_', '').replace('_match_scenarios.json', '')

        with open(fpath, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        # Support both a single scenario object and an array of scenarios
        scenarios = raw if isinstance(raw, list) else [raw]

        for scenario in scenarios:
            if not isinstance(scenario, dict):
                continue
            label     = scenario.get('_scenario', '?')[:70]
            jd        = scenario.get('job_description', {})
            title     = jd.get('title', '')
            mandatory = jd.get('mandatory_skills', [])
            preferred = jd.get('preferred_skills', [])
            certs     = jd.get('certifications', [])
            jd_text   = jd.get('jd_text', '')
            # Infer seniority from title
            jd_level  = 'SENIOR' if 'senior' in title.lower() else ('MID' if 'mid' in title.lower() else 'MID')

            # Determine scenario letter from _scenario field
            scenario_letter = 'A' if '— A' in label or 'A —' in label or label.strip().startswith('A') else 'B'

            print(f"\n{'-'*80}")
            print(f"  Candidate {member_id}  |  Scenario {scenario_letter}: {title}")
            print(f"  Mandatory: {mandatory}")
            print(f"  Preferred: {preferred[:4]}{'...' if len(preferred) > 4 else ''}")

            # BM25
            bm25_q    = build_bm25_query(mandatory, preferred, certs)
            bm25_rows = run_bm25(db, bm25_q)
            bm25_rank = find_rank(bm25_rows, member_id)

            # Semantic
            vecs      = build_vecs(agent, jd_text, title, jd_level, mandatory, preferred, certs)
            sem_rows  = run_semantic(db, vecs)
            sem_rank  = find_rank(sem_rows, member_id)

            # RRF
            rrf_pairs = compute_rrf(bm25_rows, sem_rows)
            rrf_rank  = find_rank(rrf_pairs, member_id)

            reaches   = (rrf_rank is not None and rrf_rank <= cap)
            status    = "PASS (reaches scoring)" if reaches else (
                        f"MISS — RRF rank {rrf_rank or 'not in pool'} > cap {cap}" if rrf_rank else
                        f"MISS — not in merged pool of {len(rrf_pairs)}")

            print(f"  BM25 rank:     {bm25_rank or 'not in pool':<8}  (pool size {len(bm25_rows)})")
            print(f"  Semantic rank: {sem_rank or 'not in pool':<8}  (pool size {len(sem_rows)})")
            print(f"  RRF rank:      {rrf_rank or 'not in pool':<8}  (merged {len(rrf_pairs)} unique)")
            print(f"  --> {status}")

            summary_rows.append({
                'member_id': member_id,
                'scenario': scenario_letter,
                'title': title[:35],
                'bm25': bm25_rank,
                'sem': sem_rank,
                'rrf': rrf_rank,
                'reaches': reaches,
            })

    db.close()

    # Summary table
    print(f"\n{'='*80}")
    print(f"SUMMARY  (RAG cap = {cap})")
    print(f"{'='*80}")
    header = f"{'Cand':>6}  {'Sc':>2}  {'Title':<35}  {'BM25':>5}  {'Sem':>5}  {'RRF':>5}  Status"
    print(header)
    print('-' * len(header))
    for r in summary_rows:
        bm25_s = str(r['bm25']) if r['bm25'] else 'miss'
        sem_s  = str(r['sem'])  if r['sem']  else 'miss'
        rrf_s  = str(r['rrf'])  if r['rrf']  else 'miss'
        status = 'OK' if r['reaches'] else 'MISS'
        print(f"{r['member_id']:>6}  {r['scenario']:>2}  {r['title']:<35}  {bm25_s:>5}  {sem_s:>5}  {rrf_s:>5}  {status}")


if __name__ == '__main__':
    main()
