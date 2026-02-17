# Change Request: PII Scrubber for RAG Pipeline

**CR ID:** CR-PII-001  
**Spec Version:** 1.0.0  
**Classification:** MAJOR (Security & Compliance Impacting)  
**Created:** 2026-02-16  
**Status:** Proposed  
**Priority:** P0 - Critical  

---

## 1. Overview

### 1.1 Problem Statement

The current RAG (Retrieval-Augmented Generation) pipeline ingests, stores, and retrieves team member profile data containing Personally Identifiable Information (PII) without adequate sanitization controls. This creates significant regulatory compliance, legal liability, and data breach exposure risks.

**Current Risk Exposure:**

1. **Storage Risk:** Raw PII persisted in `team_member_embeddings.profile_text` and `metadata` fields
2. **Transmission Risk:** PII sent to third-party embedding APIs (OpenAI/Azure) without scrubbing
3. **Retrieval Risk:** RAG responses may leak PII to unauthorized API consumers
4. **Logging Risk:** System logs, metrics, and traces may inadvertently capture PII during debugging
5. **Vector Embedding Risk:** Semantic embeddings may encode PII patterns enabling reconstruction attacks

**Specific Exposure Points:**
- Team member names embedded in plaintext profile descriptions
- Email addresses in contact metadata
- Phone/mobile numbers in communication fields
- Addresses in location data
- Date of birth in profile records
- Client names exposing business relationships
- Project names revealing contractual information

### 1.2 Risk Exposure in RAG Systems

RAG systems present unique PII exposure risks beyond traditional databases:

| Risk Category | RAG-Specific Concern | Impact Severity |
|--------------|---------------------|-----------------|
| **Semantic Leakage** | PII encoded in vector embeddings may be extractable via adversarial queries | HIGH |
| **Third-Party Exposure** | Embedding APIs receive raw text before vectorization | CRITICAL |
| **Aggregation Risk** | Multiple weak identifiers combined reveal identity (DOB + Location + Job Title) | HIGH |
| **Retrieval Amplification** | Single query may return PII across multiple candidates | MEDIUM |
| **Audit Gap** | No immutable record of who accessed what PII through RAG queries | HIGH |

**Quantified Risk:**
- Estimated 250,000+ PII records currently stored without scrubbing
- Potential GDPR fines: €20M or 4% of global revenue
- Estimated breach notification cost: $2-5M per incident
- Customer contract violations: Loss of Fortune 500 enterprise clients

### 1.3 Regulatory and Contractual Drivers

| Regulation/Standard | Specific Requirement | Non-Compliance Penalty |
|--------------------|--------------------|----------------------|
| **GDPR (EU)** | Article 5(1)(c) - Data Minimization<br>Article 25 - Data Protection by Design | Fines up to €20M or 4% global revenue |
| **CCPA (California)** | §1798.100 - Right to Know<br>§1798.105 - Right to Deletion | $7,500 per intentional violation |
| **ISO 27001:2013** | A.8.2.3 - Handling of Assets<br>A.18.1.4 - Privacy and PII | Certification revocation |
| **SOC 2 Type II** | CC6.1 - Logical Access Controls<br>PI1.2 - PII Processing | Customer contract breach, audit failure |
| **AI Act (EU)** | Article 10 - Data Governance<br>Annex IV - Transparency | Ban on system deployment in EU |
| **HIPAA** (if healthcare data) | §164.514 - De-identification | Up to $50,000 per violation |

**Contractual Obligations:**
- Fortune 500 customer contracts require PII minimization (15 active contracts at risk)
- Third-party processor agreements with OpenAI/Azure prohibit raw PII transmission
- Cyber insurance policy requires data sanitization for sensitive fields

---

## 2. Scope

### 2.1 In-Scope Components

| Component | Scrubbing Requirement | Enforcement Point |
|-----------|---------------------|------------------|
| **Ingestion Pipeline** | MANDATORY | Before embedding generation |
| **Vector Storage** | MANDATORY | Only scrubbed data persisted |
| **Embedding Generation** | MANDATORY | Only scrubbed text vectorized |
| **Retrieval Responses** | MANDATORY | Secondary filtering before API response |
| **Application Logs** | MANDATORY | Structured logging with PII redaction |
| **Audit Logs** | MANDATORY | PII masked except for authorized roles |
| **Metrics & Traces** | MANDATORY | No PII in Prometheus labels or trace attributes |
| **Error Messages** | MANDATORY | Generic errors without exposing PII |

### 2.2 Ingestion-Time Scrubbing (Mandatory)

**Requirement:** All data entering the RAG pipeline MUST pass through the PII Scrubber before any processing.

**Enforcement:**
- Scrubber executes as first stage in LangGraph topology (Node 0)
- Database constraints prevent insertion of unscrubbed records (`pii_scrubbed` flag required)
- API gateway validates scrubbing metadata before accepting ingestion requests

**Testability:** 
- Unit tests validate scrubber invocation on 100% of ingestion paths
- Integration tests verify database rejects unscrubbed data

### 2.3 Retrieval-Time Secondary Filtering (Mandatory)

**Requirement:** RAG retrieval results MUST undergo secondary PII filtering before API responses.

**Rationale:** Defense-in-depth strategy protects against:
- Historical data ingested before scrubber implementation
- Scrubber logic bugs allowing PII leakage
- Data corruption or schema migration errors

**Enforcement:**
- Retrieval service applies PII detection to all response fields
- Detected PII automatically redacted with `<REDACTED>` tokens
- Alert triggered for any PII detected (indicates scrubber bypass)

**Testability:**
- Chaos engineering tests inject unscrubbed data and validate secondary filtering
- Penetration tests attempt to extract PII through adversarial queries

### 2.4 Logging Sanitization (Mandatory)

**Requirement:** All application logs, error logs, and debug logs MUST NOT contain raw PII.

**Enforcement:**
- Structured logging with explicit PII-safe fields only
- Log aggregation pipeline (Fluentd/Vector) applies final scrubbing pass
- Automated daily scans detect PII patterns in stored logs

**Testability:**
- Automated regex/NER scans of log files (daily)
- Test cases inject PII into log statements and validate redaction

### 2.5 Metadata Sanitization (Mandatory)

**Requirement:** JSONB `metadata` columns, request headers, and trace baggage MUST NOT contain PII.

**Enforcement:**
- Schema validation rejects payloads with PII-matching keys
- Sanitization middleware strips PII keys from request/response headers
- OpenTelemetry instrumentation configured to exclude PII attributes

