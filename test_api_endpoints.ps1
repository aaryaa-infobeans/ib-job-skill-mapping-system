# API Testing Script for IB Job Skill Mapping System
# Date: February 5, 2026

$baseUrl = "http://localhost:8001"
$testResults = @()

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "API Testing - IB Job Skill Mapping System" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Wait for server to start
Start-Sleep -Seconds 3

# Test 1: Health Check
Write-Host "[TEST 1] Testing Health Endpoint" -ForegroundColor Yellow
Write-Host "Endpoint: GET /health" -ForegroundColor Gray
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/health" -UseBasicParsing -Method GET
    $testResults += @{
        Test = "Health Check"
        Endpoint = "GET /health"
        Status = $response.StatusCode
        Result = if ($response.StatusCode -eq 200) { "PASS" } else { "FAIL" }
        Response = $response.Content
        Error = $null
    }
    Write-Host "Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "Response: $($response.Content)`n" -ForegroundColor White
} catch {
    $testResults += @{
        Test = "Health Check"
        Endpoint = "GET /health"
        Status = $_.Exception.Response.StatusCode.value__
        Result = "FAIL"
        Response = $null
        Error = $_.Exception.Message
    }
    Write-Host "ERROR: $($_.Exception.Message)`n" -ForegroundColor Red
}

# Test 2: Metrics Endpoint
Write-Host "[TEST 2] Testing Metrics Endpoint" -ForegroundColor Yellow
Write-Host "Endpoint: GET /api/v1/metrics" -ForegroundColor Gray
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/api/v1/metrics" -UseBasicParsing -Method GET
    $testResults += @{
        Test = "Metrics"
        Endpoint = "GET /api/v1/metrics"
        Status = $response.StatusCode
        Result = if ($response.StatusCode -eq 200) { "PASS" } else { "FAIL" }
        Response = $response.Content.Substring(0, [Math]::Min(200, $response.Content.Length))
        Error = $null
    }
    Write-Host "Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "Response: $($response.Content.Substring(0, [Math]::Min(500, $response.Content.Length)))...`n" -ForegroundColor White
} catch {
    $testResults += @{
        Test = "Metrics"
        Endpoint = "GET /api/v1/metrics"
        Status = $_.Exception.Response.StatusCode.value__
        Result = "FAIL"
        Response = $null
        Error = $_.Exception.Message
    }
    Write-Host "ERROR: $($_.Exception.Message)`n" -ForegroundColor Red
}

# Test 3: Bulk Upsert - Without Auth (Should fail with 401)
Write-Host "[TEST 3] Testing Bulk Upsert Without Auth (Expected 401)" -ForegroundColor Yellow
Write-Host "Endpoint: POST /api/v1/team-members/skill-availability/bulk-upsert" -ForegroundColor Gray
$bulkUpsertPayload = @{
    metadata = @{
        batch_id = "TEST-BATCH-001"
        source = "API-Test"
        timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    }
    team_members = @(
        @{
            team_member_id = "TM001"
            name = "John Doe"
            email = "john.doe@example.com"
            designation = "Senior Software Engineer"
            primary_skills = @("Python", "FastAPI", "PostgreSQL")
            secondary_skills = @("Docker", "Kubernetes")
            total_experience_years = 8
            relevant_experience_years = 5
        }
    )
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-WebRequest -Uri "$baseUrl/api/v1/team-members/skill-availability/bulk-upsert" `
        -Method POST `
        -ContentType "application/json" `
        -Body $bulkUpsertPayload `
        -UseBasicParsing
    $testResults += @{
        Test = "Bulk Upsert (No Auth)"
        Endpoint = "POST /api/v1/team-members/skill-availability/bulk-upsert"
        Status = $response.StatusCode
        Result = if ($response.StatusCode -eq 401) { "PASS (Expected 401)" } else { "UNEXPECTED" }
        Response = $response.Content
        Error = $null
    }
    Write-Host "Status: $($response.StatusCode)" -ForegroundColor Yellow
    Write-Host "Response: $($response.Content)`n" -ForegroundColor White
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    $testResults += @{
        Test = "Bulk Upsert (No Auth)"
        Endpoint = "POST /api/v1/team-members/skill-availability/bulk-upsert"
        Status = $statusCode
        Result = if ($statusCode -eq 401) { "PASS (Expected 401)" } else { "FAIL" }
        Response = $null
        Error = $_.Exception.Message
    }
    if ($statusCode -eq 401) {
        Write-Host "Status: 401 - Authentication Required (Expected)" -ForegroundColor Green
    } else {
        Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    }
    Write-Host ""
}

