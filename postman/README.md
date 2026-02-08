# IB Job Skill Mapping System - Postman Collection

Comprehensive API test collection for the IB Job Skill Mapping System. This collection covers all API endpoints including job requisition management, skill availability, matching, and monitoring.

## 📦 Contents

- **Postman Collection**: `IB-Job-Skill-Mapping-API.postman_collection.json`
- **Environment File**: `IB-Job-Skill-Mapping-API.postman_environment.json`

## 🚀 Quick Start

### 1. Import Collection

1. Open Postman
2. Click **Import** button
3. Drag and drop both JSON files:
   - `IB-Job-Skill-Mapping-API.postman_collection.json`
   - `IB-Job-Skill-Mapping-API.postman_environment.json`
4. Select the **"IB Job Skill Mapping - Local"** environment from the dropdown

### 2. Configure Environment

The environment includes these variables:

| Variable | Default Value | Description |
|----------|--------------|-------------|
| `base_url` | `http://localhost:8080` | API server base URL |
| `auth_token` | JWT token | Bearer token for authentication |
| `correlation_id` | (auto-set) | Set automatically by FR-1 requests |
| `request_id` | (auto-set) | Set automatically by tests |

**For Production/Staging**: Update `base_url` and `auth_token` in the environment.

### 3. Start Local Services

```powershell
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Start API Gateway
cd src/app
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

### 4. Run Collection

**Option A: Run All Tests**
1. Click the collection name
2. Click **Run** button
3. Select all folders
4. Click **Run IB Job Skill Mapping**

**Option B: Run Specific Folder**
1. Right-click a folder (e.g., "FR-1: Job Requisition")
2. Select **Run folder**

**Option C: Run Individual Request**
1. Select a request
2. Click **Send**

## 📋 Collection Structure

### 1. Health & Monitoring (3 endpoints)

**Public endpoints - no authentication required**

- **Root Endpoint**: `GET /`
  - Returns system information and version
  - Tests: Status 200, response structure

- **Health Check**: `GET /health`
  - Verifies database connectivity
  - Tests: Status 200, database healthy, response time < 200ms

- **Prometheus Metrics**: `GET /api/v1/metrics`
  - Returns Prometheus-format metrics
  - Tests: Status 200, metric format validation

### 2. FR-1: Job Requisition (4 endpoints)

**Protected endpoints - JWT authentication required**

- **Create Requisition - Success**: `POST /api/v1/jd-skill-mapping/`
  - Creates new job requisition
  - Auto-generates unique `request_id`
  - Saves `correlation_id` to environment
  - Tests: Status 202, correlation_id present

- **Create Requisition - Minimal**: `POST /api/v1/jd-skill-mapping/`
  - Tests with minimal required fields
  - Tests: Status 202, valid response structure

- **Create Requisition - Duplicate**: `POST /api/v1/jd-skill-mapping/`
  - Resubmits same `request_id`
  - Tests: Status 409 Conflict

- **Create Requisition - Invalid**: `POST /api/v1/jd-skill-mapping/`
  - Sends invalid payload
  - Tests: Status 422 Unprocessable Entity

### 3. FR-2: Match Results (3 endpoints)

**Protected endpoints - JWT authentication required**

- **Get Matches - Success**: `GET /api/v1/jd-skill-mapping/{correlation_id}/matches`
  - Uses `correlation_id` from FR-1
  - Tests: Status 200, matches array, match structure

- **Get Matches - Processing**: `GET /api/v1/jd-skill-mapping/{correlation_id}/matches`
  - Immediate check after requisition
  - Tests: Status 200, PROCESSING or COMPLETED state

- **Get Matches - Not Found**: `GET /api/v1/jd-skill-mapping/INVALID-ID/matches`
  - Tests invalid correlation_id
  - Tests: Status 404, error message

### 4. FR-3: Skill Availability (3 endpoints)

**Protected endpoints - JWT authentication required**

- **Bulk Upsert - Success**: `POST /api/v1/team-members/skill-availability/bulk-upsert`
  - Multiple team members with skills, allocations, certifications
  - Auto-generates `batch_id`
  - Tests: Status 202, summary statistics, zero failures

- **Bulk Upsert - Single Member**: `POST /api/v1/team-members/skill-availability/bulk-upsert`
  - Minimal single team member
  - Tests: Status 202, single record processed

- **Bulk Upsert - Idempotency Test**: `POST /api/v1/team-members/skill-availability/bulk-upsert`
  - Updates existing team member
  - Tests: Status 202, idempotent operation

### 5. Authentication (2 endpoints)

**Test authentication enforcement**

- **Protected Endpoint - No Auth**: No Authorization header
  - Tests: Status 401 Unauthorized

- **Protected Endpoint - Invalid Token**: Invalid JWT
  - Tests: Status 401

### 6. API Documentation (2 endpoints)

**Access API documentation**

- **OpenAPI Spec**: `GET /openapi.json`
- **Swagger UI**: `GET /docs`

## 🔑 Authentication

### Development Mode

The included JWT token works in development mode:
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LWNsaWVudCIsImNsaWVudF9pZCI6InRlc3QtY2xpZW50IiwiaWF0IjoxNzA2OTc2MDAwLCJleHAiOjE3Mzg1MTIwMDB9.test
```

