"""Unit tests for External API client module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from app.cron.api.external_client import TeamDataClient


class TestTeamDataClient:
    """Test suite for TeamDataClient class."""

    @patch("app.cron.api.external_client.OAuthClient")
    @patch("app.cron.api.external_client.requests.Session")
    def test_fetch_team_data_success(self, mock_session_class, mock_oauth_class):
        """Test successful team data fetch."""
        # Mock OAuth client
        mock_oauth = mock_oauth_class.return_value
        mock_oauth.get_access_token.return_value = "valid_token"
        
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "metadata": {"batch_id": "batch-001"},
            "team_members": [{"employee_id": "EMP001"}],
        }
        
        mock_session = mock_session_class.return_value
        mock_session.get.return_value = mock_response
        
        client = TeamDataClient(base_url="http://localhost", endpoint="/team-members")
        result = client.fetch_team_data()
        
        assert result["metadata"]["batch_id"] == "batch-001"
        assert len(result["team_members"]) == 1
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert "Authorization" in call_args[1]["headers"]
        assert call_args[1]["headers"]["Authorization"] == "Bearer valid_token"

    @patch("app.cron.api.external_client.OAuthClient")
    @patch("app.cron.api.external_client.requests.Session")
    def test_fetch_team_data_401_token_refresh(self, mock_session_class, mock_oauth_class):
        """Test 401 triggers token refresh and retry."""
        # Mock OAuth client
        mock_oauth = mock_oauth_class.return_value
        mock_oauth.get_access_token.side_effect = ["expired_token", "fresh_token"]
        
        # First call returns 401, second call succeeds
        mock_response_401 = Mock()
        mock_response_401.status_code = 401
        
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {
            "metadata": {"batch_id": "batch-001"},
            "team_members": [],
        }
        
        mock_session = mock_session_class.return_value
        mock_session.get.side_effect = [mock_response_401, mock_response_200]
        
        client = TeamDataClient(base_url="http://localhost", endpoint="/team-members")
        result = client.fetch_team_data()
        
        assert result["metadata"]["batch_id"] == "batch-001"
        # Should clear cache after 401
        mock_oauth.clear_cache.assert_called_once()
        # Should make 2 API calls (first 401, then retry with fresh token)
        assert mock_session.get.call_count == 2

    @patch("app.cron.api.external_client.OAuthClient")
    @patch("app.cron.api.external_client.requests.Session")
    def test_fetch_team_data_timeout(self, mock_session_class, mock_oauth_class):
        """Test timeout error handling."""
        mock_oauth = mock_oauth_class.return_value
        mock_oauth.get_access_token.return_value = "valid_token"
        
        mock_session = mock_session_class.return_value
        mock_session.get.side_effect = requests.Timeout("Request timed out")
        
        client = TeamDataClient(base_url="http://localhost", endpoint="/team-members", timeout=5)
        
        with pytest.raises(requests.Timeout):
            client.fetch_team_data()

    @patch("app.cron.api.external_client.OAuthClient")
    @patch("app.cron.api.external_client.requests.Session")
    def test_fetch_team_data_network_error(self, mock_session_class, mock_oauth_class):
        """Test network error handling."""
        mock_oauth = mock_oauth_class.return_value
        mock_oauth.get_access_token.return_value = "valid_token"
        
        mock_session = mock_session_class.return_value
        mock_session.get.side_effect = requests.ConnectionError("Network unreachable")
        
        client = TeamDataClient(base_url="http://localhost", endpoint="/team-members")
        
        with pytest.raises(requests.ConnectionError):
            client.fetch_team_data()

    @patch("app.cron.api.external_client.OAuthClient")
    @patch("app.cron.api.external_client.requests.Session")
    def test_fetch_team_data_http_error(self, mock_session_class, mock_oauth_class):
        """Test HTTP error (non-401) handling."""
        mock_oauth = mock_oauth_class.return_value
        mock_oauth.get_access_token.return_value = "valid_token"
        
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError("500 Internal Server Error")
        
        mock_session = mock_session_class.return_value
        mock_session.get.return_value = mock_response
        
        client = TeamDataClient(base_url="http://localhost", endpoint="/team-members")
        
        with pytest.raises(requests.HTTPError):
            client.fetch_team_data()

    @patch("app.cron.api.external_client.OAuthClient")
    @patch("app.cron.api.external_client.requests.Session")
    def test_fetch_team_data_invalid_json(self, mock_session_class, mock_oauth_class):
        """Test invalid JSON response handling."""
        mock_oauth = mock_oauth_class.return_value
        mock_oauth.get_access_token.return_value = "valid_token"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        
        mock_session = mock_session_class.return_value
        mock_session.get.return_value = mock_response
        
        client = TeamDataClient(base_url="http://localhost", endpoint="/team-members")
        
        with pytest.raises(ValueError, match="Invalid API response format"):
            client.fetch_team_data()

    @patch("app.cron.api.external_client.OAuthClient")
    @patch("app.cron.api.external_client.requests.Session")
    def test_fetch_team_data_missing_team_members(self, mock_session_class, mock_oauth_class):
        """Test response missing team_members field."""
        mock_oauth = mock_oauth_class.return_value
        mock_oauth.get_access_token.return_value = "valid_token"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "metadata": {"batch_id": "batch-001"},
            # Missing team_members field
        }
        
        mock_session = mock_session_class.return_value
        mock_session.get.return_value = mock_response
        
        client = TeamDataClient(base_url="http://localhost", endpoint="/team-members")
        
        with pytest.raises(ValueError, match="Invalid API response format"):
            client.fetch_team_data()

    @patch("app.cron.api.external_client.OAuthClient")
    @patch("app.cron.api.external_client.requests.Session")
    def test_fetch_team_data_non_dict_response(self, mock_session_class, mock_oauth_class):
        """Test response that is not a dictionary."""
        mock_oauth = mock_oauth_class.return_value
        mock_oauth.get_access_token.return_value = "valid_token"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []  # List instead of dict
        
        mock_session = mock_session_class.return_value
        mock_session.get.return_value = mock_response
        
        client = TeamDataClient(base_url="http://localhost", endpoint="/team-members")
        
        with pytest.raises(ValueError, match="Invalid API response format"):
            client.fetch_team_data()

    @patch("app.cron.api.external_client.OAuthClient")
    @patch("app.cron.api.external_client.requests.Session")
    def test_fetch_batch_by_id_success(self, mock_session_class, mock_oauth_class):
        """Test successful batch fetch by ID."""
        mock_oauth = mock_oauth_class.return_value
        mock_oauth.get_access_token.return_value = "valid_token"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "batch_id": "batch-001",
            "data": [{"employee_id": "EMP001"}],
        }
        
        mock_session = mock_session_class.return_value
        mock_session.get.return_value = mock_response
        
        client = TeamDataClient(base_url="http://localhost", endpoint="/team-members")
        result = client.fetch_batch_by_id("batch-001")
        
        assert result["batch_id"] == "batch-001"
        assert len(result["data"]) == 1
        # Verify URL includes batch ID
        call_args = mock_session.get.call_args
        assert "batch-001" in call_args[0][0]

    @patch("app.cron.api.external_client.OAuthClient")
    @patch("app.cron.api.external_client.requests.Session")
    def test_fetch_batch_by_id_not_found(self, mock_session_class, mock_oauth_class):
        """Test batch not found (404) error."""
        mock_oauth = mock_oauth_class.return_value
        mock_oauth.get_access_token.return_value = "valid_token"
        
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        
        mock_session = mock_session_class.return_value
        mock_session.get.return_value = mock_response
        
        client = TeamDataClient(base_url="http://localhost", endpoint="/team-members")
        
        with pytest.raises(requests.HTTPError):
            client.fetch_batch_by_id("nonexistent-batch")

    @patch("app.cron.api.external_client.OAuthClient")
    @patch("app.cron.api.external_client.requests.Session")
    def test_fetch_batch_by_id_401_token_refresh(self, mock_session_class, mock_oauth_class):
        """Test 401 triggers token refresh for batch fetch."""
        mock_oauth = mock_oauth_class.return_value
        mock_oauth.get_access_token.side_effect = ["expired_token", "fresh_token"]
        
        mock_response_401 = Mock()
        mock_response_401.status_code = 401
        
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {
            "batch_id": "batch-001",
            "data": [],
        }
        
        mock_session = mock_session_class.return_value
        mock_session.get.side_effect = [mock_response_401, mock_response_200]
        
        client = TeamDataClient(base_url="http://localhost", endpoint="/team-members")
        result = client.fetch_batch_by_id("batch-001")
        
        assert result["batch_id"] == "batch-001"
        mock_oauth.clear_cache.assert_called_once()
        assert mock_session.get.call_count == 2

    @patch("app.cron.api.external_client.OAuthClient")
    @patch("app.cron.api.external_client.requests.Session")
    def test_custom_timeout(self, mock_session_class, mock_oauth_class):
        """Test custom timeout configuration."""
        mock_oauth = mock_oauth_class.return_value
        mock_oauth.get_access_token.return_value = "valid_token"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "metadata": {},
            "team_members": [],
        }
        
        mock_session = mock_session_class.return_value
        mock_session.get.return_value = mock_response
        
        client = TeamDataClient(
            base_url="http://localhost",
            endpoint="/team-members",
            timeout=60,
        )
        client.fetch_team_data()
        
        # Verify custom timeout was used
        call_args = mock_session.get.call_args
        assert call_args[1]["timeout"] == 60

    @patch("app.cron.api.external_client.OAuthClient")
    @patch("app.cron.api.external_client.requests.Session")
    def test_correlation_id_propagation(self, mock_session_class, mock_oauth_class):
        """Test correlation ID is included in request headers."""
        mock_oauth = mock_oauth_class.return_value
        mock_oauth.get_access_token.return_value = "valid_token"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "metadata": {},
            "team_members": [],
        }
        
        mock_session = mock_session_class.return_value
        mock_session.get.return_value = mock_response
        
        client = TeamDataClient(base_url="http://localhost", endpoint="/team-members")
        client.fetch_team_data()
        
        # Verify X-Correlation-ID header present
        call_args = mock_session.get.call_args
        assert "X-Correlation-ID" in call_args[1]["headers"]

    @patch("app.cron.api.external_client.OAuthClient")
    def test_default_settings(self, mock_oauth_class):
        """Test client uses default settings when not provided."""
        client = TeamDataClient()
        
        # Verify OAuth client was created
        mock_oauth_class.assert_called_once()
        
        # Verify defaults from settings
        assert client.timeout == 30  # Default timeout

    @patch("app.cron.api.external_client.OAuthClient")
    @patch("app.cron.api.external_client.requests.Session")
    def test_retry_strategy_configured(self, mock_session_class, mock_oauth_class):
        """Test retry strategy is configured on session."""
        client = TeamDataClient(base_url="http://localhost", endpoint="/team-members")
        
        # Verify session was created
        mock_session_class.assert_called_once()
        
        # Verify mount was called (retry adapter configured)
        mock_session = mock_session_class.return_value
        assert mock_session.mount.call_count == 2  # http:// and https://
