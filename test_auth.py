"""
Test authentication middleware enforcement
"""

import requests

BASE_URL = "http://localhost:8001"

print("="*60)
print("Testing Authentication Enforcement")
print("="*60)

# Test 1: No auth header
print("\n[TEST 1] No Authorization header")
try:
    response = requests.post(
        f"{BASE_URL}/api/v1/jd-skill-mapping/",
        json={"request_id": "TEST"},
        timeout=5
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    if response.status_code == 401:
        print("✅ PASS - Correctly rejected")
    else:
        print(f"❌ FAIL - Expected 401, got {response.status_code}")
except Exception as e:
    print(f"ERROR: {e}")

# Test 2: Invalid token format
print("\n[TEST 2] Invalid token format (not Bearer)")
try:
    response = requests.post(
        f"{BASE_URL}/api/v1/jd-skill-mapping/",
        json={"request_id": "TEST"},
        headers={"Authorization": "InvalidToken xyz"},
        timeout=5
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    if response.status_code == 401:
        print("✅ PASS - Correctly rejected")
    else:
        print(f"❌ FAIL - Expected 401, got {response.status_code}")
except Exception as e:
    print(f"ERROR: {e}")

# Test 3: Malformed JWT
print("\n[TEST 3] Malformed JWT token")
try:
    response = requests.post(
        f"{BASE_URL}/api/v1/jd-skill-mapping/",
        json={"request_id": "TEST"},
        headers={"Authorization": "Bearer invalid.jwt.token"},
        timeout=5
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    if response.status_code == 401:
        print("✅ PASS - Correctly rejected")
    else:
        print(f"❌ FAIL - Expected 401, got {response.status_code}")
except Exception as e:
    print(f"ERROR: {e}")

# Test 4: Expired token
print("\n[TEST 4] Expired JWT token")
import jwt
from datetime import datetime, timedelta

expired_token = jwt.encode(
    {
        "sub": "test-client",
        "exp": datetime.utcnow() - timedelta(hours=1)  # Expired 1 hour ago
    },
    "test-secret-key-for-development-only-change-in-production",
    algorithm="HS256"
)

try:
    response = requests.post(
        f"{BASE_URL}/api/v1/jd-skill-mapping/",
        json={"request_id": "TEST"},
        headers={"Authorization": f"Bearer {expired_token}"},
        timeout=5
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    if response.status_code == 401:
        print("✅ PASS - Correctly rejected expired token")
    else:
        print(f"❌ FAIL - Expected 401 for expired token, got {response.status_code}")
except Exception as e:
    print(f"ERROR: {e}")

# Test 5: Valid token (should work)
print("\n[TEST 5] Valid JWT token")
valid_token = jwt.encode(
    {
        "sub": "test-client",
        "exp": datetime.utcnow() + timedelta(hours=1)
    },
    "test-secret-key-for-development-only-change-in-production",
    algorithm="HS256"
)

try:
    response = requests.post(
        f"{BASE_URL}/api/v1/jd-skill-mapping/",
        json={
            "request_id": f"TEST-{int(datetime.utcnow().timestamp())}",
            "schema_version": "1.0",
            "source_system": "test",
            "job_description": {
                "client_name": "Test",
                "title": "Test",
                "role": "Test",
                "priority": "HIGH",
                "location": ["Remote"],
                "work_mode": ["Remote"],
                "jd_text": "Test"
            },
            "metadata": {"submitted_by": "test"}
        },
        headers={"Authorization": f"Bearer {valid_token}"},
        timeout=5
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    if response.status_code in [200, 202]:
        print("✅ PASS - Valid token accepted")
    else:
        print(f"❌ FAIL - Valid token rejected with {response.status_code}")
except Exception as e:
    print(f"ERROR: {e}")

print("\n" + "="*60)
print("Authentication Tests Complete")
print("="*60)
