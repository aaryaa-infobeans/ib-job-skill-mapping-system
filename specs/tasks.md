# Engineering Task Backlog

## Phase 1: Foundation & Platform Setup

### Epic: Project Scaffolding & Governance

#### Task 1.1: Initialize Git Repository
- **Description**: Set up the Git repository on the chosen platform (e.g., GitHub) with a default `main` branch.
- **Inputs**: N/A
- **Outputs**: Initialized Git repository.
- **Spec References**:
  - `specs/constitution.md`
- **Acceptance Criteria**:
  - The repository is created and accessible to the team.
- **Dependencies**: None
- **Owner Role**: Platform / DevOps
- **Task Type**: Configure (Completed)

#### Task 1.2: Configure Branch Protection Rules
- **Description**: Implement branch protection rules for the `main` branch to require pull requests and passing status checks before merging.
- **Inputs**: Git repository.
- **Outputs**: Branch protection rules configured.
- **Spec References**:
  - `specs/constitution.md`
- **Acceptance Criteria**:
  - Merging directly to `main` is blocked.
  - Pull requests require at least one approval.
- **Dependencies**: Task 1.1
- **Owner Role**: Platform / DevOps
- **Task Type**: Configure (Completed)

### Epic: Database & Data Model

#### Task 1.3: Provision Cloud-Based PostgreSQL Instances
- **Description**: Provision separate PostgreSQL databases for `development` and `staging` environments using Infrastructure as Code (e.g., Terraform).
- **Inputs**: Cloud provider account.
- **Outputs**: Provisioned PostgreSQL instances with connection details.
- **Spec References**:
  - `specs/data/logical-data-model.md`
- **Acceptance Criteria**:
  - Databases are accessible from the development environment.
  - Connection strings are stored securely.
- **Dependencies**: None
- **Owner Role**: Platform / DevOps
- **Task Type**: Configure (Completed)

#### Task 1.4: Set up Database Migration Tooling
- **Description**: Integrate Alembic into the project to manage database schema migrations.
- **Inputs**: Python project structure, DB connection details.
- **Outputs**: Alembic environment and configuration.
- **Spec References**:
  - `specs/data/logical-data-model.md`
- **Acceptance Criteria**:
  - The `alembic` command can connect to the development database.
- **Dependencies**: Task 1.3
- **Owner Role**: Backend Engineering
- **Task Type**: Build (Completed)

#### Task 1.5: Create Initial Schema Migration
- **Description**: Write the first Alembic migration script to create all tables as defined in the logical data model.
- **Inputs**: Alembic configuration.
- **Outputs**: A migration script (`..._initial_schema.py`).
- **Spec References**:
  - `specs/data/logical-data-model.md`
- **Acceptance Criteria**:
  - Running `alembic upgrade head` successfully creates all tables in the database.
- **Dependencies**: Task 1.4
- **Owner Role**: Backend Engineering
- **Task Type**: Build (Completed)

### Epic: Continuous Integration

#### Task 1.6: Configure CI Pipeline for Linting & Formatting
- **Description**: Set up a CI job (e.g., GitHub Actions) that runs code formatters (e.g., Black) and linters (e.g., Ruff) on every pull request.
- **Inputs**: Git repository.
- **Outputs**: A CI workflow YAML file.
- **Spec References**:
  - `specs/non-functional/nfr-maintainability.md`
- **Acceptance Criteria**:
  - The CI job fails if code is not formatted or has linting errors.
- **Dependencies**: Task 1.1
- **Owner Role**: Platform / DevOps
- **Task Type**: Configure (Completed)

#### Task 1.7: Configure CI Pipeline for Unit Testing
- **Description**: Add a step to the CI pipeline to execute the `pytest` test suite.
- **Inputs**: CI workflow YAML file.
- **Outputs**: Updated CI workflow.
- **Spec References**:
  - `specs/constitution.md`
