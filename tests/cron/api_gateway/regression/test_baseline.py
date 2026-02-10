"""Baseline regression tests for API Gateway endpoints.

These tests capture the baseline behavior of existing API Gateway
endpoints to ensure the nightly batch ingestion job doesn't break them.
"""

import pytest
import requests
import json
from .conftest import API_ENDPOINTS, BASE_URL, save_baseline, load_baseline


class TestAPIGatewayBaseline:
    """Baseline regression tests for API Gateway."""
    
    @pytest.fixture(scope="class")
    def test_token(self):
        """Generate test JWT token (same secret as server)."""
        import jwt
        token = jwt.encode(
            {"sub": "test-client", "client_id": "test-client", "scopes": ["read", "write"]},
            "test-secret-key-for-development-only-change-in-production",
            algorithm="HS256"
        )
        return token
    
    def test_health_endpoint_baseline(self):
        """Baseline test for health endpoint."""
        endpoint = API_ENDPOINTS["health"]
        response = requests.get(f"{BASE_URL}{endpoint['path']}", timeout=5)
        
        assert response.status_code == endpoint["expected_status"]
        assert response.json() is not None
    
    def test_metrics_endpoint_baseline(self):
        """Baseline test for metrics endpoint."""
        endpoint = API_ENDPOINTS["metrics"]
        response = requests.get(f"{BASE_URL}{endpoint['path']}", timeout=5)
        
        assert response.status_code == endpoint["expected_status"]
        assert len(response.text) > 0
    
    def test_bulk_upsert_no_auth_baseline(self):
        """Baseline test for bulk upsert without auth (should return 401)."""
        endpoint = API_ENDPOINTS["bulk_upsert"]
        payload = {
            "metadata": {
                "batch_id": "TEST-BASELINE-001",
                "timestamp": "2026-02-06T00:00:00Z",
                "total_records": 1,
                "source_system": "TEST"
            },
            "team_members": []
        }
        
        response = requests.post(
            f"{BASE_URL}{endpoint['path']}",
            json=payload,
            timeout=5
        )
        
        assert response.status_code == 401
    
    def test_bulk_upsert_with_auth_baseline(self, test_token):
        """Baseline test for bulk upsert with authentication."""
        endpoint = API_ENDPOINTS["bulk_upsert"]
        payload = {
            "metadata": {
                "batch_id": "TEST-BASELINE-002",
                "timestamp": "2026-02-06T00:00:00Z",
                "total_records": 0,
                "source_system": "TEST"
            },
            "team_members": []
        }
        headers = {"Authorization": f"Bearer {test_token}"}
        
        response = requests.post(
            f"{BASE_URL}{endpoint['path']}",
            json=payload,
            headers=headers,
            timeout=10
        )
        
        assert response.status_code in endpoint["expected_status"]
    
    def test_jd_skill_mapping_no_auth_baseline(self):
        """Baseline test for JD skill mapping without auth (should return 401)."""
        endpoint = API_ENDPOINTS["jd_skill_mapping"]
        payload = {
            "request_id": "TEST-BASELINE-001",
            "job_description": {"title": "Test"}
        }
        
        response = requests.post(
            f"{BASE_URL}{endpoint['path']}",
            json=payload,
            timeout=5
        )
        
        assert response.status_code == 401


@pytest.mark.skip(reason="Manual baseline capture only")
def test_capture_baseline(test_token):
    """Manually capture baseline responses (run once before implementation)."""
    baseline = {}
    
    # Capture health
    response = requests.get(f"{BASE_URL}/health", timeout=5)
    baseline["health"] = {
        "status_code": response.status_code,
        "response_shape": list(response.json().keys()) if response.status_code == 200 else None
    }
    
    # Capture metrics
    response = requests.get(f"{BASE_URL}/api/v1/metrics", timeout=5)
    baseline["metrics"] = {
        "status_code": response.status_code,
        "has_content": len(response.text) > 0
    }
    
    save_baseline(baseline)
    print(f"✓ Baseline captured: {baseline}")
