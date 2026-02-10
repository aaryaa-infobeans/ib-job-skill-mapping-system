# FR-5: Security, Authentication, and Authorization

## 1. Purpose
This document specifies the security, authentication, and authorization requirements for the system, ensuring that all interactions are secure and access is properly controlled.

## 2. Authentication
- **Traceability**: FR-5.1

- All API endpoints MUST be secured.
- The system SHALL implement OAuth 2.0 with JWT-based authentication for service-to-service communication.
- Access tokens MUST be validated for every API call.
- Token validation MUST include:
  - Signature verification using configured JWT secret key
  - Expiration time (`exp` claim) verification
  - Required claims presence (`sub` or `client_id`)
- The following endpoints are exempt from authentication:
  - `/health` - Health check endpoint
  - `/api/v1/metrics` - Prometheus metrics endpoint
  - `/docs`, `/openapi.json`, `/redoc` - API documentation endpoints
- If JWT secret key is not configured, the system SHALL reject all authenticated requests with HTTP 401.
- No "dev mode" or bypass mechanisms SHALL be allowed in production deployments.

## 3. Authorization
- **Traceability**: FR-5.2, FR-5.3

### 3.1. Service-Level Authorization
- The system SHALL support service-account-based access.
- Specific client systems (e.g., HRMS, Resource Management) will be issued unique client IDs and secrets.
- Access rights SHALL be granted on a per-service basis. For example:
  - The HRMS service account MAY have access to the Requisition API (FR-1) and Match Response API (FR-2).
  - The Resource Management service account MAY have access to the Bulk Upsert API (FR-3).

### 3.2. Role-Based Access Control (RBAC)
- For any future human-facing interfaces or direct API access, the system MUST implement a Role-Based Access Control (RBAC) model.
- The following roles SHALL be defined at a minimum:
  - `HR Admin`
  - `Recruiter`
  - `Delivery Manager`
  - `Engineering Manager`
- Permissions associated with these roles will be defined as part of the implementation of any human-facing features.

## 4. Credential Storage
- Client secrets and any other sensitive credentials MUST be stored securely.
- Storage SHOULD use a dedicated secrets management service (e.g., HashiCorp Vault, AWS Secrets Manager).
- Secrets MUST NOT be stored in plaintext in configuration files or source code.

## 5. Implementation Details
- **Traceability**: FR-5.1, FR-5.2

### 5.1. OAuth2 Middleware
- The system implements `OAuth2Middleware` class in `src/app/middleware/auth.py`
- Middleware configuration:
  - `JWT_SECRET_KEY` environment variable (required)
  - `JWT_ALGORITHM` environment variable (default: HS256)
- Token validation flow:
  1. Extract Authorization header
  2. Verify Bearer token format
  3. Decode and validate JWT signature
  4. Verify token expiration
  5. Validate required claims (sub or client_id)
  6. Inject client_id into request.state for downstream use

### 5.2. Token Requirements
- JWT tokens MUST include:
  - `sub` or `client_id`: Client identifier
  - `exp`: Expiration timestamp (Unix epoch)
  - `iat`: Issued at timestamp (optional but recommended)
- Token format: `Authorization: Bearer <jwt_token>`

### 5.3. Error Responses
- Missing Authorization header: `401 Unauthorized - "Missing Authorization header"`
- Invalid token format: `401 Unauthorized - "Invalid Authorization header format"`
- Expired token: `401 Unauthorized - "Token has expired"`
- Invalid signature: `401 Unauthorized - "Token validation failed"`
- Missing claims: `401 Unauthorized - "Token missing required claims"`
- Unconfigured secret: `401 Unauthorized - "Authentication service not properly configured"`

### 5.4. Status Code Updates
- **Fixed Issue**: Repository status code updated from `1` to `100` to match `requisition_status_master` table
- Status codes defined in `requisition_status_master`:
  - `100` - RECEIVED
  - `101` - VALIDATED
  - `102` - MATCHING_INITIATED
  - `103` - MATCHING_IN_PROGRESS
  - `104` - MATCHING_COMPLETED
  - `105` - FAILED
  - `106` - INVALID_JD