**Testability:**
- Schema validation tests with PII-containing payloads
- Header inspection tests validate sanitization

---

## 3. Definitions

### 3.1 Personally Identifiable Information (PII)

**Definition:** Any information that can be used to identify, contact, or locate an individual, either alone or combined with other data.

**Categories:**

**Direct Identifiers** (High Sensitivity):
- Full name (first + last name)
- Email address
- Phone number
- Mobile number
- Address (street, city, postal code)
- Date of birth (DOB)
- Government-issued ID numbers (SSN, passport, etc.)

**Quasi-Identifiers** (Medium Sensitivity):
- Combination of: Age + Location + Job Title
- Combination of: Gender + Ethnicity + City
- Unique job titles (e.g., "Chief Quantum Computing Officer at Startup X")

### 3.2 Business-Sensitive Data

**Definition:** Information that, while not identifying individuals, reveals confidential business relationships or operations.

**Categories:**
- **Client Names:** Customer/partner organization names
- **Project Names:** Internal project codenames, client engagement identifiers
- **Contract Values:** Financial terms, pricing information
- **Strategic Initiatives:** Confidential business plans

**Treatment:** Business-sensitive data SHALL be tokenized (not redacted) to preserve semantic meaning for matching while protecting confidentiality.

### 3.3 Redaction

**Definition:** Complete removal of PII with replacement by a generic placeholder token.

**Use Case:** When PII adds no semantic value to RAG matching (e.g., full names, email addresses).

**Implementation:**
```
Original: "John Smith works as a Python Developer"
Redacted: "<NAME_REDACTED> works as a Python Developer"
```

**Properties:**
- **Irreversible:** Original data cannot be recovered
- **Deterministic:** Same input always produces same output
- **Non-unique:** Multiple individuals may map to same token

### 3.4 Masking

**Definition:** Partial obfuscation of PII while preserving structure and uniqueness.

**Use Case:** When structure is semantically important but content must be protected.

**Implementation:**
```
Original Email: "john.smith@company.com"
Masked: "j***@company.com"

Original Phone: "+1-555-0123"
Masked: "+*-***-0123"
```

**Properties:**
- **Irreversible:** Original data cannot be fully recovered
- **Partially Unique:** Retains domain/area code for context
- **Deterministic:** Same input produces same output

### 3.5 Tokenization

**Definition:** Replacement of PII with a unique, deterministic hash-based token.

**Use Case:** When semantic meaning must be preserved for matching while protecting confidentiality (e.g., client names, project names).

**Implementation:**
```
Original: "Acme Corporation"
Tokenized: "CLIENT_TOKEN_a7b9c2d1"

Token Generation: SHA256(value + salt)[0:8]
```

**Properties:**
- **Irreversible:** Original data cannot be recovered (one-way hash)
- **Unique:** Each unique value maps to a unique token
- **Deterministic:** Same input produces same token
- **Collision-Resistant:** Different inputs produce different tokens

### 3.6 Hashing (Cryptographic One-Way)

**Definition:** SHA-256 hash of PII with secret salt for duplicate detection without storing plaintext.

**Use Case:** Detecting duplicate records without exposing PII (e.g., "same email address already registered").

**Implementation:**
```
Original: "john.smith@company.com"
Hashed: "a4f8e2b1c9d7..." (64-character hex)

Calculation: SHA256(original + SALT)
```

**Properties:**
- **Irreversible:** Cannot recover original (one-way function)
- **Deterministic:** Same input + salt produces same hash
- **Collision-Resistant:** Different inputs produce different hashes (negligible collision probability)
- **Non-Unique-Preserving:** Hash does not reveal similarity

---

## 4. Functional Requirements

### FR-PII-001: Pattern-Based Detection (Structured PII)

**Requirement:** The PII Scrubber MUST detect structured PII using regex patterns with 100% recall on well-formed inputs.

**Covered PII Types:**

| PII Type | Pattern | Example Match | Confidence Score |
|----------|---------|---------------|-----------------|
| **Email** | `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b` | `john.smith@company.com` | 1.0 (deterministic) |
| **Phone (E.164)** | `\+?[1-9]\d{1,14}` | `+1-555-0123`, `5551234567` | 0.95 (may have false positives) |
| **Date of Birth** | `\b(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01])/\d{4}\b` | `03/15/1985`, `12/31/1990` | 0.90 (ambiguous with other dates) |
| **Postal Code (US)** | `\b\d{5}(-\d{4})?\b` | `94105`, `10001-1234` | 0.85 (generic number pattern) |
| **Postal Code (UK)** | `\b[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2}\b` | `SW1A 1AA`, `EC1A1BB` | 0.90 |

**Implementation Constraints:**
- Patterns MUST be externally configurable (YAML/JSON)
- Patterns MUST support Unicode for international names/addresses
- False positive rate target: < 2% (validated on 10,000-sample test set)

**Acceptance Criteria:**
- [ ] 100% recall on test set of 1,000 well-formed emails
- [ ] 100% recall on test set of 1,000 well-formed phone numbers
- [ ] 95%+ recall on test set of 1,000 date patterns
- [ ] Configurable patterns hot-reloadable without service restart

### FR-PII-002: Named Entity Recognition (Unstructured PII)

**Requirement:** The PII Scrubber MUST detect unstructured PII using Named Entity Recognition (NER) with minimum F1-score of 0.90.

**Covered Entity Types:**

| Entity Type | Detection Method | Confidence Threshold | Example |
|-------------|-----------------|---------------------|---------|
| **PERSON** | SpaCy `en_core_web_trf` | ≥ 0.85 | "Jane Smith", "Dr. Robert Johnson" |
| **GPE** (Geopolitical Entity) | SpaCy `en_core_web_trf` | ≥ 0.85 | "San Francisco", "New York" |
| **ORG** (Organization)* | SpaCy `en_core_web_trf` + Dictionary | ≥ 0.80 | "Acme Corp", "Google" |
| **DATE** (DOB Context) | SpaCy `en_core_web_trf` + Context Rules | ≥ 0.75 | "born on March 15, 1985" |
| **CARDINAL** (Ages) | SpaCy `en_core_web_trf` + Context Rules | ≥ 0.70 | "38 years old" |

*Note: ORG detection combined with client/project dictionary for business-sensitive filtering.

**NER Model Requirements:**
- Model: SpaCy `en_core_web_trf` (Transformer-based, 560MB)
- Inference: GPU-accelerated (CUDA) or CPU fallback (max 200ms latency)
- Context Window: 512 tokens (sufficient for profile descriptions)

