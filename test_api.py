"""
API Testing Script for IB Job Skill Mapping System
Date: February 5, 2026
"""

import requests
import json
from datetime import datetime
from typing import Dict, List, Any
import time
import warnings

# Suppress datetime warnings for test script
warnings.filterwarnings('ignore', category=DeprecationWarning)

BASE_URL = "http://localhost:8001"

class APITester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.results: List[Dict[str, Any]] = []
        self.auth_token = None
        
    def add_result(self, test_name: str, endpoint: str, status_code: int, 
                   result: str, response: Any = None, error: str = None):
        """Add test result to results list"""
        self.results.append({
            "test": test_name,
            "endpoint": endpoint,
            "status_code": status_code,
            "result": result,
            "response": response,
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    def print_header(self, text: str):
        """Print formatted header"""
        print(f"\n{'='*60}")
        print(f"{text}")
        print(f"{'='*60}\n")
        
    def test_health_endpoint(self):
        """Test the health check endpoint"""
        print("[TEST 1] Testing Health Endpoint")
        print("Endpoint: GET /health")
        
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}\n")
            
            self.add_result(
                "Health Check",
                "GET /health",
                response.status_code,
                "PASS" if response.status_code == 200 else "FAIL",
                response.json() if response.status_code == 200 else response.text
            )
            return response.status_code == 200
        except Exception as e:
            print(f"ERROR: {str(e)}\n")
            self.add_result("Health Check", "GET /health", 0, "FAIL", error=str(e))
            return False
            
    def test_metrics_endpoint(self):
        """Test the metrics endpoint"""
        print("[TEST 2] Testing Metrics Endpoint")
        print("Endpoint: GET /api/v1/metrics")
        
        try:
            response = requests.get(f"{self.base_url}/api/v1/metrics", timeout=5)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}...\n")
            
            self.add_result(
                "Metrics",
                "GET /api/v1/metrics",
                response.status_code,
                "PASS" if response.status_code == 200 else "FAIL",
                response.text[:200]
            )
            return response.status_code == 200
        except Exception as e:
            print(f"ERROR: {str(e)}\n")
            self.add_result("Metrics", "GET /api/v1/metrics", 0, "FAIL", error=str(e))
            return False
            
    def test_bulk_upsert_no_auth(self):
        """Test bulk upsert without authentication (should fail with 401)"""
        print("[TEST 3] Testing Bulk Upsert Without Auth (Expected 401)")
        print("Endpoint: POST /api/v1/team-members/skill-availability/bulk-upsert")
        
        payload = {
            "metadata": {
                "batch_id": "TEST-BATCH-001",
                "timestamp": datetime.now().isoformat() + "Z",
                "total_records": 1,
                "batch_number": 1,
                "total_batches": 1,
                "records_in_batch": 1,
                "source_system": "API-Test",
                "schema_version": "1.0",
                "status": {
                    "code": 200,
                    "key": "SUCCESS",
                    "message": "Batch submitted"
                }
            },
            "team_members": [
                {
                    "team_member_id": "TM001",
                    "team_member_status": "active",
                    "experience_in_months": 96,
                    "full_name": "John Doe",
                    "designation": "Senior Software Engineer",
                    "skills": [
                        {
                            "skill_id": "SKILL001",
                            "skill_name": "Python",
                            "rating": 9,
                            "experience_in_months": 60
                        }
                    ]
                }
            ]
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/team-members/skill-availability/bulk-upsert",
                json=payload,
                timeout=5
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}\n")
            
            result = "PASS (Expected 401)" if response.status_code == 401 else "UNEXPECTED"
            self.add_result(
                "Bulk Upsert (No Auth)",
                "POST /api/v1/team-members/skill-availability/bulk-upsert",
                response.status_code,
                result,
                response.text if response.status_code != 401 else None
            )
            return response.status_code == 401
        except Exception as e:
            print(f"ERROR: {str(e)}\n")
            self.add_result(
                "Bulk Upsert (No Auth)",
                "POST /api/v1/team-members/skill-availability/bulk-upsert",
                0,
                "FAIL",
                error=str(e)
            )
            return False
            
    def test_requisition_no_auth(self):
        """Test requisition request without authentication (should fail with 401)"""
        print("[TEST 4] Testing Requisition Request Without Auth (Expected 401)")
        print("Endpoint: POST /api/v1/jd-skill-mapping/")
        
        payload = {
            "request_id": "REQ-TEST-001",
            "schema_version": "1.0",
            "source_system": "API-Test",
            "job_description": {
                "client_name": "Test Client",
                "title": "Senior Backend Engineer",
                "role": "Backend Development",
                "priority": "HIGH",
                "location": ["Bangalore", "Remote"],
                "work_mode": ["Remote", "Hybrid"],
                "jd_text": "We are seeking a Senior Backend Engineer with 5+ years of experience in Python, FastAPI, and PostgreSQL."
            },
            "metadata": {
                "submitted_by": "test@example.com"
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/jd-skill-mapping/",
                json=payload,
                timeout=5
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}\n")
            
            result = "PASS (Expected 401)" if response.status_code == 401 else "UNEXPECTED"
            self.add_result(
                "Requisition Request (No Auth)",
                "POST /api/v1/jd-skill-mapping/",
                response.status_code,
                result,
                response.text if response.status_code != 401 else None
            )
            return response.status_code == 401
        except Exception as e:
            print(f"ERROR: {str(e)}\n")
            self.add_result(
                "Requisition Request (No Auth)",
                "POST /api/v1/jd-skill-mapping/",
                0,
                "FAIL",
                error=str(e)
            )
            return False
            
    def test_get_matches_no_auth(self):
        """Test get matches without authentication (should fail with 401)"""
        print("[TEST 5] Testing Get Matches Without Auth (Expected 401)")
        print("Endpoint: GET /api/v1/jd-skill-mapping/test-correlation-id/matches")
        
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/jd-skill-mapping/test-correlation-id/matches",
                timeout=5
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}\n")
            
            result = "PASS (Expected 401)" if response.status_code == 401 else "UNEXPECTED"
            self.add_result(
                "Get Matches (No Auth)",
                "GET /api/v1/jd-skill-mapping/{correlation_id}/matches",
                response.status_code,
                result,
                response.text if response.status_code != 401 else None
            )
            return response.status_code == 401
        except Exception as e:
            print(f"ERROR: {str(e)}\n")
            self.add_result(
                "Get Matches (No Auth)",
                "GET /api/v1/jd-skill-mapping/{correlation_id}/matches",
                0,
                "FAIL",
                error=str(e)
            )
            return False
            
    def test_bulk_upsert_with_auth(self, token: str):
        """Test bulk upsert with authentication"""
        print("[TEST 6] Testing Bulk Upsert With Auth")
        print("Endpoint: POST /api/v1/team-members/skill-availability/bulk-upsert")
        
        payload = {
            "metadata": {
                "batch_id": "TEST-BATCH-002",
                "timestamp": datetime.now().isoformat() + "Z",
                "total_records": 1,
                "batch_number": 1,
                "total_batches": 1,
                "records_in_batch": 1,
                "source_system": "API-Test-Auth",
                "schema_version": "1.0",
                "status": {
                    "code": 200,
                    "key": "SUCCESS",
                    "message": "Batch submitted"
                }
            },
            "team_members": [
                {
                    "team_member_id": "TM002",
                    "team_member_status": "active",
                    "experience_in_months": 120,
                    "full_name": "Jane Smith",
                    "designation": "Tech Lead",
                    "skills": [
                        {
                            "skill_id": "SKILL002",
                            "skill_name": "Python",
                            "rating": 9,
                            "experience_in_months": 96
                        },
                        {
                            "skill_id": "SKILL003",
                            "skill_name": "Django",
                            "rating": 8,
                            "experience_in_months": 72
                        }
                    ],
                    "allocations": [
                        {
                            "project_id": "PROJ001",
                            "allocation_percentage": 50.0,
                            "start_date": "2026-01-01",
                            "end_date": "2026-06-30"
                        }
                    ]
                }
            ]
        }
        
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/team-members/skill-availability/bulk-upsert",
                json=payload,
                headers=headers,
                timeout=10
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}\n")
            
            result = "PASS" if response.status_code in [200, 202] else "FAIL"
            self.add_result(
                "Bulk Upsert (With Auth)",
                "POST /api/v1/team-members/skill-availability/bulk-upsert",
                response.status_code,
                result,
                response.json() if response.status_code in [200, 202] else response.text
            )
            return response.status_code in [200, 202]
        except Exception as e:
            print(f"ERROR: {str(e)}\n")
            self.add_result(
                "Bulk Upsert (With Auth)",
                "POST /api/v1/team-members/skill-availability/bulk-upsert",
                0,
                "FAIL",
                error=str(e)
            )
            return False
            
    def test_requisition_with_auth(self, token: str):
        """Test requisition request with authentication"""
        print("[TEST 7] Testing Requisition Request With Auth")
        print("Endpoint: POST /api/v1/jd-skill-mapping/")
        
        payload = {
            "request_id": f"REQ-TEST-{int(time.time())}",
            "schema_version": "1.0",
            "source_system": "API-Test-Auth",
            "job_description": {
                "client_name": "Test Client",
                "title": "Senior Backend Engineer",
                "role": "Backend Development",
                "priority": "HIGH",
                "location": ["Bangalore", "Remote"],
                "work_mode": ["Remote", "Hybrid"],
                "jd_text": "We are seeking a Senior Backend Engineer with 5+ years of experience in Python, FastAPI, and PostgreSQL. The candidate should have experience with Docker, Kubernetes, and CI/CD pipelines."
            },
            "metadata": {
                "submitted_by": "test@example.com",
                "department": "Engineering"
            }
        }
        
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/jd-skill-mapping/",
                json=payload,
                headers=headers,
                timeout=10
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}\n")
            
            result = "PASS" if response.status_code in [200, 202] else "FAIL"
            response_data = response.json() if response.status_code in [200, 202] else response.text
            
            self.add_result(
                "Requisition Request (With Auth)",
                "POST /api/v1/jd-skill-mapping/",
                response.status_code,
                result,
                response_data
            )
            
            # Extract correlation_id for next test
            if response.status_code in [200, 202]:
                return response.json().get("correlation_id")
            return None
        except Exception as e:
            print(f"ERROR: {str(e)}\n")
            self.add_result(
                "Requisition Request (With Auth)",
                "POST /api/v1/jd-skill-mapping/",
                0,
                "FAIL",
                error=str(e)
            )
            return None
            
    def test_get_matches_with_auth(self, token: str, correlation_id: str):
        """Test get matches with authentication"""
        print(f"[TEST 8] Testing Get Matches With Auth")
        print(f"Endpoint: GET /api/v1/jd-skill-mapping/{correlation_id}/matches")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            # Wait for processing
            print("Waiting 5 seconds for AI processing...")
            time.sleep(5)
            
            response = requests.get(
                f"{self.base_url}/api/v1/jd-skill-mapping/{correlation_id}/matches",
                headers=headers,
                timeout=10
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}\n")
            
            result = "PASS" if response.status_code in [200, 404] else "FAIL"
            self.add_result(
                "Get Matches (With Auth)",
                "GET /api/v1/jd-skill-mapping/{correlation_id}/matches",
                response.status_code,
                result,
                response.json() if response.status_code == 200 else response.text
            )
            return response.status_code in [200, 404]
        except Exception as e:
            print(f"ERROR: {str(e)}\n")
            self.add_result(
                "Get Matches (With Auth)",
                "GET /api/v1/jd-skill-mapping/{correlation_id}/matches",
                0,
                "FAIL",
                error=str(e)
            )
            return False
            
    def print_summary(self):
        """Print test summary"""
        self.print_header("Test Summary")
        
        passed = sum(1 for r in self.results if "PASS" in r["result"])
        failed = sum(1 for r in self.results if r["result"] == "FAIL")
        total = len(self.results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        
        self.print_header("Detailed Results")
        
        for result in self.results:
            print(f"\nTest: {result['test']}")
            print(f"Endpoint: {result['endpoint']}")
            print(f"Status Code: {result['status_code']}")
            print(f"Result: {result['result']}")
            if result['error']:
                print(f"Error: {result['error']}")
                
    def save_results(self, filename: str = "api_test_results.json"):
        """Save results to JSON file"""
        with open(filename, 'w') as f:
            json.dump({
                "test_date": datetime.utcnow().isoformat(),
                "base_url": self.base_url,
                "results": self.results,
                "summary": {
                    "total": len(self.results),
                    "passed": sum(1 for r in self.results if "PASS" in r["result"]),
                    "failed": sum(1 for r in self.results if r["result"] == "FAIL")
                }
            }, f, indent=2)
        print(f"\nResults saved to: {filename}")

def main():
    tester = APITester(BASE_URL)
    
    tester.print_header("API Testing - IB Job Skill Mapping System")
    
    # Wait for server
    print("Waiting for server to be ready...")
    time.sleep(2)
    
    # Phase 1: Test endpoints without authentication
    tester.test_health_endpoint()
    tester.test_metrics_endpoint()
    tester.test_bulk_upsert_no_auth()
    tester.test_requisition_no_auth()
    tester.test_get_matches_no_auth()
    
    # Phase 2: Test with authentication
    tester.print_header("Testing with Authentication")
    
    # Generate a test token with the same secret key as the server
    import jwt
    test_token = jwt.encode(
        {"sub": "test-client", "client_id": "test-client", "scopes": ["read", "write"]},
        "test-secret-key-for-development-only-change-in-production",
        algorithm="HS256"
    )
    
    tester.test_bulk_upsert_with_auth(test_token)
    correlation_id = tester.test_requisition_with_auth(test_token)
    
    if correlation_id:
        tester.test_get_matches_with_auth(test_token, correlation_id)
    
    # Print summary and save
    tester.print_summary()
    tester.save_results()

if __name__ == "__main__":
    main()
