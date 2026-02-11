"""Test script to verify stub implementations work correctly after API integration removal."""

from app.cron.oauth.token_client import OAuthClient, TokenCache
from app.cron.api.external_client import TeamDataClient

def test_oauth_stub():
    """Test OAuth client stub."""
    print("Testing OAuth Client Stub...")
    client = OAuthClient()
    token = client.get_access_token()
    assert token == "STUB_TOKEN_mock_auth_removed", f"Unexpected token: {token}"
    print(f"  ✓ OAuth token: {token}")
    return True

def test_token_cache_stub():
    """Test token cache stub."""
    print("Testing Token Cache Stub...")
    cache = TokenCache()
    assert cache.is_valid() is True, "Cache should always be valid"
    token = cache.get_token()
    assert token == "STUB_TOKEN_mock_auth_removed", f"Unexpected token: {token}"
    print(f"  ✓ Token cache: {token}")
    return True

def test_api_client_stub():
    """Test external API client stub."""
    print("Testing External API Client Stub...")
    client = TeamDataClient()
    data = client.fetch_team_data()
    
    assert "metadata" in data, "Missing metadata"
    assert "team_members" in data, "Missing team_members"
    assert data["metadata"]["total_records"] == 0, "Should have 0 records (stub)"
    assert data["metadata"]["source_system"] == "STUB", "Should be STUB source"
    assert len(data["team_members"]) == 0, "Should have empty team_members list"
    
    print(f"  ✓ API data batch_id: {data['metadata']['batch_id']}")
    print(f"  ✓ Total records: {data['metadata']['total_records']}")
    print(f"  ✓ Source system: {data['metadata']['source_system']}")
    return True

def test_batch_fetch_stub():
    """Test batch fetch by ID stub."""
    print("Testing Batch Fetch Stub...")
    client = TeamDataClient()
    data = client.fetch_batch_by_id("TEST-BATCH-123")
    
    assert "metadata" in data, "Missing metadata"
    assert data["metadata"]["batch_id"] == "TEST-BATCH-123", "Batch ID mismatch"
    assert len(data["team_members"]) == 0, "Should have empty team_members list"
    
    print(f"  ✓ Batch fetch: {data['metadata']['batch_id']}")
    return True

def main():
    """Run all stub tests."""
    print("=" * 70)
    print("API INTEGRATION REMOVAL - STUB VALIDATION")
    print("=" * 70)
    
    tests = [
        ("OAuth Client Stub", test_oauth_stub),
        ("Token Cache Stub", test_token_cache_stub),
        ("API Client Stub", test_api_client_stub),
        ("Batch Fetch Stub", test_batch_fetch_stub),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✓ {name} PASSED\n")
        except Exception as e:
            failed += 1
            print(f"✗ {name} FAILED: {e}\n")
    
    print("=" * 70)
    print(f"RESULTS: {passed}/{len(tests)} tests passed")
    if failed == 0:
        print("✓ ALL STUB IMPLEMENTATIONS WORKING CORRECTLY")
    else:
        print(f"✗ {failed} test(s) failed")
    print("=" * 70)
    
    return failed == 0

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
