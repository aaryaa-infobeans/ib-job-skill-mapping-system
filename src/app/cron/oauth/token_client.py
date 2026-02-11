"""
STUB IMPLEMENTATION - OAuth 2.0 Client (API Integration Removed)

This is a minimal stub implementation that maintains API compatibility
but does not perform actual OAuth authentication. The external API
integration specification has been removed.

Original spec: specs/cron/api-integration.md (REMOVED)
"""

from typing import Optional
import structlog

logger = structlog.get_logger(__name__)


class TokenCache:
    """Stub token cache - always returns valid mock token."""

    def __init__(self):
        """Initialize mock token cache."""
        self._access_token = "dev-token-12345"

    def is_valid(self) -> bool:
        """Always returns True for stub implementation."""
        return True

    def store(self, access_token: str, expires_in: int) -> None:
        """Stub store method - does nothing."""
        pass

    def get_token(self) -> Optional[str]:
        """Returns stub token."""
        return self._access_token

    def clear(self) -> None:
        """Stub clear method - does nothing."""
        pass


class OAuthClient:
    """
    STUB OAuth client - returns mock token without actual authentication.
    
    This stub maintains API compatibility with the original OAuth client
    but does not perform real OAuth 2.0 authentication or API calls.
    """

    def __init__(
        self,
        token_url: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        scope: Optional[str] = None,
        timeout: int = 10,
    ):
        """
        Initialize stub OAuth client (parameters ignored).

        Args:
            token_url: Ignored in stub
            client_id: Ignored in stub
            client_secret: Ignored in stub
            scope: Ignored in stub
            timeout: Ignored in stub
        """
        self._cache = TokenCache()
        logger.info("Stub OAuth client initialized (no real authentication)")

    def get_access_token(self) -> str:
        """
        Returns stub access token.

        Returns:
            Mock access token string

        Note:
            This is a stub implementation and does not perform real OAuth authentication.
        """
        logger.debug("Returning stub OAuth token (no real authentication)")
        return self._cache.get_token()

    def clear_cache(self) -> None:
        """Stub method - does nothing."""
        pass
