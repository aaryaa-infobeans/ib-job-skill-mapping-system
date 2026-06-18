"""
Compare composite 5-vector semantic vs single full-profile vector semantic.

For every postman candidate (+ member_id overrides) prints:
  - BM25 rank
  - Semantic rank: 5-vector composite (current pipeline)
  - Semantic rank: single full_jd <=> embedding
  - RRF rank: composite
  - RRF rank: single-vec
  - Whether each reaches the pipeline cap

Run:
    python scripts/dev/check_rag_rank_single_vec.py
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

POSTMAN_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'tests', 'postman')
POOL = 300
TOP  = 10

W_FULL_JD   = settings.rag_weight_full_jd
W_LEVEL     = settings.rag_weight_level
W_MANDATORY = settings.rag_weight_skills_mandatory
W_PREFERRED = settings.rag_weight_skills_preferred
W_CERT      = settings.rag_weight_cert

# Extra one-off candidates: (member_id, title, jd_level, mandatory, preferred, certs, jd_text)
EXTRA_CANDIDATES = [
    {
        "member_id": "10908",
        "title": "ServiceNow Developer",
        "jd_level": "MID",
        "mandatory_skills": ["ServiceNow", "ITSM", "JavaScript", "Dell Boomi", "Salesforce"],
        "preferred_skills": ["Service Portal", "ITIL", "REST API", "HTML", "CSS"],
        "certifications": [
            "Certified Implementation Specialist - IT Service Management",
            "ITIL4 Foundation",
            "Certified System Administrator",
        ],
        "jd_text": (
            "We are seeking a ServiceNow Developer with 2 to 10 years of experience. "
            "Required Certifications: Certified Implementation Specialist - IT Service Management, "
            "ITIL4 Foundation certification, Certified System Administrator. "
            "Good experience in ServiceNow and Salesforce Implementation. "
            "Proficiency in customization, configuration and implementation in ServiceNow and Scripting. "
            "Expertise in ServiceNow and Dell Boomi Integration. "
            "Experience in Service Portal framework. "
            "Configured Salesforce including validation rules, workflows, custom labels, "
            "custom settings, profiles and permissions. "
            "Good knowledge of web development technologies like HTML, CSS and JavaScript."
        ),
    }
]


def embed(agent, text_input: str) -> list:
    if not text_input or not text_input.strip():
        return np.zeros(768).astype(float).tolist()
    return agent.embed_text(text_input).tolist()


def build_bm25_query(mandatory, preferred, certifications):
    def phrase(k):
        k = k.strip()
        return f'"{k}"' if ' ' in k else k
    terms = [phrase(k) for k in mandatory + preferred + certifications if k.strip()]
    return ' OR '.join(terms)


def run_bm25(db, bm25_query):
    if not bm25_query.strip():
        return []
    return db.execute(text('''
        SELECT e.team_member_id,
               COALESCE(tm.designation, '') AS designation,
               paradedb.score(e.id)         AS score
        FROM team_member_embeddings e
        JOIN team_member tm ON tm.team_member_id = e.team_member_id
        WHERE e @@@ paradedb.parse(:q)
          AND tm.is_active = true AND e.embedding IS NOT NULL
        ORDER BY paradedb.score(e.id) DESC
        LIMIT :pool
    '''), {'q': bm25_query, 'pool': POOL}).fetchall()


def run_composite(db, vecs):
    return db.execute(text(f'''
        SELECT e.team_member_id,
               COALESCE(tm.designation, '') AS designation,
               (
                 (e.embedding <=> CAST(:full_jd_vector AS vector))              * {W_FULL_JD} +
                 (COALESCE(e.resume_embedding, e.embedding)
                     <=> CAST(:jd_level_vector AS vector))                      * {W_LEVEL} +
                 (COALESCE(e.skills_embedding, e.embedding)
                     <=> CAST(:mandatory_vector AS vector))                     * {W_MANDATORY} +
                 (COALESCE(e.skills_embedding, e.embedding)
                     <=> CAST(:preferred_vector AS vector))                     * {W_PREFERRED} +
                 (COALESCE(e.certifications_embedding, e.embedding)
                     <=> CAST(:cert_vector AS vector))                          * {W_CERT}
               ) AS dist
        FROM team_member_embeddings e
        JOIN team_member tm ON tm.team_member_id = e.team_member_id
        WHERE tm.is_active = true AND e.embedding IS NOT NULL
        ORDER BY dist ASC
        LIMIT :pool
    '''), {**vecs, 'pool': POOL}).fetchall()


def run_single_vec(db, full_jd_vector: str):
    """Pure full-profile embedding distance — no skill/level specialisation."""
    return db.execute(text('''
        SELECT e.team_member_id,
               COALESCE(tm.designation, '') AS designation,
               (e.embedding <=> CAST(:v AS vector)) AS dist
        FROM team_member_embeddings e
        JOIN team_member tm ON tm.team_member_id = e.team_member_id
        WHERE tm.is_active = true AND e.embedding IS NOT NULL
        ORDER BY dist ASC
        LIMIT :pool
    '''), {'v': full_jd_vector, 'pool': POOL}).fetchall()


def rrf(rows_a, rows_b, k=60):
    scores, desig = {}, {}
    for i, r in enumerate(rows_a, 1):
        scores[r[0]] = scores.get(r[0], 0.0) + 1.0 / (k + i)
        desig[r[0]] = r[1]
    for i, r in enumerate(rows_b, 1):
        scores[r[0]] = scores.get(r[0], 0.0) + 1.0 / (k + i)
        desig.setdefault(r[0], r[1])
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def find_rank(rows_or_pairs, mid):
    mid = str(mid)
    for i, row in enumerate(rows_or_pairs, 1):
        if str(row[0]) == mid:
            return i
    return None


def process(db, agent, member_id, title, jd_level, mandatory, preferred, certs, jd_text, scenario_letter, cap, results):
    full_jd_input   = f"search_query: {jd_text}" if jd_text else ""
    level_input     = f"Seniority: {jd_level}. Title: {title}." if jd_level and title else full_jd_input
    mandatory_input = f"Required skills: {', '.join(mandatory)}" if mandatory else full_jd_input
    preferred_input = f"Preferred skills: {', '.join(preferred)}" if preferred else full_jd_input
    cert_input      = f"Certifications: {', '.join(certs)}" if certs else full_jd_input

    full_jd_vec = str(embed(agent, full_jd_input))
    vecs = {
        'full_jd_vector':   full_jd_vec,
        'jd_level_vector':  str(embed(agent, level_input)),
        'mandatory_vector': str(embed(agent, mandatory_input)),
        'preferred_vector': str(embed(agent, preferred_input)),
        'cert_vector':      str(embed(agent, cert_input)),
    }

    bm25_q    = build_bm25_query(mandatory, preferred, certs)
    bm25_rows = run_bm25(db, bm25_q)
    comp_rows = run_composite(db, vecs)
    sing_rows = run_single_vec(db, full_jd_vec)

    rrf_comp = rrf(bm25_rows, comp_rows)
    rrf_sing = rrf(bm25_rows, sing_rows)

    bm25_r      = find_rank(bm25_rows, member_id)
    comp_sem_r  = find_rank(comp_rows, member_id)
    sing_sem_r  = find_rank(sing_rows, member_id)
    rrf_comp_r  = find_rank(rrf_comp, member_id)
    rrf_sing_r  = find_rank(rrf_sing, member_id)

    reach_comp = rrf_comp_r is not None and rrf_comp_r <= cap
    reach_sing = rrf_sing_r is not None and rrf_sing_r <= cap

    fmt = lambda x: str(x) if x else 'miss'
    status = lambda ok: 'OK' if ok else 'MISS'

    print(f"\n  {member_id} Sc{scenario_letter}  [{title[:40]}]")
    print(f"  BM25={fmt(bm25_r):<5}  "
          f"Sem(5vec)={fmt(comp_sem_r):<5} RRF(5vec)={fmt(rrf_comp_r):<5} -> {status(reach_comp)}   |   "
          f"Sem(1vec)={fmt(sing_sem_r):<5} RRF(1vec)={fmt(rrf_sing_r):<5} -> {status(reach_sing)}")

    results.append({
        'mid': member_id, 'sc': scenario_letter, 'title': title[:32],
        'bm25': bm25_r,
        'sem5': comp_sem_r, 'rrf5': rrf_comp_r, 'ok5': reach_comp,
        'sem1': sing_sem_r, 'rrf1': rrf_sing_r, 'ok1': reach_sing,
    })


def main():
    cap = settings.rag_final_candidates
    print(f"Composite weights: full_jd={W_FULL_JD} level={W_LEVEL} mandatory={W_MANDATORY} preferred={W_PREFERRED} cert={W_CERT}")
    print(f"Pool={POOL}  RAG cap={cap}")
    print("=" * 100)

    agent   = get_embedding_agent()
    db      = SessionLocal()
    results = []

    # --- Postman candidates ---
    for fpath in sorted(glob.glob(os.path.join(POSTMAN_DIR, 'candidate_*.json'))):
        member_id = os.path.basename(fpath).replace('candidate_', '').replace('_match_scenarios.json', '')
        with open(fpath, encoding='utf-8') as f:
            scenarios = json.load(f)
        for scenario in scenarios:
            if not isinstance(scenario, dict):
                continue
            label = scenario.get('_scenario', '')
            sc    = 'A' if ('A -' in label or '- A' in label or '— A' in label or 'A —' in label or label.strip().startswith('A')) else 'B'
            jd    = scenario.get('job_description', {})
            title = jd.get('title', '')
            jd_level = 'SENIOR' if 'senior' in title.lower() else 'MID'
            process(db, agent, member_id, title, jd_level,
                    jd.get('mandatory_skills', []), jd.get('preferred_skills', []),
                    jd.get('certifications', []), jd.get('jd_text', ''), sc, cap, results)

    # --- Extra one-off candidates ---
    for cfg in EXTRA_CANDIDATES:
        process(db, agent, cfg['member_id'], cfg['title'], cfg['jd_level'],
                cfg['mandatory_skills'], cfg['preferred_skills'],
                cfg['certifications'], cfg['jd_text'], 'A', cap, results)

    db.close()

    # Summary
    print(f"\n{'='*100}")
    print(f"SUMMARY  (cap={cap})   5vec = current composite   1vec = full-profile only")
    print(f"{'='*100}")
    hdr = f"{'Cand':>6} Sc {'Title':<32} {'BM25':>5}  {'Sem5':>5} {'RRF5':>5} St5   {'Sem1':>5} {'RRF1':>5} St1   Delta"
    print(hdr)
    print('-' * len(hdr))
    for r in results:
        f = lambda x: str(x) if x else 'miss'
        s = lambda ok: 'OK  ' if ok else 'MISS'
        # Delta: did single-vec improve, worsen, or stay the same?
        if r['ok5'] == r['ok1']:
            delta = '='
        elif r['ok1'] and not r['ok5']:
            delta = 'BETTER(1vec)'
        else:
            delta = 'WORSE(1vec)'
        print(f"{r['mid']:>6} {r['sc']}  {r['title']:<32} {f(r['bm25']):>5}  "
              f"{f(r['sem5']):>5} {f(r['rrf5']):>5} {s(r['ok5'])}  "
              f"{f(r['sem1']):>5} {f(r['rrf1']):>5} {s(r['ok1'])}  {delta}")


if __name__ == '__main__':
    main()
