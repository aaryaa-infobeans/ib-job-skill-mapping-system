#!/bin/bash

# Configuration
APP_PORT=9000
DB_PORT=5433
PROJECT_DIR="/var/www/html/ib-job-skill-mapping-system"
VENV_DIR="$PROJECT_DIR/venv"

echo "🚀 Starting IB Job Skill Mapping System..."

# 1. Stop existing processes
echo "🛑 Stopping existing processes on ports $APP_PORT and $DB_PORT..."

# Kill process on app port
APP_PID=$(lsof -t -i :$APP_PORT)
if [ ! -z "$APP_PID" ]; then
    echo "Killing existing app process (PID: $APP_PID)..."
    kill -9 $APP_PID
fi

# We don't necessarily want to kill local Postgres if it's not the Docker one, 
# but we do want to make sure port 5432 is available for Docker.
# If Docker is already running, 'docker compose up' handles it, but let's be thorough.

# 2. Start Database via Docker Compose
cd "$PROJECT_DIR"
echo "🐘 Starting PostgreSQL 17 with pgvector..."

# Check if old volume exists with incompatible data
if docker volume inspect postgres_data &> /dev/null; then
    echo "🔍 Checking PostgreSQL version compatibility..."
    
    # Try to get the version from the old data directory
    OLD_VERSION=$(docker run --rm -v postgres_data:/data busybox cat /data/PG_VERSION 2>/dev/null || echo "unknown")
    
    if [ "$OLD_VERSION" != "unknown" ] && [ "$OLD_VERSION" != "17" ]; then
        echo "⚠️  Old PostgreSQL volume (v$OLD_VERSION) detected but upgrading to v17"
        echo "🔄 Removing old volume and creating fresh database..."
        docker compose down
        docker volume rm postgres_data
        echo "✅ Old volume removed. Fresh v17 database will be created."
    fi
fi

docker compose pull postgres
docker compose up -d postgres

# 3. Wait for Database to be ready
echo "⏳ Waiting for database to be ready..."
MAX_RETRIES=30
COUNT=0
until docker compose exec -e PGPASSWORD=password postgres pg_isready -U user -h localhost > /dev/null 2>&1 || [ $COUNT -eq $MAX_RETRIES ]; do
    sleep 1
    COUNT=$((COUNT + 1))
    echo -n "."
done
echo ""

if [ $COUNT -eq $MAX_RETRIES ]; then
    echo "❌ Database failed to start in time."
    echo "🔧 Checking Docker container status..."
    docker compose logs postgres | tail -20
    exit 1
fi
echo "✅ Database is ready! (PostgreSQL 17 with pgvector)"

# 4. Activate Virtual Environment and Run Migrations
if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
else
    echo "❌ Virtual environment not found at $VENV_DIR"
    exit 1
fi

# Ensure pip is up to date
python -m pip install --upgrade pip --quiet

# Check if SpaCy is installed
echo "🔍 Checking SpaCy installation..."
if ! python -c "import spacy" &> /dev/null; then
    echo "📦 SpaCy not found. Installing from requirements.txt..."
    pip install -r requirements.txt
fi

# Check if SpaCy NER model is installed
echo "🔍 Checking SpaCy NER model..."
if ! python -c "import spacy; spacy.load('en_core_web_sm')" &> /dev/null; then
    echo "📦 SpaCy NER model not found. Downloading en_core_web_sm (CPU-based, no compilation needed)..."
    python -m spacy download en_core_web_sm
    if [ $? -ne 0 ]; then
        echo "⚠️  Failed to download SpaCy model. PII scrubbing may not work correctly."
        echo "NOTE: For better NER performance, use Python 3.11 or 3.12 to install en_core_web_trf"
    else
        echo "✅ SpaCy model downloaded successfully!"
        echo "NOTE: Using CPU-based model (en_core_web_sm). For transformer-based accuracy, use Python 3.11/3.12."
    fi
else
    echo "✅ SpaCy NER model already installed."
fi

echo "🔄 Running database migrations with Alembic..."
PYTHONPATH=src alembic upgrade heads

if [ $? -ne 0 ]; then
    echo "❌ Database migration failed."
    echo "🔧 Checking database logs..."
    docker compose logs postgres | tail -20
    exit 1
fi
echo "✅ Database migrations completed!"

# 5. Start Backend Application
echo "🌐 Starting FastAPI backend on port $APP_PORT..."
echo "---------------------------------------------------"
echo "PostgreSQL: localhost:$DB_PORT (v17 + pgvector)"
echo "App URL: http://127.0.0.1:$APP_PORT"
echo "API Docs: http://127.0.0.1:$APP_PORT/docs"
echo "---------------------------------------------------"

PYTHONPATH=src python -m uvicorn src.app.main:app --reload --host 127.0.0.1 --port $APP_PORT