**Note**: In development mode (`DEV_MODE=true`), JWT signature validation is disabled.

### Production Mode

For staging/production:

1. Obtain valid JWT token from OAuth2 provider
2. Update `auth_token` in environment:
   - Click environment dropdown
   - Select "IB Job Skill Mapping - Local"
   - Update `auth_token` value
   - Save

3. Token format: `Bearer {token}` (auto-handled by collection)

## 🎯 Test Workflows

### Workflow 1: Complete Requisition Flow

1. **Create Requisition** → FR-1: Create Requisition - Success
2. **Wait 2-5 seconds** (for AI processing)
3. **Get Matches** → FR-2: Get Matches - Success

```javascript
// correlation_id is automatically saved from step 1
// and used in step 3
```

### Workflow 2: Skill Availability Update

1. **Bulk Upsert** → FR-3: Bulk Upsert - Success
2. **Create Requisition** → FR-1: Create Requisition - Success
3. **Get Matches** → FR-2: Get Matches - Success (should include new team members)

### Workflow 3: Idempotency Testing

1. **Bulk Upsert - Success** → Save `batch_id`
2. **Bulk Upsert - Idempotency Test** → Same `batch_id`
3. Verify: Both succeed, data updated correctly

### Workflow 4: Error Handling

1. **Create Requisition - Invalid** → Verify 422 validation errors
2. **Create Requisition - Duplicate** → Verify 409 conflict
3. **Get Matches - Not Found** → Verify 404 error
4. **No Auth** → Verify 401 unauthorized

## 📊 Test Assertions

Each request includes test scripts that automatically validate:

- ✅ HTTP status codes
- ✅ Response structure and required fields
- ✅ Data types and formats
- ✅ Error messages
- ✅ Performance metrics (response times)
- ✅ Business logic (e.g., match scores, availability)

View test results in the **Test Results** tab after running requests.

## 🔄 Pre-request Scripts

Some requests include pre-request scripts that:

- Generate unique `request_id` values with timestamps
- Generate unique `batch_id` for bulk operations
- Set dynamic test data
- Calculate timestamps

## 🌍 Multiple Environments

Create additional environments for different deployment stages:

### Staging Environment
```json
{
  "base_url": "https://staging.ibskillmatch.com",
  "auth_token": "<staging-jwt-token>"
}
```

### Production Environment
```json
{
  "base_url": "https://api.ibskillmatch.com",
  "auth_token": "<production-jwt-token>"
}
```

## 🎨 Example Requests

### Create Requisition (Full)

```json
POST /api/v1/jd-skill-mapping/
Authorization: Bearer {{auth_token}}
Content-Type: application/json

{
  "request_id": "REQ-1707389472000-POSTMAN",
  "schema_version": "v1",
  "source_system": "POSTMAN_TEST",
  "job_description": {
    "client_name": "Acme Corporation",
    "title": "Senior Backend Engineer",
    "role": "Backend Development",
    "priority": "HIGH",
    "location": ["Bangalore", "Remote"],
    "work_mode": ["Remote", "Hybrid"],
    "jd_text": "We are seeking a highly skilled Senior Backend Engineer...",
    "requisition_duration_month": 6,
    "experience_range": {
      "min_years": 5,
      "max_years": 10
    }
  },
  "metadata": {
    "created_by": "postman_user",
    "department": "Engineering"
  }
}
```

### Response (202 Accepted)

```json
{
  "request_id": "REQ-1707389472000-POSTMAN",
  "correlation_id": "CORR-4a8f9b2c-e3d1-4567-89ab-cdef01234567",
  "status": "PROCESSING",
  "message": "Requisition accepted for processing",
  "timestamp": "2026-02-08T10:31:12.000Z"
}
```