- **Acceptance Criteria**:
  - The CI job fails if any unit test fails.
- **Dependencies**: Task 1.6
- **Owner Role**: Platform / DevOps
- **Task Type**: Configure (Completed)

---

## Phase 2: Core Data & API Layer

### Epic: API Framework & Request Handling

#### Task 2.1: Initialize FastAPI Application
- **Description**: Set up the basic FastAPI application structure, including the main app entrypoint and initial API router configuration.
- **Inputs**: Python project structure.
- **Outputs**: A runnable FastAPI application.
- **Spec References**:
  - `specs/functional/fr-1-requisition-request-api.md`
- **Acceptance Criteria**:
  - The application can be started locally and serves a root `/` endpoint.
- **Dependencies**: Phase 1
- **Owner Role**: Backend Engineering
- **Task Type**: Build (Completed)

#### Task 2.2: Implement Pydantic Models for FR-3 (Bulk Upsert)
- **Description**: Create Pydantic models for the request and response bodies of the `skill-availability/bulk-upsert` endpoint.
- **Inputs**: `fr-3` specification.
- **Outputs**: Python code defining the Pydantic models.
- **Spec References**:
  - `specs/functional/fr-3-skill-availability-upsert.md`
- **Acceptance Criteria**:
  - Models accurately reflect the JSON structure in `FR-3.3`.
- **Dependencies**: Task 2.1
- **Owner Role**: Backend Engineering
- **Task Type**: Build (Completed)

#### Task 2.3: Implement `POST /api/v1/team-members/skill-availability/bulk-upsert` Endpoint
- **Description**: Implement the business logic for the bulk upsert endpoint, including request validation and idempotent database writes.
- **Inputs**: Pydantic models for FR-3, DB schema.
- **Outputs**: Endpoint implementation in a FastAPI router.
- **Spec References**:
  - `specs/functional/fr-3-skill-availability-upsert.md` (FR-3.1)
  - `specs/data/idempotency-rules.md` (FR-3.4)
- **Acceptance Criteria**:
  - The endpoint correctly processes a valid batch and upserts data to the database.
  - The endpoint returns a `400 Bad Request` for invalid payloads.
- **Dependencies**: Task 2.2, Task 1.5
- **Owner Role**: Backend Engineering
- **Task Type**: Build (Completed)

#### Task 2.4: Write Integration Test for FR-3 Success Case
- **Description**: Create an integration test that sends a valid payload to the bulk upsert endpoint and verifies the database state.
- **Inputs**: FR-3 endpoint implementation.
- **Outputs**: A new `pytest` test case.
- **Spec References**:
  - `specs/functional/fr-3-skill-availability-upsert.md`
- **Acceptance Criteria**:
  - The test passes and confirms that data is correctly inserted and updated.
- **Dependencies**: Task 2.3
- **Owner Role**: QA / Test Automation
- **Task Type**: Test (Completed)

#### Task 2.5: Implement Pydantic Models for FR-1 (Requisition Request)
- **Description**: Create Pydantic models for the request and response bodies of the `/jd-skill-mapping` endpoint.
- **Inputs**: `fr-1` specification.
- **Outputs**: Python code defining the Pydantic models.
- **Spec References**:
  - `specs/functional/fr-1-requisition-request-api.md`
- **Acceptance Criteria**:
  - Models accurately reflect the JSON structure in `FR-1.1`.
- **Dependencies**: Task 2.1
- **Owner Role**: Backend Engineering
- **Task Type**: Build (Completed)

#### Task 2.6: Implement `POST /api/v1/jd-skill-mapping` Endpoint
- **Description**: Implement the logic to accept, validate, and persist a requisition request. At this stage, it will not trigger the AI pipeline.
- **Inputs**: Pydantic models for FR-1, DB schema.
- **Outputs**: Endpoint implementation in a FastAPI router.
- **Spec References**:
  - `specs/functional/fr-1-requisition-request-api.md` (FR-1.1)
  - `specs/data/idempotency-rules.md`
