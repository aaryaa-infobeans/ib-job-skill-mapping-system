// Performance test suite for IB Job Skill Mapping System
// Uses k6 load testing framework (https://k6.io/)
//
// Run tests:
//   k6 run performance-tests/load-test.js
//
// Run with specific VUs and duration:
//   k6 run --vus 10 --duration 30s performance-tests/load-test.js
//
// Environment variables:
//   BASE_URL: API base URL (default: http://localhost:8000)
//   AUTH_TOKEN: JWT token for authentication

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Configuration
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const AUTH_TOKEN = __ENV.AUTH_TOKEN || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LWNsaWVudCIsImNsaWVudF9pZCI6InRlc3QtY2xpZW50IiwiaWF0IjoxNzA2OTc2MDAwLCJleHAiOjE3MDY5Nzk2MDB9.test';

// Custom metrics
const errorRate = new Rate('errors');
const requisitionLatency = new Trend('requisition_create_latency');
const matchesLatency = new Trend('matches_get_latency');
const bulkUpsertLatency = new Trend('bulk_upsert_latency');
const successfulRequisitions = new Counter('successful_requisitions');
const failedRequisitions = new Counter('failed_requisitions');

// Test configuration
export const options = {
    stages: [
        { duration: '30s', target: 10 },   // Ramp up to 10 users
        { duration: '1m', target: 10 },    // Stay at 10 users
        { duration: '30s', target: 50 },   // Ramp up to 50 users
        { duration: '2m', target: 50 },    // Stay at 50 users
        { duration: '30s', target: 100 },  // Ramp up to 100 users
        { duration: '1m', target: 100 },   // Stay at 100 users
        { duration: '30s', target: 0 },    // Ramp down to 0 users
    ],
    thresholds: {
        'http_req_duration': ['p(95)<2000', 'p(99)<5000'],  // 95th percentile < 2s, 99th < 5s
        'errors': ['rate<0.05'],                             // Error rate < 5%
        'http_req_failed': ['rate<0.05'],                    // Failed requests < 5%
    },
};

