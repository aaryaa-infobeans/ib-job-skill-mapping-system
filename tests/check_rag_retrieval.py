#!/usr/bin/env python3
"""
RAG retrieval diagnostic — shows the rank of each expected candidate across
all test scenarios in tests/postman/, without calling the HTTP API.

Checks per scenario:
  1. Hard filter  — is_active, location, experience (same logic as rag_retrieval.py)
  2. BM25 rank    — where the expected candidate sits in keyword retrieval
  3. Semantic rank — where the candidate sits in vector retrieval
  4. Top-N list   — who actually appears in the top N

Usage (from project root):
  python tests/check_rag_retrieval.py
  python tests/check_rag_retrieval.py --top 30   # wider search window (default 20)
  python tests/check_rag_retrieval.py --no-semantic  # skip embedding (fast, BM25-only)
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

try:
    from sqlalchemy import create_engine, text as sql
    from app.settings import settings
    DB_URL = settings.get_database_url()
except Exception as exc:
    print(f"[ERROR] Could not load app settings: {exc}")
    sys.exit(1)

POSTMAN_DIR = ROOT / "tests" / "postman"

VIRTUAL_LOCATIONS = frozenset({
    "remote", "wfh", "work from home", "work-from-home", "work_from_home",
    "anywhere", "global", "virtual", "online", "n/a", "na", "any",
})
WORK_MODE_MAP: Dict[str, str] = {
    "remote": "wfh", "wfh": "wfh", "work from home": "wfh", "work-from-home": "wfh",
    "wfo": "wfo", "office": "wfo", "onsite": "wfo", "on-site": "wfo", "in-office": "wfo",
    "hybrid": "hybrid", "flexible": "hybrid", "mixed": "hybrid",
}

# ── embedding (lazy-loaded) ───────────────────────────────────────────────────

_embedder = None

def _get_embedder():
    global _embedder
    if _embedder is None:
        try:
            from app.ai.utils.gemma_embedding import GemmaEmbeddingAgent
            model_name = (
                settings.embedding_model
                or settings.gemma_model_path
                or settings.embedding_model_name
                or "google/embeddinggemma-300m"
            )
            device = getattr(settings, "embedding_device", "cpu")
            print(f"[INFO] Loading embedding model: {model_name} on {device} ...")
            _embedder = GemmaEmbeddingAgent(device=device, model_name=model_name)
            print("[INFO] Embedding model loaded.")
        except Exception as exc:
            print(f"[WARN] Could not load embedding model: {exc}")
            _embedder = False  # sentinel: tried and failed
    return _embedder if _embedder else None


def embed(text: str) -> Optional[List[float]]:
    agent = _get_embedder()
    if agent is None:
        return None
    try:
        return agent.embed_text(text).tolist()
    except Exception as exc:
        print(f"[WARN] Embedding failed: {exc}")
        return None

# ── scenario loading ─────────────────────────────────────────────────────────

def load_scenarios() -> List[Dict]:
    out = []
    for f in sorted(POSTMAN_DIR.glob("candidate_*.json")):
        m = re.match(r"candidate_(\d+)_", f.name)
        if not m:
            continue
        cid = m.group(1)
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[WARN] Cannot parse {f.name}: {exc}")
            continue
        for idx, s in enumerate(data):
            out.append({**s, "_cid": cid, "_file": f.name, "_idx": idx})
    return out

# ── JD helpers ───────────────────────────────────────────────────────────────

def _accepts_remote(jd: Dict) -> bool:
    modes = [WORK_MODE_MAP.get(m.strip().lower()) for m in jd.get("work_mode", [])]
    locs  = [l.strip().lower() for l in jd.get("location", [])]
    return "wfh" in modes or any(l in VIRTUAL_LOCATIONS for l in locs)

def _requires_onsite(jd: Dict) -> bool:
    modes = [WORK_MODE_MAP.get(m.strip().lower()) for m in jd.get("work_mode", [])]
    modes = [m for m in modes if m]
    return bool(modes) and "wfh" not in modes

def _physical_locs(jd: Dict) -> List[str]:
    return [l for l in jd.get("location", []) if l.strip().lower() not in VIRTUAL_LOCATIONS]

# ── DB helpers ────────────────────────────────────────────────────────────────

def get_candidate_info(conn, cid: str) -> Optional[Dict]:
    row = conn.execute(sql("""
        SELECT is_active,
               COALESCE(base_location, '') AS base_location,
               COALESCE(CAST(work_type AS text), 'hybrid') AS work_type,
               experience_in_months,
               COALESCE(designation, '') AS designation
        FROM team_member
        WHERE team_member_id = :cid
    """), {"cid": cid}).fetchone()
    if row is None:
        return None
    return {
        "is_active": row.is_active,
        "location": row.base_location,
        "work_type": row.work_type,
        "exp_months": row.experience_in_months,
        "designation": row.designation,
    }


def check_hard_filter(info: Optional[Dict], jd: Dict) -> Tuple[bool, str]:
    if info is None:
        return False, "NOT IN DB"
    if not info["is_active"]:
        return False, "is_active=FALSE"
    # Location filter: skipped entirely if JD accepts remote/WFH.
    # Work mode: NOT a hard filter in rag_retrieval.py — removed to match actual RAG behaviour.
    if not _accepts_remote(jd):
        phys = _physical_locs(jd)
        if phys and not any(p.lower() in info["location"].lower() for p in phys):
            return False, f"LOCATION: '{info['location']}' not in {phys}"
    return True, "PASS"


def get_db_skills(conn, cid: str) -> List[str]:
    rows = conn.execute(sql("""
        SELECT sm.skill_name
        FROM team_member_skill tms
        JOIN skill_master sm ON sm.skill_id = tms.skill_id
        WHERE tms.team_member_id = :cid AND tms.is_deleted = false
    """), {"cid": cid}).fetchall()
    return [r.skill_name for r in rows]


def bm25_top_n(conn, mandatory: List[str], preferred: List[str], top_n: int) -> List[Dict]:
    """Return top-N BM25 candidates (mandatory + preferred keywords)."""
    all_kw = mandatory + preferred
    if not all_kw:
        return []

    def _phrase(k):
        k = k.strip()
        return f'"{k}"' if " " in k else k

    query = " OR ".join(_phrase(k) for k in all_kw if k.strip())
    try:
        rows = conn.execute(sql("""
            SELECT e.team_member_id,
                   COALESCE(tm.designation, '') AS designation,
                   COALESCE(tm.base_location, '') AS location,
                   paradedb.score(e.id) AS score
            FROM team_member_embeddings e
            JOIN team_member tm ON tm.team_member_id = e.team_member_id
            WHERE e @@@ paradedb.parse(:q)
              AND e.embedding IS NOT NULL
              AND tm.is_active = true
            ORDER BY score DESC
            LIMIT :n
        """), {"q": query, "n": top_n}).fetchall()
        return [
            {"rank": i + 1, "cid": r.team_member_id, "designation": r.designation,
             "location": r.location, "score": round(r.score, 2)}
            for i, r in enumerate(rows)
        ]
    except Exception as exc:
        return [{"error": str(exc)}]


def semantic_top_n(conn, jd_text: str, mandatory_text: str, top_n: int) -> List[Dict]:
    """Run pgvector semantic search. Returns top-N by composite distance."""
    full_vec = embed(jd_text)
    if full_vec is None:
        return [{"error": "embedding model unavailable"}]
    mand_vec = embed(mandatory_text) if mandatory_text.strip() else full_vec

    # Mirror the composite ordering used in rag_retrieval._build_sql():
    # full_jd * weight_full + mandatory * weight_mandatory + preferred * weight_preferred
    # For simplicity use a 2-vector blend: 0.4 full_jd + 0.6 mandatory_skills
    try:
        rows = conn.execute(sql("""
            SELECT
                e.team_member_id,
                COALESCE(tm.designation, '') AS designation,
                COALESCE(tm.base_location, '') AS location,
                (
                    (e.embedding <-> CAST(:full_jd AS vector)) * 0.4
                    + (COALESCE(e.skills_embedding, e.embedding) <-> CAST(:mand AS vector)) * 0.6
                ) AS distance
            FROM team_member_embeddings e
            JOIN team_member tm ON tm.team_member_id = e.team_member_id
            WHERE e.embedding IS NOT NULL
              AND tm.is_active = true
            ORDER BY distance ASC
            LIMIT :n
        """), {"full_jd": full_vec, "mand": mand_vec, "n": top_n}).fetchall()
        return [
            {"rank": i + 1, "cid": r.team_member_id, "designation": r.designation,
             "location": r.location, "distance": round(float(r.distance), 4)}
            for i, r in enumerate(rows)
        ]
    except Exception as exc:
        return [{"error": str(exc)}]


def db_skill_top_n(conn, mandatory: List[str], top_n: int) -> List[Dict]:
    """Return top-N candidates by count of mandatory skills present in DB."""
    if not mandatory:
        return []
    like_cases = " + ".join(
        f"CASE WHEN EXISTS (SELECT 1 FROM team_member_skill tms2 JOIN skill_master sm2 ON sm2.skill_id=tms2.skill_id "
        f"WHERE tms2.team_member_id=tms.team_member_id AND sm2.skill_name ILIKE :sk{i} AND tms2.is_deleted=false) "
        f"THEN 1 ELSE 0 END"
        for i, _ in enumerate(mandatory)
    )
    params = {f"sk{i}": ms for i, ms in enumerate(mandatory)}
    params["n"] = top_n
    try:
        rows = conn.execute(sql(f"""
            SELECT DISTINCT tms.team_member_id,
                   COALESCE(tm.designation, '') AS designation,
                   COALESCE(tm.base_location, '') AS location,
                   ({like_cases}) AS match_count
            FROM team_member_skill tms
            JOIN team_member tm ON tm.team_member_id = tms.team_member_id
            WHERE tm.is_active = true
            ORDER BY match_count DESC
            LIMIT :n
        """), params).fetchall()
        return [
            {"rank": i + 1, "cid": r.team_member_id, "designation": r.designation,
             "location": r.location, "match_count": r.match_count}
            for i, r in enumerate(rows)
        ]
    except Exception as exc:
        return [{"error": str(exc)}]


# ── reporting ─────────────────────────────────────────────────────────────────

SEP  = "-" * 120
SEP2 = "=" * 120

def _find_rank(results: List[Dict], cid: str) -> Optional[int]:
    for r in results:
        if str(r.get("cid", "")) == str(cid):
            return r["rank"]
    return None


def main(top_n: int = 20, skip_semantic: bool = False) -> None:
    engine = create_engine(DB_URL, echo=False)
    scenarios = load_scenarios()

    # Pre-load embedding model (unless skipped)
    if not skip_semantic:
        _get_embedder()

    semantic_window = min(top_n * 10, 500)  # wider window for semantic — candidates can be far down

    print(f"\nLoaded {len(scenarios)} scenarios  |  BM25/semantic search window: top {top_n} / {semantic_window}")
    if skip_semantic:
        print("Semantic search: SKIPPED (--no-semantic)")
    print(SEP2)

    summary_rows = []

    with engine.connect() as conn:
        for s in scenarios:
            cid       = s["_cid"]
            fname     = s["_file"]
            jd        = s.get("job_description", {})
            label     = s.get("_scenario", f"Scenario {s['_idx']}")
            mandatory = jd.get("mandatory_skills", [])
            preferred = jd.get("preferred_skills", [])
            jd_text   = jd.get("jd_text", " ".join(mandatory + preferred))
            mand_text = ", ".join(mandatory)

            info = get_candidate_info(conn, cid)
            filter_pass, filter_reason = check_hard_filter(info, jd)
            cand_skills = get_db_skills(conn, cid)

            def has_skill(ms):
                ml = ms.lower()
                return any(ml in cs.lower() or cs.lower() in ml for cs in cand_skills)

            db_hit  = [ms for ms in mandatory if has_skill(ms)]
            db_miss = [ms for ms in mandatory if not has_skill(ms)]

            # BM25 top-N (mandatory + preferred, same as real RAG)
            bm25_results = bm25_top_n(conn, mandatory, preferred, top_n)
            bm25_rank    = _find_rank(bm25_results, cid)

            # Semantic top-N
            if skip_semantic:
                sem_results = []
                sem_rank    = None
            else:
                sem_results = semantic_top_n(conn, jd_text, mand_text, semantic_window)
                sem_rank    = _find_rank(sem_results, cid)

            # DB-skill rank
            skill_results = db_skill_top_n(conn, mandatory, top_n)
            skill_rank    = _find_rank(skill_results, cid)

            print()
            print(f"  File     : {fname}   candidate={cid}")
            print(f"  Scenario : {label}")
            print(f"  JD       : {jd.get('title','')}  |  mandatory={mandatory}")

            if info:
                print(f"  Profile  : {info['designation']}  loc={info['location']}  "
                      f"mode={info['work_type']}  exp={info['exp_months']}m")

            fstatus = "PASS" if filter_pass else f"FAIL ({filter_reason})"
            print(f"  Filter   : {fstatus}")

            db_ratio = f"{len(db_hit)}/{len(mandatory)}"
            print(f"  DB skills: {db_ratio} matched={db_hit}  missing={db_miss}")

            # BM25 result
            if bm25_results and "error" in bm25_results[0]:
                print(f"  BM25     : ERROR - {bm25_results[0]['error']}")
                bm25_str = "ERROR"
            elif bm25_rank:
                print(f"  BM25     : rank {bm25_rank}/{top_n} (candidate IS in top {top_n})")
                bm25_str = f"rank {bm25_rank}"
            else:
                print(f"  BM25     : NOT in top {top_n}")
                bm25_str = f"NOT in top {top_n}"

            # Semantic result
            if skip_semantic:
                sem_str = "skipped"
            elif sem_results and "error" in sem_results[0]:
                print(f"  Semantic : ERROR - {sem_results[0]['error']}")
                sem_str = "ERROR"
            elif sem_rank:
                print(f"  Semantic : rank {sem_rank}/{semantic_window} (candidate IS in top {semantic_window})")
                sem_str = f"rank {sem_rank}"
            else:
                print(f"  Semantic : NOT in top {semantic_window}")
                sem_str = f"NOT in top {semantic_window}"

            skill_str = f"rank {skill_rank}" if skill_rank else f"NOT in top {top_n}"
            print(f"  DB-skill : {skill_str} (by mandatory skill count)")

            # Show top-5 BM25 competitors
            if bm25_results and "error" not in bm25_results[0]:
                print(f"  Top-5 BM25:")
                for r in bm25_results[:5]:
                    marker = " <<< TARGET" if str(r["cid"]) == str(cid) else ""
                    print(f"    #{r['rank']:>2}  {r['cid']:<6}  score={r['score']:.2f}"
                          f"  {r['designation'][:38]:<38}  {r['location']}{marker}")
                if bm25_rank and bm25_rank > 5:
                    tgt = next((r for r in bm25_results if str(r["cid"]) == str(cid)), None)
                    if tgt:
                        print(f"    ...")
                        print(f"    #{tgt['rank']:>2}  {tgt['cid']:<6}  score={tgt['score']:.2f}"
                              f"  {tgt['designation'][:38]:<38}  {tgt['location']}  <<< TARGET")

            # Show top-5 Semantic competitors
            if not skip_semantic and sem_results and "error" not in sem_results[0]:
                print(f"  Top-5 Semantic:")
                for r in sem_results[:5]:
                    marker = " <<< TARGET" if str(r["cid"]) == str(cid) else ""
                    print(f"    #{r['rank']:>2}  {r['cid']:<6}  dist={r['distance']:.4f}"
                          f"  {r['designation'][:38]:<38}  {r['location']}{marker}")
                if sem_rank and sem_rank > 5:
                    tgt = next((r for r in sem_results if str(r["cid"]) == str(cid)), None)
                    if tgt:
                        print(f"    ...")
                        print(f"    #{tgt['rank']:>2}  {tgt['cid']:<6}  dist={tgt['distance']:.4f}"
                              f"  {tgt['designation'][:38]:<38}  {tgt['location']}  <<< TARGET")

            print(SEP)

            summary_rows.append({
                "file": fname, "cid": cid,
                "filter": "PASS" if filter_pass else "FAIL",
                "db": f"{len(db_hit)}/{len(mandatory)}",
                "bm25_rank": bm25_str,
                "sem_rank": sem_str,
                "skill_rank": skill_str,
                "flag": (
                    "FILTERED" if not filter_pass
                    else "0 DB skills" if not db_hit
                    else "not in BM25" if "NOT in" in bm25_str
                    else ""
                ),
            })

    # Summary table
    print()
    print(SEP2)
    print(f"SUMMARY  (bm25_window={top_n}, semantic_window={semantic_window})")
    print(SEP2)
    print(f"{'File':<44} {'CID':<6} {'Fltr':<5} {'DB':^5} {'BM25 rank':<18} {'Semantic rank':<20} {'DB-skill rank':<18} Note")
    print(SEP)
    for r in summary_rows:
        flag = f"<< {r['flag']}" if r["flag"] else ""
        print(f"{r['file']:<44} {r['cid']:<6} {r['filter']:<5} {r['db']:^5} "
              f"{r['bm25_rank']:<18} {r['sem_rank']:<20} {r['skill_rank']:<18} {flag}")
    print(SEP2)

    counts = {
        "total": len(summary_rows),
        "filtered": sum(1 for r in summary_rows if r["filter"] == "FAIL"),
        "no_db_skills": sum(1 for r in summary_rows if r["db"].startswith("0/")),
        "bm25_missed": sum(1 for r in summary_rows if "NOT in" in r["bm25_rank"]),
        "sem_missed": sum(1 for r in summary_rows if "NOT in" in r["sem_rank"]),
    }
    print(f"\nTotal scenarios : {counts['total']}")
    print(f"Hard-filtered   : {counts['filtered']}")
    print(f"Zero DB skills  : {counts['no_db_skills']}")
    print(f"BM25-missed     : {counts['bm25_missed']}  (not in top {top_n} BM25)")
    if not skip_semantic:
        print(f"Semantic-missed : {counts['sem_missed']}  (not in top {semantic_window} semantic)")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=20,
                        help="BM25 search depth (default: 20); semantic uses 10x this value")
    parser.add_argument("--no-semantic", action="store_true",
                        help="Skip semantic search (faster, BM25 only)")
    args = parser.parse_args()
    main(top_n=args.top, skip_semantic=args.no_semantic)
