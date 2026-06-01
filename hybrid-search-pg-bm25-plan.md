# True Hybrid Search — pg_bm25 + RRF & Team DB Sync

> **Implementation complete.** For the final implemented state see `HYBRID_SEARCH_AND_SCORE_IMPROVEMENT.md` § 2.
> This document is the original pre-implementation plan. Two architectural decisions evolved
> during implementation and differ from what is described below:
> - The `bm25_scores` dict + 13-col trim approach was replaced by a LEFT JOIN BM25 subquery
>   embedded directly in SQL #1 — both SQLs now return 14 cols with `bm25_score` as col 14.
> - The weighted `_compute_total_score()` formula was deleted and replaced by Reciprocal Rank
>   Fusion (RRF). `_filter_and_rank()` no longer applies a similarity threshold.

---

## Part A — Team DB Sync System

### Problem
Colleagues need the same database state (schema + data). Currently there is no automated way
for a teammate to go from zero to a working DB that matches yours.

### Two sources of truth
| What | Mechanism | Who acts |
|------|-----------|----------|
| **Schema** (tables, indexes, extensions) | Alembic migrations committed to git | Teammates run `alembic upgrade head` after `git pull` |
| **Data** (members, skills, embeddings) | SQL dump `db/ib_job_skill_mapping_latest.sql` committed to git | Teammates run `make db-reset` after `git pull` |

### Files to change
- `Makefile` — add two targets: `db-reset` and `db-dump`

### `db-reset` — teammate runs this once to get your DB state
```makefile
db-reset:
	@echo "--- Tearing down old DB volume ---"
	docker compose down -v
	docker compose up -d postgres
	@echo "--- Waiting for postgres ---"
	@until docker compose exec -T postgres pg_isready -U user -q; do sleep 2; done
	docker compose cp db/ib_job_skill_mapping_latest.sql postgres:/tmp/dump.sql
	docker compose exec -T postgres sh -c 'pg_restore -U user -d ib_job_skill_mapping --clean --if-exists /tmp/dump.sql; echo done'
	@echo "--- Applying migrations ---"
	alembic upgrade head
	@echo "--- DB reset complete ---"
```

### `db-dump` — you run this before committing a data snapshot
```makefile
db-dump:
	@echo "--- Dumping current DB ---"
	docker compose exec -T postgres sh -c 'pg_dump -U user -Fc ib_job_skill_mapping' > db/ib_job_skill_mapping_latest.sql
	@echo "--- Dump saved to db/ib_job_skill_mapping_latest.sql (git add + commit it) ---"
```

### Team workflow going forward
```
# Schema change (new index, column, etc.):
  You:      write Alembic migration → git commit → git push
  Teammate: git pull → alembic upgrade head

# Data snapshot (new seed data, bulk import, etc.):
  You:      make db-dump → git add db/ib_job_skill_mapping_latest.sql → git commit → git push
  Teammate: git pull → make db-reset   (wipes their volume, restores your dump, runs migrations)
```

### Note on first-time setup (ParadeDB image change)
Because we switched from `pgvector/pgvector:pg17` to `paradedb/paradedb:latest` (PG18),
`make db-reset` handles this automatically — it does `docker compose down -v` first, which
removes the old PG17 data directory before starting the new PG18 container.

---

## Part B — Item 2: True Hybrid Search with pg_bm25 (ParadeDB)

---

## Context

Item 1 (skill_ontology synonym expansion) is complete (commit d844d56). This plan implements
true hybrid search: two independent retrieval paths (semantic vector + BM25 keyword) whose
results merge into one pool, scored and filtered to the top-40 for Node 5.

**Why pg_bm25 (ParadeDB) instead of Python `rank_bm25`:**
`rank_bm25` would compute BM25 AFTER a boolean `tsvector` pre-filter fetches rows — the
boolean filter, not BM25, would determine who enters the pool. That is not true BM25 retrieval.
`pg_bm25` (ParadeDB `pg_search` extension) creates an inverted BM25 index in PostgreSQL.
At query time, BM25 scores from the full corpus are computed inside the DB and returned as a
column — BM25 itself determines who enters the keyword candidate pool.

**Same table, no duplication:** The BM25 index is created ON `team_member_embeddings` directly,
alongside the existing IVFFlat and B-tree indexes. No separate table is needed.

