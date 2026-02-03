// Stress test to find system limits
// Run: k6 run performance-tests/stress-test.js

import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const AUTH_TOKEN = __ENV.AUTH_TOKEN || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LWNsaWVudCIsImNsaWVudF9pZCI6InRlc3QtY2xpZW50IiwiaWF0IjoxNzA2OTc2MDAwLCJleHAiOjE3MDY5Nzk2MDB9.test';

export const options = {
    stages: [
        { duration: '2m', target: 100 },   // Ramp up to 100 users
        { duration: '5m', target: 100 },   // Stay at 100 users
        { duration: '2m', target: 200 },   // Ramp up to 200 users
        { duration: '5m', target: 200 },   // Stay at 200 users
        { duration: '2m', target: 300 },   // Push to 300 users
        { duration: '5m', target: 300 },   // Stay at 300 users
        { duration: '2m', target: 400 },   // Push to 400 users (breaking point)
        { duration: '5m', target: 400 },   // Stay at 400 users
        { duration: '5m', target: 0 },     // Gradual ramp down
    ],
    thresholds: {
        'http_req_duration': ['p(95)<5000', 'p(99)<10000'],  // More lenient for stress test
        'http_req_failed': ['rate<0.10'],                     // Allow 10% failures
    },
};

function getHeaders() {
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${AUTH_TOKEN}`,
    };
}

export default function () {
    const scenario = __VU % 2;
    
    if (scenario === 0) {
        // Create requisitions
        const payload = {
            request_id: `stress-test-${Date.now()}-${__VU}-${__ITER}`,
            schema_version: 'v1',
            source_system: 'STRESS_TEST',
            job_description: {
                client_name: 'Stress Test Corp',
                title: 'Engineer',
                role: 'Developer',
                priority: 'HIGH',
                location: ['Remote'],
                work_mode: ['Remote'],
                jd_text: 'Stress testing the system with high load.',
            },
            metadata: {test_vu: __VU, test_iter: __ITER},
        };
        
        const res = http.post(
            `${BASE_URL}/api/v1/jd-skill-mapping/`,
            JSON.stringify(payload),
            { headers: getHeaders() }
        );
        
        check(res, { 'requisition created': (r) => r.status === 202 });
        
    } else {
        // Bulk upserts
        const payload = {
            sync_timestamp: new Date().toISOString(),
            team_members: Array.from({ length: 10 }, (_, i) => ({
                team_member_id: `stress-tm-${Date.now()}-${__VU}-${i}`,
                name: `Stress Member ${__VU}-${i}`,
                email: `stress.${__VU}.${i}@test.com`,
                designation: 'Engineer',
                primary_skills: ['Python', 'FastAPI'],
                secondary_skills: ['Docker'],
                total_experience_years: 5,
                relevant_experience_years: 3,
                certifications: [],
                project_allocations: [],
            })),
        };
        
        const res = http.post(
            `${BASE_URL}/api/v1/team-members/skill-availability/bulk-upsert`,
            JSON.stringify(payload),
            { headers: getHeaders() }
        );
        
        check(res, { 'bulk upsert accepted': (r) => r.status === 202 });
    }
    
    sleep(0.5); // Minimal think time for stress test
}
