# Refactor Analysis — src/app/ai/
**Date:** 2026-05-07
**Scope:** `src/app/ai/` (agents/, utils/, root module files)
**Mode:** Analysis only — no code changes made
**Baseline:** Test suite blocked (trulens_eval module missing; tests cannot load)

---

## Phase 0 — Baseline

### Test Suite
**Status: BLOCKED**

```
ModuleNotFoundError: No module named 'trulens_eval'
```

Import chain: `tests/conftest.py` → `app.main` → `app.ai.graph_executor` → `app.ai.graph` → `app.ai.utils.llm_client` → `trulens_eval.tru_custom_app`

`trulens-eval 2.7.2` is listed in `requirements.txt` but the module is not resolvable in the active environment. Fix the environment before applying any changes.

### Codebase Research
Read and current: `docs/architecture/codebase-research.md`

---

## Phase 1 — Duplication Report

```
Code block duplicates:       2 found
Parallel data structures:    1 found (window calculation with behavioral gap)
Redundant utility agents:    4 found (all dead code — see Phase 2)
Unused data models:          2 found (dead — see Phase 2)
Stale __init__.py exports:   4 entries
```

### DUPLICATE-001 — `metrics` dict literal
**Type:** Exact 5-line block  
**Appears in:**
- `src/app/ai/graph_executor.py:196-201`
- `src/app/ai/resumption.py:213-218`

**Diff:** Identical — same 4 keys, same state key lookups:
```python
metrics = {
    "total_evaluated": current_state.get("total_evaluated", 0),
    "total_qualified": current_state.get("total_qualified", 0),
    "token_count": current_state.get("cumulative_tokens", 0),
    "cost_usd": current_state.get("cumulative_cost_usd", 0.0),
}
```
**Risk to unify:** LOW  
**Verdict:** Only 2 callsites — below the 3x threshold for extracting a new helper. Note it, leave it.

---

### DUPLICATE-002 — Availability window calculation (near-duplicate, behavioral difference)
**Type:** Near-exact function with divergent date math  
**Appears in:**
- `src/app/ai/availability.py:11-43` — `calculate_requisition_window()` — uses `timedelta(days=30 * months)`, handles string/datetime input parsing
- `src/app/ai/agents/candidate_availability.py:106-109` — `calculate_window()` — uses `dateutil.relativedelta(months=months)` (calendar months)

**Diff:** Different duration math — 30-day-month approximation vs true calendar months. The two endpoints produce different end-dates for the same inputs.  
**Risk to unify:** HIGH — unifying without deciding which math is correct is a behavior change.  
**Verdict:** Skipped. Flag as inconsistency (see Flagged Items).

---

### DUPLICATE-003 — Checkpoint state construction (intentionally different)
**Type:** Similar structure, different shape  
**Appears in:**
- `src/app/ai/graph_executor.py:131-142` — "fat" checkpoint (all pipeline state fields for every node)
- `src/app/ai/resumption.py:160-185` — "lean" per-node checkpoint (only node-specific outputs)

**Verdict:** Not a duplicate — the difference is load-bearing for recovery. `graph_executor` writes enough state for any node to resume from; `resumption` writes only the minimum for audit. Do not unify.

---

## Phase 2 — Dead Code Report

```
Unused classes:      4 (all high-confidence)
Unused data models:  2 (RankedCandidate, RankedCandidateList)
Stale exports:       4 entries in utils/__init__.py
```

### DEAD-001 — `utils/validation.py` — `ValidationAgent`
**Lines:** 92  
**Callsites outside own file:** 0  
**Exported from `utils/__init__.py`:** Yes (via `ValidationResult` — but no one imports it from there)  
**Superseded by:** `agents/requisition_validation.py` (standalone function used inside `requisition_parsing_node`)  
**Safe to remove:** YES — also remove its `ValidationResult` export from `utils/__init__.py` (see DEAD-006 for caution)

---

### DEAD-002 — `utils/normalizer.py` — `NormalizerAgent`
**Lines:** 143  
**Callsites outside own file:** 0  
**Superseded by:** `agents/skill_normalization.py` (`skill_normalization_node`)  
**Safe to remove:** YES

---