**Docker:** Current image is `pgvector/pgvector:pg17`. ParadeDB's image
`paradedb/paradedb:latest` bundles both pgvector and pg_search. One line change in
`docker-compose.yml`. The `docker-compose.test.yml` (uses `postgres:15-alpine`) is left
unchanged — tests use a mock/skip strategy for pg_bm25.

**IDF accuracy:** pg_bm25 computes BM25 over ALL rows in the table at index time — full
corpus IDF, not a windowed approximation. This is what Items 2+3 of the rollout plan aimed
for. Combining them into one implementation.

---

## Environment Matrix

| Environment | PostgreSQL setup | ParadeDB installation |
|-------------|-----------------|----------------------|
| Team (Docker) | `pgvector/pgvector:pg17` in `docker-compose.yml` | Swap image to `paradedb/paradedb:latest` — done |
| Local dev (Windows, non-Docker) | Native Windows PostgreSQL | ParadeDB has **no native Windows installer**. Must use one of the options below. |

### Local dev options (Windows)

**Recommended — DB in Docker, app runs natively:**
Run only the database container locally. Your FastAPI app stays on Windows.
```
docker compose up db          # starts paradedb/paradedb:latest on port 5433
```
`.env` `DATABASE_URL` already points to `localhost:5433` — no change needed.
This gives full pg_bm25 parity with the team and avoids WSL2 complexity.

**Alternative — WSL2:**
Install PostgreSQL + ParadeDB `.deb` inside WSL2. Point `.env` at the WSL2 host IP.
More complex setup; only worthwhile if you already use WSL2 for other tooling.

**Not viable:**
Building pg_search from source on Windows-native PostgreSQL is unsupported and fragile.

---

## Files to Change

| File | Change |
|------|--------|
| `docker-compose.yml` | Image: `pgvector/pgvector:pg17` → `paradedb/paradedb:latest` |
| `alembic/versions/20260519_01_add_pg_bm25_index.py` | New migration: enable pg_search + create BM25 index |
| `src/app/settings.py` | Add `rag_keyword_fetch_limit: int = 500` |
| `src/app/ai/utils/rag_retrieval.py` | Replace ts_rank with pg_bm25 query; dual-path retrieval |

---

## Current State

| Change | Status |
|--------|--------|
| `docker-compose.yml` image: `paradedb/paradedb:latest`, volume: `/var/lib/postgresql` | ✅ Done |
| `_compute_bm25_scores()` method | ✅ Not present (never needed — pg_bm25 provides scores from DB) |
| `_build_sql()` lines 264–271: `ts_rank(...) AS keyword_score` still present | ❌ Pending |
| Alembic migration for pg_search extension + BM25 index | ❌ Pending |
| `settings.py`: `rag_keyword_fetch_limit` | ❌ Pending |
| `_build_keyword_sql()` (pg_bm25 `@@@` version) | ❌ Pending |
| `_merge_result_sets()` static method | ❌ Pending |
| `_build_filters()` lines 179–183: add `bm25_query` + `keyword_fetch_limit` | ❌ Pending |
| `execute()` lines 68–84: dual-path retrieval | ❌ Pending |
| `_build_structured_candidate()` line 339: `keyword_score` → `profile_text` unpack | ❌ Pending |
| `_build_structured_candidate()` line 371: `kw_norm` → `bm25_scores.get(...)` | ❌ Pending |
| `_compute_total_score()` lines 409–442: `kw_norm` → `bm25_score` | ❌ Pending |
| `_build_breakdown()` lines 444–474: param + key rename | ❌ Pending |

---

## Architecture: Before vs After

```
BEFORE (single path):
  execute()
    SQL #1: ORDER BY full_jd_distance ASC → top 100
    ts_rank → kw_norm (TF-only, not BM25)
    filter+rank → top 40 → Node 5

AFTER (true hybrid — pg_bm25 index in DB):
  execute()
    SQL #1 (semantic):  ORDER BY composite_distance ASC → top 100
                        composite = full_jd×0.25 + level×0.35 + mandatory×0.20
                                  + preferred×0.10 + cert×0.10
                        col 13 = profile_text (was ts_rank keyword_score)
    SQL #2 (keyword):   WHERE e @@@ paradedb.parse(:bm25_query)
                        ORDER BY paradedb.score(e.id) DESC
                        LIMIT :keyword_fetch_limit (500 safety cap)
                        col 13 = profile_text, col 14 = bm25_score (from DB index)
    extract bm25_scores dict from keyword_rows col 14 → {team_member_id: score}
    trim keyword_rows to 13 cols → merge with semantic_rows (dedup by team_member_id)
    _build_structured_candidate(): bm25_score = bm25_scores.get(team_member_id, 0.0)
    filter+rank → top 40 → Node 5
```

