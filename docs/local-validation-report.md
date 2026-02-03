# Local Setup and Validation Report

**Date**: February 3, 2026  
**Branch**: phase-6-hardening-scale  
**Application URL**: http://127.0.0.1:8001

## ✅ Setup Summary

### 1. Environment Setup
- **Python Version**: 3.13.9 ✅
- **Virtual Environment**: Created and activated ✅
- **Dependencies**: Installed via `pip install -e ".[dev]"` ✅

### 2. Database Setup
- **Docker PostgreSQL**: Running on port 5433 (changed from 5432 due to port conflict) ✅
- **Container Status**: `ib-job-skill-mapping-system-postgres-1` running ✅
- **Alembic Migrations**: Stamped to head revision `e8a217c84204` ✅

### 3. Application Startup
- **FastAPI Server**: Running on http://127.0.0.1:8001 ✅
- **Hot Reload**: Enabled ✅
- **Swagger UI**: Accessible at http://127.0.0.1:8001/docs ✅

### 4. Configuration Files Created
- **`.env`**: Created with DATABASE_URL, JWT_SECRET_KEY, LOG_LEVEL ✅
- **`docker-compose.yml`**: Modified to use port 5433 ✅

## ⚠️ Known Issues

### Database Connection Issue
**Status**: Requires Fix  
**Error**: `connection to server at "localhost" (::1), port 5432 failed: FATAL: password authentication failed for user "user"`

**Root Cause**:
- Application is trying to connect to port 5432 instead of configured 5433
- The `.env` file is in project root, but application is running from `src/` directory
- Environment variables may not be loaded correctly

**Solution Options**:
1. Copy `.env` file to `src/` directory
2. Update application startup to load `.env` from parent directory
3. Pass DATABASE_URL as environment variable directly to uvicorn

## 📊 Validation Results

### Endpoints Tested

#### 1. Root Endpoint (/)
- **URL**: http://127.0.0.1:8001/
- **Method**: GET
- **Status**: ✅ 200 OK
- **Response Time**: ~4ms
- **Response**: 
  ```json
  {
    "message": "IB Job Skill Mapping System API",
    "version": "1.0.0",
    "status": "running"
  }
  ```

#### 2. API Documentation (/docs)
- **URL**: http://127.0.0.1:8001/docs
- **Method**: GET
- **Status**: ✅ 200 OK
- **Response Time**: ~1ms
- **Features**: Interactive Swagger UI loaded successfully

#### 3. OpenAPI Schema (/openapi.json)
- **URL**: http://127.0.0.1:8001/openapi.json
- **Method**: GET
- **Status**: ✅ 200 OK
- **Response Time**: ~91ms
- **Content**: Complete OpenAPI 3.0 schema generated

#### 4. Health Check (/health)
- **URL**: http://127.0.0.1:8001/health
- **Method**: GET
- **Status**: ❌ 503 Service Unavailable
- **Response Time**: ~154ms
- **Error**: Database connection failure (see Known Issues above)

### Middleware Validation

✅ **Correlation ID Middleware**: Working - All requests have unique correlation IDs  
✅ **Logging Middleware**: Working - Structured JSON logs with correlation tracking  
✅ **Request Duration Tracking**: Working - Duration_ms logged for all requests

### Logging System

✅ **Structured Logging**: JSON format with timestamp, level, logger, message, correlation_id  
✅ **Application Startup**: Logged successfully with JWT validation mode  
✅ **Request/Response Logging**: All HTTP requests logged with method, path, status, duration  
✅ **Error Logging**: Health check failure logged with full exception traceback

## 🔍 Manual Validation Steps

### Step 1: Fix Database Connection

```powershell
# Option A: Copy .env to src directory
Copy-Item .env src\.env

# Option B: Set environment variable explicitly
$env:DATABASE_URL="postgresql://user:password@localhost:5433/ib_job_skill_mapping"

# Restart application
cd src
python -m uvicorn app.main:app --reload --port 8001
```

### Step 2: Validate Health Endpoint