// Request headers with authentication
function getHeaders() {
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${AUTH_TOKEN}`,
    };
}

// Generate sample requisition payload
function generateRequisitionPayload() {
    const timestamp = Date.now();
    return {
        request_id: `perf-test-${timestamp}-${__VU}-${__ITER}`,
        schema_version: 'v1',
        source_system: 'PERFORMANCE_TEST',
        job_description: {
            client_name: 'Test Corp',
            title: 'Senior Software Engineer',
            role: 'Backend Developer',
            priority: 'HIGH',
            location: ['Remote', 'Bangalore'],
            work_mode: ['Remote', 'Hybrid'],
            jd_text: 'We are seeking a Senior Software Engineer with expertise in Python, FastAPI, PostgreSQL, and cloud technologies. Experience with microservices architecture and CI/CD pipelines is required. Familiarity with LangGraph and AI/ML frameworks is a plus.',
        },
        metadata: {
            submitted_by: `perf-tester-${__VU}@test.com`,
            department: 'Engineering',
            test_iteration: __ITER,
        },
    };
}

// Generate sample bulk upsert payload
function generateBulkUpsertPayload() {
    const timestamp = Date.now();
    const numMembers = 5; // 5 team members per request
    
    return {
        sync_timestamp: new Date().toISOString(),
        team_members: Array.from({ length: numMembers }, (_, i) => ({
            team_member_id: `perf-tm-${timestamp}-${__VU}-${i}`,
            name: `Test Member ${__VU}-${i}`,
            email: `test.member.${__VU}.${i}@test.com`,
            designation: 'Senior Engineer',
            primary_skills: ['Python', 'FastAPI', 'PostgreSQL'],
            secondary_skills: ['Docker', 'Kubernetes', 'AWS'],
            total_experience_years: 5 + (i % 10),
            relevant_experience_years: 3 + (i % 5),
            certifications: ['AWS Certified Developer'],
            project_allocations: [
                {
                    project_id: `proj-${i}`,
                    project_name: `Project ${i}`,
                    allocation_percentage: 50,
                    start_date: '2026-01-01',
                    end_date: '2026-06-30',
                },
            ],
        })),
    };
}

// Test scenario: Create requisition (FR-1)
export function testCreateRequisition() {
    const payload = generateRequisitionPayload();
    
    const res = http.post(
        `${BASE_URL}/api/v1/jd-skill-mapping/`,
        JSON.stringify(payload),
        { headers: getHeaders() }
    );
    
    const success = check(res, {
        'requisition created (202)': (r) => r.status === 202,
        'has correlation_id': (r) => JSON.parse(r.body).correlation_id !== undefined,
    });
    
    requisitionLatency.add(res.timings.duration);
    errorRate.add(!success);
    
    if (success) {
        successfulRequisitions.add(1);
        return JSON.parse(res.body).correlation_id;
    } else {
        failedRequisitions.add(1);
        console.error(`Failed to create requisition: ${res.status} - ${res.body}`);
        return null;
    }
}

// Test scenario: Get matches (FR-2)
export function testGetMatches(correlationId) {
    if (!correlationId) {
        return;
    }
    
    const res = http.get(
        `${BASE_URL}/api/v1/jd-skill-mapping/${correlationId}/matches`,
        { headers: getHeaders() }
    );
    
    const success = check(res, {
        'matches retrieved (200 or 404)': (r) => r.status === 200 || r.status === 404,
    });
    
    matchesLatency.add(res.timings.duration);
    errorRate.add(!success);
}

// Test scenario: Bulk upsert skill availability (FR-3)
export function testBulkUpsert() {
    const payload = generateBulkUpsertPayload();
    
    const res = http.post(
        `${BASE_URL}/api/v1/team-members/skill-availability/bulk-upsert`,
        JSON.stringify(payload),
        { headers: getHeaders() }
    );
    
    const success = check(res, {
        'bulk upsert accepted (202)': (r) => r.status === 202,
    });
    
    bulkUpsertLatency.add(res.timings.duration);
    errorRate.add(!success);
    
    if (!success) {
        console.error(`Failed bulk upsert: ${res.status} - ${res.body}`);
    }
}

// Test scenario: Health check (non-authenticated)
export function testHealthCheck() {
    const res = http.get(`${BASE_URL}/health`, {
        headers: { 'Content-Type': 'application/json' },
    });
    
    check(res, {
        'health check OK': (r) => r.status === 200,
    });
}

// Main test scenario
export default function () {
    // Mix of different operations to simulate realistic traffic
    const scenario = __VU % 4;
    
    switch (scenario) {
        case 0:
            // Requisition creation + matches retrieval workflow
            const correlationId = testCreateRequisition();
            sleep(1); // Wait a bit before checking matches
            testGetMatches(correlationId);
            break;
            
        case 1:
            // Bulk upsert operation
            testBulkUpsert();
            break;
            
        case 2:
            // Just requisition creation
            testCreateRequisition();
            break;
            
        case 3:
            // Health check
            testHealthCheck();
            break;
    }
    
    // Think time between requests (1-3 seconds)
    sleep(1 + Math.random() * 2);
}

// Setup function (runs once per VU)
export function setup() {
    console.log(`Starting performance tests against ${BASE_URL}`);
    console.log(`Test will simulate realistic user behavior with mixed operations`);
    
    // Verify API is accessible
    const res = http.get(`${BASE_URL}/health`);
    if (res.status !== 200 && res.status !== 503) {
        throw new Error(`API is not accessible at ${BASE_URL}`);
    }
    
    return { startTime: new Date().toISOString() };
}

// Teardown function (runs once after all VUs complete)
export function teardown(data) {
    console.log(`Performance tests completed. Started at ${data.startTime}`);
}