---

## All Pending Changes (in implementation order)

---

### Step 0 — `docker-compose.yml`: swap PostgreSQL image

**File:** `docker-compose.yml`

```yaml
# Before:
image: pgvector/pgvector:pg17

# After:
image: paradedb/paradedb:latest
```

`paradedb/paradedb:latest` ships with both `pgvector` AND `pg_search` pre-installed.
All existing vector functionality is unaffected. `docker-compose.test.yml` is NOT changed.

---

### Step 1 — New Alembic migration: enable pg_search + create BM25 index

**New file:** `alembic/versions/20260519_01_add_pg_bm25_index.py`

```python
"""Add pg_bm25 (ParadeDB) index on team_member_embeddings for true BM25 keyword search.

Revision ID: 20260519_01
Revises: 20260403_01
Create Date: 2026-05-19
"""
from alembic import op

revision = '20260519_01'
down_revision = '20260403_01'  # set to most recent migration ID
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_search;")
    op.execute("""
        CALL paradedb.create_bm25(
            index_name  => 'idx_tme_bm25',
            table_name  => 'team_member_embeddings',
            key_field   => 'id',
            text_fields => paradedb.field('skills_text') ||
                           paradedb.field('certifications_text') ||
                           paradedb.field('profile_text')
        );
    """)


def downgrade() -> None:
    op.execute("CALL paradedb.drop_bm25('idx_tme_bm25');")
    op.execute("DROP EXTENSION IF EXISTS pg_search;")
```

**Why `key_field = 'id'`:** ParadeDB requires the key field to be the table's primary key
(`id` UUID). `team_member_id` is a String(50) FK — using `id` avoids type compatibility issues.

**Why index all three text columns:** The mandatory WHERE clause already searches across
`skills_text || certifications_text || profile_text`. The BM25 index mirrors this exactly.

**Previous revision ID:** Set `down_revision` to the ID of `20260403_01_widen_profile_type.py`
(the current most-recent migration). Find it by reading the `revision` variable in that file.

---

### Step 2 — `settings.py`: add `rag_keyword_fetch_limit`

After the `rag_sql_limit: int = 100` line, add:

```python
rag_keyword_fetch_limit: int = 500  # safety cap for BM25 keyword SQL (SQL #2)
```

---

### Step 3A — `_build_sql()`: replace `ts_rank` with `profile_text` + composite ORDER BY

Two changes in `_build_sql()`:

**Change 1 — SELECT col 13:** Replace the `ts_rank(...)  AS keyword_score` block with `profile_text`:

```sql
-- Before (lines 264–271):
                ts_rank(
                    to_tsvector('english',
                        coalesce(e.skills_text, '') || ' ' ||
                        coalesce(e.certifications_text, '') || ' ' ||
                        coalesce(e.profile_text, '')
                    ),
                    websearch_to_tsquery('english', :kw_query)
                )                                                  AS keyword_score

-- After:
                COALESCE(e.profile_text, '')                       AS profile_text
```

Column 13 type changes from `float` → `str`. SQL #1 now has 13 columns.

**Change 2 — ORDER BY:** Replace `ORDER BY full_jd_distance ASC` with a weighted composite
of all 5 vector distances using the same weights as scoring. This aligns retrieval priority
with scoring priority (level vector at 35% now influences who gets fetched, not just scored).

For ~1,500 members the IVFFlat index speed advantage is irrelevant — a full table scan on
1,500 rows with 5 distance computations takes milliseconds.