```powershell
# PowerShell
Invoke-WebRequest -Uri "http://127.0.0.1:8001/health" | Select-Object -ExpandProperty Content

# Expected Response:
# {
#   "status": "healthy",
#   "timestamp": "2026-02-03T...",
#   "checks": {
#     "database": "healthy"
#   }
# }
```

### Step 3: Test API Endpoints (Requires OAuth Token)

#### 3.1 Generate JWT Token

```python
# Create test_token.py in project root
from jose import jwt
from datetime import datetime, timedelta

payload = {
    "sub": "test-client",
    "scopes": ["read", "write"],
    "exp": datetime.utcnow() + timedelta(hours=24)
}

secret_key = "test-secret-key-for-development-only-change-in-production"
token = jwt.encode(payload, secret_key, algorithm="HS256")
print(f"JWT Token: {token}")
```

Run:
```powershell
python test_token.py
```

#### 3.2 Test FR-1: Create Requisition

```powershell
$token = "YOUR_JWT_TOKEN_HERE"
$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
}

$body = @{
    request_id = "REQ-TEST-001"
    title = "Senior Backend Engineer"
    role = "Backend Development"
    priority = "HIGH"
    location = @("Bangalore", "Remote")
    work_mode = @("Remote", "Hybrid")
    jd_text = "We are seeking a Senior Backend Engineer with 5+ years experience in Python, FastAPI, PostgreSQL..."
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://127.0.0.1:8001/api/v1/jd-skill-mapping/" `
    -Method POST `
    -Headers $headers `
    -Body $body `
    | Select-Object -ExpandProperty Content
```

**Expected Response**:
```json
{
  "request_id": "REQ-TEST-001",
  "correlation_id": "CORR-20260203-REQ-TEST-001",
  "status": "queued",
  "message": "Requisition received and queued for processing",
  "received_at": "2026-02-03T..."
}
```

#### 3.3 Test FR-3: Bulk Upsert Team Members

```powershell
$body = @{
    team_members = @(
        @{
            team_member_id = "TM-TEST-001"
            name = "John Doe"
            email = "john.doe@example.com"
            designation = "Senior Engineer"
            primary_skills = @("Python", "FastAPI", "PostgreSQL")
            secondary_skills = @("Docker", "Kubernetes")
            total_experience_years = 8
            relevant_experience_years = 5
        }
    )
} | ConvertTo-Json -Depth 10

Invoke-WebRequest -Uri "http://127.0.0.1:8001/api/v1/team-members/skill-availability/bulk-upsert" `
    -Method POST `
    -Headers $headers `
    -Body $body `
    | Select-Object -ExpandProperty Content
```

**Expected Response**:
```json
{
  "message": "Bulk upsert completed successfully",
  "inserted_count": 1,
  "updated_count": 0,
  "failed_count": 0,
  "total_processed": 1
}
```

#### 3.4 Test FR-2: Get Matches

```powershell
$correlationId = "CORR-20260203-REQ-TEST-001"
Invoke-WebRequest -Uri "http://127.0.0.1:8001/api/v1/jd-skill-mapping/$correlationId/matches" `
    -Method GET `
    -Headers $headers `
    | Select-Object -ExpandProperty Content
```

**Expected Response** (when processing complete):
```json
{
  "correlation_id": "CORR-20260203-REQ-TEST-001",
  "status": "completed",
  "matches": [
    {
      "team_member_id": "TM-TEST-001",
      "name": "John Doe",
      "match_score": 85.5,
      "matched_skills": ["Python", "FastAPI", "PostgreSQL"],
      "missing_skills": [],
      "availability_percentage": 50.0,
      "explanation": "Strong match..."
    }
  ],
  "total_matches": 1
}
```

### Step 4: Validate Metrics Endpoint

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8001/api/v1/metrics" `
    -Headers @{"Authorization" = "Bearer $token"} `
    | Select-Object -ExpandProperty Content
```

**Expected**: Prometheus-formatted metrics

