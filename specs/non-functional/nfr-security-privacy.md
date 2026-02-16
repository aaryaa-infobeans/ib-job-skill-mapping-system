# NFR: Security & Privacy

**Version:** 1.1  
**Modified By:** CR_PII_scrubber (CR-PII-001)  
**Last Updated:** 2026-02-16  

## 1. Purpose
This document specifies the security and privacy requirements to protect the system and its data from unauthorized access and to ensure compliance with privacy regulations.

## 2. Security Requirements

### 2.1. Data in Transit Encryption
- **Requirement**: All data transferred over the network MUST be encrypted.
- **Traceability**: NFR-4.1
- **Implementation**: All API endpoints SHALL enforce HTTPS by using TLS (Transport Layer Security) 1.2 or higher.

### 2.2. Data at Rest Encryption
- **Requirement**: All data at rest in the PostgreSQL database SHALL be encrypted.
- **Traceability**: NFR-4.3
- **Implementation**: This will be implemented using the native encryption-at-rest features of the cloud provider or database hosting environment, adhering to organizational policies.

## 3. Privacy Requirements

### 3.1. PII Minimization
- **Requirement**: The system MUST minimize the storage of Personally Identifiable Information (PII).
- **Traceability**: NFR-4.2, CR-PII-001
- **Implementation**:
  - The system SHALL only store attributes that are absolutely necessary for the matching process (e.g., `team_member_id`, skills, experience, allocations).
  - Sensitive PII such as full names, while required for the upsert process (FR-3.3), should be handled with care. The system should evaluate if storing `full_name` is necessary long-term or if it can be discarded after initial processing.
  - No other PII from a CV or profile document should be stored unless explicitly required for a specified and approved purpose.

### 3.1-A. PII Scrubbing (NEW: CR-PII-001)
- **Requirement**: All data entering the RAG pipeline MUST undergo automated PII detection and scrubbing.
- **Traceability**: CR-PII-001 (FR-PII-001 through FR-PII-006)
- **Implementation**:
  - **Ingestion-Time Scrubbing**: Mandatory for all data before embedding generation or storage.
  - **Detection Methods**: 
    - Pattern-based (regex) for structured PII: email (100% recall), phone (95% recall), DOB
    - NER-based (SpaCy) for unstructured PII: names (F1≥0.90), locations, organizations
  - **Scrubbing Actions**:
    - **Redaction**: Complete removal with generic tokens (`<NAME_REDACTED>`)
    - **Masking**: Partial obfuscation preserving structure (`+1-***-0123`)
    - **Tokenization**: Reversible replacement for business-sensitive data (client/project names)
    - **Hashing**: One-way SHA-256 for duplicate detection without storing plaintext
  - **Performance**: Scrubbing latency ≤ 50ms (p95), false positive rate ≤ 3%
  - **Audit**: Every scrubbing operation logged in `pii_scrub_audit` table (immutable, 7-year retention)
  - **Fail-Closed**: If scrubbing fails, reject ingestion (503 Service Unavailable)
  - **Retrieval Filtering**: Secondary PII filter on RAG responses (defense-in-depth)
- **Compliance**: GDPR Article 5(1)(c), CCPA §1798.100, ISO 27001 A.18.1.4, SOC 2 PI1.2

### 3.2. Access Control
- **Requirement**: Access to data, especially PII, MUST be strictly controlled.
- **Implementation**:
  - The RBAC model defined in FR-5 SHALL be enforced.
  - Direct database access MUST be restricted to a minimal number of authorized personnel (e.g., database administrators, SREs).
  - All access to data, whether through the API or directly, MUST be logged for auditing purposes.