```sql
-- Before:
            ORDER BY full_jd_distance ASC

-- After:
            ORDER BY (
                (e.embedding <-> CAST(:full_jd_vector AS vector))
                    * {settings.rag_weight_full_jd} +
                (COALESCE(e.resume_embedding, e.embedding) <-> CAST(:jd_level_vector AS vector))
                    * {settings.rag_weight_level} +
                (COALESCE(e.skills_embedding, e.embedding) <-> CAST(:mandatory_vector AS vector))
                    * {settings.rag_weight_skills_mandatory} +
                (COALESCE(e.skills_embedding, e.embedding) <-> CAST(:preferred_vector AS vector))
                    * {settings.rag_weight_skills_preferred} +
                (COALESCE(e.certifications_embedding, e.embedding) <-> CAST(:cert_vector AS vector))
                    * {settings.rag_weight_cert}
            ) ASC
```

The weights are injected via Python f-string (safe — they are float settings values, not user
input). Changing weights in `settings.py` automatically changes retrieval priority.

---

### Step 3B — Remove `_compute_bm25_scores()` method

Delete the entire `_compute_bm25_scores()` method (lines 135–175). pg_bm25 returns BM25
scores from the DB index — Python-side BM25 computation is no longer needed.

---

### Step 3C — Add `_build_keyword_sql()` (pg_bm25 version)

Add after `_build_sql()`. Returns **14 columns**: same 13 as SQL #1 + `bm25_score` as col 14.

```python
def _build_keyword_sql(self, filters: List[str]):
    """SQL #2: pg_bm25 keyword retrieval path.

    Uses ParadeDB =@@@ operator for true Okapi BM25 from the DB index.
    Returns 14 columns: 13 matching _build_sql() + bm25_score as col 14.
    Ordered by BM25 score DESC so the top-ranked keyword candidates come first.
    """
    return text("""
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

            COALESCE(e.profile_text, '')                                         AS profile_text,

            paradedb.score(e.id)                                                 AS bm25_score

        FROM team_member_embeddings e
        LEFT JOIN team_member tm ON tm.team_member_id = e.team_member_id
        WHERE e @@@ paradedb.parse(:bm25_query)
        ORDER BY paradedb.score(e.id) DESC
        LIMIT :keyword_fetch_limit
    """)
```

**Note on `paradedb.parse(:bm25_query)`:** The `bm25_query` param is built from expanded
mandatory + preferred skill terms (same source as the existing `kw_query`, different param
name to distinguish). Format: `"python" OR "react.js" OR "aws"` — ParadeDB's parse function
accepts Lucene-like syntax and searches across all indexed fields (`skills_text`,
`certifications_text`, `profile_text`).

---

### Step 3D — Add `_merge_result_sets()` (static method)

Add before `_filter_and_rank()`. Accepts 13-col semantic rows and 13-col trimmed keyword
rows (bm25_score is extracted separately before calling this).

```python
@staticmethod
def _merge_result_sets(semantic_rows: list, keyword_rows: list) -> list:
    """Union semantic and keyword rows, deduplicating by team_member_id (col 0).

    Semantic rows take priority for duplicate candidates (vector distances are
    identical but semantic ordering reflects full_jd_distance ranking).
    Keyword-only rows appended after all semantic rows.
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
```

---

### Step 3E — `_build_filters()`: add `keyword_fetch_limit` + `bm25_query` params

In `_build_filters()` (lines ~221–225):

```python
# Before:
        params: Dict[str, Any] = {
            **vectors,
            "kw_query":  keyword_query_str,
            "sql_limit": settings.rag_sql_limit,
        }

# After:
        params: Dict[str, Any] = {
            **vectors,
            "kw_query":            keyword_query_str,
            "bm25_query":          keyword_query_str,   # same source, separate param for pg_bm25
            "sql_limit":           settings.rag_sql_limit,
            "keyword_fetch_limit": settings.rag_keyword_fetch_limit,
        }
```

---

### Step 3F — `execute()`: dual-path retrieval with pg_bm25

Replace the single SQL execution block (lines ~68–84):

