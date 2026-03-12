# Cron Ingest-Embed Pipeline — Setup & Operations Guide

End-to-end runbook for the CR-EMB-002 nightly batch pipeline:
**ingest** team member data → **embed** skills/certs/resume → store 768-dim vectors in pgvector.

---

## Architecture Overview

```
python -m app.cron ingest-embed
          │
          ├─ Phase 1: INGEST (async)
          │     TeamDataClient ──► external HR API
          │     BatchProcessor ──► PostgreSQL (team_members, skills, certs)
          │
          └─ Phase 2: EMBED (sync, separate transaction)
                GemmaEmbeddingAgent  ──► local HuggingFace model (768-dim)
                MCPResumeClient      ──► MCP subprocess
                                              └─ gdrive/server.py
                                                    └─ Google Drive API
                                                          └─ DOCX → plain text
                EmbeddingProcessor   ──► team_member_embeddings (upsert)
```

---

## Prerequisites

### 1. Python Environment

```bash
# From repo root
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

pip install -r requirements.txt
```

Key packages installed by requirements.txt:
- `google-api-python-client>=2.120` — Drive & Docs API
- `google-auth>=2.28`, `google-auth-oauthlib` — OAuth2 / SA auth
- `mcp[cli]>=1.0` — FastMCP STDIO server/client
- `transformers>=4.40`, `torch` — local embedding model
- `python-docx>=1.1` — parse DOCX resume files
- `pgvector` — PostgreSQL vector column support

### 2. PostgreSQL + pgvector

```bash
# Must be at migration emb002_multi_vec
alembic upgrade head

# Verify
alembic current   # should show: emb002_multi_vec (head)
```

### 3. Local Embedding Model

The pipeline uses `sentence-transformers/all-mpnet-base-v2` (768-dim, downloaded to HuggingFace cache).

```bash
python scripts/setup_gemma_model.py
```

This downloads the model once and writes `GEMMA_MODEL_PATH` to `.env`.

---

## Google Drive MCP Setup

The MCP server reads resume DOCX files from Google Drive using OAuth2 user credentials.
**Service account sharing is blocked by InfoBeans org policy** — OAuth is the required auth path.

### Step 1 — Create OAuth Client ID in GCP Console

