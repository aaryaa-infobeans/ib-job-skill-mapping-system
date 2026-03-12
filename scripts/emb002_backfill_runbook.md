# CR-EMB-002 Backfill & Validation Runbook (TASK-EMB-051..060)

## Pre-Backfill Snapshot SQL (TASK-EMB-051)

```sql
-- Capture baseline before backfill
CREATE TABLE IF NOT EXISTS _emb002_pre_backfill_snapshot AS
SELECT
    team_member_id,
    embedding,
    profile_text,
    pii_scrubbed,
    scrubbed_at,
    created_at
FROM team_member_embeddings;

-- Record row count
SELECT count(*) AS pre_backfill_count FROM team_member_embeddings;

-- Confirm all new columns are NULL before backfill
SELECT count(*) AS already_populated
FROM team_member_embeddings
WHERE resume_embedding IS NOT NULL
   OR skills_embedding IS NOT NULL
   OR certifications_embedding IS NOT NULL;
-- Expected: 0
```

## DDL Migration Execution (TASK-EMB-052)

```bash
# Verify current HEAD before migration
alembic current

# Apply migration
alembic upgrade head

# Verify 10 new columns present
psql $DATABASE_URL -c "
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'team_member_embeddings'
ORDER BY column_name;
"
# Must include: certifications_embedding, certifications_text, content_hash,
#               embedding_model, embedding_updated_at, resume_embedding,
#               resume_fetched_at, resume_text, skills_embedding, skills_text

# AC-9: Downgrade + re-upgrade (idempotency)
alembic downgrade bca284b2d901
alembic upgrade head
```

## embed --force Backfill (TASK-EMB-053)

```bash
# Full backfill of all 39 members
python -m app.cron.main embed --force

# Monitor progress via structured logs:
# grep '"metric":"embedding_batch_total_duration_seconds"' server.log
# grep '"metric":"resume_fetch_success_total"' server.log | python -c "import sys,json; [print(json.loads(l)) for l in sys.stdin]"
```

## Validation SQL — AC-1..AC-4 (TASK-EMB-054)

```sql
-- AC-1: resume_embedding populated for members with profile_url
SELECT count(*) AS members_with_resume_emb
FROM team_member_embeddings tme
JOIN team_member tm ON tme.team_member_id = tm.team_member_id
WHERE tm.profile_url IS NOT NULL
  AND tme.resume_embedding IS NOT NULL;
-- Expected: > 0

-- AC-2: skills_embedding populated for members with skills
SELECT count(*) AS members_with_skills_emb
FROM team_member_embeddings tme
WHERE tme.skills_embedding IS NOT NULL;
-- Expected: > 0

-- AC-3: certifications_embedding populated
SELECT count(*) AS members_with_certs_emb
FROM team_member_embeddings tme
WHERE tme.certifications_embedding IS NOT NULL;

-- AC-4: embedding_model column default value
SELECT DISTINCT embedding_model FROM team_member_embeddings;
-- Expected: ('embedding-gemma-300m',)

-- AC-5: No raw PII in resume_text (manual spot-check 5 members)
SELECT team_member_id, left(resume_text, 200) AS resume_sample
FROM team_member_embeddings
WHERE resume_text IS NOT NULL
LIMIT 5;
-- Manual: verify no emails, phone numbers, names

-- AC-6: Content hash populated (enables skip on second run)
SELECT count(*) AS has_content_hash
FROM team_member_embeddings
WHERE content_hash IS NOT NULL;

-- AC-7: Weighted average spot-check (5 members)
SELECT
    team_member_id,
    embedding,
    resume_embedding,
    skills_embedding,
    certifications_embedding
FROM team_member_embeddings
WHERE resume_embedding IS NOT NULL
  AND skills_embedding IS NOT NULL
  AND certifications_embedding IS NOT NULL
LIMIT 5;
-- Verify in Python: np.allclose(embedding, normalize(0.5*R + 0.3*S + 0.2*C), atol=1e-4)

-- AC-9: Migration idempotency (see DDL section above)
```