```python
            # Semantic path: vector-ordered top-N
            sql = self._build_sql(filters)
            semantic_rows = self.db.execute(sql, params).fetchall()
            self.logger.info(
                f"RAG SQL (semantic) returned {len(semantic_rows)} rows | "
                f"kw_query={params.get('kw_query', '')!r}"
            )

            # Keyword path: pg_bm25 index — BM25 does retrieval, not a boolean pre-filter
            keyword_rows_raw: list = []
            bm25_scores: Dict[str, float] = {}
            if keyword_query_str.strip():
                kw_sql = self._build_keyword_sql(filters)
                keyword_rows_raw = self.db.execute(kw_sql, params).fetchall()
                # Extract bm25_score (col 14, index 13) before trimming to 13-col schema
                bm25_scores = {
                    row[0]: round(float(row[13]), 4)
                    for row in keyword_rows_raw
                }
                self.logger.info(
                    f"RAG SQL (keyword/pg_bm25) returned {len(keyword_rows_raw)} rows "
                    f"(cap={settings.rag_keyword_fetch_limit})"
                )

            # Trim keyword rows to 13 cols (drop bm25_score col) so merge schema matches
            keyword_rows = [tuple(row)[:13] for row in keyword_rows_raw]

            merged_rows = self._merge_result_sets(semantic_rows, keyword_rows)
            self.logger.info(
                f"Merged pool: {len(merged_rows)} unique candidates "
                f"(semantic={len(semantic_rows)}, keyword={len(keyword_rows)}, "
                f"keyword-only={len(merged_rows) - len(semantic_rows)})"
            )

            candidates = [
                self._build_structured_candidate(
                    row, bm25_scores,
                    mandatory_skills, preferred_skills,
                    certifications, locations, work_modes, experience_req,
                    expanded_mandatory, expanded_preferred,
                )
                for row in merged_rows
            ]
```

---

### Step 3G — `_build_structured_candidate()`: 4 sub-changes

**G1 — Add `bm25_scores` as 2nd parameter:**
```python
def _build_structured_candidate(
    self, row,
    bm25_scores: Dict[str, float],
    mandatory_skills, preferred_skills, ...
```

**G2 — Fix row unpacking: col 13 is now `profile_text` (str), not `keyword_score` (float):**
```python
# Before:
    cert_distance, keyword_score,
) = row

# After:
    cert_distance, profile_text,
) = row
```

**G3 — Replace `kw_norm` computation:**
```python
# Before (delete):
kw_norm = round(float(keyword_score) / (0.03 + float(keyword_score)), 4) if float(keyword_score) > 0 else 0.0

# After (add):
bm25_score = bm25_scores.get(team_member_id, 0.0)
# Semantic-only candidates get 0.0; keyword-path candidates get their pg_bm25 score.
```

**G4 — Replace `kw_norm` → `bm25_score` in all call sites + add `profile_text` to RAGCandidate:**

`_compute_total_score()` call: `kw_norm` → `bm25_score`
`_build_breakdown()` call: `kw_norm` → `bm25_score`
RAGCandidate constructor: add `profile_text=profile_text`

---

### Step 3H — `_compute_total_score()`: rename parameter `kw_norm` → `bm25_score`

Parameter rename only. Formula and weights unchanged.

---

### Step 3I — `_build_breakdown()`: rename parameter + output key

```python
# Before:
def _build_breakdown(total_score, kw_norm, ...):
    return { ..., "keyword_score": round(kw_norm, 4), ... }

# After:
def _build_breakdown(total_score, bm25_score, ...):
    return { ..., "bm25_score": round(bm25_score, 4), ... }
```

---

## Summary Table

| Step | File | Change |
|------|------|--------|
| 0 | `docker-compose.yml` | Image: `pgvector/pgvector:pg17` → `paradedb/paradedb:latest` |
| 1 | `alembic/versions/20260519_01_add_pg_bm25_index.py` | New file: CREATE EXTENSION pg_search + CALL paradedb.create_bm25() |
| 2 | `settings.py` | Add `rag_keyword_fetch_limit: int = 500` |
| 3A | `rag_retrieval.py` `_build_sql()` | Replace `ts_rank AS keyword_score` → `profile_text` |
| 3B | `rag_retrieval.py` | Delete `_compute_bm25_scores()` method (replaced by pg_bm25) |
| 3C | `rag_retrieval.py` | Add `_build_keyword_sql()` using `=@@@` pg_bm25 operator, 14 cols |
| 3D | `rag_retrieval.py` | Add `_merge_result_sets()` static method |
| 3E | `rag_retrieval.py` `_build_filters()` | Add `bm25_query` + `keyword_fetch_limit` params |
| 3F | `rag_retrieval.py` `execute()` | Dual-path retrieval; extract bm25_scores from col 14; trim + merge |
| 3G | `rag_retrieval.py` `_build_structured_candidate()` | Signature, row unpack, bm25_score lookup, profile_text on RAGCandidate |
| 3H | `rag_retrieval.py` `_compute_total_score()` | `kw_norm` → `bm25_score` (rename only) |
| 3I | `rag_retrieval.py` `_build_breakdown()` | `kw_norm` → `bm25_score`; `"keyword_score"` → `"bm25_score"` |