**Confidence Handling:**
- Detections ≥ 0.85: Automatic scrubbing
- Detections 0.70-0.84: Scrub + log for manual review
- Detections < 0.70: Log only (no scrubbing)

**Acceptance Criteria:**
- [ ] F1-score ≥ 0.90 on internal PII test corpus (5,000 samples)
- [ ] False positive rate ≤ 5% on skill/technology terms (e.g., "Python", "Java")
- [ ] NER model loaded successfully on service startup
- [ ] Graceful degradation to regex-only mode if NER unavailable

### FR-PII-003: Configurable Rule Engine (Business-Sensitive Data)

**Requirement:** The PII Scrubber MUST support configurable rules for client/project name detection with hot-reloadable policies.

**Configuration Schema:**

```yaml
# config/pii-scrubbing-rules-v1.yaml
version: "1.0.0"
effective_date: "2026-03-01"

business_sensitive:
  client_names:
    mode: "tokenize"  # Options: tokenize, redact, mask
    sources:
      - type: "database"
        query: "SELECT client_name FROM clients WHERE is_active = TRUE"
        refresh_interval: "1h"
      
      - type: "file"
        path: "s3://config-bucket/client-names.json"
        format: "json"
        refresh_interval: "24h"
    
    fuzzy_matching:
      enabled: true
      algorithm: "levenshtein"
      threshold: 0.85  # 85% similarity required
    
    case_sensitive: false
  
  project_names:
    mode: "tokenize"
    sources:
      - type: "database"
        query: "SELECT project_name FROM projects WHERE status IN ('active', 'pending')"
        refresh_interval: "1h"
    
    pattern_matching:
      enabled: true
      patterns:
        - "\\bProject [A-Z][a-z]+\\b"  # "Project Phoenix", "Project Alpha"
        - "\\b[A-Z]{2,}-\\d{4}\\b"      # "PX-2024", "AL-1234"
```

**Tokenization Policy:**
- Client names → `CLIENT_TOKEN_{SHA256(name+salt)[0:8]}`
- Project names → `PROJECT_TOKEN_{SHA256(name+salt)[0:8]}`
- Tokens generated deterministically using HMAC-SHA256

**Rule Engine Requirements:**
- Rules MUST be validated against JSON schema before application
- Invalid rules MUST trigger service startup failure with descriptive error
- Rule changes MUST be audited in `pii_rule_change_log` table
- Hot-reload triggered via `SIGHUP` signal or `/admin/reload-pii-rules` API endpoint

**Acceptance Criteria:**
- [ ] Rules loaded from YAML on service startup
- [ ] Rule validation catches schema errors (tested with 10 invalid configs)
- [ ] Hot-reload updates rules without service restart
- [ ] Fuzzy matching correctly identifies "Acme Corp" and "ACME Corporation" as same entity

### FR-PII-004: Deterministic Replacement Tokens

**Requirement:** For the same input, the PII Scrubber MUST produce identical output across all executions (determinism requirement).

**Replacement Token Formats:**

| PII Type | Scrubbing Method | Token Format | Example |
|----------|-----------------|--------------|---------|
| **Name** | Redaction | `<NAME_REDACTED>` | Always the same token |
| **Email** | Hashing | `EMAIL_HASH_{SHA256(email+salt)[0:16]}` | `EMAIL_HASH_a4f8e2b1c9d7f3a2` |
| **Phone** | Masking | `+{country_code}-***-{last_4_digits}` | `+1-***-0123` |
| **Address (Street)** | Redaction | `<ADDRESS_REDACTED>` | Always the same token |
| **Address (City)** | Generalization | Region mapping (e.g., "Bangalore" → "South Asia") | Deterministic mapping |
| **DOB** | Generalization | Age band (e.g., "1985-03-15" → "Age: 35-40") | Deterministic bucketing |
| **Client Name** | Tokenization | `CLIENT_TOKEN_{hash[0:8]}` | `CLIENT_TOKEN_a7b9c2d1` |
| **Project Name** | Tokenization | `PROJECT_TOKEN_{hash[0:8]}` | `PROJECT_TOKEN_x4y8z1w3` |

**Determinism Requirements:**
- MUST use static salt from environment variable (rotated quarterly)
- MUST NOT use random UUIDs or timestamps in token generation
- MUST use greedy decoding for NER (no sampling)
- MUST process records serially to avoid race conditions

**Testability:**
```python
def test_scrubber_determinism():
    input_profile = {
        "name": "Jane Doe",
        "email": "jane.doe@example.com",
        "phone": "+1-555-0199"
    }
    
    result_1 = pii_scrubber.scrub(input_profile)
    result_2 = pii_scrubber.scrub(input_profile)
    
    assert result_1 == result_2, "PII scrubber must be deterministic"
```

**Acceptance Criteria:**
- [ ] 1,000 repeated executions on same input produce identical output
- [ ] Salt rotation procedure documented in runbook
- [ ] No random functions used in scrubbing logic (code audit)

### FR-PII-005: No Raw PII Persistence in Vector DB

**Requirement:** The `team_member_embeddings` table MUST NOT store raw PII in any column.

**Schema Constraints:**

```sql
-- Enforced via database constraint
ALTER TABLE team_member_embeddings
  ADD CONSTRAINT check_pii_scrubbed 
  CHECK (pii_scrubbed = TRUE);

-- Enforced via application logic
ALTER TABLE team_member_embeddings
  ALTER COLUMN profile_text_scrubbed SET NOT NULL;

-- Index to prevent queries on unscrubbed data
CREATE INDEX idx_embeddings_scrubbed_only 
  ON team_member_embeddings(embedding) 
  WHERE pii_scrubbed = TRUE;
```

**Verification Process:**
1. **Pre-Storage Validation:** Application validates scrubbing metadata before INSERT
2. **Database Constraint:** CHECK constraint rejects unscrubbed records
3. **Automated Scanning:** Daily cron job scans `profile_text_scrubbed` for PII patterns
4. **Manual Audits:** Quarterly security audit of 1,000 random samples

**Acceptance Criteria:**
- [ ] Attempt to INSERT unscrubbed record fails with constraint violation
- [ ] Automated scan finds 0 PII instances in 100,000-record sample
- [ ] Penetration test cannot extract PII from vector embeddings

### FR-PII-006: Configurable Strictness Mode

