// Smoke test for quick validation
// Run: k6 run performance-tests/smoke-test.js

import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const AUTH_TOKEN = __ENV.AUTH_TOKEN || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LWNsaWVudCIsImNsaWVudF9pZCI6InRlc3QtY2xpZW50IiwiaWF0IjoxNzA2OTc2MDAwLCJleHAiOjE3MDY5Nzk2MDB9.test';

export const options = {
    vus: 1,
    duration: '30s',
    thresholds: {
        'http_req_duration': ['p(95)<3000'],
        'http_req_failed': ['rate<0.01'],
    },
};

function getHeaders() {
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${AUTH_TOKEN}`,
    };
}

export default function () {
    // Test 1: Health check
    let res = http.get(`${BASE_URL}/health`);
    check(res, { 'health OK': (r) => r.status === 200 });
    
    // Test 2: Metrics endpoint
    res = http.get(`${BASE_URL}/api/v1/metrics`);
    check(res, { 'metrics OK': (r) => r.status === 200 });
    
    // Test 3: Create requisition
    const requisitionPayload = {
        request_id: `smoke-test-${Date.now()}`,
        schema_version: 'v1',
        source_system: 'SMOKE_TEST',
        job_description: {
            client_name: 'Test Corp',
            title: 'Software Engineer',
            role: 'Developer',
            priority: 'MEDIUM',
            location: ['Remote'],
            work_mode: ['Remote'],
            jd_text: 'Looking for a software engineer with Python experience.',
        },
        metadata: {},
    };
    
    res = http.post(
        `${BASE_URL}/api/v1/jd-skill-mapping/`,
        JSON.stringify(requisitionPayload),
        { headers: getHeaders() }
    );
    
    const success = check(res, {
        'requisition created': (r) => r.status === 202,
        'has correlation_id': (r) => JSON.parse(r.body).correlation_id !== undefined,
    });
    
    if (success) {
        const correlationId = JSON.parse(res.body).correlation_id;
        
        // Test 4: Get matches
        sleep(2); // Wait for processing
        res = http.get(
            `${BASE_URL}/api/v1/jd-skill-mapping/${correlationId}/matches`,
            { headers: getHeaders() }
        );
        
        check(res, {
            'matches endpoint accessible': (r) => r.status === 200 || r.status === 404,
        });
    }
    
    // Test 5: Bulk upsert
    const bulkPayload = {
        sync_timestamp: new Date().toISOString(),
        team_members: [
            {
                team_member_id: `smoke-tm-${Date.now()}`,
                name: 'Smoke Test Member',
                email: 'smoke@test.com',
                designation: 'Engineer',
                primary_skills: ['Python'],
                secondary_skills: ['Docker'],
                total_experience_years: 3,
                relevant_experience_years: 2,
                certifications: [],
                project_allocations: [],
            },
        ],
    };
    
    res = http.post(
        `${BASE_URL}/api/v1/team-members/skill-availability/bulk-upsert`,
        JSON.stringify(bulkPayload),
        { headers: getHeaders() }
    );
    
    check(res, { 'bulk upsert accepted': (r) => r.status === 202 });
    
    sleep(1);
}
