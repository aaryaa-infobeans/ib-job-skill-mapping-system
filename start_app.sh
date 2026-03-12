#!/bin/bash

# Configuration
APP_PORT=9000
DB_PORT=5432
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
echo "🐘 Starting PostgreSQL database..."
docker compose up -d postgres

# 3. Wait for Database to be ready
echo "⏳ Waiting for database to be ready..."
MAX_RETRIES=30
COUNT=0
until docker compose exec postgres pg_isready -U user > /dev/null 2>&1 || [ $COUNT -eq $MAX_RETRIES ]; do
    sleep 1
    COUNT=$((COUNT + 1))
    echo -n "."
done
echo ""

if [ $COUNT -eq $MAX_RETRIES ]; then
    echo "❌ Database failed to start in time."
    exit 1
fi
echo "✅ Database is ready!"

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

echo "🔄 Running database migrations..."
alembic upgrade head

# 5. Start Backend Application
echo "🌐 Starting FastAPI backend on port $APP_PORT..."
echo "---------------------------------------------------"
echo "App URL: http://127.0.0.1:$APP_PORT"
echo "API Docs: http://127.0.0.1:$APP_PORT/docs"
echo "---------------------------------------------------"

python -m uvicorn src.app.main:app --reload --host 127.0.0.1 --port $APP_PORT
