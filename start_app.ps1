param(
    [switch]$ResetDb = $false
)

# Configuration
$APP_PORT = 9000
$DB_PORT = 5432
$PROJECT_DIR = Get-Location
$VENV_DIR = Join-Path $PROJECT_DIR "venv"

Write-Host "Starting IB Job Skill Mapping System..." -ForegroundColor Cyan

# 1. Stop existing processes
Write-Host "Stopping existing processes on ports $APP_PORT and $DB_PORT..." -ForegroundColor Yellow

# Kill process on app port
$appProcess = Get-NetTCPConnection -LocalPort $APP_PORT -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($appProcess) {
    Write-Host "Killing existing app process (PID: $appProcess)..." -ForegroundColor Yellow
    Stop-Process -Id $appProcess -Force -ErrorAction SilentlyContinue
}

# 2. Optionally reset Database (containers + volume) for a clean start
Set-Location $PROJECT_DIR
if ($ResetDb) {
    Write-Host "Resetting PostgreSQL containers and volume (local data will be LOST)..." -ForegroundColor Yellow
    docker compose down -v
}

# 3. Start Database via Docker Compose
Write-Host "Starting PostgreSQL database..." -ForegroundColor Cyan
docker compose up -d postgres

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to start database container" -ForegroundColor Red
    exit 1
}

# 4. Wait for Database to be ready
Write-Host "Waiting for database to be ready..." -ForegroundColor Yellow
$MAX_RETRIES = 30
$COUNT = 0

do {
    $dbReady = docker compose exec -T postgres pg_isready -U user 2>$null
    if ($LASTEXITCODE -eq 0) {
        break
    }
    Start-Sleep -Seconds 1
    $COUNT++
    Write-Host -NoNewline "."
} while ($COUNT -lt $MAX_RETRIES)

Write-Host ""

if ($COUNT -eq $MAX_RETRIES) {
    Write-Host "Database failed to start in time." -ForegroundColor Red
    exit 1
}
Write-Host "Database is ready!" -ForegroundColor Green

# 5. Activate Virtual Environment and Run Migrations
$venvActivate = Join-Path $VENV_DIR "Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    Write-Host "Activating virtual environment..." -ForegroundColor Cyan
    & $venvActivate
} else {
    Write-Host "Virtual environment not found at $VENV_DIR" -ForegroundColor Red
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    & $venvActivate
    Write-Host "Upgrading pip..." -ForegroundColor Yellow
    python -m pip install --upgrade pip
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt
    
    Write-Host "Downloading SpaCy NER model (en_core_web_trf)..." -ForegroundColor Yellow
    python -m spacy download en_core_web_trf
}

# Ensure pip is up to date (for existing venvs)
python -m pip install --upgrade pip --quiet

# Check if SpaCy is installed
Write-Host "Checking SpaCy installation..." -ForegroundColor Cyan
$spacyInstalled = python -c "import spacy" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "SpaCy not found. Installing from requirements.txt..." -ForegroundColor Yellow
    pip install -r requirements.txt
    
    # If still not installed, try installing just spacy with --only-binary
    $spacyCheck = python -c "import spacy" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Attempting to install SpaCy with pre-built wheels only..." -ForegroundColor Yellow
        pip install --only-binary=:all: "spacy>=3.7,<3.8"
        
        # Final check
        $spacyFinal = python -c "import spacy" 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "WARNING: Could not install SpaCy. PII scrubbing will not be available." -ForegroundColor Red
            Write-Host "Consider using Python 3.11 or 3.12 for better package compatibility." -ForegroundColor Yellow
        }
    }
}

# Check if SpaCy NER model is installed (for existing venvs)
Write-Host "Checking SpaCy NER model..." -ForegroundColor Cyan
$spacyModelCheck = python -c "import spacy; spacy.load('en_core_web_sm')" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "SpaCy NER model not found. Downloading en_core_web_sm (CPU-based, no compilation needed)..." -ForegroundColor Yellow
    python -m spacy download en_core_web_sm
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to download SpaCy model. PII scrubbing may not work correctly." -ForegroundColor Red
        Write-Host "NOTE: For better NER performance, use Python 3.11 or 3.12 to install en_core_web_trf" -ForegroundColor Yellow
    } else {
        Write-Host "SpaCy model downloaded successfully!" -ForegroundColor Green
        Write-Host "NOTE: Using CPU-based model (en_core_web_sm). For transformer-based accuracy, use Python 3.11/3.12." -ForegroundColor Cyan
    }
} else {
    Write-Host "SpaCy NER model already installed." -ForegroundColor Green
}

Write-Host "Running database migrations..." -ForegroundColor Cyan
alembic upgrade head

if ($LASTEXITCODE -ne 0) {
    Write-Host "Database migrations failed" -ForegroundColor Red
    exit 1
}

# 6. Start Backend Application
Write-Host "Starting FastAPI backend on port $APP_PORT..." -ForegroundColor Green
Write-Host "---------------------------------------------------" -ForegroundColor Cyan
Write-Host "App URL: http://127.0.0.1:$APP_PORT" -ForegroundColor Green
Write-Host "API Docs: http://127.0.0.1:$APP_PORT/docs" -ForegroundColor Green
Write-Host "---------------------------------------------------" -ForegroundColor Cyan

python -m uvicorn src.app.main:app --reload --host 127.0.0.1 --port $APP_PORT
