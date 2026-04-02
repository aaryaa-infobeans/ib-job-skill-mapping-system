# PII Scrubber — Setup & Operations Guide

Setup guide for the resume PII scrubbing pipeline that runs inside `python -m app.cron embed`.

---

## Architecture Overview

```
EmbeddingProcessor._scrub_pii(raw_resume_text)
          │
          └─ PIIScrubber(PIIConfig.from_env())
                │
                ├─ NERDetector (SpaCy en_core_web_sm)
                │     └─ PERSON  → [NAME_REDACTED]
                │     └─ ORG     → CLIENT_TOKEN_<8-char HMAC>
                │
                ├─ Regex rules
                │     └─ email   → [EMAIL_REDACTED]
                │     └─ phone   → [PHONE_REDACTED]
                │     └─ SSN     → [SSN_REDACTED]
                │     └─ ZIP     → [POSTAL_REDACTED]
                │
                └─ Tech whitelist (python, react, docker, …)
                      └─ these terms are never redacted even if NER flags them
```

Scrubbed text is stored in `team_member_embeddings.resume_text`.
`pii_scrubbed = true` and `scrubbed_at` are set on successful runs.

---

## Prerequisites

### 1. Python Environment

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

pip install -r requirements.txt
```

Key packages:
- `spacy>=3.8` — NER engine
- `python-dotenv` — loads `.env` into `os.environ`

### 2. SpaCy Language Model

```bash
python -m spacy download en_core_web_sm
```

Verify installation:

```bash
python -c "import spacy; print(spacy.util.get_installed_models())"
# Expected: ['en_core_web_sm']
```

> **Python 3.13 note**: Use `en_core_web_sm` (CPU, 12.8 MB).
> The transformer model `en_core_web_trf` requires Python 3.11/3.12 and a GPU.

---

## Environment Variables (`.env`)

Add the following block to your `.env` file:

```dotenv
# PII Scrubber Configuration
PII_USE_GPU=false
PII_TOKENIZATION_SALT=<replace-with-32-char-secret-minimum>
PII_ENABLE_AUDIT=false
```

| Variable | Required | Description |
|----------|----------|-------------|
| `PII_USE_GPU` | Yes | Set `false` on CPU-only machines (dev, Windows). Set `true` only when NVIDIA GPU + CUDA 11+ are present. |
| `PII_TOKENIZATION_SALT` | Yes | Secret salt for deterministic HMAC tokenization of ORG entities. Must be ≥ 32 characters. |
| `PII_ENABLE_AUDIT` | No | Set `true` to write a scrub audit log to `pii_scrub_audit` table (default `true`). |

### Generating a salt

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output into `PII_TOKENIZATION_SALT=<output>` in `.env`.

> **Security**: Keep this salt private. Changing it will produce different tokens for the same org names — existing tokenized text in the DB will no longer match new runs. Treat it like a signing key.

---

## What Gets Scrubbed

| PII Type | Detection | Action | Example |
|----------|-----------|--------|---------|
| Person names | SpaCy NER (`PERSON`) | Redact | `Neha Iyer` → `[NAME_REDACTED]` |
| Organizations | SpaCy NER (`ORG`) | Tokenize | `Infosys` → `CLIENT_TOKEN_4a2f9c11` |
| Email addresses | Regex | Redact | `user@company.com` → `[EMAIL_REDACTED]` |
| Phone numbers | Regex | Redact | `+1-800-555-0123` → `[PHONE_REDACTED]` |
| Social Security Numbers | Regex | Redact | `123-45-6789` → `[SSN_REDACTED]` |
| US ZIP codes | Regex | Redact | `94105` → `[POSTAL_REDACTED]` |

**Tech whitelist** — these are never redacted even if SpaCy flags them as names:
`python, java, react, django, docker, kubernetes, aws, azure, gcp, redis, oracle` and others.
See `src/app/pii/scrubber.py:_load_tech_whitelist()` for the full list.

---

## Running the Scrubber

PII scrubbing runs automatically as part of the embed phase:

```bash
# Full pipeline (ingest + embed + scrub)
python -m app.cron ingest-embed

# Embed + scrub only (no re-ingest)
python -m app.cron embed

# Force re-scrub all members (bypasses hash check)
python -m app.cron embed --force
```

Scrubbing happens per-member inside `EmbeddingProcessor._scrub_pii()` before the text is embedded or written to the database.

---

## Verifying Scrubbing in the Database

```sql
-- Check scrub status across all members
SELECT pii_scrubbed, COUNT(*)
FROM team_member_embeddings
GROUP BY pii_scrubbed;

-- Preview scrubbed resume text for recent members
SELECT team_member_id,
       pii_scrubbed,
       scrubbed_at,
       LEFT(resume_text, 500) AS resume_preview
FROM team_member_embeddings
WHERE resume_text IS NOT NULL AND resume_text <> ''
ORDER BY scrubbed_at DESC
LIMIT 5;
```

Expected output for `resume_preview`:
- Person names replaced: `[NAME_REDACTED]`
- Organisation names replaced: `CLIENT_TOKEN_<8hex>`
- No raw email/phone/SSN patterns remaining

---

## Troubleshooting

### `nvidia-smi not found. GPU instance not properly configured`

`PII_USE_GPU` is `true` (or not set) but no NVIDIA GPU is present.

Fix: set `PII_USE_GPU=false` in `.env`.

### `Environment variable PII_TOKENIZATION_SALT not set`

The salt is missing or too short (< 32 chars).

Fix: generate and set the variable — see [Generating a salt](#generating-a-salt).

### `pii_scrub_failed; returning original text`

The scrubber raised an unexpected exception and fell back to storing unscrubbed text. The member will have `pii_scrubbed = false` in the DB.

Check the structured log for the `error=` field on the `pii_scrub_failed` event:

```bash
python -m app.cron embed --force 2>&1 | grep pii_scrub
```

### `en_core_web_sm not found` / `OSError: [E050]`

SpaCy model not installed.

Fix:
```bash
python -m spacy download en_core_web_sm
```

### `pii_scrubbed` column missing (`UndefinedColumn`)

The `pii_scrubbed` / `scrubbed_at` columns were added to the `TeamMemberEmbedding` SQLAlchemy model. If the columns are missing from the database, they were created by an earlier migration. Verify:

```sql
SELECT column_name FROM information_schema.columns
WHERE table_name = 'team_member_embeddings'
ORDER BY ordinal_position;
```

Both `pii_scrubbed` and `scrubbed_at` should be present. If not, check your migration history:

```bash
alembic current
alembic upgrade head
```

---

## Key Source Files

| File | Purpose |
|------|---------|
| [src/app/pii/scrubber.py](../src/app/pii/scrubber.py) | Core `PIIScrubber` class — detection, redaction, tokenization |
| [src/app/pii/config.py](../src/app/pii/config.py) | `PIIConfig` — reads env vars, validates GPU/salt |
| [src/app/pii/ner_detector.py](../src/app/pii/ner_detector.py) | SpaCy NER wrapper |
| [src/app/pii/tokenizer.py](../src/app/pii/tokenizer.py) | HMAC-SHA256 deterministic tokenizer |
| [src/app/cron/embedding/embedding_processor.py](../src/app/cron/embedding/embedding_processor.py) | `_scrub_pii()` — called per-member before embed |