# Test 4: Requisition Request - Without Auth (Should fail with 401)
Write-Host "[TEST 4] Testing Requisition Request Without Auth (Expected 401)" -ForegroundColor Yellow
Write-Host "Endpoint: POST /api/v1/jd-skill-mapping/" -ForegroundColor Gray
$requisitionPayload = @{
    request_id = "REQ-TEST-001"
    title = "Senior Backend Engineer"
    role = "Backend Development"
    priority = "HIGH"
    location = @("Bangalore", "Remote")
    work_mode = @("Remote", "Hybrid")
    job_description = @{
        jd_text = "We are seeking a Senior Backend Engineer with 5+ years of experience in Python, FastAPI, and PostgreSQL. The ideal candidate should have strong experience in building scalable REST APIs and working with relational databases."
    }
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-WebRequest -Uri "$baseUrl/api/v1/jd-skill-mapping/" `
        -Method POST `
        -ContentType "application/json" `
        -Body $requisitionPayload `
        -UseBasicParsing
    $testResults += @{
        Test = "Requisition Request (No Auth)"
        Endpoint = "POST /api/v1/jd-skill-mapping/"
        Status = $response.StatusCode
        Result = if ($response.StatusCode -eq 401) { "PASS (Expected 401)" } else { "UNEXPECTED" }
        Response = $response.Content
        Error = $null
    }
    Write-Host "Status: $($response.StatusCode)" -ForegroundColor Yellow
    Write-Host "Response: $($response.Content)`n" -ForegroundColor White
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    $testResults += @{
        Test = "Requisition Request (No Auth)"
        Endpoint = "POST /api/v1/jd-skill-mapping/"
        Status = $statusCode
        Result = if ($statusCode -eq 401) { "PASS (Expected 401)" } else { "FAIL" }
        Response = $null
        Error = $_.Exception.Message
    }
    if ($statusCode -eq 401) {
        Write-Host "Status: 401 - Authentication Required (Expected)" -ForegroundColor Green
    } else {
        Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    }
    Write-Host ""
}

# Test 5: Get Matches - Without Auth (Should fail with 401)
Write-Host "[TEST 5] Testing Get Matches Without Auth (Expected 401)" -ForegroundColor Yellow
Write-Host "Endpoint: GET /api/v1/jd-skill-mapping/test-correlation-id/matches" -ForegroundColor Gray
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/api/v1/jd-skill-mapping/test-correlation-id/matches" `
        -Method GET `
        -UseBasicParsing
    $testResults += @{
        Test = "Get Matches (No Auth)"
        Endpoint = "GET /api/v1/jd-skill-mapping/{correlation_id}/matches"
        Status = $response.StatusCode
        Result = if ($response.StatusCode -eq 401) { "PASS (Expected 401)" } else { "UNEXPECTED" }
        Response = $response.Content
        Error = $null
    }
    Write-Host "Status: $($response.StatusCode)" -ForegroundColor Yellow
    Write-Host "Response: $($response.Content)`n" -ForegroundColor White
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    $testResults += @{
        Test = "Get Matches (No Auth)"
        Endpoint = "GET /api/v1/jd-skill-mapping/{correlation_id}/matches"
        Status = $statusCode
        Result = if ($statusCode -eq 401) { "PASS (Expected 401)" } else { "FAIL" }
        Response = $null
        Error = $_.Exception.Message
    }
    if ($statusCode -eq 401) {
        Write-Host "Status: 401 - Authentication Required (Expected)" -ForegroundColor Green
    } else {
        Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    }
    Write-Host ""
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$passed = ($testResults | Where-Object { $_.Result -like "PASS*" }).Count
$failed = ($testResults | Where-Object { $_.Result -eq "FAIL" }).Count
$total = $testResults.Count

Write-Host "Total Tests: $total" -ForegroundColor White
Write-Host "Passed: $passed" -ForegroundColor Green
Write-Host "Failed: $failed" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Detailed Results" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

foreach ($result in $testResults) {
    Write-Host "`nTest: $($result.Test)" -ForegroundColor White
    Write-Host "Endpoint: $($result.Endpoint)" -ForegroundColor Gray
    Write-Host "Status Code: $($result.Status)" -ForegroundColor White
    Write-Host "Result: $($result.Result)" -ForegroundColor $(if ($result.Result -like "PASS*") { "Green" } else { "Red" })
    if ($result.Error) {
        Write-Host "Error: $($result.Error)" -ForegroundColor Red
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Next Steps" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "1. Create OAuth client in database" -ForegroundColor Yellow
Write-Host "2. Generate JWT token" -ForegroundColor Yellow
Write-Host "3. Run authenticated endpoint tests" -ForegroundColor Yellow

# Export results to JSON
$testResults | ConvertTo-Json -Depth 10 | Out-File "api_test_results_phase1.json"
Write-Host "`nResults exported to: api_test_results_phase1.json" -ForegroundColor Cyan