### DEAD-003 — `utils/ranking.py` — `RankingAgent`
**Lines:** 103  
**Callsites outside own file:** 0  
**Superseded by:** `agents/result_aggregation.py` (`result_aggregation_node`)  
**Safe to remove:** YES

---

### DEAD-004 — `utils/requisition_parser.py` — `RequisitionParserAgent`
**Lines:** 98  
**Callsites outside own file:** 0  
**Superseded by:** `agents/requisition_parsing.py` (`requisition_parsing_node`)  
**Safe to remove:** YES

---

### DEAD-005 — `utils/models.py::RankedCandidate` + `RankedCandidateList`
**Lines:** ~15  
**Only referenced in:** `utils/ranking.py` (DEAD-003) and `utils/__init__.py` (exports)  
**Safe to remove:** YES — remove from `models.py` and remove export lines from `utils/__init__.py`

---

### DEAD-006 — `utils/models.py::ValidationResult` *(low-confidence — flag for manual review)*
**Lines:** ~5  
**Only referenced in:** `utils/validation.py` (DEAD-001) and `utils/__init__.py`  
**Risk:** Might be imported by tests outside the `src/app/ai/` scope  
**Verification command:**
```bash
grep -r "ValidationResult" tests/
```
**Safe to auto-remove:** NO — verify manually first.

---

### Stale `utils/__init__.py` exports (remove with dead code)
Remove these lines once the dead files are deleted:
- `RankedCandidate` import and `__all__` entry
- `RankedCandidateList` import and `__all__` entry
- `ValidationResult` import and `__all__` entry (only after DEAD-006 verified)

---

## Phase 3 — Complexity Report

All complex functions below are flagged only — not auto-simplified. Complexity is inherent to domain logic.

| File | Lines | Issue | Action |
|---|---|---|---|
| `utils/scoring.py` | 460 | Role-specific weight tables, two-stage gates, family penalty system | Leave — domain complexity |
| `agents/skill_normalization.py` | 382 | LLM path + deterministic fallback + fuzzy matching + ontology expansion | Leave — domain complexity |
| `agents/matching_scoring.py` | 307 | Multi-stage scoring + AI confidence override + PII token filtering | Contains PERF-001 |
| `agents/explanation_generation.py` | 302 | LLM call → validate → retry → template fallback | Well-structured — leave |

### Recurring pattern — NOT a complexity issue
`state["error_message"] = None` reset + `except: state["error_message"] = ...` appears in all 7 active agent nodes. This is enforced by the GraphState contract and the fail-fast conditional edge design in `graph.py`. It cannot be extracted into a wrapper without changing node signatures, which would break LangGraph's streaming and checkpoint behaviour.

---

## Phase 4 — Performance Report

### PERF-001 (HIGH IMPACT) — N+5 query pattern in `agents/matching_scoring.py:124-165`

For each team member in the evaluation loop, the node executes 5 separate DB queries:

| Line | Query | Table |
|---|---|---|
| 128 | `.filter(team_member_id == ...)` | `TeamMemberSkill` |
| 134 | `.filter(team_member_id == ...)` | `TeamMemberSkillCertification` |
| 142 | `.filter(team_member_id == ...)` | `TeamMemberEmbedding` |
| 149 | JOIN `.filter(team_member_id == ...)` | `SkillMaster` × `TeamMemberSkill` |
| 159 | via `evaluate_availability()` | `TeamMemberAllocation` |

**Current cost:** 5N queries (at default RAG top_k=10: 50 queries per node execution)  
**Target cost:** 5 batch queries regardless of N

**Safe fix — no behavior change:**
Before the `for member in team_members:` loop, run 5 batch queries using `.filter(team_member_id.in_(team_member_ids))` and build `dict[team_member_id → data]` lookups. Replace per-member queries inside the loop with dict lookups.

The returned data is identical — fetched in bulk instead of one-by-one.

**Risk:** LOW — additive change to query strategy, same rows returned  
**Impact:** O(5N) → O(5) queries per node. At N=10: ~45 fewer DB round-trips per requisition

---

## Flagged for Human Review

These are not refactor items — they require a decision before any action.