**Requirement:** The PII Scrubber MUST support two operational modes: STRICT and BALANCED.

**Mode Definitions:**

| Mode | Description | Use Case | False Positive Handling |
|------|-------------|----------|------------------------|
| **STRICT** | Scrub any detection above 0.50 confidence | Production, regulated industries | Accept higher false positive rate |
| **BALANCED** | Scrub detections above 0.85 confidence | Development, internal tools | Minimize false positives |

**Configuration:**

```yaml
scrubber:
  mode: "STRICT"  # Options: STRICT, BALANCED
  
  confidence_thresholds:
    STRICT:
      auto_scrub: 0.50
      manual_review: 0.30
    
    BALANCED:
      auto_scrub: 0.85
      manual_review: 0.70
```

**Acceptance Criteria:**
- [ ] STRICT mode scrubs 100% of test PII (may have false positives)
- [ ] BALANCED mode achieves < 2% false positive rate
- [ ] Mode configurable via environment variable (`PII_SCRUBBER_MODE`)

---

## 5. Processing Rules

### 5.1 Order of Operations in RAG Pipeline

**Requirement:** PII scrubbing MUST occur at specific points in the pipeline with defined sequencing.

**Pipeline Topology:**

```
┌───────────────────────────────────────────────────────────────┐
│                 RAG Pipeline (PII-Protected)                   │
└───────────────────────────────────────────────────────────────┘

[Raw Data Ingestion]
        ↓
  ① PII Detection
        ↓
  ② PII Scrubbing ← YOU ARE HERE (NODE 0)
        ↓
  ③ Validation (pii_scrubbed = TRUE)
        ↓
  ④ JD Parsing Agent
        ↓
  ⑤ Skill Extraction Agent
        ↓
  ⑥ Embedding Generation ← Only receives scrubbed text
        ↓
  ⑦ Vector Storage (profile_text_scrubbed only)
        ↓
        ...
        ↓
  ⑧ RAG Retrieval
        ↓
  ⑨ Secondary PII Filter ← Defense-in-depth
        ↓
  ⑩ API Response
```

**Node 0 (PII Scrubber) Responsibilities:**
1. Receive raw team member profile or JD text
2. Apply pattern-based detection (FR-PII-001)
3. Apply NER-based detection (FR-PII-002)
4. Apply business-sensitive rules (FR-PII-003)
5. Generate scrubbed output with metadata
6. Create audit record in `pii_scrub_audit`
7. Pass scrubbed data to next node

**Validation Gate (Node 3):**
- Reject any data with `pii_scrubbed != TRUE`
- Log critical alert if unscrubbed data detected
- Return HTTP 422 Unprocessable Entity

**Acceptance Criteria:**
- [ ] Integration tests validate scrubber executes before embedding generation
- [ ] Attempt to bypass scrubber fails at validation gate
- [ ] All 10 pipeline stages logged in LangGraph checkpoints

### 5.2 Idempotency Requirement

**Requirement:** Applying the PII Scrubber multiple times to the same input MUST produce the same output.

**Idempotency Test:**

```python
def test_scrubber_idempotency():
    original = {"name": "Jane Doe", "email": "jane@example.com"}
    
    scrubbed_once = pii_scrubber.scrub(original)
    scrubbed_twice = pii_scrubber.scrub(scrubbed_once)
    
    assert scrubbed_once == scrubbed_twice
```

**Implementation Constraints:**
- Scrubber MUST detect already-scrubbed tokens and skip re-scrubbing
- Pattern: `<[A-Z_]+REDACTED>` → Already redacted, do not re-process
- Pattern: `TOKEN_[A-F0-9]+` → Already tokenized, do not re-process

**Acceptance Criteria:**
- [ ] 100 iterations of scrubbing same input produces identical output
- [ ] Scrubbing a scrubbed document does not introduce double-redaction

### 5.3 Same Input → Same Scrubbed Output (Determinism)

**Requirement:** See FR-PII-004. This is a critical architectural constraint.

**Verification:**
- Unit tests with 1,000 determinism assertions
- CI/CD pipeline fails if any non-deterministic behavior detected

---

## 6. Non-Functional Requirements

### NFR-PII-001: Maximum Performance Overhead

**Requirement:** PII scrubbing MUST NOT increase embedding generation latency by more than 50ms (p95).

**Baseline Measurements (No Scrubbing):**
- Embedding generation: 150ms (p95)
- Total ingestion pipeline: 500ms (p95)

**Target Performance (With Scrubbing):**
- PII Scrubber execution: ≤ 50ms (p95)
- Total embedding generation: ≤ 200ms (p95)
- Total ingestion pipeline: ≤ 550ms (p95)

**Performance Optimization Strategies:**
- Batch processing: Scrub 50 profiles in single NER pass
- GPU acceleration: Use CUDA for NER inference (5x faster than CPU)
- Async processing: Run scrubber asynchronously for non-real-time ingestion

**Acceptance Criteria:**
- [ ] Load test with 10,000 profiles achieves ≤ 200ms p95 latency
- [ ] Performance regression tests in CI/CD (fails if > 250ms)
- [ ] Prometheus metric: `pii_scrub_duration_seconds{quantile="0.95"}` ≤ 0.05

### NFR-PII-002: Observability Without PII Leakage

**Requirement:** All observability data (logs, metrics, traces) MUST NOT contain raw PII.

**Logging Standards:**

```python
# ❌ WRONG: PII in logs
logger.info(f"Scrubbed email: {email}")

# ✅ CORRECT: No PII in logs
logger.info(
    "Scrubbed email",
    extra={
        "pii_type": "email",
        "action": "hash",
        "input_length": len(email),
        "output_hash_prefix": hashed_email[:8],
        "confidence": 1.0
    }
)
```

**Metrics (Prometheus):**

```prometheus
# Safe metrics (no PII)
pii_scrub_operations_total{pii_type="email", action="hash"} 12453
pii_scrub_duration_seconds_bucket{le="0.05"} 9823
pii_detection_confidence_score{pii_type="name", quantile="0.95"} 0.98
pii_false_positive_rate 0.018
```

**Distributed Tracing:**

```yaml
# OpenTelemetry span attributes (PII-safe)
span.attributes:
  - pii.detected: true
  - pii.types: ["email", "phone"]
  - pii.actions: ["hash", "mask"]
  - pii.confidence_avg: 0.93
  
  # ❌ NOT ALLOWED:
  # - pii.email_value: "john@example.com"
  # - pii.name: "John Smith"
```

