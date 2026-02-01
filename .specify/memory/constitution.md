# Job Description to Team member Skill Mapping System Constitution

## Core Principles

### I. API-First
The system is a backend service at its core, and all functionality MUST be exposed via REST APIs. This ensures that the system is interoperable and can be integrated with other systems easily.

### II. AI-Driven Matching
The system MUST use AI agents to perform job description parsing, skill extraction, and matching. This is a core feature of the system and ensures that the matching process is intelligent and accurate.

### III. Data-Centric Architecture
The system MUST use a PostgreSQL database to persist all data, including requisitions, team member skills, and availability. The data model should be designed to support the core matching and ranking functionality.

### IV. Security by Design
All APIs MUST be secured using appropriate authentication and authorization mechanisms (e.g., OAuth2/JWT or organization SSO). The system MUST also implement Role-Based Access Control (RBAC) for any human-facing endpoints.
- **PII Handling**: All Personally Identifiable Information (PII) MUST be minimized, and only necessary attributes for matching are stored. Access to PII MUST be strictly controlled and logged.

### V. Observability
The system MUST have robust logging, monitoring, and auditing capabilities. This includes logging all API requests and responses, as well as providing health and metrics endpoints.

## Additional Constraints

- **Technology Stack**:
    - **Database**: The primary database MUST be PostgreSQL.
    - **Backend**: Python 3.11+ with FastAPI
    - **API Style:** REST, API-first, OpenAPI documented
    - **Message Broker:** RabbitMQ
    - **AI/ML**: LangGraph,  LangChain, Scikit-learn
- **Performance**: The system MUST return top-N matches within a few seconds for a typical number of team members. Retrieval of previously computed matches MUST be sub-second.
- **Scalability**: The system architecture MUST support horizontal scaling of its stateless components to handle future growth.
- **Reliability**: The system MUST maintain a minimum uptime of 99.5%.

### Security
- **Authentication:** OAuth2 + JWT
- **Authorization:** Role-Based Access Control (RBAC)
- **Secrets Management:** Vault or cloud-native key management
- **Transport Security:** TLS enforced


## Development Workflow

- **API Documentation**: All APIs MUST be documented using the OpenAPI/Swagger specification.
- **Versioning**: The system MUST support versioning for both the API and the data schema to allow for evolution without breaking client integrations.
- **Testing Strategy**:
    - **Unit Tests**: All new code MUST be accompanied by unit tests with a target of 80% code coverage.
    - **Integration Tests**: Integration tests MUST be written for all API endpoints and critical workflows.
    - **End-to-End Tests**: E2E tests SHOULD be created for key user journeys.
- **CI/CD**:
    - A CI/CD pipeline MUST be implemented to automate the build, test, and deployment process.
    - All code MUST pass linting, static analysis, and all tests in the CI pipeline before being merged to the main branch.
- **Error Handling**:
    - The system MUST implement a standardized error handling and reporting mechanism.
    - All errors MUST be logged with a unique correlation ID to facilitate debugging.

## Governance
This constitution is the single source of truth for the system's architecture and development practices. Any deviation must be justified, documented, and approved by the project stakeholders.

**Version**: 1.1 | **Ratified**: 2026-02-01 | **Last Amended**: 2026-02-01