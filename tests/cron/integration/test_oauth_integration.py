"""Integration tests for OAuth and API client with mock server.

NOTE: These tests require the mock API server to be running.
Start it before running tests:
    python tests/cron/integration/mock_api_server.py 8080

For CI/CD, use pytest-xdist or a setup script to start the server.
"""

import pytest
import requests

from app.cron.oauth.token_client import OAuthClient
from app.cron.api.external_client import TeamDataClient


# Mock server URL - assumes server is running on port 8080
MOCK_SERVER_URL = "http://localhost:8080"


def check_server_available():
    """Check if mock server is running."""
    try:
        response = requests.post(
            f"{MOCK_SERVER_URL}/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": "test-client",
                "client_secret": "test-secret",
            },
            timeout=2,
        )
        return response.status_code == 200
    except (requests.ConnectionError, requests.Timeout):
        return False


# Skip all tests if server not running
pytestmark = pytest.mark.skipif(
    not check_server_available(),
    reason="Mock API server not running on localhost:8080",
)


class TestOAuthIntegration:
    """Integration tests for OAuth client with mock server."""

    def test_oauth_token_fetch(self):
        """Test fetching OAuth token from mock server."""
        client = OAuthClient(
            token_url=f"{MOCK_SERVER_URL}/oauth/token",
            client_id="test-client",
            client_secret="test-secret",
        )
        
        token = client.get_access_token()
        
        assert token is not None
        assert token.startswith("mock_token_")
        
        # Verify token is cached
        cached_token = client.get_access_token()
        assert cached_token == token

    def test_oauth_invalid_credentials(self):
        """Test OAuth with invalid credentials."""
        client = OAuthClient(
            token_url=f"{MOCK_SERVER_URL}/oauth/token",
            client_id="invalid-client",
            client_secret="wrong-secret",
        )
        
        with pytest.raises(requests.HTTPError):
            client.get_access_token()

    def test_oauth_token_caching(self):
        """Test OAuth token caching behavior."""
        client = OAuthClient(
            token_url=f"{MOCK_SERVER_URL}/oauth/token",
            client_id="test-client",
            client_secret="test-secret",
        )
        
        # First fetch
        token1 = client.get_access_token()
        
        # Second fetch should use cache (same token)
        token2 = client.get_access_token()
        assert token2 == token1
        
        # Clear cache
        client.clear_cache()
        
        # Third fetch should get new token
        token3 = client.get_access_token()
        assert token3 != token1