- **Acceptance Criteria**:
  - The endpoint persists the request to the `requisition_requests` table on success.
  - The endpoint returns a `202 Accepted` with a `correlation_id`.
- **Dependencies**: Task 2.5, Task 1.5
- **Owner Role**: Backend Engineering
- **Task Type**: Build (Completed)

#### Task 2.7: Implement `GET /api/v1/jd-skill-mapping/{correlation_id}/matches` Stub
- **Description**: Implement a stub for the match results endpoint that returns a correctly structured but empty or placeholder response.
- **Inputs**: `fr-2` specification.
- **Outputs**: Endpoint implementation.
- **Spec References**:
  - `specs/functional/fr-2-requisition-match-response.md` (FR-2.1)
- **Acceptance Criteria**:
  - The endpoint returns a `200 OK` with a valid JSON structure as per `FR-2.2`.
- **Dependencies**: Task 2.6
- **Owner Role**: Backend Engineering
- **Task Type**: Build (Completed)

---

## Phase 3: AI Orchestration & LangGraph Scaffolding

### Epic: AI Pipeline Scaffolding

#### Task 3.1: Implement LangGraph State Schema
- **Description**: Translate the `GraphState` TypedDict from the specification into executable Python code.
- **Inputs**: `ai/state-schema.md`.
- **Outputs**: A Python file (`state.py`) containing the state definition.
- **Spec References**:
  - `specs/ai/state-schema.md`
- **Acceptance Criteria**:
  - The Python code matches the structure defined in the specification.
- **Dependencies**: Phase 2
- **Owner Role**: AI / ML Engineering
- **Task Type**: Build (Completed)

#### Task 3.2: Implement LangGraph Topology with Stubs
- **Description**: Define the LangGraph graph with nodes and edges as specified. Each node will be a stub function that performs no logic but logs its execution.
- **Inputs**: `ai/graph-topology.md`, `state.py`.
- **Outputs**: A Python file (`graph.py`) containing the graph definition.
- **Spec References**:
  - `specs/ai/graph-topology.md`
- **Acceptance Criteria**:
  - The graph compiles and can be visualized.
  - The sequence of stubbed node executions matches the defined topology.
- **Dependencies**: Task 3.1
- **Owner Role**: AI / ML Engineering
- **Task Type**: Build (Completed)

#### Task 3.3: Integrate Graph Trigger into Requisition API
- **Description**: Modify the `POST /api/v1/jd-skill-mapping` endpoint to trigger the LangGraph execution as a background task.
- **Inputs**: `fr-1` endpoint, `graph.py`.
- **Outputs**: Updated API endpoint logic.
- **Spec References**:
  - `specs/functional/fr-1-requisition-request-api.md` (FR-1.3)
- **Acceptance Criteria**:
  - Submitting a requisition successfully starts the LangGraph execution.
  - The API response time is not blocked by the graph execution.
- **Dependencies**: Task 3.2, Task 2.6
- **Owner Role**: Backend Engineering
- **Task Type**: Build (Completed)

#### Task 3.4: Write Integration Test for Graph Triggering
- **Description**: Create a test to verify that a successful requisition submission correctly initiates the (stubbed) AI pipeline.
- **Inputs**: Updated `fr-1` endpoint.
- **Outputs**: A new `pytest` integration test.
- **Spec References**:
  - `specs/functional/fr-1-requisition-request-api.md`
- **Acceptance Criteria**:
  - The test confirms that the `graph.run()` method is called with the correct initial state.
- **Dependencies**: Task 3.3
- **Owner Role**: QA / Test Automation
- **Task Type**: Test (Completed)

---

## Phase 4: Matching Engine & AI Agent Implementation

### Epic: Deterministic Matching Engine