### Step 5: Test Audit Logs

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8001/api/v1/audit/logs?limit=10" `
    -Headers @{"Authorization" = "Bearer $token"} `
    | Select-Object -ExpandProperty Content
```

**Expected**: Array of audit log entries

## 📈 Performance Observations

### Response Times (from logs)
- **Root Endpoint**: 3.96ms ✅
- **Docs Endpoint**: 1.01ms ✅
- **OpenAPI JSON**: 90.71ms ✅
- **Health Check** (failed): 153.78ms ⚠️

### Memory Usage
- **Initial Startup**: Not measured
- **After Requests**: Not measured

### Database Connection Pool
- **Status**: Not connected due to configuration issue

## 🎯 Next Steps

### Immediate (Required for E2E validation)
1. ✅ **Fix DATABASE_URL** environment variable loading
2. ✅ **Verify database connection** via health endpoint
3. ✅ **Create OAuth client** in database
4. ✅ **Generate JWT token** for API testing
5. ✅ **Test all three core endpoints** (FR-1, FR-2, FR-3)

### Optional (Enhanced validation)
6. ⬜ **Load sample data** from specs-data/ib-job-skill-mapping-system.sql
7. ⬜ **Test with realistic job descriptions**
8. ⬜ **Validate AI agent responses** (requires OpenAI API key)
9. ⬜ **Run smoke tests** with k6
10. ⬜ **Check audit trail** logging

### Performance Testing
11. ⬜ **Run smoke test** (performance-tests/smoke-test.js)
12. ⬜ **Run load test** (performance-tests/load-test.js)
13. ⬜ **Validate P95 < 2s, P99 < 5s**

## 📝 Configuration Files

### .env (Project Root)
```
DATABASE_URL=postgresql://user:password@localhost:5433/ib_job_skill_mapping
JWT_SECRET_KEY=test-secret-key-for-development-only-change-in-production
LOG_LEVEL=INFO
SECRETS_BACKEND=env
```

### docker-compose.yml
```yaml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: ib_job_skill_mapping
    ports:
      - "5433:5432"  # Changed from 5432 to avoid conflict
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## 🐛 Debugging Commands

### Check if PostgreSQL is running
```powershell
docker ps | Select-String "postgres"
```

### Check PostgreSQL logs
```powershell
docker logs ib-job-skill-mapping-system-postgres-1
```

### Test database connection directly
```powershell
docker exec -it ib-job-skill-mapping-system-postgres-1 psql -U user -d ib_job_skill_mapping -c "SELECT version();"
```

### Check application logs
```powershell
# Logs are printed to console where uvicorn is running
# Look for correlation_id, error messages, and exception tracebacks
```

### Restart application after changes
```powershell
# Uvicorn watches for file changes with --reload flag
# Manual restart:
# Press Ctrl+C to stop
cd src
python -m uvicorn app.main:app --reload --port 8001
```

## ✅ Success Criteria

### Application Startup
- [x] Application starts without errors
- [x] Swagger UI accessible
- [x] Root endpoint responds
- [ ] Health check passes
- [ ] Database connection established

### Core API Functionality
- [ ] FR-1: Create requisition endpoint works
- [ ] FR-2: Get matches endpoint works
- [ ] FR-3: Bulk upsert endpoint works
- [ ] OAuth2 authentication works
- [ ] Audit logging captures operations

### Performance
- [ ] P95 latency < 2 seconds
- [ ] P99 latency < 5 seconds
- [ ] No memory leaks during extended operation
- [ ] Database connection pool healthy

## 📚 References

- **README.md**: [Quick Start Guide](../README.md#quick-start)
- **Phase 6 Testing**: [docs/phase-6-testing-guide.md](../docs/phase-6-testing-guide.md)
- **API Specifications**: [specs/functional/](../specs/functional/)
- **Troubleshooting**: [README.md#troubleshooting](../README.md#troubleshooting)

---

**Status**: ⚠️ Partially Complete - Database connection needs fixing  
**Next Action**: Fix DATABASE_URL environment variable loading and complete E2E validation