**Acceptance Criteria:**
- [ ] Automated daily scan finds 0 PII in logs
- [ ] Prometheus metrics contain no label values with PII
- [ ] Distributed traces contain no PII in span attributes

### NFR-PII-003: Audit Logging of Scrub Events

**Requirement:** Every PII scrubbing operation MUST generate an immutable audit record.

**Audit Schema:**

```sql
CREATE TABLE pii_scrub_audit (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    source_table VARCHAR(100) NOT NULL,
    source_record_id VARCHAR(255) NOT NULL,
    pii_detected JSONB NOT NULL,  -- [{type: "email", confidence: 1.0, action: "hash"}]
    rule_version VARCHAR(20) NOT NULL,
    scrubber_version VARCHAR(20) NOT NULL,
    triggered_by VARCHAR(100),
    processing_time_ms INT,
    
    CONSTRAINT no_update_delete CHECK (false)  -- Immutable audit log
);

CREATE INDEX idx_audit_timestamp ON pii_scrub_audit(timestamp DESC);
CREATE INDEX idx_audit_source ON pii_scrub_audit(source_table, source_record_id);
```

**Audit Record Example:**

```json
{
  "audit_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-02-16T14:30:00Z",
  "source_table": "team_member",
  "source_record_id": "TM-12345",
  "pii_detected": [
    {"type": "email", "confidence": 1.0, "action": "hash", "field": "email"},
    {"type": "person", "confidence": 0.92, "action": "redact", "field": "profile_text"},
    {"type": "phone", "confidence": 0.95, "action": "mask", "field": "mobile_number"}
  ],
  "rule_version": "1.0.0",
  "scrubber_version": "1.2.3",
  "triggered_by": "ingestion_api",
  "processing_time_ms": 47
}
```

**Retention Policy:**
- Audit logs retained for 7 years (regulatory requirement)
- Archived to S3 after 90 days (encrypted)
- Monthly exports for compliance reporting

**Acceptance Criteria:**
- [ ] Every scrubbing operation creates exactly one audit record
- [ ] Audit table has no UPDATE/DELETE permissions (except DBA)
- [ ] Query API: `GET /api/v1/admin/pii-audit?source_id={id}&from={date}&to={date}`

### NFR-PII-004: False Positive Rate Threshold

**Requirement:** The PII Scrubber MUST achieve a false positive rate ≤ 3% on skill and technology terms.

**Definition of False Positive:**
A skill name or technology term incorrectly flagged as PII and scrubbed.

**Examples:**
- "Python" detected as PERSON (false positive)
- "Java" detected as GPE location (false positive)
- "Ruby on Rails" detected as PERSON (false positive)

**Mitigation Strategy:**

```yaml
# config/pii-whitelist.yaml
false_positive_whitelist:
  skill_names:
    - "Python"
    - "Java"
    - "Ruby"
    - "Swift"
    - "Pascal"
    - "Ada"
  
  technology_terms:
    - "Oracle"  # Database, not person
    - "Amazon"  # AWS, not location
    - "Spring"  # Framework, not season
  
  context_rules:
    - pattern: "\\b(Python|Java|Ruby)\\s+(Developer|Engineer|Programmer)\\b"
      interpretation: "SKILL"  # Not PII
    
    - pattern: "\\bexperience with (\\w+)\\b"
      interpretation: "SKILL"  # Likely a technology
```

**Whitelist Sources:**
- `skill_master` table: All skill names automatically whitelisted
- Technology dictionary: 500+ common tech terms
- Manual curation: Weekly review of false positives

**Acceptance Criteria:**
- [ ] False positive rate ≤ 3% on test set of 5,000 skill descriptions
- [ ] Manual review queue processes 100% of flagged cases within 7 days
- [ ] Whitelist hot-reloadable without service restart

---

## 7. Failure Handling

### 7.1 Fail-Closed Policy for Ingestion

**Requirement:** If PII scrubbing fails, the system MUST reject the ingestion request (fail-closed).

**Failure Scenarios:**

| Failure Scenario | Policy | HTTP Response | Retry Strategy |
|-----------------|--------|---------------|----------------|
| **Scrubbing rules file corrupt** | REJECT | 503 Service Unavailable | Fix rules, retry after 5 min |
| **NER model unavailable** | DEGRADE* | 202 Accepted (degraded) | Regex-only scrubbing, manual review queued |
| **Database unreachable (audit table)** | REJECT | 503 Service Unavailable | Exponential backoff (1s, 2s, 4s) |
| **Confidence below threshold** | LOG + QUEUE | 202 Accepted | Manual review within 24h |

*Degraded mode: Regex patterns only (no NER), flag for manual review.

**Error Response Example:**

```json
{
  "error": {
    "code": "PII_SCRUB_FAILURE",
    "message": "Unable to scrub PII due to service unavailability",
    "details": {
      "failure_mode": "NER_MODEL_UNAVAILABLE",
      "degraded_mode": true,
      "retry_after": 300,
      "incident_id": "INC-2026-02-16-001"
    }
  },
  "status": 503
}
```

**Acceptance Criteria:**
- [ ] Chaos test: Kill NER service, validate fail-closed behavior
- [ ] Load test: 100% of failures return 503 (no silent failures)
- [ ] Degraded mode logs critical alerts within 30 seconds

### 7.2 Retry Behavior

**Requirement:** Failed scrubbing operations MUST implement exponential backoff with jitter.

**Retry Policy:**

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10) + wait_random(0, 2),
    retry=retry_if_exception_type((DatabaseError, TimeoutError)),
    before_sleep=log_retry_attempt
)
def scrub_with_retry(profile: dict) -> dict:
    return pii_scrubber.scrub(profile)
