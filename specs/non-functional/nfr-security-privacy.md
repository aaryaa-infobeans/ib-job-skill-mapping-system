# NFR: Security & Privacy

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
- **Traceability**: NFR-4.2
- **Implementation**:
  - The system SHALL only store attributes that are absolutely necessary for the matching process (e.g., `team_member_id`, skills, experience, allocations).
  - Sensitive PII such as full names, while required for the upsert process (FR-3.3), should be handled with care. The system should evaluate if storing `full_name` is necessary long-term or if it can be discarded after initial processing.
  - No other PII from a CV or profile document should be stored unless explicitly required for a specified and approved purpose.

### 3.2. Access Control
- **Requirement**: Access to data, especially PII, MUST be strictly controlled.
- **Implementation**:
  - The RBAC model defined in FR-5 SHALL be enforced.
  - Direct database access MUST be restricted to a minimal number of authorized personnel (e.g., database administrators, SREs).
  - All access to data, whether through the API or directly, MUST be logged for auditing purposes.
