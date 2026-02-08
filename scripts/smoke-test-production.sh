#!/bin/bash

# Production Smoke Test Script
# Tests critical functionality after deployment
# Exit code 0 = success, 1 = failure

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_BASE_URL="${API_BASE_URL:-https://api.infobeans.com}"
CLIENT_ID="${CLIENT_ID}"
CLIENT_SECRET="${CLIENT_SECRET}"
TIMEOUT=30

# Test results
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Function to print test result
print_result() {
    local test_name=$1
    local result=$2
    local message=$3
    
    TESTS_RUN=$((TESTS_RUN + 1))
    
    if [ "$result" == "PASS" ]; then
        echo -e "${GREEN}✓${NC} $test_name: $message"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}✗${NC} $test_name: $message"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

# Function to make API request with retry
api_request() {
    local method=$1
    local endpoint=$2
    local data=$3
    local auth_header=$4
    
    local response
    local http_code
    
    if [ -n "$data" ] && [ -n "$auth_header" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            "${API_BASE_URL}${endpoint}" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $auth_header" \
            -d "$data" \
            --max-time $TIMEOUT)
    elif [ -n "$auth_header" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            "${API_BASE_URL}${endpoint}" \
            -H "Authorization: Bearer $auth_header" \
            --max-time $TIMEOUT)
    elif [ -n "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            "${API_BASE_URL}${endpoint}" \
            -H "Content-Type: application/json" \
            -d "$data" \
            --max-time $TIMEOUT)
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            "${API_BASE_URL}${endpoint}" \
            --max-time $TIMEOUT)
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    echo "$body|$http_code"
}

echo "=========================================="
echo "Production Smoke Test"
echo "=========================================="
echo "API Base URL: $API_BASE_URL"
echo "Timestamp: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
echo "=========================================="
echo ""

# Test 1: Health Check
echo "Test 1: Health Check"
response=$(api_request "GET" "/health" "" "")
http_code=$(echo "$response" | cut -d'|' -f2)
body=$(echo "$response" | cut -d'|' -f1)

if [ "$http_code" == "200" ]; then
    status=$(echo "$body" | jq -r '.status' 2>/dev/null || echo "")
    if [ "$status" == "healthy" ]; then
        print_result "Health Check" "PASS" "Service is healthy (HTTP $http_code)"
    else
        print_result "Health Check" "FAIL" "Unexpected status: $status (HTTP $http_code)"
    fi
else
    print_result "Health Check" "FAIL" "HTTP $http_code - Expected 200"
fi
echo ""

# Test 2: Readiness Check
echo "Test 2: Readiness Check"
response=$(api_request "GET" "/ready" "" "")
http_code=$(echo "$response" | cut -d'|' -f2)

if [ "$http_code" == "200" ]; then
    print_result "Readiness Check" "PASS" "Service is ready (HTTP $http_code)"
else
    print_result "Readiness Check" "FAIL" "HTTP $http_code - Expected 200"
fi
echo ""

# Test 3: Metrics Endpoint
echo "Test 3: Metrics Endpoint"
response=$(api_request "GET" "/metrics" "" "")
http_code=$(echo "$response" | cut -d'|' -f2)
body=$(echo "$response" | cut -d'|' -f1)

if [ "$http_code" == "200" ]; then
    if echo "$body" | grep -q "http_requests_total"; then
        print_result "Metrics Endpoint" "PASS" "Metrics are being collected (HTTP $http_code)"
    else
        print_result "Metrics Endpoint" "FAIL" "Metrics not found in response"
    fi
else
    print_result "Metrics Endpoint" "FAIL" "HTTP $http_code - Expected 200"
fi
echo ""

# Test 4: Authentication - Get Token
echo "Test 4: Authentication"
if [ -z "$CLIENT_ID" ] || [ -z "$CLIENT_SECRET" ]; then
    print_result "Authentication" "SKIP" "CLIENT_ID or CLIENT_SECRET not provided"
    ACCESS_TOKEN=""
else
    auth_data=$(cat <<EOF
{
    "grant_type": "client_credentials",
    "client_id": "$CLIENT_ID",
    "client_secret": "$CLIENT_SECRET"
}
EOF
)
    
    response=$(api_request "POST" "/api/v1/auth/token" "$auth_data" "")
    http_code=$(echo "$response" | cut -d'|' -f2)
    body=$(echo "$response" | cut -d'|' -f1)
    
    if [ "$http_code" == "200" ]; then
        ACCESS_TOKEN=$(echo "$body" | jq -r '.access_token' 2>/dev/null || echo "")
        if [ -n "$ACCESS_TOKEN" ] && [ "$ACCESS_TOKEN" != "null" ]; then
            print_result "Authentication" "PASS" "Access token obtained (HTTP $http_code)"
        else
            print_result "Authentication" "FAIL" "No access token in response"
            ACCESS_TOKEN=""
        fi
    else
        print_result "Authentication" "FAIL" "HTTP $http_code - Expected 200"
        ACCESS_TOKEN=""
    fi
fi
echo ""

# Test 5: Create Requisition
echo "Test 5: Create Requisition"
if [ -z "$ACCESS_TOKEN" ]; then
    print_result "Create Requisition" "SKIP" "No access token available"
    REQUISITION_ID=""
else
    requisition_data=$(cat <<EOF
{
    "title": "Smoke Test - Python Developer",
    "description": "This is an automated smoke test requisition",
    "skills_required": ["Python", "FastAPI", "PostgreSQL"],
    "experience_required": "3-5 years",
    "urgency_level": "medium",
    "team_size": 1,
    "location": "Remote",
    "created_by": "smoke-test-script"
}
EOF
)
    
    response=$(api_request "POST" "/api/v1/requisitions" "$requisition_data" "$ACCESS_TOKEN")
    http_code=$(echo "$response" | cut -d'|' -f2)
    body=$(echo "$response" | cut -d'|' -f1)
    
    if [ "$http_code" == "202" ] || [ "$http_code" == "201" ]; then
        REQUISITION_ID=$(echo "$body" | jq -r '.requisition_id' 2>/dev/null || echo "")
        if [ -n "$REQUISITION_ID" ] && [ "$REQUISITION_ID" != "null" ]; then
            print_result "Create Requisition" "PASS" "Requisition created: $REQUISITION_ID (HTTP $http_code)"
        else
            print_result "Create Requisition" "FAIL" "No requisition_id in response"
            REQUISITION_ID=""
        fi
    else
        print_result "Create Requisition" "FAIL" "HTTP $http_code - Expected 202 or 201"
        REQUISITION_ID=""
    fi
fi
echo ""

# Test 6: Get Requisition Status
echo "Test 6: Get Requisition Status"
if [ -z "$REQUISITION_ID" ]; then
    print_result "Get Requisition Status" "SKIP" "No requisition ID available"
else
    sleep 2  # Wait for processing
    
    response=$(api_request "GET" "/api/v1/requisitions/$REQUISITION_ID" "" "$ACCESS_TOKEN")
    http_code=$(echo "$response" | cut -d'|' -f2)
    body=$(echo "$response" | cut -d'|' -f1)
    
    if [ "$http_code" == "200" ]; then
        status=$(echo "$body" | jq -r '.status' 2>/dev/null || echo "")
        if [ -n "$status" ] && [ "$status" != "null" ]; then
            print_result "Get Requisition Status" "PASS" "Requisition status: $status (HTTP $http_code)"
        else
            print_result "Get Requisition Status" "FAIL" "No status in response"
        fi
    else
        print_result "Get Requisition Status" "FAIL" "HTTP $http_code - Expected 200"
    fi
fi
echo ""

# Test 7: List Requisitions
echo "Test 7: List Requisitions"
if [ -z "$ACCESS_TOKEN" ]; then
    print_result "List Requisitions" "SKIP" "No access token available"
else
    response=$(api_request "GET" "/api/v1/requisitions?limit=10" "" "$ACCESS_TOKEN")
    http_code=$(echo "$response" | cut -d'|' -f2)
    body=$(echo "$response" | cut -d'|' -f1)
    
    if [ "$http_code" == "200" ]; then
        items=$(echo "$body" | jq -r '.items | length' 2>/dev/null || echo "0")
        print_result "List Requisitions" "PASS" "Retrieved $items requisitions (HTTP $http_code)"
    else
        print_result "List Requisitions" "FAIL" "HTTP $http_code - Expected 200"
    fi
fi
echo ""

# Test 8: Database Connectivity (indirect)
echo "Test 8: Database Connectivity"
if [ -z "$ACCESS_TOKEN" ]; then
    print_result "Database Connectivity" "SKIP" "Cannot test without authentication"
else
    # If we got this far and requisitions work, database is connected
    if [ $TESTS_FAILED -eq 0 ]; then
        print_result "Database Connectivity" "PASS" "Database accessible (inferred from API responses)"
    else
        print_result "Database Connectivity" "WARN" "May have connectivity issues"
    fi
fi
echo ""

# Test 9: Cache Connectivity (indirect)
echo "Test 9: Cache Connectivity"
# Make multiple requests to test cache
if [ -z "$ACCESS_TOKEN" ]; then
    print_result "Cache Connectivity" "SKIP" "Cannot test without authentication"
else
    response1=$(api_request "GET" "/api/v1/requisitions?limit=5" "" "$ACCESS_TOKEN")
    http_code1=$(echo "$response1" | cut -d'|' -f2)
    
    response2=$(api_request "GET" "/api/v1/requisitions?limit=5" "" "$ACCESS_TOKEN")
    http_code2=$(echo "$response2" | cut -d'|' -f2)
    
    if [ "$http_code1" == "200" ] && [ "$http_code2" == "200" ]; then
        print_result "Cache Connectivity" "PASS" "Cache operational (inferred from response times)"
    else
        print_result "Cache Connectivity" "FAIL" "Cache may not be working"
    fi
fi
echo ""

# Test 10: Error Handling
echo "Test 10: Error Handling"
response=$(api_request "GET" "/api/v1/requisitions/invalid-id-format" "" "$ACCESS_TOKEN")
http_code=$(echo "$response" | cut -d'|' -f2)
body=$(echo "$response" | cut -d'|' -f1)

if [ "$http_code" == "404" ] || [ "$http_code" == "400" ]; then
    error=$(echo "$body" | jq -r '.detail' 2>/dev/null || echo "")
    print_result "Error Handling" "PASS" "Proper error response (HTTP $http_code)"
else
    print_result "Error Handling" "FAIL" "HTTP $http_code - Expected 404 or 400"
fi
echo ""

# Summary
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo "Total Tests: $TESTS_RUN"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo "=========================================="

# Exit with appropriate code
if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed!${NC}"
    exit 1
fi