#### Task 4.1: Implement Availability Evaluation Logic
- **Description**: Write a deterministic Python function to calculate team member availability based on their project allocations.
- **Inputs**: `team_member_allocations` data model.
- **Outputs**: A Python function `evaluate_availability(team_member_id, start_date, end_date)`.
- **Spec References**:
  - `specs/ai/agent-specs/availability-evaluation-agent.md`
- **Acceptance Criteria**:
  - Unit tests verify correct availability calculation for various overlap scenarios.
- **Dependencies**: Task 1.5
- **Owner Role**: Backend Engineering
- **Task Type**: Build

#### Task 4.2: Implement Deterministic Scoring Logic
- **Description**: Write Python functions to calculate `skill_score`, `experience_score`, and the `final_score` based on the algorithms in the spec.
- **Inputs**: Normalized skill and experience data.
- **Outputs**: Scoring functions.
- **Spec References**:
  - `specs/ai/agent-specs/matching-scoring-agent.md` (FR-4.3)
- **Acceptance Criteria**:
  - Unit tests verify that scoring calculations are correct and handle edge cases (e.g., division by zero).
- **Dependencies**: Phase 3
- **Owner Role**: Backend Engineering
- **Task Type**: Build

#### Task 4.3: Implement `Matching_Scoring_Agent` Node
- **Description**: Replace the stub for the `Matching_Scoring_Agent` with the real implementation that uses the scoring and availability functions.
- **Inputs**: `graph.py`, scoring functions, availability function.
- **Outputs**: Updated `graph.py` with the implemented node.
- **Spec References**:
  - `specs/ai/agent-specs/matching-scoring-agent.md`
- **Acceptance Criteria**:
  - The node correctly populates the `state.candidate_scores` field.
- **Dependencies**: Task 4.1, Task 4.2
- **Owner Role**: Backend Engineering
- **Task Type**: Build

### Epic: AI Agent Implementation

#### Task 4.4: Develop Prompt for `JD_Parsing_Agent`
- **Description**: Engineer the system prompt for the JD Parsing Agent to reliably extract information and return it in the specified JSON format.
- **Inputs**: `jd-parsing-agent.md` spec.
- **Outputs**: A final, tested prompt string.
- **Spec References**:
  - `specs/ai/agent-specs/jd-parsing-agent.md`
- **Acceptance Criteria**:
  - The prompt consistently works for a variety of sample job descriptions in a test environment (e.g., LLM playground).
- **Dependencies**: Phase 3
- **Owner Role**: AI / ML Engineering
- **Task Type**: Build

#### Task 4.5: Implement `JD_Parsing_Agent` Node Logic
- **Description**: Replace the agent stub with code that calls the LLM with the engineered prompt and validates the output against the `ParsedJD` schema.
- **Inputs**: Prompt from Task 4.4.
- **Outputs**: Implemented agent node in `graph.py`.
- **Spec References**:
  - `specs/ai/agent-specs/jd-parsing-agent.md`
  - `specs/ai/ai-guardrails.md`
- **Acceptance Criteria**:
  - The node populates `state.parsed_jd` on success.
  - The node populates `state.error_message` on schema validation failure after retries.
- **Dependencies**: Task 4.4
- **Owner Role**: AI / ML Engineering
- **Task Type**: Build

#### Task 4.6: Implement `Skill_Normalization_Agent` Node Logic
- **Description**: Implement the hybrid deterministic/LLM logic for the skill normalization agent.
- **Inputs**: `skill-normalization-agent.md` spec.
- **Outputs**: Implemented agent node in `graph.py`.
- **Spec References**:
  - `specs/ai/agent-specs/skill-normalization-agent.md`
- **Acceptance Criteria**:
  - The node correctly uses deterministic matching first.
  - Unmatched skills are passed to the LLM for fuzzy matching.
  - The node populates `state.normalized_skills`.
- **Dependencies**: Task 4.5
- **Owner Role**: AI / ML Engineering
- **Task Type**: Build

