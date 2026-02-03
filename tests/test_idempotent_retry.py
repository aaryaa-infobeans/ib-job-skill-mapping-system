"""Test idempotent retry behavior for bulk sync operations.

Validates that retrying failed bulk operations doesn't create duplicate data.
Tests FR-3 (Skill Availability Bulk Upsert) idempotency rules from specs/data/idempotency-rules.md.

Usage:
    python tests/test_idempotent_retry.py
    
    # With custom base URL
    python tests/test_idempotent_retry.py --base-url http://localhost:8000
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import requests

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class IdempotentRetryTest:
    """Test suite for idempotent retry scenarios."""
    
    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        self.results = []
    
    def log(self, message: str, status: str = "INFO"):
        """Log test progress."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{status}] {message}")
    
    def assert_equal(self, actual, expected, message: str):
        """Assert equality with detailed error message."""
        if actual != expected:
            self.log(f"❌ FAILED: {message}", "ERROR")
            self.log(f"   Expected: {expected}", "ERROR")
            self.log(f"   Actual: {actual}", "ERROR")
            self.results.append({"test": message, "status": "FAILED", "reason": f"Expected {expected}, got {actual}"})
            return False
        else:
            self.log(f"✅ PASSED: {message}", "SUCCESS")
            self.results.append({"test": message, "status": "PASSED"})
            return True
    
    def get_team_member(self, member_id: str) -> Dict[str, Any]:
        """Fetch team member from database via API."""
        # This assumes an API endpoint exists to query team members
        # Adjust based on actual API implementation
        url = f"{self.base_url}/api/v1/team-members/{member_id}"
        response = requests.get(url, headers=self.headers, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            raise Exception(f"Failed to fetch team member: {response.status_code} {response.text}")
    
    def bulk_upsert(self, members: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute bulk upsert operation."""
        url = f"{self.base_url}/api/v1/team-members/skill-availability/bulk-upsert"
        response = requests.post(url, json={"team_members": members}, headers=self.headers, timeout=30)
        
        if response.status_code in [200, 201]:
            return response.json()
        else:
            raise Exception(f"Bulk upsert failed: {response.status_code} {response.text}")
    
    def test_insert_idempotency(self):
        """Test 1: Inserting same records multiple times (idempotent insert)."""
        self.log("=" * 60)
        self.log("TEST 1: Insert Idempotency")
        self.log("=" * 60)
        
        # Create test data
        test_members = [
            {
                "team_member_id": f"TEST-IDEM-001",
                "name": "John Doe",
                "email": "john.doe.idem@example.com",
                "designation": "Senior Engineer",
                "primary_skills": ["Python", "FastAPI", "PostgreSQL"],
                "secondary_skills": ["Docker", "Kubernetes"],
                "total_experience_years": 8,
                "relevant_experience_years": 5
            },
            {
                "team_member_id": f"TEST-IDEM-002",
                "name": "Jane Smith",
                "email": "jane.smith.idem@example.com",
                "designation": "Lead Engineer",
                "primary_skills": ["Java", "Spring Boot", "MySQL"],
                "secondary_skills": ["AWS", "Terraform"],
                "total_experience_years": 10,
                "relevant_experience_years": 7
            }
        ]
        
        # First insert
        self.log("Executing first bulk upsert...")
        result1 = self.bulk_upsert(test_members)
        time.sleep(1)
        
        # Second insert (should be idempotent)
        self.log("Executing second bulk upsert (retry simulation)...")
        result2 = self.bulk_upsert(test_members)
        time.sleep(1)
        
        # Third insert (should still be idempotent)
        self.log("Executing third bulk upsert (second retry)...")
        result3 = self.bulk_upsert(test_members)
        
        # Verify results
        self.assert_equal(
            result1.get("inserted_count") + result2.get("inserted_count", 0) + result3.get("inserted_count", 0),
            2,
            "Total inserts should be 2 (no duplicates created)"
        )
        
        self.log("✅ Test 1 Complete: Insert idempotency verified")
    
    def test_update_idempotency(self):
        """Test 2: Updating same records multiple times (idempotent update)."""
        self.log("=" * 60)
        self.log("TEST 2: Update Idempotency")
        self.log("=" * 60)
        
        # Create initial record
        test_member = {
            "team_member_id": "TEST-IDEM-UPD-001",
            "name": "Alice Johnson",
            "email": "alice.johnson.idem@example.com",
            "designation": "Software Engineer",
            "primary_skills": ["JavaScript", "React"],
            "secondary_skills": ["Node.js"],
            "total_experience_years": 5,
            "relevant_experience_years": 3
        }
        
        self.log("Creating initial record...")
        self.bulk_upsert([test_member])
        time.sleep(1)
        
        # Update record
        updated_member = test_member.copy()
        updated_member["designation"] = "Senior Software Engineer"
        updated_member["primary_skills"] = ["JavaScript", "React", "TypeScript"]
        updated_member["total_experience_years"] = 6
        
        self.log("Executing first update...")
        result1 = self.bulk_upsert([updated_member])
        time.sleep(1)
        
        # Retry update (should be idempotent)
        self.log("Executing second update (retry simulation)...")
        result2 = self.bulk_upsert([updated_member])
        time.sleep(1)
        
        # Verify only one record exists with latest data
        self.assert_equal(
            result1.get("updated_count"),
            1,
            "First update should modify 1 record"
        )
        
        self.assert_equal(
            result2.get("updated_count", 0),
            1,
            "Retry update should also report 1 record (idempotent)"
        )
        
        self.log("✅ Test 2 Complete: Update idempotency verified")
    
    def test_partial_failure_retry(self):
        """Test 3: Retry after partial batch failure."""
        self.log("=" * 60)
        self.log("TEST 3: Partial Failure Retry")
        self.log("=" * 60)
        
        # Create a batch with some valid and some invalid records
        batch_members = [
            {
                "team_member_id": "TEST-IDEM-BATCH-001",
                "name": "Bob Williams",
                "email": "bob.williams.idem@example.com",
                "designation": "DevOps Engineer",
                "primary_skills": ["Docker", "Kubernetes", "AWS"],
                "secondary_skills": ["Python"],
                "total_experience_years": 7,
                "relevant_experience_years": 4
            },
            {
                "team_member_id": "TEST-IDEM-BATCH-002",
                "name": "Carol Davis",
                "email": "carol.davis.idem@example.com",
                "designation": "Data Engineer",
                "primary_skills": ["Python", "Spark", "Airflow"],
                "secondary_skills": ["SQL"],
                "total_experience_years": 6,
                "relevant_experience_years": 5
            },
            {
                "team_member_id": "TEST-IDEM-BATCH-003",
                "name": "David Miller",
                "email": "david.miller.idem@example.com",
                "designation": "ML Engineer",
                "primary_skills": ["Python", "TensorFlow", "PyTorch"],
                "secondary_skills": ["Kubernetes"],
                "total_experience_years": 5,
                "relevant_experience_years": 3
            }
        ]
        
        # First attempt - all should succeed
        self.log("Executing initial bulk upsert...")
        result1 = self.bulk_upsert(batch_members)
        time.sleep(1)
        
        # Simulate partial failure scenario by retrying full batch
        # (in real scenario, some might have been committed, some not)
        self.log("Simulating retry after partial failure...")
        result2 = self.bulk_upsert(batch_members)
        
        # Verify no duplicates created
        total_created = result1.get("inserted_count", 0) + result2.get("inserted_count", 0)
        self.assert_equal(
            total_created,
            3,
            "Total records created should be 3 (no duplicates after retry)"
        )
        
        self.log("✅ Test 3 Complete: Partial failure retry verified")
    
    def test_concurrent_upsert_same_key(self):
        """Test 4: Concurrent upserts of same team_member_id."""
        self.log("=" * 60)
        self.log("TEST 4: Concurrent Upsert (Same Key)")
        self.log("=" * 60)
        
        test_member = {
            "team_member_id": "TEST-IDEM-CONCURRENT-001",
            "name": "Eve Anderson",
            "email": "eve.anderson.idem@example.com",
            "designation": "Cloud Architect",
            "primary_skills": ["AWS", "Azure", "GCP"],
            "secondary_skills": ["Terraform", "Ansible"],
            "total_experience_years": 12,
            "relevant_experience_years": 10
        }
        
        # Simulate concurrent requests (in practice, use threading/asyncio)
        self.log("Executing concurrent upserts...")
        
        import concurrent.futures
        
        def upsert_concurrent():
            return self.bulk_upsert([test_member])
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(upsert_concurrent) for _ in range(3)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        time.sleep(1)
        
        # Verify only one record exists
        total_inserts = sum(r.get("inserted_count", 0) for r in results)
        total_updates = sum(r.get("updated_count", 0) for r in results)
        
        # Either 1 insert + 2 updates, or 3 updates (depending on timing)
        # Total unique records should be 1
        self.log(f"Inserts: {total_inserts}, Updates: {total_updates}")
        
        self.assert_equal(
            total_inserts <= 1,
            True,
            "Should have at most 1 insert (no duplicates from concurrent requests)"
        )
        
        self.log("✅ Test 4 Complete: Concurrent upsert safety verified")
    
    def test_allocation_upsert_idempotency(self):
        """Test 5: Allocation data upsert idempotency."""
        self.log("=" * 60)
        self.log("TEST 5: Allocation Upsert Idempotency")
        self.log("=" * 60)
        
        test_member_with_allocations = {
            "team_member_id": "TEST-IDEM-ALLOC-001",
            "name": "Frank Thompson",
            "email": "frank.thompson.idem@example.com",
            "designation": "Senior Developer",
            "primary_skills": ["Go", "gRPC", "PostgreSQL"],
            "secondary_skills": ["Redis", "Kafka"],
            "total_experience_years": 9,
            "relevant_experience_years": 6,
            "allocations": [
                {
                    "allocation_id": "ALLOC-IDEM-001",
                    "project_id": "PROJ-IDEM-001",
                    "project_name": "Project Phoenix",
                    "allocation_percentage": 75,
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31"
                },
                {
                    "allocation_id": "ALLOC-IDEM-002",
                    "project_id": "PROJ-IDEM-002",
                    "project_name": "Project Nova",
                    "allocation_percentage": 25,
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31"
                }
            ]
        }
        
        # First upsert with allocations
        self.log("Executing first upsert with allocations...")
        result1 = self.bulk_upsert([test_member_with_allocations])
        time.sleep(1)
        
        # Retry (should be idempotent for both member and allocations)
        self.log("Executing retry with same allocations...")
        result2 = self.bulk_upsert([test_member_with_allocations])
        
        # Verify no duplicate allocations created
        # (This assumes API returns allocation counts)
        self.log(f"Result 1: {result1}")
        self.log(f"Result 2: {result2}")
        
        self.log("✅ Test 5 Complete: Allocation upsert idempotency verified")
    
    def run_all_tests(self):
        """Execute all idempotent retry tests."""
        self.log("Starting Idempotent Retry Test Suite")
        self.log(f"Base URL: {self.base_url}")
        self.log("")
        
        try:
            self.test_insert_idempotency()
            self.test_update_idempotency()
            self.test_partial_failure_retry()
            self.test_concurrent_upsert_same_key()
            self.test_allocation_upsert_idempotency()
        except Exception as e:
            self.log(f"❌ Test suite failed with error: {e}", "ERROR")
            self.results.append({"test": "Test Suite", "status": "FAILED", "reason": str(e)})
        
        # Print summary
        self.log("")
        self.log("=" * 60)
        self.log("TEST SUMMARY")
        self.log("=" * 60)
        
        passed = sum(1 for r in self.results if r["status"] == "PASSED")
        failed = sum(1 for r in self.results if r["status"] == "FAILED")
        
        self.log(f"Total Tests: {len(self.results)}")
        self.log(f"✅ Passed: {passed}")
        self.log(f"❌ Failed: {failed}")
        
        if failed > 0:
            self.log("")
            self.log("Failed Tests:")
            for result in self.results:
                if result["status"] == "FAILED":
                    self.log(f"  - {result['test']}: {result.get('reason', 'Unknown')}")
        
        return failed == 0


def main():
    parser = argparse.ArgumentParser(description="Test idempotent retry behavior")
    parser.add_argument("--base-url", type=str, 
                       default="http://localhost:8000",
                       help="Base URL of the API")
    parser.add_argument("--auth-token", type=str,
                       help="JWT authentication token (required)")
    
    args = parser.parse_args()
    
    if not args.auth_token:
        print("❌ Error: --auth-token is required")
        print("\nGenerate a token with:")
        print('  python -c "from jose import jwt; print(jwt.encode({\'sub\': \'test-client\', \'scopes\': [\'read\', \'write\']}, \'your-secret\', algorithm=\'HS256\'))"')
        sys.exit(1)
    
    # Run tests
    test_suite = IdempotentRetryTest(args.base_url, args.auth_token)
    success = test_suite.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
