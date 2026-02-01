# NFR: Performance

## 1. Purpose
This document specifies the performance requirements for the system to ensure a responsive and efficient user experience for integrating client systems.

## 2. Performance Requirements

### 2.1. Asynchronous Matching Latency
- **Requirement**: For a typical job requisition, the system SHOULD complete the entire AI matching pipeline and have results ready for retrieval within a few seconds.
- **Traceability**: NFR-1.1
- **Context**: This applies to the asynchronous processing time from when a requisition is submitted (FR-1) to when the results are persisted and available for retrieval (FR-2).
- **Measurement**: This will be measured as the 95th percentile (p95) of the duration between the request timestamp and the completion timestamp for the matching process.
- **Target**: p95 latency < 5 seconds for a repository of up to 1500 team members.

### 2.2. Match Retrieval Latency
- **Requirement**: The retrieval of previously computed match results MUST be sub-second.
- **Traceability**: NFR-1.2
- **Context**: This applies to the `GET /api/v1/jd-skill-mapping/{correlation_id}/matches` endpoint (FR-2).
- **Measurement**: This will be measured as the 99th percentile (p99) of the response time for this endpoint.
- **Target**: p99 response time < 1000ms for a response size of up to 50 records.

### 2.3. Bulk Upsert Throughput
- **Requirement**: The bulk upsert API for team member skills and availability SHOULD be able to process a high volume of records efficiently.
- **Context**: This applies to the `POST /api/v1/team-members/skill-availability/bulk-upsert` endpoint (FR-3).
- **Measurement**: This will be measured in records processed per second.
- **Target**: To be determined based on the size of the nightly sync and the available processing window. The initial target is 100 records/second.
