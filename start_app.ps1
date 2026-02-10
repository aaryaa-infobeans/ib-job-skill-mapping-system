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

# 2. Start Database via Docker Compose
Set-Location $PROJECT_DIR
Write-Host "Starting PostgreSQL database..." -ForegroundColor Cyan
docker compose up -d postgres

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to start database container" -ForegroundColor Red
    exit 1
}

# 3. Wait for Database to be ready
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

# 4. Activate Virtual Environment and Run Migrations
$venvActivate = Join-Path $VENV_DIR "Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    Write-Host "Activating virtual environment..." -ForegroundColor Cyan
    & $venvActivate
} else {
    Write-Host "Virtual environment not found at $VENV_DIR" -ForegroundColor Red
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    & $venvActivate
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt
}

Write-Host "Running database migrations..." -ForegroundColor Cyan
alembic upgrade head

if ($LASTEXITCODE -ne 0) {
    Write-Host "Database migrations failed" -ForegroundColor Red
    exit 1
}

# 5. Start Backend Application
Write-Host "Starting FastAPI backend on port $APP_PORT..." -ForegroundColor Green
Write-Host "---------------------------------------------------" -ForegroundColor Cyan
Write-Host "App URL: http://127.0.0.1:$APP_PORT" -ForegroundColor Green
Write-Host "API Docs: http://127.0.0.1:$APP_PORT/docs" -ForegroundColor Green
Write-Host "---------------------------------------------------" -ForegroundColor Cyan

python -m uvicorn src.app.main:app --reload --host 127.0.0.1 --port $APP_PORT
