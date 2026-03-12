## End-to-End Validation Guide

Follow these steps to manually validate the application:

### Step 1: Start PostgreSQL Database

```powershell
docker compose up -d postgres
```

### Step 2: Run Database Migrations

```powershell
.\venv\Scripts\Activate.ps1
alembic upgrade head
```

### Step 3: Start the API Server

Open a NEW PowerShell window and run:

```powershell
cd "C:\Users\Aarya Bhosale\Documents\ib-job-skill-mapping-system"
.\venv\Scripts\Activate.ps1
python start_server.py
```

Leave this window open - the server will be running on http://127.0.0.1:8001

### Step 4: Access API Documentation

Open your web browser and navigate to:
- **Swagger UI**: http://127.0.0.1:8001/docs
- **Health Check**: http://127.0.0.1:8001/health

### Step 5: Generate JWT Token for Testing

In another PowerShell window:

```powershell
.\venv\Scripts\Activate.ps1
python -c "from jose import jwt; from datetime import datetime, timedelta; print(jwt.encode({'sub': 'test-client', 'client_id': 'test-client', 'scopes': ['read', 'write'], 'exp': datetime.utcnow() + timedelta(hours=1)}, 'test-secret-key-for-testing', algorithm='HS256'))"
```

Copy the generated token.

### Step 6: Test Endpoints in Swagger UI

1. Click the **Authorize** button in Swagger UI
2. Enter: `Bearer YOUR_TOKEN_HERE` (replace with the token from Step 5)
3. Click **Authorize**

#### Test 1: Bulk Upsert Team Members

1. Navigate to **POST /api/v1/team-members/skill-availability/bulk-upsert**
2. Click **Try it out**
3. Use this JSON payload:

```json
{
  "team_members": [
    {
      "team_member_id": "TM001",
      "name": "Rahul Sharma",
      "email": "rahul.sharma@example.com",
      "designation": "Senior Software Engineer",
      "primary_skills": ["Python", "Django", "FastAPI", "PostgreSQL"],
      "secondary_skills": ["AWS", "Docker", "Redis"],
      "total_experience_years": 7,
      "relevant_experience_years": 5
    },
    {
      "team_member_id": "TM002",
      "name": "Priya Patel",
      "email": "priya.patel@example.com",
      "designation": "Lead Engineer",
      "primary_skills": ["Python", "Django", "DRF", "MySQL"],
      "secondary_skills": ["Kubernetes", "Jenkins", "AWS"],
      "total_experience_years": 10,
      "relevant_experience_years": 8
    }
  ]
}
```

4. Click **Execute**
5. Verify response shows `inserted_count: 2`

#### Test 2: Submit Job Requisition

1. Navigate to **POST /api/v1/jd-skill-mapping/**
2. Click **Try it out**
3. Use this JSON payload:

```json
{
  "request_id": "REQ-TEST-001",
  "schema_version": "1.1",
  "source_system": "EAGLE",
  "client_name": "EAGLE",
  "job_description": {
    "client_name": "ICC",
    "title": "Senior Software Engineer",
    "role": "Backend Developer",
    "requisition_duration_month": 12,
    "expected_start_date": "2026-03-01",
    "priority": "HIGH",
    "location": ["Pune", "Bangalore"],
    "work_mode": ["wfh", "hybrid"],
    "experience": {
      "min_months": 60,
      "max_months": 120
    },
    "mandatory_skills": ["Python", "Django", "DRF", "PostgreSQL"],
    "preferred_skills": ["AWS", "Docker", "Kubernetes"],
    "jd_text": "We are looking for a Senior Software Engineer with 5+ years of experience in Python and Django."
  },
  "metadata": {
    "submitted_by": "Aarya",
    "submitted_at": "2026-02-19T10:00:00Z",
    "department": "Open Source"
  }
}
```

4. Click **Execute**
5. Copy the `correlation_id` from the response

#### Test 3: Get Matching Results

1. Navigate to **GET /api/v1/jd-skill-mapping/{correlation_id}/matches**
2. Click **Try it out**
3. Paste the `correlation_id` from Test 2
4. Click **Execute**
5. Verify you see matches for the requisition with team members ranked by fit score

### Step 7: Verify Database

Connect to PostgreSQL and verify data:

```powershell
docker exec -it ib-job-skill-mapping-system-postgres-1 psql -U user -d ib_job_skill_mapping
```

SQL queries to verify:

```sql
-- Check team members
SELECT team_member_id, name, primary_skills FROM team_members;

-- Check requisitions
SELECT request_id, correlation_id, status FROM requisition_requests;

-- Check matches
SELECT * FROM requisition_matches WHERE correlation_id = 'YOUR_CORRELATION_ID';
```

### Expected Results

✅ Health endpoint returns healthy status  
✅ Team members successfully inserted  
✅ Requisition created with correlation_id  
✅ Matches returned with fit scores for team members  
✅ Data persisted in PostgreSQL database

### Troubleshooting

If server shuts down immediately:
- Make sure you're running the server in a SEPARATE PowerShell window
- Don't run other Python scripts in the same window as the server
- Use the browser or Swagger UI for testing, not curl from PowerShell

If authentication fails:
- Verify JWT token is fresh (not expired)
- Ensure you included "Bearer " prefix
- Check that JWT_SECRET_KEY in .env matches the key used to generate token

If database errors occur:
- Verify PostgreSQL is running: `docker ps`
- Check DATABASE_URL in .env matches container port (5433)
- Run migrations: `alembic upgrade head`