### Get Matches

```json
GET /api/v1/jd-skill-mapping/CORR-4a8f9b2c-e3d1-4567-89ab-cdef01234567/matches
Authorization: Bearer {{auth_token}}
```

### Response (200 OK)

```json
{
  "correlation_id": "CORR-4a8f9b2c-e3d1-4567-89ab-cdef01234567",
  "status": "COMPLETED",
  "total_matches": 5,
  "matches": [
    {
      "team_member_id": "TM-POST-001",
      "name": "Alice Johnson",
      "profile_score": 8.5,
      "fit_level": "STRONG",
      "availability_score": 7.2,
      "availability_match": true,
      "explanation": "Strong match: Python (4.5/5), FastAPI (4.0/5), 50% available",
      "matched_skills": ["Python", "FastAPI", "PostgreSQL"],
      "skill_gaps": ["Kubernetes"],
      "current_allocation_pct": 50
    }
  ],
  "processing_time_ms": 2847
}
```

### Bulk Upsert

```json
POST /api/v1/team-members/skill-availability/bulk-upsert
Authorization: Bearer {{auth_token}}
Content-Type: application/json

{
  "metadata": {
    "batch_id": "BATCH-1707389472000",
    "timestamp": "2026-02-08T10:00:00Z",
    "source_system": "POSTMAN_TEST"
  },
  "team_members": [
    {
      "team_member_id": "TM-POST-001",
      "name": "Alice Johnson",
      "email": "alice.johnson@example.com",
      "skills": [
        {
          "skill_name": "Python",
          "rating": 4.5,
          "experience_months": 60
        }
      ],
      "allocations": [
        {
          "project_id": "PROJ-001",
          "allocation_percentage": 50,
          "start_date": "2026-01-01",
          "end_date": "2026-06-30"
        }
      ]
    }
  ]
}
```

## 🐛 Troubleshooting

### Connection Refused
```
Error: connect ECONNREFUSED 127.0.0.1:8080
```
**Solution**: Ensure API server is running on port 8080

### 401 Unauthorized
```json
{"detail": "Not authenticated"}
```
**Solution**: 
1. Check `auth_token` is set in environment
2. Verify token is valid (not expired)
3. Ensure `DEV_MODE=true` in `.env` for development

### 404 Not Found - correlation_id
```json
{"detail": "Requisition not found"}
```
**Solution**:
1. Run "FR-1: Create Requisition - Success" first
2. Check `correlation_id` is saved in environment
3. Wait a few seconds for processing

### 422 Validation Error
```json
{"detail": [{"loc": ["body", "field"], "msg": "field required"}]}
```
**Solution**: Check request body matches schema in OpenAPI spec

### Database Connection Error
```json
{"detail": "Database health check failed"}
```
**Solution**: Verify PostgreSQL is running:
```powershell
docker-compose ps postgres
```

### Slow Response Times
**Solution**:
1. Check AI agents are not overloaded
2. Verify Redis is running
3. Check database connection pool
4. Review Prometheus metrics

## 📖 Related Documentation

- [Local Development Runbook](../docs/runbooks/local_dev.md)
- [Local Validation Report](../docs/local-validation-report-2026-02-08.md)
- [API Specifications](../specs/functional/)
  - [FR-1: Requisition Request API](../specs/functional/fr-1-requisition-request-api.md)
  - [FR-2: Requisition Match Response](../specs/functional/fr-2-requisition-match-response.md)
  - [FR-3: Skill Availability Upsert](../specs/functional/fr-3-skill-availability-upsert.md)

## 🤝 Contributing

To add new test cases:

1. Create new request in appropriate folder
2. Add test scripts for validation
3. Update this README with details
4. Export collection and commit

## 📝 Notes

- **Pre-request Scripts**: Auto-generate unique IDs with timestamps
- **Test Scripts**: Validate responses and save variables
- **Environment Variables**: Automatically managed between requests
- **Idempotency**: Uses same IDs to test duplicate handling
- **Workflow**: FR-1 → FR-2 flow automatically handles correlation_id

## ✅ Collection Statistics

- **Total Requests**: 17
- **Folders**: 6
- **Test Scripts**: 17
- **Pre-request Scripts**: 5
- **Environment Variables**: 4
- **Authentication Methods**: Bearer Token

---

**Last Updated**: 2026-02-08  
**Collection Version**: 1.0.0  
**API Version**: v1
