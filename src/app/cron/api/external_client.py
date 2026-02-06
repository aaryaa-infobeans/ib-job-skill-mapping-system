"""External API client for fetching team member data."""

from typing import Dict, Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import structlog

from app.cron.config import settings
from app.cron.oauth.token_client import OAuthClient
from app.cron.utils.logging import get_correlation_id

logger = structlog.get_logger(__name__)


class TeamDataClient:
    """Client for external team member data API with retry logic and error handling."""

    def __init__(
        self,
        oauth_client: Optional[OAuthClient] = None,
        base_url: Optional[str] = None,
        endpoint: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Initialize team data API client.

        Args:
            oauth_client: OAuth client for authentication (creates new if None)
            base_url: API base URL (defaults to settings.api_base_url)
            endpoint: API endpoint path (defaults to settings.external_api_endpoint)
            timeout: Request timeout in seconds (default: 30)
        """
        self.oauth_client = oauth_client or OAuthClient()
        self.base_url = base_url or settings.api_base_url
        self.endpoint = endpoint or settings.external_api_endpoint
        self.timeout = timeout

        # Configure session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def fetch_team_data(self) -> Dict[str, Any]:
        """
        Fetch all team member data from external API.

        Returns:
            Dictionary containing team member data with structure:
            {
                "metadata": {...},
                "team_members": [...]
            }

        Raises:
            requests.HTTPError: If API request fails
            requests.RequestException: If network error occurs
            ValueError: If response format is invalid
        """
        correlation_id = get_correlation_id()
        url = f"{self.base_url}{self.endpoint}"

        logger.info(
            "Fetching team data from external API",
            correlation_id=correlation_id,
            url=url,
        )

        try:
            # Get valid access token
            access_token = self.oauth_client.get_access_token()

            # Make API request
            response = self.session.get(
                url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-Correlation-ID": correlation_id,
                    "Content-Type": "application/json",
                },
                timeout=self.timeout,
            )

            # Handle 401 - token might be expired, try refreshing
            if response.status_code == 401:
                logger.warning(
                    "Received 401, clearing token cache and retrying",
                    correlation_id=correlation_id,
                )
                self.oauth_client.clear_cache()
                
                # Retry with fresh token
                access_token = self.oauth_client.get_access_token()
                response = self.session.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "X-Correlation-ID": correlation_id,
                        "Content-Type": "application/json",
                    },
                    timeout=self.timeout,
                )

            response.raise_for_status()

            data = response.json()

            # Validate response structure
            if not isinstance(data, dict):
                raise ValueError("Response must be a dictionary")
            if "team_members" not in data:
                raise ValueError("Response missing 'team_members' field")

            team_member_count = len(data.get("team_members", []))
            logger.info(
                "Team data fetched successfully",
                correlation_id=correlation_id,
                team_member_count=team_member_count,
            )

            return data

        except requests.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            
            logger.error(
                "API request failed",
                correlation_id=correlation_id,
                status_code=status_code,
                url=url,
                error=str(e),
            )
            raise

        except requests.Timeout as e:
            logger.error(
                "API request timeout",
                correlation_id=correlation_id,
                url=url,
                timeout=self.timeout,
                error=str(e),
            )
            raise

        except requests.RequestException as e:
            logger.error(
                "Network error during API request",
                correlation_id=correlation_id,
                url=url,
                error=str(e),
            )
            raise

        except (ValueError, KeyError) as e:
            logger.error(
                "Invalid API response format",
                correlation_id=correlation_id,
                url=url,
                error=str(e),
            )
            raise ValueError(f"Invalid API response format: {e}") from e

    def fetch_batch_by_id(self, batch_id: str) -> Dict[str, Any]:
        """
        Fetch specific batch data by ID for retry scenarios.

        Args:
            batch_id: Batch identifier to fetch

        Returns:
            Dictionary containing batch data

        Raises:
            requests.HTTPError: If API request fails (including 404 if batch not found)
            requests.RequestException: If network error occurs
            ValueError: If response format is invalid
        """
        correlation_id = get_correlation_id()
        url = f"{self.base_url}{self.endpoint}/batch/{batch_id}"

        logger.info(
            "Fetching batch data from external API",
            correlation_id=correlation_id,
            batch_id=batch_id,
            url=url,
        )

        try:
            # Get valid access token
            access_token = self.oauth_client.get_access_token()

            # Make API request
            response = self.session.get(
                url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "X-Correlation-ID": correlation_id,
                    "Content-Type": "application/json",
                },
                timeout=self.timeout,
            )

            # Handle 401 - token might be expired, try refreshing
            if response.status_code == 401:
                logger.warning(
                    "Received 401, clearing token cache and retrying",
                    correlation_id=correlation_id,
                )
                self.oauth_client.clear_cache()
                
                # Retry with fresh token
                access_token = self.oauth_client.get_access_token()
                response = self.session.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "X-Correlation-ID": correlation_id,
                        "Content-Type": "application/json",
                    },
                    timeout=self.timeout,
                )

            response.raise_for_status()

            data = response.json()

            # Validate response structure
            if not isinstance(data, dict):
                raise ValueError("Response must be a dictionary")

            logger.info(
                "Batch data fetched successfully",
                correlation_id=correlation_id,
                batch_id=batch_id,
            )

            return data

        except requests.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            
            if status_code == 404:
                logger.warning(
                    "Batch not found",
                    correlation_id=correlation_id,
                    batch_id=batch_id,
                    status_code=404,
                )
            else:
                logger.error(
                    "API request failed",
                    correlation_id=correlation_id,
                    batch_id=batch_id,
                    status_code=status_code,
                    url=url,
                    error=str(e),
                )
            raise

        except requests.Timeout as e:
            logger.error(
                "API request timeout",
                correlation_id=correlation_id,
                batch_id=batch_id,
                url=url,
                timeout=self.timeout,
                error=str(e),
            )
            raise

        except requests.RequestException as e:
            logger.error(
                "Network error during API request",
                correlation_id=correlation_id,
                batch_id=batch_id,
                url=url,
                error=str(e),
            )
            raise

        except (ValueError, KeyError) as e:
            logger.error(
                "Invalid API response format",
                correlation_id=correlation_id,
                batch_id=batch_id,
                url=url,
                error=str(e),
            )
            raise ValueError(f"Invalid API response format: {e}") from e