1. Go to [GCP Console → Credentials](https://console.cloud.google.com/apis/credentials)
   (Project: `infobeansrequisitionsystem`)
2. **Create Credentials → OAuth client ID → Desktop app**
   Name: `gdrive-mcp`
3. Download the JSON → save as:
   ```
   secrets/oauth-client-secrets.json
   ```
4. Ensure these APIs are enabled in the project:
   - **Google Drive API**
   - **Google Docs API**

### Step 2 — Run One-Time OAuth Consent Flow

```bash
python scripts/setup_gdrive_oauth.py
```

- Opens a browser → sign in with your **InfoBeans Google account**
  (the account that owns/has access to the Drive folder with resumes)
- Grants `drive.readonly` scope
- Saves `secrets/oauth-token.json` and adds `GOOGLE_OAUTH_TOKEN_FILE` to `.env`

> **Token refresh is automatic** — the server refreshes the token on every run using the stored refresh token. You only need to run this script once (or after revoking access).

### Step 3 — Verify Drive Access

```bash
python -c "
import sys; sys.path.insert(0, 'src')
from mcp_servers.gdrive.server import get_file_metadata, search_files
print(search_files(query='', max_results=5))
"
```

Expected output: `{'files': [{...}, ...]}` listing Drive files visible to your account.

---

## Environment Variables (`.env`)

```dotenv
# Database
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5433/ib_job_skill_mapping

# Embedding model (set by setup_gemma_model.py)
GEMMA_MODEL_PATH=C:\Users\...\models--sentence-transformers--all-mpnet-base-v2\snapshots\...

# Google Drive MCP — OAuth2 (primary, set by setup_gdrive_oauth.py)
GOOGLE_OAUTH_TOKEN_FILE=C:\...\secrets\oauth-token.json

# Google Drive MCP — Service Account (fallback, only if SA has Drive access)
GOOGLE_SERVICE_ACCOUNT_FILE=C:\...\secrets\sa-key.json

# Optional overrides
MCP_GDRIVE_SERVER_PATH=src/mcp_servers/gdrive/server.py   # default
EMBEDDING_DEVICE=cpu                                        # or cuda/mps
```

**Credential priority**: `oauth-token.json` takes precedence over `sa-key.json`.
If `oauth-token.json` exists, the SA key is never used for Drive access.

---

## Running the Pipeline

### Full ingest + embed (nightly)

```bash
python -m app.cron ingest-embed
```

- Phase 1 fetches team data from the external HR API and commits to DB
- Phase 2 opens an MCP session per member, fetches resume, embeds, upserts
- Exit codes: `0` = success, `1` = partial success, `2` = fatal error

### Embed only (re-embed without re-ingesting)

```bash
python -m app.cron embed
```

Skips members whose `content_hash` hasn't changed (skills + certs + resume).

### Force re-embed all members

```bash
python -m app.cron embed --force
```

Bypasses hash check — useful after model changes or first-time setup.

### Ingest only (no embed)

```bash
python -m app.cron        # runs ingest phase only (default behavior)
```

---

## What Gets Stored

Each successful member run upserts one row in `team_member_embeddings`:

| Column | Description |
|--------|-------------|
| `resume_embedding` | 768-dim vector of PII-scrubbed resume text |
| `skills_embedding` | 768-dim vector of assembled skills text |
| `certifications_embedding` | 768-dim vector of certifications text |
| `embedding` | Weighted average (resume×0.5 + skills×0.3 + certs×0.2) |
| `resume_text` | Scraped + PII-scrubbed resume plain text |
| `skills_text` | Concatenated skill names |
| `certifications_text` | Concatenated certification names |
| `content_hash` | SHA-256 of all three texts — used for idempotency |
| `embedding_model` | `embedding-gemma-300m` |
| `resume_fetched_at` | Timestamp of last successful resume fetch |
| `embedding_updated_at` | Timestamp of last upsert |

---

## Resume Fetch: How It Works

1. For each member with a `profile_url` (Google Doc/DOCX link):
   - `MCPResumeClient` spawns `src/mcp_servers/gdrive/server.py` as a subprocess
   - Calls the `read_document` MCP tool with the URL
   - Server authenticates via OAuth2 user token (`secrets/oauth-token.json`)
   - If the file is a native Google Doc → `documents.get()` API
   - If the file is a DOCX (`http_400` from Docs API) → `files.get_media()` download + `python-docx` parse
   - Returns plain text (truncated at 100 KB)
2. Text is PII-scrubbed before embedding
3. Members without `profile_url` skip resume fetch gracefully

---

## Troubleshooting

### `resume_fetch_success_total status=error`

| Symptom | Cause | Fix |
|---------|-------|-----|
| All members fail | OAuth token missing or expired | Run `python scripts/setup_gdrive_oauth.py` |
| Some members fail | Those Drive files not accessible to auth account | Share files/folder with the authorizing Google account |
| `not_found` errors | File IDs in DB are synthetic/stale | Re-ingest real data via `python -m app.cron ingest-embed` |
| `permission_denied` | Account lacks viewer access | Share the Drive folder with the account used in OAuth setup |

### `UndefinedColumn: resume_embedding does not exist`

Migration not applied. Run:
```bash
alembic upgrade head
```

### `InvalidColumnReference: no unique constraint matching ON CONFLICT`

Unique constraint missing. Run:
```bash
alembic downgrade bca284b2d901
alembic upgrade head
```

### `InFailedSqlTransaction` on member N+1

Fixed in code (rollback on per-member error). If it recurs, the DB may be in a bad state — restart the process.

### `asyncio: an error occurred during closing of asynchronous generator`

Cosmetic warning from the MCP library's STDIO cleanup on Windows. Does not affect correctness — the tool call itself succeeds.

---

## Secrets Files (gitignored)

```
secrets/
├── sa-key.json               # Google Service Account key (fallback)
├── oauth-client-secrets.json # GCP OAuth Desktop app credentials
└── oauth-token.json          # User OAuth token (auto-refreshed)
```

All three are in `.gitignore` under `secrets/`. **Never commit these files.**

---

## Re-authorization

If the OAuth token is revoked or expired beyond refresh:

```bash
rm secrets/oauth-token.json
python scripts/setup_gdrive_oauth.py
```

Then re-run embed:
```bash
python -m app.cron embed --force
```