---

## Edge Cases

| Case | Behaviour |
|------|-----------|
| `keyword_query_str` is empty | Skip SQL #2; `bm25_scores = {}`; all candidates get `bm25_score = 0.0` |
| pg_search extension not installed | Migration fails at `CREATE EXTENSION` — clear error, fix docker image first |
| Candidate in both paths | Semantic row kept (13-col); bm25_score comes from `bm25_scores` dict (keyword path value) |
| Candidate in keyword path only | Keyword row (trimmed to 13-col) appended to merged pool; bm25_score from dict |
| Candidate in semantic path only | 13-col row kept; `bm25_score = 0.0` (not in keyword path) |
| pg_bm25 query parse error (bad bm25_query) | ParadeDB raises SQL error — wrap kw_sql execution in try/except, log warning, use empty keyword_rows |
| `keyword_fetch_limit` hit (500 rows returned) | Top-500 by BM25 score enter merge; lower-ranked BM25 candidates missed — acceptable trade-off |

---

## What Does NOT Change

- `_build_keyword_strings()` — output still feeds both WHERE clause `:kw_query` and `:bm25_query`
- `_filter_and_rank()` — unchanged
- `_compute_total_score()` formula/weights — parameter rename only
- `RAGCandidate` dataclass in `models.py` — `profile_text: Optional[str] = None` already declared
- `docker-compose.test.yml` — unchanged (`postgres:15-alpine`; unit tests do not hit pg_bm25)

---

## Verification Plan

1. **Container startup** — `docker compose up db` with new image. Run `psql -c "SELECT * FROM pg_extension WHERE extname = 'pg_search';"` — must return one row.

2. **Migration** — `alembic upgrade head`. Check `\d team_member_embeddings` in psql — new BM25 index `idx_tme_bm25` should appear.

3. **Smoke test** — run one requisition end-to-end:
   - Logs show `RAG SQL (semantic)` count + `RAG SQL (keyword/pg_bm25)` count + merged count with `keyword-only=N`
   - `phase0_score_breakdown` contains `"bm25_score"` key (not `"keyword_score"`)
   - `RAGCandidate.profile_text` is non-empty for candidates with profile data

4. **Recall test** — find a candidate whose `skills_text` or `profile_text` contains exact query keywords but whose embedding is generic. Confirm `keyword-only` count > 0 in logs.

5. **Empty keyword edge case** — requisition with no mandatory/preferred/cert skills. Confirm only semantic SQL runs, no crash, all `bm25_score = 0.0`.

6. **Unit tests** — `pytest tests/unit/` — no existing test references `keyword_score` or `kw_norm` (confirmed by codebase search). No test updates needed for existing tests.

7. **BM25 score sanity** — for a candidate appearing in both paths, confirm their `bm25_score > 0.0` (keyword dict value used, not the 0.0 semantic default).

---

## Post-Implementation Filter Improvements

Changes made after the pg_bm25 implementation was live, in response to over-filtering issues observed in testing.

### A. `filter_ids` parameter removed from `execute()`

The `filter_ids: Optional[List[str]]` parameter was removed from `RAGRetrievalAgent.execute()`. It was intended to pin specific candidates into the retrieval pool but was never correctly wired — `initial_filter_ids` was read from state in `rag_retrieval_node` but then silently dropped in the agent. The parameter is removed entirely; target-member pinning is now handled via `target_member_ids` in the graph state (see API schema overrides section in HYBRID_SEARCH_AND_SCORE_IMPROVEMENT.md).

### B. Location filter — conditional on JD accepting remote

**Old behaviour:** location SQL filter applied unconditionally for every JD that specified locations.

**Problem:** A JD listing `["Bangalore", "Remote"]` would still filter candidates by city — excluding WFH candidates who should qualify.