```

**Configuration:**
- Max attempts: 3
- Initial backoff: 1 second
- Max backoff: 10 seconds
- Jitter: ±2 seconds (prevent thundering herd)

**Acceptance Criteria:**
- [ ] Retry logic tested with simulated transient failures
- [ ] No infinite retry loops (max 3 attempts enforced)
- [ ] Retry count tracked in Prometheus: `pii_scrub_retries_total`

### 7.3 Alerting Requirements

**Requirement:** PII scrubbing failures MUST trigger alerts with appropriate severity.

**Alert Definitions:**

```yaml
# alerts/pii-scrubber.yaml
groups:
  - name: pii_scrubber
    rules:
      - alert: PIIScrubberHighFailureRate
        expr: |
          rate(pii_scrub_failures_total[5m]) > 0.05
        for: 2m
        labels:
          severity: critical
          component: pii_scrubber
        annotations:
          summary: "PII scrubber failure rate exceeds 5%"
          description: "{{ $value }} failures/sec in last 5 minutes"
      
      - alert: PIIDetectedInLogs
        expr: |
          log_scrubbing_pii_detected_total > 0
        for: 1m
        labels:
          severity: critical
          component: logging
        annotations:
          summary: "PII detected in application logs"
          description: "Scrubber bypass detected, immediate investigation required"
      
      - alert: PIIScrubberDegradedMode
        expr: |
          pii_scrubber_degraded_mode == 1
        for: 5m
        labels:
          severity: warning
          component: pii_scrubber
        annotations:
          summary: "PII scrubber operating in degraded mode (regex-only)"
          description: "NER model unavailable, manual review queue growing"
```

**Notification Channels:**
- Critical alerts → PagerDuty → On-call engineer
- Warning alerts → Slack `#security-alerts` channel
- Info alerts → Datadog dashboard only

**Acceptance Criteria:**
- [ ] Alerts fire within 30 seconds of failure condition
- [ ] Alert runbook exists: `docs/runbooks/pii-scrubber-alerts.md`
- [ ] Monthly alert drill validates on-call response

---

## 8. Backward Compatibility & Migration

### 8.1 Handling Existing Embeddings Containing PII

**Challenge:** Approximately 250,000 existing embeddings may contain unscrubbed PII.

**Migration Strategy (4 Phases):**

**Phase 1: Dual-Write (Weeks 1-2)**
- New ingestions write to both old and new schema
- Old: `pii_scrubbed=FALSE` (legacy)
- New: `pii_scrubbed=TRUE`, includes `scrub_metadata`

**Phase 2: Backfill (Weeks 3-6)**
- For each legacy embedding:
  - Attempt to fetch raw data from source system
  - If available: Re-scrub and update
  - If unavailable: Mark as non-compliant, flag for deletion

```sql
-- Backfill script (runs as batch job)
UPDATE team_member_embeddings SET
  pii_scrubbed = FALSE,
  scrub_metadata = '{"legacy": true, "requires_manual_review": true}'::jsonb
WHERE pii_scrubbed IS NULL;
```

**Phase 3: Cutover (Week 7)**
- RAG queries filter: `WHERE pii_scrubbed = TRUE`
- Monitor match quality (should remain stable)
- Gradually reduce legacy embedding queries to 0%

**Phase 4: Cleanup (Weeks 8-12)**
- Delete or archive legacy embeddings after 90-day grace period
- Archive to S3 (encrypted, 7-year retention for compliance)

**Rollback Plan:**
- Keep old table for 90 days
- Revert query filter to include `pii_scrubbed=FALSE`
- Debug scrubbing issues in non-production

**Acceptance Criteria:**
- [ ] Backfill processes 100% of existing embeddings
- [ ] Match quality within 5% of baseline (A/B test)
- [ ] Zero data loss (validated via row counts)
- [ ] Rollback tested in staging environment

### 8.2 Re-Indexing Strategy

**Requirement:** After scrubbing, vector embeddings may change slightly, requiring index optimization.

**Re-Indexing Approach:**

```sql
-- 1. Create new index on scrubbed embeddings
CREATE INDEX CONCURRENTLY idx_embeddings_scrubbed_vector
ON team_member_embeddings USING ivfflat (embedding vector_cosine_ops)
WHERE pii_scrubbed = TRUE;

-- 2. Monitor query performance
EXPLAIN ANALYZE
SELECT team_member_id, 1 - (embedding <=> :query_vec) AS similarity
FROM team_member_embeddings
WHERE pii_scrubbed = TRUE
ORDER BY embedding <=> :query_vec
LIMIT 100;

-- 3. Drop old index after validation
DROP INDEX CONCURRENTLY idx_embeddings_vector;
```

**Performance Targets:**

| Metric | Before Re-Index | After Re-Index | Acceptable Range |
|--------|----------------|----------------|------------------|
| Query Latency (p95) | 80ms | ≤ 85ms | 80-100ms |
| Index Size | 1.2GB | ≤ 1.5GB | < 2GB |
| Index Build Time | N/A | ≤ 30min | < 1hr |

**Acceptance Criteria:**
- [ ] Re-indexing completes without locking table (CONCURRENTLY)
- [ ] Query latency within target after re-index
- [ ] Runbook: `docs/runbooks/reindex-embeddings.md`

### 8.3 Versioned Embedding Namespace (If Required)

**Requirement:** If scrubbed embeddings are semantically incompatible with legacy embeddings, use namespace versioning.

**Namespace Strategy:**

```sql
ALTER TABLE team_member_embeddings
  ADD COLUMN embedding_namespace VARCHAR(20) DEFAULT 'v1_unscrubbed';

-- New scrubbed embeddings
INSERT INTO team_member_embeddings (
  team_member_id,
  embedding,
  pii_scrubbed,
  embedding_namespace,
  ...
) VALUES (
  'TM-12345',
  '[...]',
  TRUE,
  'v2_scrubbed',
  ...
);

-- Query only v2 namespace
SELECT * FROM team_member_embeddings
WHERE embedding_namespace = 'v2_scrubbed'
AND pii_scrubbed = TRUE;
```

**Use Case:**
- If semantic similarity between scrubbed and unscrubbed embeddings diverges significantly
- If clients need to opt into scrubbed vs. unscrubbed data (regulatory reasons)

**Acceptance Criteria:**
- [ ] Namespace column added via migration
- [ ] Queries explicitly specify namespace
- [ ] Deprecation plan for v1 namespace (12 months)

---

## 9. Acceptance Criteria

### 9.1 Functional Acceptance

| ID | Criterion | Validation Method | Target |
|----|-----------|-------------------|--------|
| **AC-F-001** | Email detection (pattern-based) | Unit tests (1,000 samples) | 100% recall |
| **AC-F-002** | Phone detection (pattern-based) | Unit tests (1,000 samples) | 95% recall |
| **AC-F-003** | Name detection (NER) | Integration tests (5,000 samples) | F1 ≥ 0.90 |
| **AC-F-004** | False positive rate | Statistical analysis | ≤ 3% |
| **AC-F-005** | Determinism | Repeated execution test (1,000 iterations) | 100% identical |
| **AC-F-006** | Idempotency | Multi-scrub test | Output unchanged |
| **AC-F-007** | No raw PII in vector DB | Automated scan (100,000 records) | 0 PII instances |
| **AC-F-008** | Rule hot-reload | Integration test | < 5s reload time |

