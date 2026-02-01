**Software Requirements Specification (SRS)** 

**for** 

**Job Description to Team Member Skill Mapping System**

**[1\. Purpose	2](#purpose)**

[2\. System Overview	2](#system-overview)

[3\. Functional Requirements	3](#functional-requirements)

[a. FR-1: Requisition Request API	3](#fr-1:-requisition-request-api)

[b. FR-2: Requisition Match Response	4](#fr-2:-requisition-match-response)

[c. FR-3: Team Member Skills & Availability Upsert API	6](#fr-3:-team-member-skills-&-availability-upsert-api)

[d. FR-4: AI Matching & Scoring	7](#fr-4:-ai-matching-&-scoring)

[e. FR-5: Security, Authentication, and Authorization	8](#fr-5:-security,-authentication,-and-authorization)

[f. FR-6: Logging, Monitoring, and Audit	8](#fr-6:-logging,-monitoring,-and-audit)

[**4\. Data Requirements (Logical View)	9**](#data-requirements-\(logical-view\))

[**5\. Non-Functional Requirements (NFRs)	10**](#non-functional-requirements-\(nfrs\))

[a. NFR-1: Performance	10](#nfr-1:-performance)

[b. NFR-2: Scalability	10](#nfr-2:-scalability)

[c. NFR-3: Reliability & Availability	10](#nfr-3:-reliability-&-availability)

[d. NFR-4: Security & Privacy	10](#nfr-4:-security-&-privacy)

[e. NFR-5: Maintainability	10](#nfr-5:-maintainability)

## 

1. # Purpose {#purpose}

   This document specifies the functional, non-functional, data, security, and operational requirements for a backend system that ingests job requisitions, normalizes job descriptions using AI agents, matches them against internal team member skills and availability, and returns ranked recommendations with explainable reasoning.  
   This SRS is intended for:  
* Solution Architects  
* Backend & AI Engineers  
* Security & Compliance Teams  
* DevOps / SRE Teams  
* Integrating System Owners (HRMS, Resource Management)

2. # System Overview {#system-overview}

   The system is a **backend service** that exposes REST APIs and orchestrates multiple AI agents to perform:  
* Requisition Job Description ingestion and parsing.  
* Skill/experience and availability-based matching.  
* Rank and explanation generation.  
* Nightly ingestion of team member skill and availability data.  
  Data is persisted in PostgreSQL and used by AI agents for scoring and ranking.

3. # Functional Requirements {#functional-requirements}

   1. ## FR-1: Requisition Request API {#fr-1:-requisition-request-api}

**FR-1.1** The system SHALL provide a REST endpoint to accept requisition requests:

* **Method**: POST  
* **Path**: /api/v1/jd-skill-mapping  
* **Request Payload**: Must align with the provided JSON schema:  
  * Top-level fields:  
    * request\_id (string, required, unique per request source).  
    * schema\_version (string, required, e.g., "v1").  
    * source\_system(string, required).  
    * client\_name (string, optional/required based on business rule).  
    * job\_description(object, required).  
    * metadata (object, required).  
  * job\_description fields:  
    * client\_name(string, required).  
    * title (string, required).  
    * role (string, required).  
    * requisition\_duration\_month (integer, optional, \>= 0).  
    * expected\_start\_date (date, ISO 8601, optional/required as per business).  
    * priority (enum: LOW, MEDIUM, HIGH, possibly CRITICAL).  
    * location (array of strings, required)  
    * work\_mode(array of strings,, required):  
    * experience (object, optional):  
      * min\_months (number, \>= 0).  
      * max\_months (number, \>= min\_years).  
    * mandatory\_skills (array of strings, optional but recommended).  
    * preferred\_skills (array of strings, optional).  
    * jd\_text (string, required for free-text parsing).

  **FR-1.2** The system SHALL validate:

* JSON format and required fields.  
* expected\_start\_date format (ISO 8601).  
* experience.min\_months \<= experience.max\_months when both provided.  
  **FR-1.3** On successful validation, the system SHALL:  
* Persist the requisition in PostgreSQL.  
* Trigger the **JD Parsing & Normalization Agent** and **Skill Extraction & Normalization Agent** to:  
  * Normalize role/title.  
  * Extract and normalize mandatory and preferred skills.  
* Trigger the matching pipeline to compute matches against team member skill and availability data.  
  **FR-1.4** The system SHALL return:  
* 202 Accepted or 200 OK depending on synchrony design.  
* A response containing internal correlation\_id and processing status.  
  (If you want immediate synchronous matches, FR-1 and FR-2 can be combined; otherwise, FR-1 only creates/queues and FR-2 fetches results.)

---

2. ## FR-2: Requisition Match Response {#fr-2:-requisition-match-response}

The response payload structure you provided is the basis for a **match result resource**.

**FR-2.1** The system SHALL provide an endpoint to retrieve ranked team members for a given requisition:

* **Method**: GET  
* **Path**: /api/v1/jd-skill-mapping/{correlation\_id}/matches  
* **Query Params** (optional):  
  * limit (e.g., default 50).

  **FR-2.2** The match results payload SHALL be shaped as:

    {

      "metadata": {

          "correlation\_id": "CORR-9987123",

          "timestamp": "2026-01-19T02:00:00Z",

          "total\_records": 1500,

          "batch\_number": 1,

          "total\_batches": 15,

          "records\_in\_batch": 100,

          "source\_system": "IB\_JOB\_SKILL\_MAP\_v1",

          "schema\_version": "1.1",

          "status": {

            "code": 0,

            "key": "MATCHING\_COMPLETED",

            "message": "Skill matching completed successfully"

          }

      },

     "team\_members": \[

        {

            "team\_member\_id": "EMP\_8842",

            "profile\_score": 87.00,

            "fit\_level": "HIGH",

            "availability\_match": true,

            "explanation": \[

              "Matched 3/3 required skills: Python, DBMS, AWS","Experience exceeds requirement"

            \],

      		}\]

    }

  **FR-2.3** The system SHALL ensure:

* match\_score reflects an aggregate of:  
  * Skill match.  
  * Experience fit.  
  * Availability fit.  
* fit\_level is derived from match\_score thresholds and possibly business rules (e.g., HIGH if ≥ 0.70).  
  **FR-2.4** The system SHALL include at least one human-readable explanation string per team member describing why they were matched (e.g., skills matched, availability, seniority).  
  **FR-2.5** The system SHALL correlate metadata.correlation\_id with the original requisition request if provided.

---

3. ## **FR-3: Team Member Skills & Availability Upsert API** {#fr-3:-team-member-skills-&-availability-upsert-api}

   **FR-3.1** The system SHALL provide a REST endpoint for bulk upsert of team member skills and availability:

* **Method**: POST  
* **Path**: /api/v1/team-members/skill-availability/bulk-upsert  
* **Request Payload**: Must follow the provided “Candidate Skill Availability Payload” structure.  
  **FR-3.2** metadata fields are required for every batch:  
* batch\_id (string, unique per sync run).  
* timestamp (ISO 8601).  
* total\_records, batch\_number, total\_batches, records\_in\_batch (integers).  
* source\_system (string, e.g., EAGLE\_v1).  
* schema\_version (string, e.g., 1.1).  
* status.code (integer; 0 indicates success, non-zero values are reserved for source-side errors).  
* status.key (string; canonical status identifier).  
* status.message (string; descriptive message for the request outcome).  
  **FR-3.3** Each team\_members\[\] entry SHALL support:  
* team\_member\_id (string, required; primary identifier).  
* team\_member\_status (enum: active, inactive, terminated, etc.).  
* profile\_type (string or enum).  
* experience\_in\_months (integer, required; months).  
* full\_name (string, required).  
* designation (string).  
* base\_location (string).  
* work-mode (string; will be normalized to work\_mode internally).  
* profile (URL string, e.g., to profile document: [https://www.infobeans.com/eagle/profile.docx](https://www.infobeans.com/eagle/profile.docx)).  
  * allocations\[\]:  
    * project\_id (string, required).  
    * project\_name (string, optional).  
    * allocation\_percentage (float; 0–100).  
    * start\_date (ISO 8601 date).  
    * end\_date (ISO 8601 date or null).  
    * billable (boolean).  
    * is\_deleted (boolean; true means logically soft-deleted allocation).  
  * skills\[\]:  
    * skill\_id (string, required).  
    * name (string, required).  
    * category (string).  
    * rating (integer, e.g., 1–5).  
    * experience\_in\_months(number).  
    * certifications\[\]:  
      * name (string).  
      * issuer (string).  
      * issued\_date (ISO 8601 date).  
      * valid\_till (ISO 8601 date).  
    * is\_deleted (boolean; logical deletion).

  **FR-3.4** The system SHALL implement **idempotent upsert** semantics:

* For the same team\_member\_id and allocation\_id/skill\_id, incoming records update existing ones.  
* is\_deleted \= true should mark allocations/skills as inactive but keep them for history.  
  **FR-3.5** The system SHALL persist metadata and processing results for each batch in sync\_logs files.  
  **FR-3.6** The system SHALL expose a status (HTTP 200/202) and simple sync processing summary (e.g., records received, inserted, updated, failed).

---

4. ## **FR-4: AI Matching & Scoring** {#fr-4:-ai-matching-&-scoring}

   **FR-4.1** The system SHALL use:

* JD/Requisition Parsing Agent to:  
  * Normalize title, role, seniority.  
  * Extract skills from mandatory\_skills, preferred\_skills, and jd\_text.

  **FR-4.2** The system SHALL use a Skill Extraction & Normalization Agent to:

* Normalize skill names from requisition and team member skills to a canonical form.  
* E.g., “JS” / “Javascript” → “JavaScript”.  
  **FR-4.3** The system SHALL compute:  
* A **skill match score** between requisition and each team member based on:  
  * % of mandatory skills matched.  
  * % of preferred skills matched.  
  * Proficiency indicators (e.g., rating, experience\_in\_months).  
* An **availability match** based on:  
  * Required expected\_start\_date and requisition\_duration\_month.  
  * Existing allocations (billable and non-billable).  
  * Derived free capacity (e.g., \<100% allocated in required window).

  **FR-4.4** The system SHALL produce:

* Aggregate match\_score (0–1).  
* fit\_level (e.g., thresholds on match\_score and availability).  
* availability\_match boolean.  
  **FR-4.5** The system SHALL generate **explanations** for each recommended team member, including at minimum:  
* A summary of mandatory and preferred skills matched.  
* Experience vs required experience.  
* Availability alignment (e.g., “Available from 2026-02-10 with 80% capacity”).

---

5. ## **FR-5: Security, Authentication, and Authorization** {#fr-5:-security,-authentication,-and-authorization}

   **FR-5.1** All APIs SHALL be secured using OAuth2/JWT or organization SSO.

   **FR-5.2** The system SHALL support service-account style access for:

* HRMS (for requisition APIs).  
* Resource Management Systems (for bulk upsert).  
  **FR-5.3** The system SHALL implement RBAC for any future human-facing endpoints:  
* Roles: HR Admin, Recruiter, Delivery Manager, Engineering Manager.

---

6. ## **FR-6: Logging, Monitoring, and Audit** {#fr-6:-logging,-monitoring,-and-audit}

   **FR-6.1** The system SHALL log:

* All API requests/responses (at least metadata and high-level outcome).  
* Matching execution summaries (e.g., number of candidates evaluated, top match scores).  
* Sync batch processing (success/fail, counts).  
  **FR-6.2** The system SHALL store:  
* Access logs or audit records for token usage for every LLM interaction to fulfill the requisition request(for compliance and LLM usage analysis).  
  **FR-6.3** The system SHALL expose health and metrics endpoints:  
* GET /api/v1/health  
* GET /api/v1/metrics 

---


4. # Data Requirements (Logical View) {#data-requirements-(logical-view)}

   At a minimum, the PostgreSQL schema must support:  
* auth\_clients   
  * id, client\_name, client\_code, client\_secret\_hash, auth\_type, is\_active, created\_at  
* auth\_access\_tokens  
  * id, auth\_client\_id, access\_token, expires\_at, is\_revoked, issued\_at  
* requisition\_status\_master  
  * status\_id, status\_key, status\_message  
* requisition\_requests  
  * id,request\_id ,auth\_client\_id ,status,client\_name ,correlation\_id,received\_at,completed\_at   
* requisition\_detail  
  * id, requisition\_request\_id, payload\_json, payload\_hash, created\_at  
* team\_member  
  * team\_member\_id,, designation, profile\_type, is\_active, experience\_in\_months, base\_location, work\_type, profile\_url, created\_at.  
* team\_member\_allocations  
  * team\_member\_id, project\_id, allocation\_percentage, start\_date, end\_date, billable, is\_deleted.  
* category\_master  
  * category\_id, category\_name, created\_at.	  
* skill\_master  
  * skill\_id, skill\_name, category\_id,created\_at.  
* team\_member\_skill  
  * team\_member\_id, skill\_id, rating, experience\_in\_months, is\_deleted  
* skill\_certification  
  * certification\_id, team\_member\_id, skill\_id, certificate,issuer, issued\_date, valid\_till  
* langgraph\_checkpoints  
  * id, request\_id, node\_name, state\_json,token\_count, created\_at

---

5. # **Non-Functional Requirements (NFRs)** {#non-functional-requirements-(nfrs)}

   1. ### NFR-1: Performance {#nfr-1:-performance}

      1. NFR-1.1: For typical requisitions, the system SHOULD return top-N matches within **a few seconds** for up to \~1500 team members.  
      2. NFR-1.2: Read of previously computed matches (GET /api/v1/jd-skill-mapping/{correlation\_id}/matches) SHOULD be **sub-second** for up to 50 results.

   2. ### NFR-2: Scalability {#nfr-2:-scalability}

      1. NFR-2.1: The system SHALL support horizontal scaling of stateless API and AI agent services.  
      2. NFR-2.2: The design SHALL support growth beyond 1500 team members without major architectural changes.

   3. ### NFR-3: Reliability & Availability {#nfr-3:-reliability-&-availability}

      1. NFR-3.1: Target API uptime **≥ 99.5%**.  
      2. NFR-3.2: Nightly sync jobs SHALL be resilient to partial failures; batches can be retried idempotently by batch\_id.

   4. ### NFR-4: Security & Privacy {#nfr-4:-security-&-privacy}

      1. NFR-4.1: All data in transit SHALL be encrypted (TLS).  
      2. NFR-4.2: All PII SHALL be minimized; only necessary attributes for matching are stored.  
      3. NFR-4.3: Data at rest in PostgreSQL SHALL be encrypted per org policies.

   5. ### NFR-5: Maintainability {#nfr-5:-maintainability}

      1. NFR-5.1: All APIs SHALL have OpenAPI/Swagger documentation.  
      2. NFR-5.2: Versioning (api\_version, schema\_version) SHALL be supported to enable evolution without breaking clients.