## Full Test Suite (TASK-EMB-055)

```bash
pytest tests/ -v --timeout=120 2>&1 | tee test_results.log

# Key test targets:
# tests/mcp_servers/test_gdrive_server.py   (10 tests)
# tests/ai/test_gemma_embedding.py           (7 tests)
# tests/cron/test_mcp_client.py              (6 tests)
# tests/cron/test_text_assembler.py          (7 tests)
# tests/cron/test_embedding_processor.py    (15 tests)
# tests/ai/test_rag_retrieval.py             (4 tests)
```

## Match Quality Comparison (TASK-EMB-056 / R1)

```bash
# After backfill, compare top-3 matches vs baseline_matches_req1.json
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:9001/api/v1/jd-skill-mapping/${TEST_REQ_ID_1}/matches \
  | python - << 'EOF'
import json, sys
new = json.load(sys.stdin)
baseline = json.load(open("tests/fixtures/rag/baseline_matches_req1.json"))
new_top3 = [m["team_member_id"] for m in new["matches"][:3]]
base_top3 = [m["team_member_id"] for m in baseline["matches"][:3]]
overlap = len(set(new_top3) & set(base_top3))
print(f"Top-3 overlap: {overlap}/3 (R1: must be >= 2)")
EOF
```

## R8: Graceful Skip Validation (TASK-EMB-057)

```bash
# Verify members with no profile_url are processed without error
python -m app.cron.main embed --force 2>&1 \
  | grep '"status":"skipped"'
# Members with no profile_url should show reason=no_content or skipped

# Confirm no EXIT_FATAL (2) when some members have no resume
echo "Exit code: $?"
```

## Performance Benchmark (TASK-EMB-058)

```bash
# Time the full embed phase (39 members, AC-11: < 5 min)
time python -m app.cron.main embed

# Expected:
#   real    < 5m00s    (AC-11: 39 members in < 300s)
#   exit 0
```

## Rollback Procedure (Phase 5)

```sql
-- RESTORE pre-backfill state if needed
UPDATE team_member_embeddings tme
SET
    resume_embedding = NULL,
    skills_embedding = NULL,
    certifications_embedding = NULL,
    resume_text = NULL,
    skills_text = NULL,
    certifications_text = NULL,
    content_hash = NULL,
    embedding_updated_at = NULL
WHERE team_member_id IN (
    SELECT team_member_id FROM _emb002_pre_backfill_snapshot
);

-- Restore legacy embeddings from snapshot (if modified)
UPDATE team_member_embeddings tme
SET embedding = snap.embedding
FROM _emb002_pre_backfill_snapshot snap
WHERE tme.team_member_id = snap.team_member_id;
```

## GATE-5: Production Readiness Checklist (TASK-EMB-060)

- [ ] AC-1: resume_embedding populated for all members with profile_url
- [ ] AC-2: skills_embedding populated for all members with skills
- [ ] AC-3: certifications_embedding populated where applicable
- [ ] AC-4: embedding_model = 'embedding-gemma-300m' for all rows
- [ ] AC-5: No raw PII in resume_text (manual spot-check 5 members)
- [ ] AC-6: Second run skip rate >= 80% (hash_match)
- [ ] AC-7: Legacy embedding = weighted average to 4 decimal places (5 members)
- [ ] AC-8: RAG /matches endpoint returns results using multi-vector path
- [ ] AC-9: Alembic upgrade -> downgrade -> upgrade passes
- [ ] AC-10: Full test suite passes (pytest tests/ -v)
- [ ] AC-11: Embed phase for 39 members completes in < 5 minutes
- [ ] AC-12: tools/list returns read_document, search_files, get_file_metadata
- [ ] AC-13: Real Google Doc fetched (deferred to staging with real SA key)
- [ ] AC-14: GOOGLE_SERVICE_ACCOUNT_FILE not in cron process os.environ
- [ ] AC-15: BrokenPipeError -> returns None, cron exits PARTIAL (1) not FATAL (2)