**New behaviour:** Location filter is skipped entirely when the JD accepts remote work:

```python
jd_accepts_remote = any(
    _WORK_MODE_ALIASES.get(m.strip().lower()) == "wfh"
    for m in work_modes
) or any(
    loc.strip().lower() in _VIRTUAL_LOCATION_TERMS
    for loc in locations
)
if not jd_accepts_remote:
    self._add_location_filters(filters, params, locations)
```

When `jd_accepts_remote` is True, all candidates pass the location gate; fit is handled downstream by `_calculate_location_score()` in scoring.

### C. Work mode filter rework

**Old behaviour:** Generated `CAST(tm.work_type AS text) ILIKE :mode_N` OR clauses for each mapped mode. If the JD accepted remote (`"wfh"` in mapped modes), the filter still ran and could produce confusing results.

**New behaviour:** Work mode is no longer a hard SQL exclusion filter in the general case. Only WFH-only candidates are excluded when the JD requires physical presence:

```python
mapped_modes = {_WORK_MODE_ALIASES[m.strip().lower()] for m in work_modes if ...}

if "wfh" in mapped_modes:
    return  # JD accepts WFH → every candidate can fulfil it, no SQL filter

# JD requires physical presence — exclude WFH-only candidates
filters.append("CAST(tm.work_type AS text) NOT ILIKE :wfh_exclude")
params["wfh_exclude"] = "wfh"
```

`hybrid` candidates pass (they can fulfil in-office days). Only `wfh`-only candidates are excluded.

### D. Experience filter — max_m removed as a hard SQL filter

**Old behaviour:** When JD specified both `min` and `max` experience, SQL used `BETWEEN` (or two one-sided filters). Inverted ranges (`min > max`) were silently swapped.

**Problem:** Over-qualified candidates (senior engineers) were excluded from mid-level JDs. The BETWEEN clause was too strict — experience over-qualification is a soft concern, not a hard one.

**New behaviour:** Only `min_m` is applied as a hard floor. `max_m` is intentionally ignored in SQL; the scoring layer's `_exp_relevance()` applies a graduated penalty for over-experience. Inverted-range repair is also removed.

```python
# Only apply minimum experience floor
if min_m is not None:
    filters.append("tm.experience_in_months >= :min_m")
    params["min_m"] = min_m
# max_m intentionally not applied — over-qualified candidates are valid, scoring penalises gently
```

### E. `exp_max_plausible_months` moved to settings

The constant `_EXP_MAX_PLAUSIBLE_MONTHS = 600` (50 years — values above this are treated as invalid JD input) was hardcoded. It is now read from settings:

```python
# settings.py
exp_max_plausible_months: int = 600   # default: 50 years

# rag_retrieval.py
_EXP_MAX_PLAUSIBLE_MONTHS: int = _settings.exp_max_plausible_months
```

### Files Modified

| File | Change |
|---|---|
| [src/app/ai/utils/rag_retrieval.py](src/app/ai/utils/rag_retrieval.py) | Remove `filter_ids` param; make location filter conditional on `jd_accepts_remote`; rework work mode filter to exclude WFH only when JD requires physical presence; drop `max_m` SQL filter; move `_EXP_MAX_PLAUSIBLE_MONTHS` to settings |
| [src/app/ai/agents/rag_retrieval.py](src/app/ai/agents/rag_retrieval.py) | Remove `initial_filter_ids` variable and `filter_ids=` kwarg in agent call |
| [src/app/settings.py](src/app/settings.py) | Add `exp_max_plausible_months: int = 600` |

### Edge Cases

| Case | Behaviour |
|---|---|
| JD locations = `["Bangalore", "Remote"]` | `jd_accepts_remote=True` → location filter skipped; all candidates retrieved |
| JD locations = `["Bangalore"]` only | Location filter applied; non-Bangalore candidates excluded at SQL |
| JD work_modes = `["Remote", "Hybrid"]` | `"wfh"` in mapped_modes → work mode filter skipped |
| JD work_modes = `["WFO"]` | Filter added: excludes WFH-only candidates |
| JD `max_experience = 60m`, candidate has `120m` | Candidate retrieved; scoring `_exp_relevance()` applies graduated penalty |