### FLAG-001 — Bug: `candidate_availability.py` router session leak + wrong LangGraph API
**File:** `src/app/api/routers/candidate_availability.py:22-24`

```python
state = {"input_data": payload, "db": db}   # built but never used
result = await availability_graph.invoke_async(payload)  # invoke_async not a LangGraph API
```

Issues:
1. Compiled LangGraph graphs expose `.ainvoke()`, not `.invoke_async()`. This may currently fail silently or raise at runtime.
2. The `state` dict with the injected `db` session is prepared but never passed. The graph receives raw `payload` instead.
3. Inside `availability_graph.py`, `query_db_node` calls `next(get_db())` directly — this opens a new session but never closes it (the generator is not exhausted). Session leak on every request to `/agents/candidate-availability`.

**Required decision:** Fix the router to call `await availability_graph.ainvoke(payload)` correctly and pass the DB session properly through graph state, or simplify the endpoint to call `evaluate_availability()` directly without the LangGraph wrapper.

---

### FLAG-002 — Inconsistency: Duration math in availability calculations
**Files:** `availability.py` vs `agents/candidate_availability.py`

| File | Function | Duration math |
|---|---|---|
| `availability.py` | `calculate_requisition_window()` | `start + timedelta(days=30 * months)` |
| `agents/candidate_availability.py` | `calculate_window()` | `start + relativedelta(months=months)` |

For a 2-month engagement starting 2026-01-31:
- `timedelta(days=60)` → end = `2026-04-01`
- `relativedelta(months=2)` → end = `2026-03-31`

The two endpoints return different availability windows for the same inputs. **Someone needs to decide which is the authoritative calculation.** The matching pipeline uses `availability.py`; the `/agents/candidate-availability` endpoint uses `candidate_availability.py`.

---

## Fix Plan & Status

| # | Item | Action | Files | Status |
|---|---|---|---|---|
| 1 | DEAD-001 | Delete `utils/validation.py` | `utils/validation.py` | ✅ Done 2026-05-07 |
| 2 | DEAD-002 | Delete `utils/normalizer.py` | `utils/normalizer.py` | ✅ Done 2026-05-07 |
| 3 | DEAD-003 | Delete `utils/ranking.py` | `utils/ranking.py` | ✅ Done 2026-05-07 |
| 4 | DEAD-004 | Delete `utils/requisition_parser.py` | `utils/requisition_parser.py` | ✅ Done 2026-05-07 |
| 5 | Stale exports | Remove `RankedCandidate`, `RankedCandidateList`, `ValidationResult` from `__init__.py` imports and `__all__` | `utils/__init__.py` | ✅ Done 2026-05-07 |
| 6 | DEAD-005 | Remove `RankedCandidate`, `RankedCandidateList` from models | `utils/models.py` | ✅ Done 2026-05-07 |
| 7 | PERF-001 | Pre-load all 5 datasets before evaluation loop | `agents/matching_scoring.py` | ✅ Done 2026-05-07 |

**Not in this plan (requires separate decisions):**
- FLAG-001: `invoke_async` bug + session leak (correctness unknown without live test)
- FLAG-002: Duration math inconsistency (behavior decision needed)
- DEAD-006: `ValidationResult` removal (verify external test references first)

---

## Summary

| Category | Count | Estimated lines removed |
|---|---|---|
| Dead code (high-confidence) | 4 files + 2 dataclasses | ~440 lines |
| Stale exports | 4 entries | ~8 lines |
| Performance (PERF-001) | 1 function | restructure only |
| **Total** | | **~448 lines** |

**Test command to run after changes:**
```bash
python -m pytest tests/ -v --tb=short
```
*(Fix trulens_eval environment first.)*

**Suggested commit message (for when changes are applied):**
```
refactor(ai/utils): remove superseded legacy agent classes

- Delete ValidationAgent, NormalizerAgent, RankingAgent, RequisitionParserAgent
  (utils/validation, normalizer, ranking, requisition_parser) — all replaced
  by active LangGraph agent nodes in agents/
- Remove RankedCandidate and RankedCandidateList data models (only used by
  deleted RankingAgent)
- Clean up stale exports from utils/__init__.py

No behavior changes. Active pipeline nodes unaffected.
```
