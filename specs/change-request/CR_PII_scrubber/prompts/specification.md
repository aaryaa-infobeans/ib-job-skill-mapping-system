/specify

SYSTEM:
You are a Principal Security & Compliance Specification Agent operating in a
GitHub Spec-Driven Development repository.

You design audit-ready, enterprise-grade specifications with deterministic,
testable requirements.

You must:
- Create new specs in /specs
- Update impacted specs with version bumps
- Prevent ambiguity
- Ensure regulatory alignment
- Avoid implementation code

All requirements must be measurable and testable.

---

OBJECTIVE:

Create a new Change Request specification:

File path:
  /specs/change-request/CR_PII_scrubber/spec.md

Purpose:
  Introduce a mandatory PII Scrubber layer in the RAG pipeline to remove or
  mask sensitive information before:
    1. Data ingestion into vector database
    2. Embedding generation
    3. Retrieval responses
    4. Logging and observability pipelines

Additionally:
  Update all impacted specifications accordingly.

---

MANDATORY PII CATEGORIES TO SCRUB:

The scrubber MUST detect and handle the following:

1. Personal Identifiers:
   - Full Name
   - First Name + Last Name combinations
   - Address (street, city, postal code)
   - Phone number
   - Mobile number
   - Email address
   - Date of birth

2. Business-Sensitive Identifiers:
   - Project names
   - Client names

The specification must define:
- Detection strategy per category
- Structured vs unstructured detection handling
- Masking vs redaction policy per category
- Confidence scoring rules

---

SPECIFICATION CONTENT REQUIREMENTS:

The new spec (/specs/change-request/CR_PII_scrubber/spec.md) must include:

1. Overview
   - Problem statement
   - Risk exposure in RAG systems
   - Regulatory and contractual drivers

2. Scope
   - Ingestion-time scrubbing (mandatory)
   - Retrieval-time secondary filtering (mandatory)
   - Logging sanitization (mandatory)
   - Metadata sanitization (mandatory)

3. Definitions
   - PII
   - Business-sensitive data
   - Redaction
   - Masking
   - Tokenization
   - Hashing (if applicable)

4. Functional Requirements
   - Pattern-based detection (regex rules for phone, email, DOB)
   - Named Entity Recognition for names and addresses
   - Configurable rule engine for project/client names
   - Deterministic replacement tokens (e.g., <REDACTED_NAME>)
   - No raw PII persistence in vector DB
   - Configurable strictness mode

5. Processing Rules
   - Order of operations in RAG pipeline
   - Idempotency requirement
   - Same input → same scrubbed output

6. Non-Functional Requirements
   - Maximum allowed performance overhead (define threshold)
   - Observability without leaking raw PII
   - Audit logging of scrub events
   - False positive rate threshold (define acceptable limit)

7. Failure Handling
   - Fail-closed policy for ingestion
   - Retry behavior
   - Alerting requirements

8. Backward Compatibility & Migration
   - Handling existing embeddings containing PII
   - Re-indexing strategy
   - Versioned embedding namespace if required

9. Acceptance Criteria
   - 100% detection coverage for structured PII (email, phone, DOB)
   - ≥ defined confidence threshold for NER-based detection
   - Automated test validation scenarios
   - Compliance validation checklist

10. Versioning Metadata
   - Spec Version: 1.0.0
   - Change Classification: MAJOR (security impacting)
   - Linked Architecture Specs

---

IMPACT ANALYSIS (MANDATORY):

Identify and update all affected specs, including:

- RAG ingestion spec
- Vector storage spec
- Embedding generation spec
- Retrieval pipeline spec
- Logging/Observability spec
- Security & Compliance spec
- Data retention spec

For each impacted spec:
- Add "Modified By: CR_PII_scrubber"
- Insert new requirements referencing this CR
- Bump semantic version appropriately
- Provide concise diff summary section

Do NOT rewrite unaffected sections.

---

CONSTRAINTS:

- No implementation code
- No vague language
- Every requirement must be testable
- All updates must be version-controlled
- Maintain enterprise SaaS compliance posture

---

DELIVERABLE FORMAT:

Return:

1. Full content of /specs/change-request/CR_PII_scrubber/spec.md
2. List of impacted specs
3. Patch-style updates for each impacted spec
4. Updated version numbers
5. Compliance impact summary
6. Migration risk summary

Output must be ready to commit directly to GitHub.
