# Postman Testing Guide

## Application Status ✅

**Application is running successfully!**

- **Base URL:** `http://127.0.0.1:9000`
- **API Documentation:** http://127.0.0.1:9000/docs
- **Health Check:** http://127.0.0.1:9000/health

## Quick Verification

### Health Check Results:
```json
{
  "status": "healthy",
  "checks": {
    "database": "healthy"
  }
}
```

### Root Endpoint:
```json
{
  "message": "IB Job Skill Mapping System",
  "version": "0.1.0"
}
```

## Using Postman Collection

### Step 1: Update Environment Variables

The Postman environment file is configured for port **8080**, but the application is running on port **9000**.

**Option A: Update in Postman Desktop**
1. Open Postman Desktop
2. Click "Import" → Select files:
   - `postman/IB-Job-Skill-Mapping-API.postman_collection.json`
   - `postman/IB-Job-Skill-Mapping-API.postman_environment.json`
3. Select the imported environment "IB Job Skill Mapping - Local"
4. Edit the environment and change:
   - `base_url` from `http://localhost:8080` to `http://localhost:9000`
5. Save the environment

**Option B: Manual Testing via Swagger UI**
1. Open browser: http://127.0.0.1:9000/docs
2. Test endpoints directly in the interactive documentation

### Step 2: Test Key Endpoints

#### 1. Root Endpoint
- **Method:** GET
- **URL:** `http://127.0.0.1:9000/`
- **Expected:** 
  ```json
  {
    "message": "IB Job Skill Mapping System",
    "version": "0.1.0"
  }
  ```

#### 2. Health Check
- **Method:** GET
- **URL:** `http://127.0.0.1:9000/health`
- **Expected:** 
  ```json
  {
    "status": "healthy",
    "checks": {
      "database": "healthy"
    }
  }
  ```

#### 3. Submit Job Requisition (requires auth)
- **Method:** POST
- **URL:** `http://127.0.0.1:9000/api/v1/requisitions`
- **Headers:**
  - `Content-Type: application/json`
  - `Authorization: Bearer <token>`
- **Body:** See Postman collection for example

#### 4. Get Match Results
- **Method:** GET
- **URL:** `http://127.0.0.1:9000/api/v1/requisitions/{requisition_id}/matches`
- **Headers:**
  - `Authorization: Bearer <token>`

## Authentication

### Generate JWT Token

Run the token generation script:

```powershell
python generate_token.py
```

This will generate a JWT token that can be used in the Postman environment variable `auth_token`.

### Using Token in Postman

1. Copy the generated token
2. In Postman environment, set `auth_token` to the generated value
3. The collection is configured to automatically use `{{auth_token}}` in Authorization headers

## Testing with Postman Collection

### Available Test Groups:

1. **Health & Monitoring**
   - Root Endpoint
   - Health Check
   - OpenAPI Schema

2. **Authentication**
   - Login
   - Token Validation

3. **Job Requisitions**
   - Create Requisition
   - Get Requisition
   - List Requisitions
   - Get Match Results

4. **Skill Availability**
   - Bulk Upload Team Member Skills
   - Get Team Member Skills
   - Update Skills

5. **Admin & Monitoring**
   - Database Health
   - System Metrics

### Running the Full Collection

1. Import both collection and environment files into Postman
2. Select the "IB Job Skill Mapping - Local" environment
3. Update `base_url` to `http://localhost:9000`
4. Generate and set `auth_token` using `generate_token.py`
5. Run the collection using "Run Collection" button
6. Review test results

## Troubleshooting

### Issue: Connection Refused
**Solution:** Ensure the application is running
```powershell
# Check if app is running on port 9000
Get-NetTCPConnection -LocalPort 9000
```

### Issue: Authentication Failed
**Solution:** Generate a new JWT token
```powershell
python generate_token.py
```

### Issue: Database Errors
**Solution:** Ensure PostgreSQL is running
```powershell
docker compose ps postgres
# If not running:
docker compose up -d postgres
```

### Issue: Port Already in Use
**Solution:** Kill the process on port 9000
```powershell
$process = Get-NetTCPConnection -LocalPort 9000 | Select-Object -ExpandProperty OwningProcess
Stop-Process -Id $process -Force
```

## Command Reference

### Start Application
```powershell
.\start_app.ps1
```

### Stop Application
```powershell
# Press Ctrl+C in the terminal where app is running
# OR kill the process:
$process = Get-NetTCPConnection -LocalPort 9000 | Select-Object -ExpandProperty OwningProcess
Stop-Process -Id $process -Force
```

### Restart Database
```powershell
docker compose restart postgres
```

### View Logs
```powershell
# Application logs (in the terminal where app is running)
# Database logs:
docker compose logs postgres
```

### Run Migrations
```powershell
.\venv\Scripts\Activate.ps1
alembic upgrade head
```

## Next Steps

1. ✅ Application is running on http://127.0.0.1:9000
2. ✅ Database is healthy and connected
3. ✅ Swagger UI available at http://127.0.0.1:9000/docs
4. 📋 Import Postman collection and update environment
5. 🔑 Generate JWT token for authenticated requests
6. 🧪 Run Postman collection tests
7. 📊 Review test results and API responses

## Additional Resources

- **Swagger UI:** http://127.0.0.1:9000/docs (interactive API documentation)
- **ReDoc:** http://127.0.0.1:9000/redoc (alternative API documentation)
- **OpenAPI Schema:** http://127.0.0.1:9000/openapi.json (machine-readable API spec)
- **Project README:** [README.md](README.md)
- **API Testing Report:** [API_TESTING_REPORT.md](API_TESTING_REPORT.md)

---

**Status:** ✅ Application is ready for testing with Postman!