class TestAPIClientIntegration:
    """Integration tests for API client with mock server."""

    def test_fetch_team_data_success(self):
        """Test successful team data fetch from mock server."""
        oauth_client = OAuthClient(
            token_url=f"{MOCK_SERVER_URL}/oauth/token",
            client_id="test-client",
            client_secret="test-secret",
        )
        
        api_client = TeamDataClient(
            oauth_client=oauth_client,
            base_url=MOCK_SERVER_URL,
            endpoint="/team-members",
        )
        
        result = api_client.fetch_team_data()
        
        assert "metadata" in result
        assert "team_members" in result
        assert len(result["team_members"]) == 5  # Mock data has 5 members
        
        # Verify data structure
        first_member = result["team_members"][0]
        assert "employee_id" in first_member
        assert "name" in first_member
        assert "skills" in first_member

    def test_fetch_batch_by_id_success(self):
        """Test successful batch fetch by ID from mock server."""
        oauth_client = OAuthClient(
            token_url=f"{MOCK_SERVER_URL}/oauth/token",
            client_id="test-client",
            client_secret="test-secret",
        )
        
        api_client = TeamDataClient(
            oauth_client=oauth_client,
            base_url=MOCK_SERVER_URL,
            endpoint="/team-members",
        )
        
        result = api_client.fetch_batch_by_id("batch-20260206-001")
        
        assert "batch_id" in result
        assert result["batch_id"] == "batch-20260206-001"
        assert "data" in result
        assert len(result["data"]) == 3  # First batch has 3 members

    def test_fetch_batch_not_found(self):
        """Test batch not found returns 404."""
        oauth_client = OAuthClient(
            token_url=f"{MOCK_SERVER_URL}/oauth/token",
            client_id="test-client",
            client_secret="test-secret",
        )
        
        api_client = TeamDataClient(
            oauth_client=oauth_client,
            base_url=MOCK_SERVER_URL,
            endpoint="/team-members",
        )
        
        with pytest.raises(requests.HTTPError) as exc_info:
            api_client.fetch_batch_by_id("nonexistent-batch")
        
        assert exc_info.value.response.status_code == 404

    def test_api_unauthorized_error(self):
        """Test API request with simulated 401 error."""
        oauth_client = OAuthClient(
            token_url=f"{MOCK_SERVER_URL}/oauth/token",
            client_id="test-client",
            client_secret="test-secret",
        )
        
        api_client = TeamDataClient(
            oauth_client=oauth_client,
            base_url=MOCK_SERVER_URL,
            endpoint="/team-members",
        )
        
        # Use query param to simulate 401
        with pytest.raises(requests.HTTPError) as exc_info:
            # Temporarily modify session to add query param
            response = api_client.session.get(
                f"{MOCK_SERVER_URL}/team-members?simulate_error=401",
                headers={"Authorization": f"Bearer {oauth_client.get_access_token()}"},
                timeout=api_client.timeout,
            )
            response.raise_for_status()
        
        assert exc_info.value.response.status_code == 401

    def test_api_rate_limit_error(self):
        """Test API request with simulated 429 rate limit (retries exhausted)."""
        oauth_client = OAuthClient(
            token_url=f"{MOCK_SERVER_URL}/oauth/token",
            client_id="test-client",
            client_secret="test-secret",
        )
        
        api_client = TeamDataClient(
            oauth_client=oauth_client,
            base_url=MOCK_SERVER_URL,
            endpoint="/team-members",
        )
        
        # Use query param to simulate 429
        # Retry adapter will exhaust retries and raise RetryError
        with pytest.raises(requests.exceptions.RetryError):
            response = api_client.session.get(
                f"{MOCK_SERVER_URL}/team-members?simulate_error=429",
                headers={"Authorization": f"Bearer {oauth_client.get_access_token()}"},
                timeout=api_client.timeout,
            )
            response.raise_for_status()

    def test_api_server_error(self):
        """Test API request with simulated 503 server error (retries exhausted)."""
        oauth_client = OAuthClient(
            token_url=f"{MOCK_SERVER_URL}/oauth/token",
            client_id="test-client",
            client_secret="test-secret",
        )
        
        api_client = TeamDataClient(
            oauth_client=oauth_client,
            base_url=MOCK_SERVER_URL,
            endpoint="/team-members",
        )
        
        # Use query param to simulate 503
        # Retry adapter will exhaust retries and raise RetryError
        with pytest.raises(requests.exceptions.RetryError):
            response = api_client.session.get(
                f"{MOCK_SERVER_URL}/team-members?simulate_error=503",
                headers={"Authorization": f"Bearer {oauth_client.get_access_token()}"},
                timeout=api_client.timeout,
            )
            response.raise_for_status()


class TestEndToEndFlow:
    """End-to-end integration tests for complete OAuth + API workflow."""

    def test_complete_flow_with_defaults(self):
        """Test complete flow: OAuth token fetch + API data fetch."""
        # Create clients with default settings pointing to mock server
        oauth_client = OAuthClient(
            token_url=f"{MOCK_SERVER_URL}/oauth/token",
            client_id="test-client",
            client_secret="test-secret",
        )
        
        api_client = TeamDataClient(
            oauth_client=oauth_client,
            base_url=MOCK_SERVER_URL,
            endpoint="/team-members",
        )
        
        # Fetch team data (internally fetches OAuth token first)
        result = api_client.fetch_team_data()
        
        # Verify we got valid data
        assert result is not None
        assert "team_members" in result
        assert len(result["team_members"]) > 0
        
        # Verify OAuth token was cached
        assert oauth_client._cache.is_valid()
        
        # Second fetch should reuse cached token
        result2 = api_client.fetch_team_data()
        assert result2 is not None

    def test_multiple_batch_fetches(self):
        """Test fetching multiple batches in sequence."""
        oauth_client = OAuthClient(
            token_url=f"{MOCK_SERVER_URL}/oauth/token",
            client_id="test-client",
            client_secret="test-secret",
        )
        
        api_client = TeamDataClient(
            oauth_client=oauth_client,
            base_url=MOCK_SERVER_URL,
            endpoint="/team-members",
        )
        
        # Fetch first batch
        batch1 = api_client.fetch_batch_by_id("batch-20260206-001")
        assert batch1["batch_id"] == "batch-20260206-001"
        
        # Fetch second batch (should reuse token)
        batch2 = api_client.fetch_batch_by_id("batch-20260206-002")
        assert batch2["batch_id"] == "batch-20260206-002"
        
        # Verify different data
        assert batch1["data"] != batch2["data"]
