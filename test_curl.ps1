# Test script for making API calls to the JD Skill Mapping API
# This demonstrates the correct curl syntax for Windows PowerShell

Write-Host "==================================================================" -ForegroundColor Green
Write-Host "  IB Job Skill Mapping System - API Test Script" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host ""

# Generate JWT Token
Write-Host "🔑 Generating JWT Token..." -ForegroundColor Yellow
$token = python -c "import jwt; from datetime import datetime, timedelta, timezone; print(jwt.encode({'sub': 'test-client', 'client_id': 'test-client', 'exp': datetime.now(timezone.utc) + timedelta(days=365)}, 'test-secret-key-for-testing', algorithm='HS256'))"

Write-Host "✅ Token Generated:" -ForegroundColor Green
Write-Host $token -ForegroundColor Cyan
Write-Host ""

# Test 1: Health Check (No Auth Required)
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "TEST 1: Health Check (No Authentication)" -ForegroundColor Yellow
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "Endpoint: GET /health" -ForegroundColor White
Write-Host ""

$healthResponse = Invoke-RestMethod -Uri "http://127.0.0.1:8001/health" -Method Get
Write-Host "✅ Health Check Response:" -ForegroundColor Green
$healthResponse | ConvertTo-Json -Depth 10
Write-Host ""

# Test 2: Submit Job Requisition (Auth Required)
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "TEST 2: Submit Job Requisition (JWT Authentication)" -ForegroundColor Yellow
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "Endpoint: POST /api/v1/jd-skill-mapping/" -ForegroundColor White
Write-Host ""

$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type" = "application/json"
    "Accept" = "application/json"
}

$body = @{
    request_id = "REQ-2026-000145"
    schema_version = "1.1"
    source_system = "EAGLE_v1"
    client_name = "DNC"
    metadata = @{
        submitted_by = "Aarya"
        submitted_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        department = "Engineering"
    }
    job_description = @{
        client_name = "DNC"
        title = "Senior Backend Engineer"
        role = "Backend Engineer"
        requisition_duration_month = 3
        expected_start_date = "2026-02-15"
        priority = "HIGH"
        location = @("Bangalore", "Pune")
        work_mode = @("wfh")
        experience = @{
            min_months = 48
            max_months = 60
        }
        mandatory_skills = @(
            "Python",
            "Django",
            "REST API",
            "AWS",
            "PostgreSQL"
        )
        preferred_skills = @(
            "Docker",
            "Kubernetes"
        )
        jd_text = "Looking for a Senior Backend Engineer with strong backend experience in Python, Django, REST APIs, AWS, and PostgreSQL."
    }
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/v1/jd-skill-mapping/" -Method Post -Headers $headers -Body $body -ContentType "application/json"
    Write-Host "✅ Requisition Submitted Successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Response:" -ForegroundColor White
    $response | ConvertTo-Json -Depth 10
    Write-Host ""
    Write-Host "📋 Correlation ID:" -ForegroundColor Yellow
    Write-Host $response.correlation_id -ForegroundColor Cyan
    
    # Save correlation_id for next test
    $correlationId = $response.correlation_id
    
} catch {
    Write-Host "❌ Error submitting requisition:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response Body:" -ForegroundColor Red
        Write-Host $responseBody -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "  Testing Complete!" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "📚 For more tests, see E2E_VALIDATION_GUIDE.md" -ForegroundColor Cyan
Write-Host "🌐 Open Swagger UI: http://127.0.0.1:8001/docs" -ForegroundColor Cyan
Write-Host ""
