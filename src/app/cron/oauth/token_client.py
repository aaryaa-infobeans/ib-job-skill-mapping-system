"""OAuth 2.0 Client Credentials token client with caching."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import structlog

from app.cron.config import settings
from app.cron.utils.logging import get_correlation_id

logger = structlog.get_logger(__name__)


class TokenCache:
    """In-memory token cache with expiration validation."""

    def __init__(self):
        """Initialize empty token cache."""
        self._access_token: Optional[str] = None
        self._expires_at: Optional[datetime] = None

    def is_valid(self) -> bool:
        """
        Check if cached token is valid.

        Returns:
            True if token exists and not expired (with 60s buffer), False otherwise
        """
        if self._access_token is None or self._expires_at is None:
            return False

        # 60-second buffer before actual expiration
        buffer = timedelta(seconds=60)
        return datetime.utcnow() < (self._expires_at - buffer)

    def store(self, access_token: str, expires_in: int) -> None:
        """
        Store access token with expiration time.

        Args:
            access_token: OAuth access token
            expires_in: Token lifetime in seconds
        """
        self._access_token = access_token
        self._expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        logger.info(
            "Token cached",
            correlation_id=get_correlation_id(),
            expires_in=expires_in,
            expires_at=self._expires_at.isoformat(),
        )

    def get_token(self) -> Optional[str]:
        """
        Get cached token if valid.

        Returns:
            Access token if valid, None otherwise
        """
        if self.is_valid():
            return self._access_token
        return None

    def clear(self) -> None:
        """Clear cached token."""
        self._access_token = None
        self._expires_at = None
        logger.info("Token cache cleared", correlation_id=get_correlation_id())


class OAuthClient:
    """OAuth 2.0 Client Credentials client with automatic token refresh."""

    def __init__(
        self,
        token_url: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        scope: Optional[str] = None,
        timeout: int = 10,
    ):
        """
        Initialize OAuth client.

        Args:
            token_url: OAuth token endpoint URL (defaults to settings.oauth_token_url)
            client_id: OAuth client ID (defaults to settings.oauth_client_id)
            client_secret: OAuth client secret (defaults to settings.oauth_client_secret)
            scope: OAuth scope (defaults to settings.oauth_scope)
            timeout: Request timeout in seconds (default: 10)
        """
        self.token_url = token_url or settings.oauth_token_url
        self.client_id = client_id or settings.oauth_client_id
        self.client_secret = client_secret or settings.oauth_client_secret
        self.scope = scope or settings.oauth_scope
        self.timeout = timeout
        self._cache = TokenCache()

        # Configure session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def get_access_token(self) -> str:
        """
        Get valid access token (cached or fetch new).

        Returns:
            Valid OAuth access token

        Raises:
            requests.HTTPError: If token fetch fails
            requests.RequestException: If network error occurs
            ValueError: If response format is invalid
        """
        correlation_id = get_correlation_id()

        # Check cache first
        cached_token = self._cache.get_token()
        if cached_token:
            logger.debug(
                "Using cached token",
                correlation_id=correlation_id,
            )
            return cached_token

        # Fetch new token
        logger.info(
            "Fetching new OAuth token",
            correlation_id=correlation_id,
            token_url=self.token_url,
        )

        return self._fetch_new_token()

    def _fetch_new_token(self) -> str:
        """
        Fetch new access token from OAuth server.

        Returns:
            New access token

        Raises:
            requests.HTTPError: If authentication fails (401) or server error
            requests.RequestException: If network error occurs
            ValueError: If response format is invalid
        """
        correlation_id = get_correlation_id()

        try:
            response = self.session.post(
                self.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": self.scope,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-Correlation-ID": correlation_id,
                },
                timeout=self.timeout,
            )

            response.raise_for_status()

            token_data = response.json()

            # Validate response format
            if "access_token" not in token_data:
                raise ValueError("Response missing 'access_token' field")
            if "expires_in" not in token_data:
                raise ValueError("Response missing 'expires_in' field")

            access_token = token_data["access_token"]
            expires_in = token_data["expires_in"]

            # Cache the token
            self._cache.store(access_token, expires_in)

            logger.info(
                "OAuth token fetched successfully",
                correlation_id=correlation_id,
                expires_in=expires_in,
            )

            return access_token

        except requests.HTTPError as e:
            if e.response.status_code == 401:
                logger.error(
                    "OAuth authentication failed",
                    correlation_id=correlation_id,
                    status_code=401,
                    error=str(e),
                )
                raise requests.HTTPError("Authentication failed: invalid credentials") from e

            logger.error(
                "OAuth token fetch failed",
                correlation_id=correlation_id,
                status_code=e.response.status_code,
                error=str(e),
            )
            raise

        except requests.RequestException as e:
            logger.error(
                "Network error fetching OAuth token",
                correlation_id=correlation_id,
                error=str(e),
            )
            raise

        except (ValueError, KeyError) as e:
            logger.error(
                "Invalid OAuth response format",
                correlation_id=correlation_id,
                error=str(e),
            )
            raise ValueError(f"Invalid OAuth response format: {e}") from e

    def clear_cache(self) -> None:
        """Clear cached token (for testing or manual refresh)."""
        self._cache.clear()
