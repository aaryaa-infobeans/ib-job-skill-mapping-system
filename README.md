# IB Job Skill Mapping System

[![Test Suite](https://github.com/aaryaa-infobeans/ib-job-skill-mapping-system/actions/workflows/test.yml/badge.svg)](https://github.com/aaryaa-infobeans/ib-job-skill-mapping-system/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/aaryaa-infobeans/ib-job-skill-mapping-system/branch/main/graph/badge.svg)](https://codecov.io/gh/aaryaa-infobeans/ib-job-skill-mapping-system)
[![Coverage](https://img.shields.io/badge/coverage-85.71%25-brightgreen)](./htmlcov/index.html)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

An AI-powered intelligent job requisition and skill mapping system that matches job descriptions with team member skills and evaluates candidate availability using LangGraph-based multi-agent orchestration.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Performance Testing](#performance-testing)
- [Project Structure](#project-structure)
- [Development Phases](#development-phases)
- [Contributing](#contributing)

## ⚡ Quick Start

Get the system up and running in 5 minutes:

### Step 1: Clone and Setup Environment

```bash
# Clone repository
git clone https://github.com/aaryaa-infobeans/ib-job-skill-mapping-system.git
cd ib-job-skill-mapping-system

# Create and activate virtual environment
python -m venv venv

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"
```

### Step 2: Start Database

```bash
# Start PostgreSQL using Docker Compose
docker compose up -d postgres

# Wait for database to be ready (about 10 seconds)
```

### Step 3: Configure Environment

Create a `.env` file in the project root:

```bash
# Required: Database connection
DATABASE_URL=postgresql://user:password@localhost:5432/ib_job_skill_mapping

# Required: OpenAI API key (get from https://platform.openai.com/api-keys)
OPENAI_API_KEY=sk-your-openai-api-key-here

# Optional: JWT secret (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
SECRET_KEY=your-generated-secret-key-here
```

### Step 4: Run Database Migrations

```bash
# Create database schema
alembic upgrade head
```

### Step 5: Start the Application

```bash
# Start API server with hot-reload
uvicorn src.main:app --reload  --host 0.0.0.0 --port 8001
```

The API is now running at:
- **Swagger UI**: http://localhost:8000/docs
- **API Base**: http://localhost:8000
- **Health Check**: http://localhost:8000/health

### Step 6: Test the API

```bash
# Check health endpoint
curl http://localhost:8000/health

# Expected output:
# {"status":"healthy","timestamp":"2026-02-03T...","database":"connected"}
```

### Next Steps

- **Configure OAuth Client**: See [OAuth Client Setup](#oauth-client-setup) section
- **Load Sample Data**: Run `psql -U user -h localhost -d ib_job_skill_mapping -f specs-data/ib-job-skill-mapping-system.sql`
- **Run Tests**: Execute `pytest` to verify installation
- **Explore API**: Visit http://localhost:8000/docs for interactive API documentation

---

## ✨ Features

### Core Functionality
- **Job Description Parsing** - AI-powered extraction of skills, experience, and requirements from JD text
- **Skill Normalization** - Standardizes skill terminology using LLM-based semantic analysis
- **Intelligent Matching** - Scores team members against requisitions based on skills, experience, and availability
- **Availability Evaluation** - Calculates capacity based on project allocations and timelines
- **Result Aggregation** - Ranks and organizes matching results with detailed explanations

### Technical Features
- **Multi-Agent AI System** - LangGraph orchestration with 6 specialized agents
- **RESTful API** - FastAPI-based async endpoints with OpenAPI documentation
- **OAuth2 Security** - JWT-based authentication with scope-based authorization
- **Bulk Operations** - Idempotent bulk upsert for team member skill availability
- **Audit Trail** - Comprehensive logging of all operations with metadata
- **Performance Optimized** - P95 latency < 2s, handles 100+ concurrent requests
- **Scalable Architecture** - Tested with 5x production data volume

## 🏗️ Architecture

### High-Level Architecture

```
┌─────────────┐     ┌──────────────────────────────────────┐     ┌──────────────┐
│   Client    │────▶│         FastAPI Layer                │────▶│  PostgreSQL  │
│ Application │     │  (FR-1, FR-2, FR-3 Endpoints)        │     │   Database   │
└─────────────┘     └──────────────────────────────────────┘     └──────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │   LangGraph Multi-Agent AI    │
                    │         Orchestrator          │
                    └───────────────────────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            ▼                       ▼                       ▼
    ┌───────────────┐      ┌────────────────┐     ┌──────────────┐
    │ JD Parsing    │      │ Skill Normal.  │     │  Matching &  │
    │    Agent      │      │     Agent      │     │Score Agent   │
    └───────────────┘      └────────────────┘     └──────────────┘
            │                       │                       │
            └───────────────────────┼───────────────────────┘
                                    ▼
                    ┌───────────────────────────────┐
                    │   Availability Evaluation     │
                    │   + Result Aggregation        │
                    └───────────────────────────────┘
```

### LangGraph Agent Topology

```
START → JD Parsing → Skill Normalization → Matching & Scoring
                                                    │
                                                    ▼
                                          Availability Evaluation
                                                    │
                                                    ▼
                                           Result Aggregation → END
```

## 📦 Prerequisites

### Required Software

- **Python 3.11+** - Core runtime
- **PostgreSQL 15+** - Database
- **Docker & Docker Compose** - Container orchestration (recommended)
- **Git** - Version control

### Optional Tools

- **k6** - Performance testing (Phase 6)
- **HTTPie or curl** - API testing
- **pgAdmin** - Database management UI

### API Keys

- **OpenAI API Key** - Required for LLM-based agents
  - Get from: https://platform.openai.com/api-keys
  - Set in `.env` file as `OPENAI_API_KEY`

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/aaryaa-infobeans/ib-job-skill-mapping-system.git
cd ib-job-skill-mapping-system
```

### 2. Set Up Python Environment

#### Using venv (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Windows (CMD)
.\venv\Scripts\activate.bat

# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"
```

#### Using conda

```bash
conda create -n ib-job-skill python=3.11
conda activate ib-job-skill
pip install -e ".[dev]"
```

### 3. Start PostgreSQL Database

#### Using Docker Compose (Recommended)

```bash
docker compose up -d postgres
```

This starts PostgreSQL on `localhost:5432` with:
- **Database**: `ib_job_skill_mapping`
- **User**: `user`
- **Password**: `password`

#### Using Local PostgreSQL

If you have PostgreSQL installed locally, create the database:

```bash
psql -U postgres
CREATE DATABASE ib_job_skill_mapping;
CREATE USER user WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE ib_job_skill_mapping TO user;
\q
```

### 4. Run Database Migrations

```bash
alembic upgrade head
```

This creates all required tables:
- `team_members`
- `team_member_allocations`
- `requisition_requests`
- `requisition_parsed_skills`
- `requisition_matches`
- `oauth_clients`
- `audit_log`

### 5. Load Sample Data (Optional)

```bash
# Load initial schema with sample OAuth client
psql -U user -h localhost -d ib_job_skill_mapping -f specs-data/ib-job-skill-mapping-system.sql
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/ib_job_skill_mapping

# OpenAI API Configuration
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_EMBEDDING_MODEL=text-embedding-3-large

# LLM Cost Tracking Configuration
OPENAI_INPUT_RATE=0.003
OPENAI_OUTPUT_RATE=0.006

# Agent Scoring Weights
WEIGHT_MANDATORY_SKILLS=0.25
WEIGHT_PREFERRED_SKILLS=0.20
WEIGHT_EXPERIENCE=0.10
WEIGHT_SEMANTIC_SIMILARITY=0.10
WEIGHT_CERTIFICATION=0.10
WEIGHT_JD_TEXT=0.10
WEIGHT_LOCATION=0.10
WEIGHT_WORK_MODE=0.05

# Thresholds
FIT_SCORE_THRESHOLD=0.55
# Lowered to 0.3 to improve candidate retrieval recall
RAG_SIMILARITY_THRESHOLD=0.3

# Retry Configuration
MAX_RETRY_ATTEMPTS=3
RETRY_BACKOFF_FACTOR=2

# pgvector Configuration
PGVECTOR_DIMENSION=3072

# Application Configuration
APP_ENV=development
LOG_LEVEL=INFO

# Security Configuration
SECRET_KEY=your-secret-key-for-jwt-signing-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Server Configuration
HOST=0.0.0.0
PORT=8000
RELOAD=true
```

### Generate Secret Key

```bash
# Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# OpenSSL
openssl rand -base64 32
```

### OAuth Client Setup

Register an OAuth client in the database:

```bash
# Connect to database
psql -U user -h localhost -d ib_job_skill_mapping

# Create OAuth client
INSERT INTO oauth_clients (client_id, client_name, hashed_secret, scopes, is_active)
VALUES (
    'test-client',
    'Test Application',
    crypt('test-secret', gen_salt('bf')),
    ARRAY['read', 'write'],
    true
);

# Exit psql
\q
```

**Generate JWT Token for Testing:**

```bash
# Using Python
python -c "from jose import jwt; from datetime import datetime, timedelta; print(jwt.encode({'sub': 'test-client', 'scopes': ['read', 'write'], 'exp': datetime.utcnow() + timedelta(hours=24)}, 'your-secret-key-here', algorithm='HS256'))"
```

Use this token in API requests:
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" http://localhost:8000/api/v1/jd-skill-mapping/
```

## 🏃 Running the Application

### Development Mode

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Or using the convenience script:

```bash
# Windows PowerShell
python -m uvicorn src.main:app --reload

# macOS/Linux
python3 -m uvicorn src.main:app --reload
```

The API will be available at:
- **API Base**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Production Mode

```bash
# Using Gunicorn with Uvicorn workers (Linux/macOS)
gunicorn src.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -

# Windows (use Uvicorn directly)
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Using Docker

```bash
# Build image
docker build -t ib-job-skill-mapping:latest .

# Run container
docker run -d \
  -p 8000:8000 \
  --env-file .env \
  --name ib-job-skill-api \
  ib-job-skill-mapping:latest
```

### Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2026-02-03T10:30:00Z",
  "database": "connected"
}
```

## 📚 API Documentation

### Authentication

All API endpoints require OAuth2 Bearer token authentication:

```bash
# Get access token (pseudo-code, implement OAuth2 flow)
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=test-client&client_secret=test-secret&grant_type=client_credentials"
```

### Core Endpoints

#### FR-1: Submit Job Requisition

```bash
POST /api/v1/jd-skill-mapping/
Authorization: Bearer <token>
Content-Type: application/json

{
  "request_id": "REQ-2026-001",
  "title": "Senior Backend Engineer",
  "role": "Backend Development",
  "priority": "HIGH",
  "location": ["Bangalore", "Remote"],
  "work_mode": ["Remote", "Hybrid"],
  "jd_text": "We are seeking a Senior Backend Engineer with 5+ years experience in Python, FastAPI, PostgreSQL..."
}
```

#### FR-2: Get Matching Results

```bash
GET /api/v1/jd-skill-mapping/{correlation_id}/matches
Authorization: Bearer <token>
```

#### FR-3: Bulk Upsert Team Member Skills

```bash
POST /api/v1/team-members/skill-availability/bulk-upsert
Authorization: Bearer <token>
Content-Type: application/json

{
  "team_members": [
    {
      "team_member_id": "TM001",
      "name": "John Doe",
      "email": "john.doe@example.com",
      "designation": "Senior Engineer",
      "primary_skills": ["Python", "FastAPI", "PostgreSQL"],
      "secondary_skills": ["Docker", "Kubernetes"],
      "total_experience_years": 8,
      "relevant_experience_years": 5
    }
  ]
}
```

### Candidate Availability Agent API

#### Endpoint

- **POST** `/api/v1/agents/candidate-availability`

#### Description
Checks the availability of one or more team members for a requisition window, applying all business rules and returning a deterministic, structured response.

#### Sample Request Payloads

##### Single Member
```json
{
  "requisition_duration_month": 3,
  "expected_start_date": "2026-02-15",
  "team_member_id": "EMP_8842"
}
```

##### Multiple Members
```json
{
  "requisition_duration_month": 3,
  "expected_start_date": "2026-02-15",
  "team_member_ids": ["EMP_8842", "EMP_1201", "EMP_7788"]
}
```

#### Sample Response
```json
{
  "request_id": "<uuid>",
  "expected_start_date": "2026-02-15",
  "expected_end_date": "2026-05-15",
  "requisition_duration_month": 3,
  "results": [
    {
      "team_member_id": "EMP_8842",
      "available": true,
      "reason_code": "AVAILABLE",
      "reason": "No conflicting billable allocations found in requested window.",
      "conflicts": []
    }
  ],
  "summary": {
    "requested": 3,
    "available_count": 1,
    "unavailable_count": 2,
    "not_found_count": 0
  },
  "errors": []
}
```

#### How to Test with Postman
- Set method to POST
- URL: `http://localhost:8000/api/v1/agents/candidate-availability`
- Body: raw, JSON, use one of the sample payloads above
- Expected: 200 OK, response matches schema above

#### Developer Notes
- Set `DATABASE_URL` in your environment (see above)
- Start the server: `uvicorn src.app.main:app --host 127.0.0.1 --port 8010 --reload`
- Run tests: `pytest`
- No DB migrations are required for this feature

### Monitoring Endpoints

```bash
# Prometheus metrics
GET /api/v1/metrics

# Audit logs
GET /api/v1/audit/logs?entity_type=requisition&limit=100
```

For detailed API documentation, visit http://localhost:8000/docs after starting the server.

## 🧪 Testing

Our comprehensive test suite ensures code quality and reliability with **85.71% coverage**.

### Quick Test Commands

```bash
# Run all tests with coverage
pytest --cov=app --cov-report=html --cov-report=term

# Smoke tests only (< 60 seconds)
pytest tests/smoke/ -m smoke -v

# Unit tests only
pytest tests/unit/ tests/cron/unit/ -v

# Integration tests (requires PostgreSQL)
pytest tests/integration/ tests/cron/integration/ -v

# Performance benchmarks
pytest tests/performance/ -m performance -v
```

### Test Categories

#### 1. Smoke Tests (<60s)
Quick validation of critical paths for CI/CD:
```bash
pytest tests/smoke/ -m smoke -v --tb=short --timeout=60
```

**Coverage:**
- Database connectivity and schema validation
- Batch processing (dry-run mode)
- Error classification logic
- OAuth client initialization
- API health endpoints
- Retry eligibility checks

#### 2. Unit Tests
Fast, isolated tests with mocked dependencies:
```bash
pytest tests/unit/ tests/cron/unit/ --cov=app --cov-report=term
```

**Current Coverage: 85.71%**
- Processing: batch_processor (98.92%), error_classifier (98.36%), retry_manager (100%)
- Database: engine (100%), migrations_check (100%), metadata (100%)
- OAuth: token_client (98.75%)
- External API: external_client (87.36%)

#### 3. Integration Tests
End-to-end tests with real database:
```bash
# Start test database
docker-compose -f docker-compose.test.yml up -d

# Run integration tests
export DB_PORT=5434
export DB_PASSWORD=postgres
export DB_NAME=ib_job_skill_mapping_test
pytest tests/integration/ tests/cron/integration/ -v
```

**Coverage:**
- Database operations and migrations
- Batch state management
- Repository UPSERT operations
- Transaction isolation
- API authentication flow

#### 4. Performance Benchmarks
Validate NFR requirements:
```bash
pytest tests/performance/ -m performance -v
```

**NFR Validations:**
- ✅ Throughput ≥ 100 records/second
- ✅ 10,000 records < 30 minutes
- ✅ Memory usage < 2 GB
- ✅ Batch sizes: 100, 1,000, 10,000 records

### Test Coverage

```bash
# Generate coverage report
pytest --cov=app --cov-report=term-missing --cov-fail-under=85

# View HTML report
pytest --cov=app --cov-report=html
# Open htmlcov/index.html in browser
```

**Coverage Enforcement:**
- Minimum threshold: **85%**
- Enforced in CI/CD pipeline
- Fails build if coverage drops below threshold

### Continuous Integration

Our GitHub Actions workflow automatically runs:
1. **Smoke tests** (< 2 min) - Fast validation on every push
2. **Unit tests** (< 15 min) - Full coverage with 85% threshold
3. **Integration tests** (< 20 min) - PostgreSQL-backed validation
4. **Performance tests** (< 30 min) - On main/develop branches only

[![Test Suite](https://github.com/aaryaa-infobeans/ib-job-skill-mapping-system/actions/workflows/test.yml/badge.svg)](https://github.com/aaryaa-infobeans/ib-job-skill-mapping-system/actions/workflows/test.yml)

### Code Quality

```bash
# Format code with Black
black src/ tests/

# Check formatting without changes
black --check src/ tests/

# Lint with Ruff
ruff check src/ tests/

# Auto-fix linting issues
ruff check --fix src/ tests/

# Type checking with mypy (if configured)
mypy src/
```

## 🚀 Performance Testing

Phase 6 includes comprehensive performance testing validating NFR requirements.

### Python Performance Benchmarks

```bash
# Run small and medium batch tests (quick)
export SKIP_LARGE_PERF_TESTS=1
pytest tests/performance/ -m performance -v

# Run all performance tests including 10K batch (slow)
export SKIP_LARGE_PERF_TESTS=0
pytest tests/performance/ -m performance -v --tb=short
```

### K6 Load Testing

```bash
# Install k6
# macOS: brew install k6
# Windows: choco install k6
# Linux: sudo apt-get install k6

# Set authentication token
export AUTH_TOKEN="your-jwt-token"

# Smoke test (30 seconds, 1 user)
k6 run performance-tests/smoke-test.js

# Load test (6 minutes, 10→100 users)
k6 run performance-tests/load-test.js

# Stress test (30 minutes, 100→400 users)
k6 run performance-tests/stress-test.js
```

### Performance Targets

| Metric | Target | Test Coverage | Status |
|--------|--------|---------------|--------|
| Bulk Upsert Throughput | ≥ 100 rec/s | Python benchmarks | ✅ Passing |
| 10K Records Processing | < 30 minutes | Python benchmarks | ✅ Passing |
| Memory Usage | < 2 GB | Python benchmarks | ✅ Passing |
| P95 API Latency | < 2 seconds | k6 load test | ✅ Passing |
| P99 API Latency | < 5 seconds | k6 load test | ✅ Passing |
| Error Rate | < 1% | All tests | ✅ Passing |

See [docs/phase-6-testing-guide.md](docs/phase-6-testing-guide.md) for detailed testing procedures.

### Scalability Testing

```bash
# Generate 5x production data
python scripts/generate_test_data.py --scale 5 --output test_data_5x.sql

# Load to database
psql -U user -h localhost -d ib_job_skill_mapping -f test_data_5x.sql

# Cleanup test data
python scripts/cleanup_test_data.py \
  --database postgresql://user:password@localhost:5432/ib_job_skill_mapping \
  --metadata scale_test
```

### Idempotency Testing

```bash
# Test retry behavior
python tests/test_idempotent_retry.py --auth-token "your-jwt-token"
```

## � Troubleshooting

### Common Setup Issues

#### Issue: `psycopg2` installation fails

**Solution:**
```bash
# Windows: Install Visual C++ Build Tools first
# Or use binary package
pip install psycopg2-binary
```

#### Issue: Docker Compose not found

**Solution:**
```bash
# Check Docker installation
docker --version
docker compose version

# If using older Docker, try:
docker-compose up -d postgres
```

#### Issue: Port 5432 already in use

**Solution:**
```bash
# Check what's using port 5432
# Windows PowerShell
netstat -ano | findstr :5432

# Kill the process or use different port in docker-compose.yml
ports:
  - "5433:5432"  # Changed host port to 5433

# Update DATABASE_URL accordingly
DATABASE_URL=postgresql://user:password@localhost:5433/ib_job_skill_mapping
```

#### Issue: Alembic migration fails

**Solution:**
```bash
# Check database connection
psql -U user -h localhost -d ib_job_skill_mapping -c "SELECT 1"

# Reset database if needed
alembic downgrade base
alembic upgrade head

# Or recreate database
psql -U user -h localhost -c "DROP DATABASE IF EXISTS ib_job_skill_mapping"
psql -U user -h localhost -c "CREATE DATABASE ib_job_skill_mapping"
alembic upgrade head
```

#### Issue: OpenAI API key not working

**Solution:**
```bash
# Verify .env file is in project root
ls -la .env  # macOS/Linux
dir .env     # Windows

# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer YOUR_OPENAI_API_KEY"

# Make sure .env is loaded (restart uvicorn after changing .env)
```

#### Issue: `uvicorn: command not found`

**Solution:**
```bash
# Ensure virtual environment is activated
# You should see (venv) in your prompt

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# macOS/Linux
source venv/bin/activate

# Verify installation
pip list | grep uvicorn

# If not installed
pip install -e ".[dev]"
```

#### Issue: Module import errors

**Solution:**
```bash
# Install package in editable mode
pip install -e ".[dev]"

# Verify src is in Python path
python -c "import sys; print('\n'.join(sys.path))"

# Run from project root directory
cd /path/to/ib-job-skill-mapping-system
uvicorn src.main:app --reload
```

#### Issue: Tests failing

**Solution:**
```bash
# Ensure test database is set up
export DATABASE_URL=postgresql://user:password@localhost:5432/ib_job_skill_mapping_test
alembic upgrade head

# Clear pytest cache
pytest --cache-clear

# Run with verbose output
pytest -v

# Run specific test
pytest tests/test_api.py -v
```

### Performance Issues

#### Slow API response times

**Causes & Solutions:**

1. **Database connection pool exhausted**
   ```bash
   # Increase pool size in src/config.py
   SQLALCHEMY_POOL_SIZE = 20
   SQLALCHEMY_MAX_OVERFLOW = 40
   ```

2. **Missing database indexes**
   ```sql
   -- Add indexes for frequently queried columns
   CREATE INDEX CONCURRENTLY idx_team_members_skills 
   ON team_members USING GIN(primary_skills);
   
   CREATE INDEX CONCURRENTLY idx_requisitions_status 
   ON requisition_requests(status);
   ```

3. **OpenAI API timeout**
   ```bash
   # Increase timeout in agent configuration
   # Check network connectivity to api.openai.com
   ```

### Getting Help

If you encounter issues not covered here:

1. **Check logs**: Look at application logs for detailed error messages
2. **Review specs**: Check [specs/](specs/) directory for requirements
3. **GitHub Issues**: Search existing issues or create a new one
4. **Documentation**: Review [docs/phase-6-testing-guide.md](docs/phase-6-testing-guide.md)



```
ib-job-skill-mapping-system/
├── src/                          # Source code
│   ├── main.py                   # FastAPI application entry point
│   ├── api/                      # API routes (FR-1, FR-2, FR-3)
│   ├── models/                   # SQLAlchemy models
│   ├── schemas/                  # Pydantic schemas
│   ├── agents/                   # LangGraph AI agents
│   ├── services/                 # Business logic
│   ├── auth/                     # OAuth2 authentication
│   └── config.py                 # Configuration management
├── tests/                        # Test suites
│   ├── test_api.py              # API endpoint tests
│   ├── test_agents.py           # Agent unit tests
│   └── test_idempotent_retry.py # Idempotency tests
├── performance-tests/            # k6 load tests
│   ├── smoke-test.js            # Quick validation
│   ├── load-test.js             # Realistic load
│   ├── stress-test.js           # Breaking point
│   └── README.md                # Testing guide
├── scripts/                      # Utility scripts
│   ├── generate_test_data.py    # Test data generation
│   └── cleanup_test_data.py     # Data cleanup
├── alembic/                      # Database migrations
│   ├── versions/                # Migration files
│   └── env.py                   # Alembic configuration
├── docs/                         # Documentation
│   ├── phase-6-testing-guide.md # Performance testing guide
│   └── architecture.md          # Architecture documentation
├── specs/                        # Requirements & specifications
│   ├── plan.md                  # Implementation plan
│   ├── tasks.md                 # Phase-wise tasks
│   ├── ai/                      # AI agent specifications
│   ├── data/                    # Data model specifications
│   ├── functional/              # Functional requirements
│   └── non-functional/          # Non-functional requirements
├── specs-data/                   # Sample data & schemas
│   └── ib-job-skill-mapping-system.sql
├── docker-compose.yml           # Docker Compose configuration
├── pyproject.toml               # Python project configuration
├── alembic.ini                  # Alembic configuration
├── .env                         # Environment variables (create this)
└── README.md                    # This file
```

## 🏗️ Development Phases

The project was developed in 6 phases, each on a separate branch:

### Phase 1: Foundation & Platform Setup
**Branch**: `phase-1-foundation`
- Database schema design (7 tables)
- Alembic migrations setup
- SQLAlchemy models
- Core configuration management

### Phase 2: Core API Layer
**Branch**: `phase-2-core-api`
- FastAPI application setup
- FR-1: Requisition Request API
- FR-2: Match Response API
- FR-3: Skill Availability Bulk Upsert
- Pydantic schemas and validation

### Phase 3: LangGraph Integration
**Branch**: `phase-3-langgraph-integration`
- LangGraph state graph setup
- State schema design
- Agent topology implementation
- OpenAI integration

### Phase 4: AI Matching Engine
**Branch**: `phase-4-matching-engine`
- 6 specialized AI agents:
  - JD Parsing Agent
  - Skill Normalization Agent
  - Matching & Scoring Agent
  - Availability Evaluation Agent
  - Result Aggregation Agent
  - Explanation Generation Agent
- Multi-agent orchestration
- Prompt engineering

### Phase 5: Security & Observability
**Branch**: `phase-5-security-observability`
- OAuth2 authentication (client credentials)
- JWT token management
- Secrets management (environment-based)
- Prometheus metrics
- Audit trail logging
- 51 passing tests

### Phase 6: Hardening & Scale Readiness
**Branch**: `phase-6-hardening-scale`
- k6 performance test suite
- Load testing (100+ concurrent users)
- Stress testing (400 users)
- Scalability validation (5x data)
- Idempotent retry testing
- Performance targets: P95<2s, P99<5s

## 🤝 Contributing

### Development Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes and test**
   ```bash
   pytest
   black src/ tests/
   ruff check src/ tests/
   ```

3. **Commit with conventional commits**
   ```bash
   git commit -m "feat: add new feature"
   git commit -m "fix: resolve bug in matching logic"
   git commit -m "docs: update API documentation"
   ```

4. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

### Code Style

- **Formatting**: Black (100 char line length)
- **Linting**: Ruff
- **Type Hints**: Use Python type annotations
- **Docstrings**: Google style docstrings

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

## 📄 License

This project is proprietary and confidential. Unauthorized copying or distribution is prohibited.

## 👥 Authors

- **Aarya Bhosale** - Initial implementation
- **InfoBeans Development Team**

## 📞 Support

For issues or questions:
- Create an issue in the GitHub repository
- Contact the development team at support@infobeans.com

## 🔗 Links

- **API Documentation**: http://localhost:8000/docs
- **GitHub Repository**: https://github.com/aaryaa-infobeans/ib-job-skill-mapping-system
- **Specification Documents**: [specs/](specs/)
- **Performance Testing Guide**: [docs/phase-6-testing-guide.md](docs/phase-6-testing-guide.md)

---

**Version**: 0.1.0  
**Last Updated**: February 3, 2026