#### Task 4.7: Implement `Explanation_Generation_Agent` Node Logic
- **Description**: Implement the agent that generates human-readable explanations based on the deterministic scores.
- **Inputs**: `explanation-generation-agent.md` spec.
- **Outputs**: Implemented agent node in `graph.py`.
- **Spec References**:
  - `specs/ai/agent-specs/explanation-generation-agent.md` (FR-4.5)
- **Acceptance Criteria**:
  - The node generates explanation strings based on the contents of `state.candidate_scores`.
- **Dependencies**: Task 4.3
- **Owner Role**: AI / ML Engineering
- **Task Type**: Build

#### Task 4.8: Implement `Result_Aggregation_Agent` Node Logic
- **Description**: Implement the final deterministic agent that formats the data for the API response.
- **Inputs**: `result-aggregation-agent.md` spec.
- **Outputs**: Implemented agent node in `graph.py`.
- **Spec References**:
  - `specs/ai/agent-specs/result-aggregation-agent.md`
- **Acceptance Criteria**:
  - The node correctly sorts candidates, derives the `fit_level`, and populates `state.final_results`.
- **Dependencies**: Task 4.7
- **Owner Role**: Backend Engineering
- **Task Type**: Build

#### Task 4.9: Update `GET /matches` Endpoint
- **Description**: Update the `/matches` endpoint to retrieve and return the results from the completed graph execution.
- **Inputs**: `fr-2` endpoint stub, completed graph state.
- **Outputs**: Fully functional `/matches` endpoint.
- **Spec References**:
  - `specs/functional/fr-2-requisition-match-response.md`
- **Acceptance Criteria**:
  - Calling the endpoint after a successful run returns the correctly ranked and formatted list of candidates.
- **Dependencies**: Task 4.8
- **Owner Role**: Backend Engineering
- **Task Type**: Build

---

## Phase 5: Security & Observability Enablement

### Epic: Security Hardening

#### Task 5.1: Implement OAuth2 Token Validation
- **Description**: Add middleware to the FastAPI application to validate OAuth2 JWTs on all API endpoints.
- **Inputs**: FastAPI application.
- **Outputs**: Security middleware.
- **Spec References**:
  - `specs/functional/fr-5-security-auth.md` (FR-5.1)
- **Acceptance Criteria**:
  - Requests without a valid token are rejected with a `401 Unauthorized` error.
- **Dependencies**: Phase 4
- **Owner Role**: Security & Compliance
- **Task Type**: Build

#### Task 5.2: Configure Secrets Management
- **Description**: Integrate a secrets manager (e.g., AWS Secrets Manager, HashiCorp Vault) for storing database credentials and LLM API keys.
- **Inputs**: Application configuration.
- **Outputs**: Configuration to pull secrets from the manager instead of environment variables.
- **Spec References**:
  - `specs/functional/fr-5-security-auth.md`
- **Acceptance Criteria**:
  - No secrets are present in configuration files or source code.
- **Dependencies**: Task 1.3
- **Owner Role**: Platform / DevOps
- **Task Type**: Configure

### Epic: Observability

#### Task 5.3: Implement Structured Logging
- **Description**: Configure the application logger to output structured JSON logs for all events, including a `correlation_id` for each request.
- **Inputs**: FastAPI application.
- **Outputs**: Logging configuration.
- **Spec References**:
  - `specs/functional/fr-6-logging-monitoring-audit.md` (FR-6.1)
- **Acceptance Criteria**:
  - Application logs are in a parsable JSON format.
- **Dependencies**: Phase 4
- **Owner Role**: Backend Engineering
- **Task Type**: Build

#### Task 5.4: Implement Health Check Endpoint
- **Description**: Implement the `GET /api/v1/health` endpoint, including a check for database connectivity.
- **Inputs**: FastAPI application.
- **Outputs**: `/health` endpoint.
- **Spec References**:
  - `specs/functional/fr-6-logging-monitoring-audit.md` (FR-6.3)
