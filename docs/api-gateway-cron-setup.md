# API Gateway & Cron Modules - Setup & Run Guide

## Overview

This guide provides comprehensive instructions for setting up and running the IB Job Skill Mapping System's two main application modules:

1. **API Gateway** - FastAPI-based REST API server
2. **Cron** - Scheduled background tasks for maintenance and data processing

Both modules share the same codebase but are deployed as separate services with different configurations.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Local Development Setup](#local-development-setup)
- [Running Locally](#running-locally)
- [Production Deployment](#production-deployment)
- [Configuration](#configuration)
- [Monitoring & Logs](#monitoring--logs)
- [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                        │
├─────────────────────────┬───────────────────────────────────┤
│    API Gateway          │         Cron Module               │
│    (FastAPI Server)     │    (APScheduler Tasks)            │
├─────────────────────────┼───────────────────────────────────┤
│ - REST API endpoints    │ - Scheduled data cleanup          │
│ - Authentication        │ - Cache warming                   │
│ - Request validation    │ - Metric aggregation              │
│ - LangGraph triggering  │ - Health checks                   │
│ - Response formatting   │ - Backup tasks                    │
└─────────────────────────┴───────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Shared Services                           │
├──────────────┬──────────────┬──────────────┬────────────────┤
│  PostgreSQL  │    Redis     │   LangGraph  │  External APIs │
│  (Database)  │   (Cache)    │  (AI Agent)  │  (LLM, Graph)  │
└──────────────┴──────────────┴──────────────┴────────────────┘
```

### Module Responsibilities

**API Gateway:**
- Handle HTTP requests (requisitions, availabilities, matches)
- Authentication and authorization
- Request validation and rate limiting
- Trigger LangGraph workflows
- Serve metrics and health endpoints

**Cron Module:**
- Cleanup expired sessions and old data
- Warm caches with frequently accessed data
- Aggregate metrics for reporting
- Run scheduled health checks
- Perform database maintenance tasks

---

## Prerequisites

### Required Software

**All Environments:**
- Python 3.11 or 3.12
- PostgreSQL 15+
- Redis 7+
- Git

**Development Only:**
- Docker & Docker Compose (optional, for containerized databases)
- Make (optional, for Makefile commands)

**Production Only:**
- Kubernetes CLI (kubectl)
- AWS CLI v2
- Access to AWS EKS cluster

### System Requirements

**Local Development:**
- CPU: 2+ cores
- RAM: 8 GB minimum, 16 GB recommended
- Disk: 10 GB free space

**Production (per pod):**
- API Gateway: 500m-2000m CPU, 1-4 GB RAM
- Cron: 250m-1000m CPU, 512 MB-2 GB RAM

---

## Local Development Setup

### 1. Clone Repository

```bash
# Clone the repository
git clone https://github.com/infobeans/ib-job-skill-mapping-system.git
cd ib-job-skill-mapping-system

# Checkout appropriate branch
git checkout main  # or feature branch
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -e .

# Install development dependencies
pip install -e ".[dev]"
```

**Verify Installation:**
```bash
python --version  # Should be 3.11 or 3.12
pip list | grep fastapi  # Verify FastAPI installed
```

### 3. Set Up Local Databases

#### Option A: Docker Compose (Recommended)

```bash
# Start PostgreSQL and Redis containers
docker-compose up -d

# Verify containers running
docker-compose ps

# Expected output:
# NAME                    IMAGE               STATUS
# postgres                postgres:15         Up
# redis                   redis:7             Up
```

**Docker Compose Configuration:**
```yaml
# docker-compose.yml (already in repo)
version: '3.8'
services:
  postgres:
    image: postgres:15
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: ib_job_skill_mapping
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

#### Option B: Local Installation

**PostgreSQL:**
```bash
# On macOS (Homebrew):
brew install postgresql@15
brew services start postgresql@15

# On Ubuntu/Debian:
sudo apt-get update
sudo apt-get install postgresql-15
sudo systemctl start postgresql

# On Windows:
# Download installer from https://www.postgresql.org/download/windows/
```

**Redis:**
```bash
# On macOS (Homebrew):
brew install redis
brew services start redis

# On Ubuntu/Debian:
sudo apt-get install redis-server
sudo systemctl start redis-server

# On Windows:
# Download from https://github.com/microsoftarchive/redis/releases
```

**Create Database:**
```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE ib_job_skill_mapping;

# Create user (optional)
CREATE USER ib_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE ib_job_skill_mapping TO ib_user;

# Exit
\q
```

### 4. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
# On Windows: notepad .env
# On macOS/Linux: nano .env
```

**Local `.env` Configuration:**
```bash
# Application
ENVIRONMENT=development
LOG_LEVEL=DEBUG
APP_NAME="IB Job Skill Mapping System"

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ib_job_skill_mapping
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_TTL=3600

# Authentication
JWT_SECRET_KEY=your-local-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# API Keys (for testing - get from team)
OPENAI_API_KEY=sk-your-openai-key
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
MICROSOFT_GRAPH_CLIENT_ID=your-client-id
MICROSOFT_GRAPH_CLIENT_SECRET=your-client-secret
MICROSOFT_GRAPH_TENANT_ID=your-tenant-id

# API Gateway Specific
API_HOST=0.0.0.0
API_PORT=8080
API_WORKERS=1  # Single worker for local dev
CORS_ORIGINS=["http://localhost:3000","http://localhost:8080"]

# Cron Specific
CRON_ENABLED=true
CRON_TIMEZONE=UTC

# Feature Flags
ENABLE_AI_MATCHING=true
ENABLE_CIRCUIT_BREAKER=false  # Disable in local dev
ENABLE_RATE_LIMITING=false    # Disable in local dev
```

### 5. Initialize Database Schema

```bash
# Run database migrations
alembic upgrade head

# Verify migration
alembic current
# Expected: Shows current revision (head)

# Seed initial data (optional)
python scripts/dev/seed_db.py
```

**Verify Database Setup:**
```bash
# Connect to database
psql -U postgres -d ib_job_skill_mapping

# List tables
\dt

# Expected tables:
# requisitions, matches, availabilities, skills, team_members, 
# audit_logs, alembic_version, etc.

# Check table counts
SELECT 
  'requisitions' as table_name, COUNT(*) as count FROM requisitions
UNION ALL
SELECT 'availabilities', COUNT(*) FROM availabilities;

# Exit
\q
```

### 6. Verify Setup

```bash
# Run health check script
python -c "
from src.app.db.connection import get_db_session
from src.app.services.cache import redis_client

# Test database
try:
    with get_db_session() as db:
        result = db.execute('SELECT 1').scalar()
        print(f'✓ Database connection: OK')
except Exception as e:
    print(f'✗ Database connection: FAILED - {e}')

# Test Redis
try:
    redis_client.ping()
    print(f'✓ Redis connection: OK')
except Exception as e:
    print(f'✗ Redis connection: FAILED - {e}')
"
```

---

## Running Locally

### Running API Gateway

#### Method 1: Using Uvicorn (Development Server)

```bash
# Activate virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Run with auto-reload (watches for code changes)
uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8080

# Or with more verbose logging
uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8080 --log-level debug
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Test API Gateway:**
```bash
# Health check
curl http://localhost:8080/health
# Expected: {"status":"healthy","timestamp":"2026-02-08T...","version":"1.0.0"}

# API documentation
open http://localhost:8080/docs  # Opens Swagger UI in browser

# Metrics
curl http://localhost:8080/metrics
# Expected: Prometheus metrics output
```

#### Method 2: Using Make Command

```bash
# Start API Gateway
make run-api

# Or with specific configuration
make run-api ENV=development PORT=8080
```

#### Method 3: Using Python Module

```bash
# Run directly
python -m uvicorn src.app.main:app --reload --port 8080
```

### Running Cron Module

#### Method 1: Direct Execution

```bash
# Activate virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Run cron module
python -m src.app.cron.main

# Or with debug logging
CRON_LOG_LEVEL=DEBUG python -m src.app.cron.main
```

**Expected Output:**
```
INFO:     Starting Cron Module
INFO:     Scheduler initialized
INFO:     Registered job: cleanup_old_data (trigger: cron[hour='2'])
INFO:     Registered job: warm_cache (trigger: interval[hours=6])
INFO:     Registered job: aggregate_metrics (trigger: interval[minutes=15])
INFO:     Scheduler started
INFO:     Cron module running. Press Ctrl+C to exit.
```

#### Method 2: Using Make Command

```bash
# Start Cron module
make run-cron

# With debug logging
make run-cron LOG_LEVEL=DEBUG
```

#### Method 3: Background Execution

```bash
# Run in background (Unix/macOS)
nohup python -m src.app.cron.main > cron.log 2>&1 &

# View logs
tail -f cron.log

# Stop cron
pkill -f "src.app.cron.main"
```

### Running Both Modules Simultaneously

#### Method 1: Multiple Terminals

**Terminal 1 - API Gateway:**
```bash
source venv/bin/activate
uvicorn src.app.main:app --reload --port 8080
```

**Terminal 2 - Cron:**
```bash
source venv/bin/activate
python -m src.app.cron.main
```

#### Method 2: Using Make

```bash
# Start all services (API + Cron + Databases)
make dev

# This runs:
# - docker-compose up -d (databases)
# - API Gateway on port 8080
# - Cron module in background
```

#### Method 3: Process Manager (Recommended)

Install **honcho** or **foreman**:
```bash
pip install honcho
```

Create `Procfile`:
```
api: uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8080
cron: python -m src.app.cron.main
```

Run both:
```bash
honcho start
```

### Testing Cron Jobs Manually

```bash
# Trigger specific cron job manually
python -c "
from src.app.cron.jobs import cleanup_old_data, warm_cache, aggregate_metrics

# Run cleanup
print('Running cleanup...')
cleanup_old_data()
print('Cleanup complete')

# Run cache warming
print('Running cache warming...')
warm_cache()
print('Cache warming complete')

# Run metrics aggregation
print('Running metrics aggregation...')
aggregate_metrics()
print('Metrics aggregation complete')
"
```

### Development Workflow

```bash
# 1. Start services
make dev

# 2. Run tests in watch mode (separate terminal)
pytest --watch

# 3. Make code changes (auto-reload enabled)

# 4. Test changes
curl http://localhost:8080/api/v1/requisitions

# 5. View logs
tail -f logs/app.log

# 6. Stop services
make stop
```

---

## Production Deployment

### Architecture

**Production Deployment:**
- **API Gateway:** Deployed as Kubernetes Deployment (3-10 pods with HPA)
- **Cron:** Deployed as Kubernetes CronJob or single Deployment pod
- **Load Balancer:** AWS Application Load Balancer
- **Database:** AWS RDS PostgreSQL (Multi-AZ)
- **Cache:** AWS ElastiCache Redis (2-node cluster)

### Prerequisites

**Access Requirements:**
- AWS account with production access
- kubectl configured for EKS cluster
- AWS CLI configured with credentials
- VPN access (if required)

**Verify Access:**
```bash
# Check AWS credentials
aws sts get-caller-identity

# Check kubectl context
kubectl config current-context
# Expected: arn:aws:eks:us-east-1:...:cluster/ib-job-skill-mapping-prod

# Check cluster access
kubectl get nodes
# Expected: 3+ nodes in Ready state
```

### 1. API Gateway Production Deployment

#### Option A: Using GitHub Actions (Recommended)

```bash
# Trigger deployment via GitHub Actions
# 1. Push to main branch or create tag
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0

# 2. Workflow automatically:
#    - Builds Docker image
#    - Pushes to ECR
#    - Runs tests
#    - Deploys to production (with approval)

# 3. Monitor deployment
# URL: https://github.com/infobeans/ib-job-skill-mapping/actions

# 4. Verify deployment
kubectl get deployments -n production
kubectl get pods -n production -l app=api-gateway
```

#### Option B: Manual Deployment

```bash
# 1. Build Docker image
docker build -t ib-job-skill-mapping:v1.0.0 .

# 2. Tag and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

docker tag ib-job-skill-mapping:v1.0.0 <account-id>.dkr.ecr.us-east-1.amazonaws.com/ib-job-skill-mapping:v1.0.0
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/ib-job-skill-mapping:v1.0.0

# 3. Update Kubernetes deployment
kubectl set image deployment/api-gateway-blue \
  api-gateway=<account-id>.dkr.ecr.us-east-1.amazonaws.com/ib-job-skill-mapping:v1.0.0 \
  -n production

# 4. Monitor rollout
kubectl rollout status deployment/api-gateway-blue -n production

# 5. Verify pods
kubectl get pods -n production -l app=api-gateway,version=blue
```

### 2. Cron Production Deployment

#### Deployment as Kubernetes Deployment (Single Replica)

```bash
# Apply cron deployment manifest
kubectl apply -f k8s/production/cron-deployment.yaml -n production

# Verify deployment
kubectl get deployment cron-scheduler -n production

# Check logs
kubectl logs -f deployment/cron-scheduler -n production
```

**Cron Deployment Manifest Example:**
```yaml
# k8s/production/cron-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cron-scheduler
  namespace: production
spec:
  replicas: 1  # Single instance to avoid duplicate job execution
  selector:
    matchLabels:
      app: cron-scheduler
  template:
    metadata:
      labels:
        app: cron-scheduler
    spec:
      serviceAccountName: api-service-account
      containers:
      - name: cron
        image: <account-id>.dkr.ecr.us-east-1.amazonaws.com/ib-job-skill-mapping:v1.0.0
        command: ["python", "-m", "src.app.cron.main"]
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: CRON_ENABLED
          value: "true"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: redis-url
        resources:
          requests:
            cpu: 250m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 2Gi
        livenessProbe:
          exec:
            command:
            - python
            - -c
            - "import sys; sys.exit(0)"
          initialDelaySeconds: 30
          periodSeconds: 60
```

#### Deployment as Kubernetes CronJobs (Alternative)

```bash
# Apply individual cron jobs
kubectl apply -f k8s/production/cronjobs/ -n production

# List cron jobs
kubectl get cronjobs -n production

# Expected:
# NAME                   SCHEDULE      SUSPEND   ACTIVE
# cleanup-old-data       0 2 * * *     False     0
# warm-cache             0 */6 * * *   False     0
# aggregate-metrics      */15 * * * *  False     0
```

**CronJob Manifest Example:**
```yaml
# k8s/production/cronjobs/cleanup-old-data.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: cleanup-old-data
  namespace: production
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM UTC
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: api-service-account
          containers:
          - name: cleanup
            image: <account-id>.dkr.ecr.us-east-1.amazonaws.com/ib-job-skill-mapping:v1.0.0
            command:
            - python
            - -c
            - "from src.app.cron.jobs import cleanup_old_data; cleanup_old_data()"
            env:
            - name: ENVIRONMENT
              value: "production"
            # ... (same env vars as deployment)
          restartPolicy: OnFailure
```

### 3. Verify Production Deployment

```bash
# Check API Gateway
kubectl get pods -n production -l app=api-gateway
kubectl logs -f -l app=api-gateway -n production --tail=50

# Check Cron
kubectl get pods -n production -l app=cron-scheduler
kubectl logs -f -l app=cron-scheduler -n production

# Test API Gateway endpoint
curl https://api.infobeans.com/health
curl https://api.infobeans.com/api/v1/requisitions -H "Authorization: Bearer <token>"

# Check metrics
curl https://api.infobeans.com/metrics

# View in Grafana
# URL: http://grafana.infobeans.com/d/system-overview
```

### 4. Scaling

```bash
# Scale API Gateway manually
kubectl scale deployment api-gateway-blue --replicas=5 -n production

# View HPA status (auto-scaling)
kubectl get hpa -n production

# View current resource usage
kubectl top pods -n production -l app=api-gateway
```

### 5. Rollback

```bash
# View rollout history
kubectl rollout history deployment/api-gateway-blue -n production

# Rollback to previous version
kubectl rollout undo deployment/api-gateway-blue -n production

# Rollback to specific revision
kubectl rollout undo deployment/api-gateway-blue --to-revision=2 -n production

# Or use blue-green traffic switch
kubectl patch service api-gateway -n production \
  -p '{"spec":{"selector":{"version":"green"}}}'
```

---

## Configuration

### Environment-Specific Configuration

| Variable | Local | Production | Description |
|----------|-------|------------|-------------|
| **ENVIRONMENT** | development | production | Environment name |
| **LOG_LEVEL** | DEBUG | INFO | Logging verbosity |
| **API_WORKERS** | 1 | 4 | Uvicorn workers |
| **DATABASE_POOL_SIZE** | 5 | 20 | DB connection pool |
| **REDIS_CACHE_TTL** | 3600 | 7200 | Cache TTL (seconds) |
| **ENABLE_RATE_LIMITING** | false | true | Rate limiting |
| **ENABLE_CIRCUIT_BREAKER** | false | true | Circuit breaker |
| **CORS_ORIGINS** | * | specific domains | CORS allowed origins |

### API Gateway Configuration

**Main Settings (`src/app/settings.py`):**
```python
class Settings(BaseSettings):
    # API Gateway specific
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    api_workers: int = 4  # Production: 4, Local: 1
    api_reload: bool = False  # True in development
    
    # CORS
    cors_origins: List[str] = ["*"]  # Restrict in production
    
    # Rate Limiting
    enable_rate_limiting: bool = True
    rate_limit_per_minute: int = 60
    
    # Timeouts
    request_timeout: int = 30  # seconds
    llm_timeout: int = 60  # seconds
```

### Cron Configuration

**Cron Settings (`src/app/cron/config.py`):**
```python
class CronConfig:
    # Enable/disable cron
    cron_enabled: bool = True
    
    # Timezone
    cron_timezone: str = "UTC"
    
    # Job Schedules
    cleanup_schedule: str = "0 2 * * *"  # Daily at 2 AM
    cache_warming_interval: int = 21600  # Every 6 hours (seconds)
    metrics_aggregation_interval: int = 900  # Every 15 minutes
    
    # Job Settings
    cleanup_retention_days: int = 90
    cache_warm_batch_size: int = 100
```

### Secrets Management

**Local Development:**
- Stored in `.env` file (gitignored)
- Plain text (acceptable for local dev)

**Production:**
- Stored in AWS Secrets Manager
- Retrieved via IRSA (IAM Roles for Service Accounts)
- Mounted as environment variables in pods

**Access Production Secrets:**
```bash
# View secrets (requires AWS access)
aws secretsmanager list-secrets --query 'SecretList[?contains(Name, `ib-job-skill-mapping/prod`)].Name'

# Get specific secret
aws secretsmanager get-secret-value --secret-id ib-job-skill-mapping/prod/database | jq -r .SecretString
```

---

## Monitoring & Logs

### Local Development

**View API Gateway Logs:**
```bash
# Console output (if running in foreground)
# Logs automatically display

# Or tail log file
tail -f logs/app.log

# Filter for errors
tail -f logs/app.log | grep ERROR

# Filter for specific endpoint
tail -f logs/app.log | grep "/api/v1/requisitions"
```

**View Cron Logs:**
```bash
# If running in background
tail -f cron.log

# Or check specific job execution
grep "cleanup_old_data" cron.log
```

**Database Query Logs:**
```bash
# Enable query logging in PostgreSQL
echo "log_statement = 'all'" >> /usr/local/var/postgresql@15/postgresql.conf

# Restart PostgreSQL
brew services restart postgresql@15

# View query logs
tail -f /usr/local/var/postgresql@15/server.log
```

### Production

**View API Gateway Logs:**
```bash
# Real-time logs (all pods)
kubectl logs -f -l app=api-gateway -n production

# Specific pod
kubectl logs -f <pod-name> -n production

# Previous pod instance (if crashed)
kubectl logs <pod-name> -n production --previous

# Last 100 lines
kubectl logs <pod-name> -n production --tail=100

# Filter errors
kubectl logs -l app=api-gateway -n production | grep ERROR
```

**View Cron Logs:**
```bash
# Cron deployment logs
kubectl logs -f deployment/cron-scheduler -n production

# Specific cron job execution
kubectl logs job/cleanup-old-data-<job-id> -n production

# List recent job runs
kubectl get jobs -n production
```

**CloudWatch Logs:**
```bash
# View in AWS Console
# URL: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups

# Or use AWS CLI
aws logs tail /aws/ib-job-skill-mapping/prod/application --follow

# Filter for errors
aws logs filter-log-events \
  --log-group-name /aws/ib-job-skill-mapping/prod/application \
  --filter-pattern "ERROR" \
  --start-time $(date -u -d '1 hour ago' +%s000)
```

**Grafana Dashboards:**
```bash
# System Overview Dashboard
open http://grafana.infobeans.com/d/system-overview

# View metrics:
# - Request rate per endpoint
# - Error rate
# - Response time (p50, p95, p99)
# - Pod resource usage
# - Cron job execution status
```

---

## Troubleshooting

### Common Issues - Local Development

#### 1. Database Connection Failed

**Symptoms:**
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) connection to server at "localhost", port 5432 failed
```

**Solutions:**
```bash
# Check if PostgreSQL is running
# Docker:
docker-compose ps postgres
docker-compose up -d postgres

# Local installation:
# macOS:
brew services list | grep postgresql
brew services start postgresql@15

# Linux:
systemctl status postgresql
sudo systemctl start postgresql

# Verify connection
psql -U postgres -d ib_job_skill_mapping -c "SELECT 1;"

# Check DATABASE_URL in .env
cat .env | grep DATABASE_URL
```

#### 2. Redis Connection Failed

**Symptoms:**
```
redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379. Connection refused.
```

**Solutions:**
```bash
# Check if Redis is running
# Docker:
docker-compose ps redis
docker-compose up -d redis

# Local installation:
redis-cli ping  # Should return PONG

# macOS:
brew services start redis

# Linux:
sudo systemctl start redis-server

# Check REDIS_URL in .env
cat .env | grep REDIS_URL
```

#### 3. Module Import Errors

**Symptoms:**
```
ModuleNotFoundError: No module named 'src'
```

**Solutions:**
```bash
# Reinstall package in editable mode
pip install -e .

# Verify installation
pip list | grep ib-job-skill-mapping

# Check PYTHONPATH
echo $PYTHONPATH

# Or run with PYTHONPATH
PYTHONPATH=. python -m src.app.main
```

#### 4. Port Already in Use

**Symptoms:**
```
OSError: [Errno 48] Address already in use
```

**Solutions:**
```bash
# Find process using port 8080
# macOS/Linux:
lsof -i :8080
# Windows:
netstat -ano | findstr :8080

# Kill process
# macOS/Linux:
kill -9 <PID>
# Windows:
taskkill /PID <PID> /F

# Or use different port
uvicorn src.app.main:app --port 8081
```

#### 5. Cron Jobs Not Running

**Symptoms:**
```
INFO: Scheduler started
# But no jobs execute
```

**Solutions:**
```python
# Check if jobs are registered
python -c "
from src.app.cron.scheduler import scheduler
scheduler.start()
print('Registered jobs:')
for job in scheduler.get_jobs():
    print(f'  - {job.id}: {job.next_run_time}')
"

# Run job manually
python -c "
from src.app.cron.jobs import cleanup_old_data
cleanup_old_data()
"

# Check CRON_ENABLED in .env
cat .env | grep CRON_ENABLED
```

### Common Issues - Production

#### 1. Pods CrashLoopBackOff

**Symptoms:**
```bash
kubectl get pods -n production
# NAME                         READY   STATUS             RESTARTS
# api-gateway-blue-xxx         0/1     CrashLoopBackOff   5
```

**Solutions:**
```bash
# Check pod logs
kubectl logs <pod-name> -n production
kubectl logs <pod-name> -n production --previous

# Describe pod for events
kubectl describe pod <pod-name> -n production

# Common causes:
# - Missing secrets
# - Database connection failed
# - Out of memory (OOMKilled)
# - Failed health checks

# Check secrets exist
kubectl get secrets -n production

# Check database connectivity from pod
kubectl exec -it <pod-name> -n production -- \
  python -c "import psycopg2; conn = psycopg2.connect(os.environ['DATABASE_URL']); print('Connected')"
```

#### 2. High Latency

**Symptoms:**
- Grafana shows p95 latency > 5s
- CloudWatch alarms firing

**Solutions:**
```bash
# Check pod resource usage
kubectl top pods -n production -l app=api-gateway

# Check for throttling
kubectl describe pod <pod-name> -n production | grep -i throttl

# Scale up
kubectl scale deployment api-gateway-blue --replicas=10 -n production

# Check database slow queries
kubectl exec -it <pod-name> -n production -- \
  psql $DATABASE_URL -c "
  SELECT query, calls, mean_exec_time, max_exec_time
  FROM pg_stat_statements
  ORDER BY mean_exec_time DESC
  LIMIT 10;"

# Check Redis performance
kubectl exec -it <pod-name> -n production -- \
  redis-cli -h $REDIS_HOST INFO stats
```

#### 3. Database Connection Pool Exhausted

**Symptoms:**
```
sqlalchemy.exc.TimeoutError: QueuePool limit of size 20 overflow 10 reached
```

**Solutions:**
```bash
# Check active connections
kubectl exec -it <pod-name> -n production -- \
  psql $DATABASE_URL -c "
  SELECT count(*) as active_connections
  FROM pg_stat_activity
  WHERE state = 'active';"

# Increase pool size (temporary)
kubectl set env deployment/api-gateway-blue \
  DATABASE_POOL_SIZE=30 \
  DATABASE_MAX_OVERFLOW=20 \
  -n production

# Or scale RDS instance
aws rds modify-db-instance \
  --db-instance-identifier ib-job-skill-mapping-prod-db \
  --db-instance-class db.r6g.2xlarge \
  --apply-immediately
```

#### 4. Cron Job Failures

**Symptoms:**
```bash
kubectl get jobs -n production
# NAME                         COMPLETIONS   DURATION   AGE
# cleanup-old-data-28474920    0/1           5m         5m
```

**Solutions:**
```bash
# Check job logs
kubectl logs job/cleanup-old-data-28474920 -n production

# Describe job
kubectl describe job cleanup-old-data-28474920 -n production

# Delete failed job
kubectl delete job cleanup-old-data-28474920 -n production

# Trigger manually
kubectl create job --from=cronjob/cleanup-old-data cleanup-test -n production

# Check cron schedule
kubectl get cronjob cleanup-old-data -n production -o yaml | grep schedule
```

#### 5. Out of Memory (OOM)

**Symptoms:**
```
OOMKilled
Exit Code: 137
```

**Solutions:**
```bash
# Check memory usage
kubectl top pod <pod-name> -n production

# Increase memory limits
kubectl set resources deployment api-gateway-blue \
  --limits=memory=4Gi \
  --requests=memory=2Gi \
  -n production

# Check for memory leaks
kubectl exec -it <pod-name> -n production -- \
  python -c "
  import tracemalloc
  tracemalloc.start()
  # ... run operations
  snapshot = tracemalloc.take_snapshot()
  top_stats = snapshot.statistics('lineno')
  for stat in top_stats[:10]:
      print(stat)
  "
```

### Getting Help

**Documentation:**
- [Local Development Guide](runbooks/local_dev.md)
- [Production Deployment Guide](runbooks/production-deployment.md)
- [Incident Response](runbooks/incident-response.md)

**Support Channels:**
- Slack: #devops or #engineering
- Email: devops@infobeans.com
- PagerDuty: For production incidents only

**Useful Commands:**
```bash
# View all make targets
make help

# Run full test suite
make test

# Check code quality
make lint

# View environment info
make info
```

---

## Quick Reference

### Start Services (Local)

```bash
# All services
make dev

# API Gateway only
make run-api

# Cron only
make run-cron

# Stop all
make stop
```

### Deploy (Production)

```bash
# Via GitHub Actions (recommended)
git tag v1.0.0
git push origin v1.0.0

# Manual
kubectl set image deployment/api-gateway-blue api-gateway=<image> -n production
kubectl rollout status deployment/api-gateway-blue -n production
```

### Monitor

```bash
# Local
tail -f logs/app.log

# Production
kubectl logs -f -l app=api-gateway -n production
# Grafana: http://grafana.infobeans.com
```

### Common Tasks

```bash
# Run migrations
alembic upgrade head

# Seed database
python scripts/dev/seed_db.py

# Run tests
pytest

# Format code
black src/

# Lint
flake8 src/
```

---

**Document Version:** 1.0  
**Last Updated:** February 8, 2026  
**Owner:** DevOps & Engineering Teams  
**Questions:** devops@infobeans.com