### 9.2 Non-Functional Acceptance

| ID | Criterion | Validation Method | Target |
|----|-----------|-------------------|--------|
| **AC-NF-001** | Scrubbing latency (p95) | Load test (10,000 profiles) | ≤ 50ms |
| **AC-NF-002** | End-to-end latency (p95) | Load test (10,000 profiles) | ≤ 200ms |
| **AC-NF-003** | No PII in logs | Automated daily scan | 0 detections |
| **AC-NF-004** | Audit record creation | Database constraint validation | 100% coverage |
| **AC-NF-005** | Fail-closed enforcement | Chaos engineering test | 100% rejection |

### 9.3 Compliance Acceptance

| ID | Criterion | Validation Method | Target |
|----|-----------|-------------------|--------|
| **AC-C-001** | GDPR Article 5(1)(c) compliance | Legal review + evidence | Documented approval |
| **AC-C-002** | CCPA §1798.100 compliance | Legal review + evidence | Documented approval |
| **AC-C-003** | ISO 27001 A.18.1.4 compliance | External audit | No findings |
| **AC-C-004** | SOC 2 PI1.2 control | External audit | Control tested |
| **AC-C-005** | Audit trail immutability | Database security test | No UPDATE/DELETE |

### 9.4 Migration Acceptance

| ID | Criterion | Validation Method | Target |
|----|-----------|-------------------|--------|
| **AC-M-001** | Backfill completion | SQL query validation | 100% processed |
| **AC-M-002** | Match quality preservation | A/B test comparison | ±5% baseline |
| **AC-M-003** | Zero data loss | Row count + checksum validation | 100% integrity |
| **AC-M-004** | Rollback procedure | Staging environment test | < 1hr rollback time |

---

## 10. Versioning Metadata

**Spec Version:** 1.0.0  
**Change Classification:** MAJOR  
**Semantic Versioning Justification:**

- **MAJOR (1.x.x):** Introduces new architectural component (PII Scrubber Agent), schema changes, and behavioral modifications to RAG pipeline
- **MINOR (x.1.x):** Would apply to future additive changes (e.g., new PII types)
- **PATCH (x.x.1):** Would apply to bug fixes in scrubbing logic

**Linked Architecture Specs:**
- `ai/graph-topology.md` (Node 0 insertion)
- `ai/state-schema.md` (PII scrubbing state fields)
- `data/logical-data-model.md` (Schema changes)
- `non-functional/nfr-security-privacy.md` (Security requirements)
- `functional/fr-6-logging-monitoring-audit.md` (Audit requirements)

**Dependencies:**
- SpaCy `en_core_web_trf` NER model (560MB)
- PostgreSQL ≥ 13 (for improved JSONB performance)

**Backward Compatibility:**
- **Breaking Change:** Existing unscrubbed embeddings incompatible with new queries
- **Migration Required:** 4-phase migration plan (8-12 weeks)
- **API Impact:** Additive only (new `pii_scrubbed` flag in responses)

---

## 11. Impacted Specifications

### 11.1 High-Impact Specifications (Require Updates)

| Specification | Version | Impact | Required Changes |
|--------------|---------|--------|-----------------|
| **ai/graph-topology.md** | 1.0 → 1.1 | Node insertion | Add Node 0 (PII Scrubber Agent) |
| **data/logical-data-model.md** | 1.0 → 1.1 | Schema change | Add `pii_scrub_audit`, modify `team_member_embeddings` |
| **non-functional/nfr-security-privacy.md** | 1.0 → 1.1 | Security requirements | Add PII scrubbing sections |
| **functional/fr-6-logging-monitoring-audit.md** | 1.0 → 1.1 | Audit requirements | Add PII scrub audit trail |
| **ai/state-schema.md** | 1.0 → 1.1 | State fields | Add `pii_scrubbed`, `scrub_metadata` |

### 11.2 Medium-Impact Specifications (Require Clarifications)

| Specification | Version | Impact | Required Changes |
|--------------|---------|--------|-----------------|
| **functional/fr-4-ai-matching-scoring.md** | 1.0 → 1.1 | Processing note | Clarify operates on scrubbed data |
| **functional/fr-3-skill-availability-upsert.md** | 1.0 → 1.1 | Ingestion flow | Add scrubbing step |
| **ai/ai-guardrails.md** | 1.0 → 1.1 | PII guardrails | Enhance existing Section 6 |

### 11.3 Low-Impact Specifications (Minor References)

| Specification | Version | Impact | Required Changes |
|--------------|---------|--------|-----------------|
| **ai/agent-specs/jd-parsing-agent.md** | 1.0 → 1.1 | Note | Document receives scrubbed data |
| **ai/agent-specs/explanation-generation-agent.md** | 1.0 → 1.1 | Guardrail | Ensure explanations don't leak PII |

---

## 12. Compliance Impact Summary

### 12.1 Regulatory Compliance Improvements

| Regulation | Current Status | Post-CR Status | Risk Reduction |
|-----------|---------------|---------------|----------------|
| **GDPR** | ❌ 2/5 articles compliant | ✅ 5/5 articles compliant | 80% liability reduction |
| **CCPA** | ⚠️ 1/3 sections partial | ✅ 3/3 sections compliant | Eliminates intentional violation risk |
| **ISO 27001** | ❌ 3/4 controls | ✅ 4/4 controls | Unblocks certification |
| **SOC 2** | ❌ 1/3 criteria | ✅ 3/3 criteria | Resolves audit findings |

**Estimated Annual Savings:**
- Avoided GDPR fines: $5M (risk-adjusted)
- Avoided CCPA penalties: $500K (risk-adjusted)
- Reduced breach notification costs: $2M (insurance premium reduction)
- **Total:** $7.5M annual risk reduction

### 12.2 Customer Contract Compliance

**At-Risk Contracts (Pre-CR):**
- 15 Fortune 500 contracts requiring PII minimization (total value: $25M ARR)
- 8 government contracts with FedRAMP-equivalent requirements ($12M ARR)
- 3 healthcare contracts requiring HIPAA compliance ($8M ARR)

**Post-CR Status:**
- ✅ All 15 Fortune 500 contracts compliant
- ✅ Government contracts pass compliance review
- ✅ Healthcare contracts HIPAA-ready

**Revenue Protection:** $45M ARR at risk → $0 at risk

---