- **Acceptance Criteria**:
  - The endpoint returns `200 OK` when the service is healthy and `503 Service Unavailable` if the database is unreachable.
- **Dependencies**: Phase 4
- **Owner Role**: Backend Engineering
- **Task Type**: Build

#### Task 5.5: Implement Metrics Endpoint
- **Description**: Add a Prometheus-compatible `/metrics` endpoint to expose application metrics like request latency and error rates.
- **Inputs**: FastAPI application.
- **Outputs**: `/metrics` endpoint.
- **Spec References**:
  - `specs/functional/fr-6-logging-monitoring-audit.md` (FR-6.3)
- **Acceptance Criteria**:
  - The endpoint exposes metrics that can be scraped by a Prometheus server.
- **Dependencies**: Phase 4
- **Owner Role**: Backend Engineering
- **Task Type**: Build

#### Task 5.6: Implement AI Audit Trail
- **Description**: Ensure that every LLM call within the LangGraph pipeline correctly writes a record to the `langgraph_checkpoints` table.
- **Inputs**: Implemented AI agents.
- **Outputs**: Persistent audit trail in the database.
- **Spec References**:
  - `specs/data/audit-model.md` (FR-6.2)
- **Acceptance Criteria**:
  - After a successful run, the `langgraph_checkpoints` table contains a complete, auditable record of the AI execution, including token counts.
- **Dependencies**: Phase 4
- **Owner Role**: AI / ML Engineering
- **Task Type**: Validate

---

## Phase 6: Hardening & Scale Readiness

### Epic: Performance & Scalability Validation

#### Task 6.1: Create Performance Test Suite
- **Description**: Develop load testing scripts (e.g., using k6 or Locust) to simulate realistic API traffic for all major endpoints.
- **Inputs**: Deployed application on a staging environment.
- **Outputs**: A suite of performance test scripts.
- **Spec References**:
  - `specs/non-functional/nfr-performance.md`
- **Acceptance Criteria**:
  - Scripts are created for FR-1, FR-2, and FR-3 endpoints.
- **Dependencies**: Phase 5
- **Owner Role**: QA / Test Automation
- **Task Type**: Test

#### Task 6.2: Execute Performance & Load Tests
- **Description**: Run the performance test suite against the staging environment to measure latency and throughput under load.
- **Inputs**: Performance test suite.
- **Outputs**: A performance test report.
- **Spec References**:
  - `specs/non-functional/nfr-performance.md`
- **Acceptance Criteria**:
  - The p95 and p99 latencies meet the targets specified in `NFR-1.1` and `NFR-1.2`.
- **Dependencies**: Task 6.1
- **Owner Role**: QA / Test Automation
- **Task Type**: Validate

#### Task 6.3: Execute Scalability Tests
- **Description**: Populate the staging database with 5x the expected production data volume and re-run performance tests to identify bottlenecks.
- **Inputs**: Staging environment.
- **Outputs**: A scalability test report.
- **Spec References**:
  - `specs/non-functional/nfr-scalability.md` (NFR-2.2)
- **Acceptance Criteria**:
  - Performance does not degrade beyond acceptable limits with the larger dataset.
- **Dependencies**: Task 6.2
- **Owner Role**: QA / Test Automation
- **Task Type**: Validate

### Epic: Reliability Validation

#### Task 6.4: Test Idempotent Retry for Bulk Sync
- **Description**: Create and execute a test scenario where a bulk sync job fails midway and is retried, verifying that no duplicate data is created.
- **Inputs**: Deployed application, bulk sync client/script.
- **Outputs**: A reliability test report.
- **Spec References**:
  - `specs/non-functional/nfr-reliability-availability.md` (NFR-3.2)
- **Acceptance Criteria**:
  - The database state is consistent after the failed and retried sync job.
- **Dependencies**: Phase 5
- **Owner Role**: QA / Test Automation
- **Task Type**: Validate
