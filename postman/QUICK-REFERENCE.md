# Postman Collection - Quick Reference

## 🎯 Import & Setup (2 minutes)

1. **Import Files** → Drag both files into Postman:
   - `IB-Job-Skill-Mapping-API.postman_collection.json`
   - `IB-Job-Skill-Mapping-API.postman_environment.json`

2. **Select Environment** → Choose "IB Job Skill Mapping - Local" from dropdown

3. **Start Services**:
   ```powershell
   docker-compose up -d postgres redis
   cd src/app
   uvicorn main:app --host 0.0.0.0 --port 8080 --reload
   ```

4. **Run Collection** → Click collection → Run → Start

## 📂 Collection Structure

```
IB Job Skill Mapping API (17 requests)
├── Health & Monitoring (3)
│   ├── Root Endpoint (GET /)
│   ├── Health Check (GET /health)
│   └── Prometheus Metrics (GET /api/v1/metrics)
│
├── FR-1: Job Requisition (4)
│   ├── Create Requisition - Success ✅
│   ├── Create Requisition - Minimal
│   ├── Create Requisition - Duplicate (409)
│   └── Create Requisition - Invalid (422)
│
├── FR-2: Match Results (3)
│   ├── Get Matches - Success ✅
│   ├── Get Matches - Processing
│   └── Get Matches - Not Found (404)
│
├── FR-3: Skill Availability (3)
│   ├── Bulk Upsert - Success ✅
│   ├── Bulk Upsert - Single Member
│   └── Bulk Upsert - Idempotency Test
│
├── Authentication (2)
│   ├── Protected Endpoint - No Auth (401)
│   └── Protected Endpoint - Invalid Token (401)
│
└── API Documentation (2)
    ├── OpenAPI Spec
    └── Swagger UI
```

## 🔥 Quick Test Workflows

### Workflow 1: Basic Smoke Test (30 seconds)
```
1. Health & Monitoring → Health Check
2. FR-1 → Create Requisition - Success
3. FR-2 → Get Matches - Success (wait 3-5 seconds)
```

### Workflow 2: Full API Test (2 minutes)
```
1. Run entire "Health & Monitoring" folder
2. Run entire "FR-1: Job Requisition" folder
3. Run entire "FR-2: Match Results" folder
4. Run entire "FR-3: Skill Availability" folder
```

### Workflow 3: End-to-End Test (1 minute)
```
1. FR-3 → Bulk Upsert - Success (add team members)
2. FR-1 → Create Requisition - Success (create job)
3. Wait 5 seconds
4. FR-2 → Get Matches - Success (get results)
```

### Workflow 4: Error Handling (30 seconds)
```
1. FR-1 → Create Requisition - Invalid (422)
2. FR-1 → Create Requisition - Duplicate (409)
3. FR-2 → Get Matches - Not Found (404)
4. Authentication → No Auth (401)
```

## 🎨 Key Requests

### ⭐ Create Requisition
```
POST /api/v1/jd-skill-mapping/
Authorization: Bearer {{auth_token}}

✅ Auto-generates unique request_id
✅ Saves correlation_id to environment
✅ Tests: 202 status, correlation_id present
```

### ⭐ Get Matches
```
GET /api/v1/jd-skill-mapping/{{correlation_id}}/matches
Authorization: Bearer {{auth_token}}

✅ Uses correlation_id from previous request
✅ Tests: 200 status, matches array, scores
```

### ⭐ Bulk Upsert
```
POST /api/v1/team-members/skill-availability/bulk-upsert
Authorization: Bearer {{auth_token}}

✅ Auto-generates batch_id
✅ Tests: 202 status, summary statistics
```

## 🔑 Environment Variables

| Variable | Value | Auto-Set |
|----------|-------|----------|
| `base_url` | http://localhost:8080 | No |
| `auth_token` | JWT token (dev mode) | No |
| `correlation_id` | Auto from FR-1 | ✅ Yes |
| `request_id` | Auto-generated | ✅ Yes |

## ✅ Test Assertions (Auto-Run)

Every request validates:
- ✅ HTTP status code
- ✅ Response structure
- ✅ Required fields present
- ✅ Data types correct
- ✅ Error messages clear
- ✅ Performance acceptable

## 🚨 Troubleshooting

| Error | Solution |
|-------|----------|
| Connection refused | Start API: `uvicorn main:app --port 8080` |
| 401 Unauthorized | Check `auth_token` in environment |
| 404 correlation_id | Run FR-1 first to generate correlation_id |
| Database error | Start Postgres: `docker-compose up -d postgres` |

## 📊 Expected Results

### Health Check
```json
{
  "status": "healthy",
  "checks": {
    "database": "healthy"
  }
}
```

### Create Requisition (202)
```json
{
  "correlation_id": "CORR-xxx",
  "status": "PROCESSING"
}
```

### Get Matches (200)
```json
{
  "total_matches": 5,
  "matches": [
    {
      "team_member_id": "TM-001",
      "profile_score": 8.5,
      "fit_level": "STRONG"
    }
  ]
}
```

### Bulk Upsert (202)
```json
{
  "batch_id": "BATCH-xxx",
  "summary": {
    "total_records": 2,
    "successful": 2,
    "failed": 0
  }
}
```

## 🎯 Success Criteria

- ✅ All Health & Monitoring: 3/3 pass
- ✅ FR-1 Success case: 202 + correlation_id
- ✅ FR-2 Success case: 200 + matches array
- ✅ FR-3 Success case: 202 + summary
- ✅ Error cases: Correct status codes (401, 404, 409, 422)
- ✅ Total: 17/17 requests configured

## 📖 Full Documentation

See [postman/README.md](./README.md) for complete documentation including:
- Detailed request descriptions
- Full example payloads
- Response schemas
- Advanced workflows
- Configuration options

---

**Total Setup Time**: ~2 minutes  
**Full Test Run Time**: ~2-3 minutes  
**Quick Smoke Test**: ~30 seconds