## 13. Migration Risk Summary

### 13.1 Risk Assessment Matrix

| Risk | Likelihood | Impact | Severity | Mitigation |
|------|------------|--------|----------|------------|
| **Data loss during backfill** | Low | Critical | HIGH | Dry-run in staging, checksums |
| **Performance degradation** | Medium | High | MEDIUM | Load testing, circuit breakers |
| **False negatives (PII leaks)** | Medium | Critical | HIGH | Daily scans, manual reviews |
| **Match quality degradation** | Medium | Medium | MEDIUM | A/B testing, rollback plan |
| **NER model unavailability** | Low | Medium | LOW | Degraded mode, CPU fallback |

**Overall Migration Risk:** MEDIUM (acceptable with mitigation)

### 13.2 Rollback Strategy

**Triggers for Rollback:**
- PII detected in logs (> 1 instance in 24 hours)
- Scrubber error rate > 5% for 10+ minutes
- Match quality degradation > 10% compared to baseline
- Customer escalations > 5 related to data quality

**Rollback Procedure:**
1. Revert application code to previous version (< 10 minutes)
2. Update RAG queries to include `pii_scrubbed=FALSE` records (< 5 minutes)
3. Disable scrubber validation gate (config change, < 1 minute)
4. Monitor for 24 hours, investigate root cause
5. Re-plan migration after fixes validated

**Rollback Time:** < 30 minutes (documented in runbook)

### 13.3 Deployment Plan

**Phased Rollout (8 Weeks):**

| Week | Phase | Activities | Success Criteria |
|------|-------|-----------|-----------------|
| 1-2 | Infrastructure | Deploy scrubber service, NER model, audit tables | Load tests pass |
| 3-4 | Canary (5%) | Enable for 5% of traffic | 0 PII leaks detected |
| 5-6 | Beta (25%) | Expand to 25% of traffic | False positive rate ≤ 3% |
| 7 | GA (75%) | Expand to 75% of traffic | Match quality stable |
| 8 | Full (100%) | 100% traffic, decommission legacy | All acceptance criteria met |

**Gate Reviews:**
- Gate 1 (Week 2): Infrastructure readiness
- Gate 2 (Week 4): Canary validation
- Gate 3 (Week 6): Beta validation
- Gate 4 (Week 8): Full deployment approval

---

## 14. Appendices

### Appendix A: PII Detection Test Corpus

Test corpus available at: `tests/fixtures/pii-test-corpus.json`

**Structure:**
- 10,000 synthetic profiles with labeled PII
- 50 real-world anonymized profiles (labeled)
- 5,000 skill descriptions (technology terms, no PII)
- 100 edge cases (ambiguous names like "Python", "Java")

**Labeling Format:**

```json
{
  "profile_id": "TEST-00001",
  "text": "Jane Doe is a Python Developer at Acme Corp, email: jane.doe@acme.com",
  "labels": [
    {"type": "PERSON", "value": "Jane Doe", "start": 0, "end": 8, "confidence": 1.0},
    {"type": "ORG", "value": "Acme Corp", "start": 36, "end": 45, "confidence": 1.0},
    {"type": "EMAIL", "value": "jane.doe@acme.com", "start": 54, "end": 71, "confidence": 1.0}
  ]
}
```

### Appendix B: Scrubbing Rules Configuration Example

```yaml
# config/pii-scrubbing-rules-v1.yaml
version: "1.0.0"
effective_date: "2026-03-01"

pattern_rules:
  email:
    pattern: "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b"
    action: "hash"
    confidence: 1.0
  
  phone_us:
    pattern: "\\+?1?[-.]?\\(?\\d{3}\\)?[-.]?\\d{3}[-.]?\\d{4}"
    action: "mask"
    mask_format: "+1-***-{last_4}"
    confidence: 0.95

ner_rules:
  person:
    entity_type: "PERSON"
    action: "redact"
    replacement: "<NAME_REDACTED>"
    confidence_threshold: 0.85
  
  gpe:
    entity_type: "GPE"
    action: "generalize"
    mapping_file: "s3://config/location-to-region.json"
    confidence_threshold: 0.85

business_sensitive:
  client_names:
    action: "tokenize"
    token_prefix: "CLIENT_TOKEN_"
    vault_table: "pii_token_vault"
```

### Appendix C: Performance Benchmarks

**Target Hardware:**
- CPU: 8 vCPUs (Intel Xeon or AMD EPYC)
- Memory: 16GB RAM
- GPU: NVIDIA T4 (optional, for NER acceleration)

**Benchmark Results (Estimated):**

| Operation | Throughput | Latency (p50) | Latency (p95) |
|-----------|-----------|---------------|---------------|
| **Pattern-based scrubbing** | 5,000 profiles/sec | 0.2ms | 0.5ms |
| **NER-based scrubbing (CPU)** | 100 profiles/sec | 10ms | 20ms |
| **NER-based scrubbing (GPU)** | 500 profiles/sec | 2ms | 5ms |
| **Combined scrubbing** | 80 profiles/sec | 12ms | 50ms |

**GPU Acceleration Impact:**
- GPU vs CPU speedup: 5x
- GPU memory usage: 4GB VRAM
- Effective throughput with GPU: 500 profiles/sec

---

## 15. References

1. **GDPR (General Data Protection Regulation):** https://gdpr-info.eu/
2. **CCPA (California Consumer Privacy Act):** https://oag.ca.gov/privacy/ccpa
3. **ISO/IEC 27001:2013:** Information Security Management Systems
4. **SOC 2 Type II:** AICPA Trust Service Criteria
5. **NIST SP 800-122:** Guide to Protecting the Confidentiality of PII
6. **SpaCy NER Documentation:** https://spacy.io/usage/linguistic-features#named-entities
7. **OpenAI Data Processing Agreement:** https://openai.com/policies/data-processing-addendum

---

## 16. Approval Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| **CISO** | TBD | ________________ | ________ |
| **DPO** | TBD | ________________ | ________ |
| **Engineering Director** | TBD | ________________ | ________ |
| **Legal Counsel** | TBD | ________________ | ________ |
| **Product Owner** | TBD | ________________ | ________ |

---

**END OF CHANGE REQUEST SPECIFICATION**

**Modification History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-02-16 | Security & Compliance Team | Initial specification |

---

**Next Steps:**
1. Review by stakeholders (Week 1)
2. Approval from CISO, DPO, Legal (Week 2)
3. Technical design review (Week 3)
4. Implementation begins (Week 4)
