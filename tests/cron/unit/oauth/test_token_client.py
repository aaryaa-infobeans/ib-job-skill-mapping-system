"""Unit tests for OAuth token client module."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import requests

from app.cron.oauth.token_client import TokenCache, OAuthClient


class TestTokenCache:
    """Test suite for TokenCache class."""

    def test_is_valid_with_valid_token(self):
        """Test is_valid returns True for valid token."""
        cache = TokenCache()
        cache.store("test_token", 3600)
        assert cache.is_valid() is True

    def test_is_valid_with_expired_token(self):
        """Test is_valid returns False for expired token."""
        cache = TokenCache()
        # Store token that expired 1 hour ago
        cache._access_token = "expired_token"
        cache._expires_at = datetime.utcnow() - timedelta(hours=1)
        assert cache.is_valid() is False

    def test_is_valid_with_buffer_expiration(self):
        """Test is_valid returns False when within 60s expiration buffer."""
        cache = TokenCache()
        # Set expiration to 30 seconds from now (within 60s buffer)
        cache._access_token = "soon_expired_token"
        cache._expires_at = datetime.utcnow() + timedelta(seconds=30)
        assert cache.is_valid() is False

    def test_is_valid_with_no_token(self):
        """Test is_valid returns False when no token stored."""
        cache = TokenCache()
        assert cache.is_valid() is False

    def test_store_token(self):
        """Test storing token with expiration."""
        cache = TokenCache()
        cache.store("new_token", 7200)
        
        assert cache._access_token == "new_token"
        assert cache._expires_at is not None
        # Verify expiration is approximately 7200 seconds from now
        expected_expiry = datetime.utcnow() + timedelta(seconds=7200)
        assert abs((cache._expires_at - expected_expiry).total_seconds()) < 5

    def test_get_token_valid(self):
        """Test get_token returns token when valid."""
        cache = TokenCache()
        cache.store("valid_token", 3600)
        assert cache.get_token() == "valid_token"

    def test_get_token_expired(self):
        """Test get_token returns None when token expired."""
        cache = TokenCache()
        cache._access_token = "expired_token"
        cache._expires_at = datetime.utcnow() - timedelta(hours=1)
        assert cache.get_token() is None

    def test_get_token_no_token(self):
        """Test get_token returns None when no token stored."""
        cache = TokenCache()
        assert cache.get_token() is None

    def test_clear_cache(self):
        """Test clearing cache removes token and expiration."""
        cache = TokenCache()
        cache.store("token_to_clear", 3600)
        cache.clear()
        
        assert cache._access_token is None
        assert cache._expires_at is None
        assert cache.is_valid() is False


class TestOAuthClient:
    """Test suite for OAuthClient class."""

    @patch("app.cron.oauth.token_client.requests.Session")
    def test_get_access_token_cached(self, mock_session_class):
        """Test get_access_token returns cached token when valid."""
        client = OAuthClient()
        client._cache.store("cached_token", 3600)
        
        token = client.get_access_token()
        
        assert token == "cached_token"
        # Session should not be called
        mock_session_class.return_value.post.assert_not_called()

    @patch("app.cron.oauth.token_client.requests.Session")
    @patch("app.cron.oauth.token_client.settings")
    def test_get_access_token_fetch_new(self, mock_settings, mock_session_class):
        """Test get_access_token fetches new token when cache empty."""
        mock_settings.oauth_token_url = "http://localhost/oauth/token"
        mock_settings.oauth_client_id = "test-client"
        mock_settings.oauth_client_secret = "test-secret"
        mock_settings.oauth_scope = "read write"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        mock_session = mock_session_class.return_value
        mock_session.post.return_value = mock_response
        
        client = OAuthClient()
        token = client.get_access_token()
        
        assert token == "new_token"
        assert client._cache.get_token() == "new_token"
        mock_session.post.assert_called_once()

    @patch("app.cron.oauth.token_client.requests.Session")
    @patch("app.cron.oauth.token_client.settings")
    def test_fetch_new_token_success(self, mock_settings, mock_session_class):
        """Test _fetch_new_token with successful response."""
        mock_settings.oauth_token_url = "http://localhost/oauth/token"
        mock_settings.oauth_client_id = "test-client"
        mock_settings.oauth_client_secret = "test-secret"
        mock_settings.oauth_scope = "read write"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "fresh_token",
            "token_type": "Bearer",
            "expires_in": 7200,
        }
        mock_session = mock_session_class.return_value
        mock_session.post.return_value = mock_response
        
        client = OAuthClient()
        token = client._fetch_new_token()
        
        assert token == "fresh_token"
        # Verify token cached
        assert client._cache.get_token() == "fresh_token"

    @patch("app.cron.oauth.token_client.requests.Session")
    @patch("app.cron.oauth.token_client.settings")
    def test_fetch_new_token_401_error(self, mock_settings, mock_session_class):
        """Test _fetch_new_token raises error on 401 authentication failure."""
        mock_settings.oauth_token_url = "http://localhost/oauth/token"
        mock_settings.oauth_client_id = "invalid-client"
        mock_settings.oauth_client_secret = "wrong-secret"
        
        mock_response = Mock()
        mock_response.status_code = 401
        
        # Create HTTPError with response attribute
        http_error = requests.HTTPError("401 Unauthorized")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        
        mock_session = mock_session_class.return_value
        mock_session.post.return_value = mock_response
        
        client = OAuthClient()
        
        with pytest.raises(requests.HTTPError):
            client._fetch_new_token()

    @patch("app.cron.oauth.token_client.requests.Session")
    @patch("app.cron.oauth.token_client.settings")
    def test_fetch_new_token_network_error(self, mock_settings, mock_session_class):
        """Test _fetch_new_token handles network errors."""
        mock_settings.oauth_token_url = "http://localhost/oauth/token"
        
        mock_session = mock_session_class.return_value
        mock_session.post.side_effect = requests.ConnectionError("Network unreachable")
        
        client = OAuthClient()
        
        with pytest.raises(requests.ConnectionError):
            client._fetch_new_token()

    @patch("app.cron.oauth.token_client.requests.Session")
    @patch("app.cron.oauth.token_client.settings")
    def test_fetch_new_token_invalid_json(self, mock_settings, mock_session_class):
        """Test _fetch_new_token handles invalid JSON response."""
        mock_settings.oauth_token_url = "http://localhost/oauth/token"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_session = mock_session_class.return_value
        mock_session.post.return_value = mock_response
        
        client = OAuthClient()
        
        with pytest.raises(ValueError):
            client._fetch_new_token()

    @patch("app.cron.oauth.token_client.requests.Session")
    @patch("app.cron.oauth.token_client.settings")
    def test_fetch_new_token_missing_access_token(self, mock_settings, mock_session_class):
        """Test _fetch_new_token raises ValueError when access_token missing."""
        mock_settings.oauth_token_url = "http://localhost/oauth/token"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "token_type": "Bearer",
            "expires_in": 3600,
            # Missing access_token
        }
        mock_session = mock_session_class.return_value
        mock_session.post.return_value = mock_response
        
        client = OAuthClient()
        
        with pytest.raises(ValueError, match="Invalid OAuth response format"):
            client._fetch_new_token()

    @patch("app.cron.oauth.token_client.requests.Session")
    @patch("app.cron.oauth.token_client.settings")
    def test_fetch_new_token_429_error(self, mock_settings, mock_session_class):
        """Test _fetch_new_token raises HTTPError on 429 rate limit.
        
        Note: Retries are handled by requests Session adapter, not application code.
        This test verifies error propagation when all retries are exhausted.
        """
        mock_settings.oauth_token_url = "http://localhost/oauth/token"
        mock_settings.oauth_client_id = "test-client"
        mock_settings.oauth_client_secret = "test-secret"
        
        mock_response = Mock()
        mock_response.status_code = 429
        http_error = requests.HTTPError("429 Too Many Requests")
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        
        mock_session = mock_session_class.return_value
        mock_session.post.return_value = mock_response
        
        client = OAuthClient()
        
        with pytest.raises(requests.HTTPError):
            client._fetch_new_token()

    @patch("app.cron.oauth.token_client.requests.Session")
    def test_clear_cache(self, mock_session_class):
        """Test clear_cache clears the token cache."""
        client = OAuthClient()
        client._cache.store("token_to_clear", 3600)
        
        client.clear_cache()
        
        assert client._cache.get_token() is None
        assert client._cache.is_valid() is False

    @patch("app.cron.oauth.token_client.requests.Session")
    @patch("app.cron.oauth.token_client.settings")
    def test_custom_token_url(self, mock_settings, mock_session_class):
        """Test OAuthClient with custom token URL."""
        custom_url = "http://custom.example.com/token"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "custom_token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        mock_session = mock_session_class.return_value
        mock_session.post.return_value = mock_response
        
        client = OAuthClient(token_url=custom_url)
        token = client._fetch_new_token()
        
        assert token == "custom_token"
        # Verify custom URL was used
        call_args = mock_session.post.call_args
        assert call_args[0][0] == custom_url

    @patch("app.cron.oauth.token_client.requests.Session")
    @patch("app.cron.oauth.token_client.settings")
    def test_token_refresh_flow(self, mock_settings, mock_session_class):
        """Test complete token refresh flow."""
        mock_settings.oauth_token_url = "http://localhost/oauth/token"
        mock_settings.oauth_client_id = "test-client"
        mock_settings.oauth_client_secret = "test-secret"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "refreshed_token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        mock_session = mock_session_class.return_value
        mock_session.post.return_value = mock_response
        
        client = OAuthClient()
        
        # First call - no cache, fetch new
        token1 = client.get_access_token()
        assert token1 == "refreshed_token"
        
        # Second call - use cache
        token2 = client.get_access_token()
        assert token2 == "refreshed_token"
        assert mock_session.post.call_count == 1  # Only one fetch
        
        # Expire token manually
        client._cache._expires_at = datetime.utcnow() - timedelta(hours=1)
        
        # Third call - cache expired, fetch new
        token3 = client.get_access_token()
        assert token3 == "refreshed_token"
        assert mock_session.post.call_count == 2  # Second fetch
