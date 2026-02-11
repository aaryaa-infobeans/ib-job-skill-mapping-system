"""
External API Client - Calls real bulk-upsert endpoint

This client calls the external bulk-upsert endpoint running on a different
codebase at http://localhost:8000/api/v1/team-members/skill-availability/bulk-upsert

Note: This endpoint is NOT part of this codebase - it runs on port 8000.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import structlog
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.cron.oauth.token_client import OAuthClient
from app.cron.utils.logging import get_correlation_id

logger = structlog.get_logger(__name__)


class TeamDataClient:
    """
    Client for external team member data API.
    
    Calls the real bulk-upsert endpoint running on localhost:8000
    """

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
            oauth_client: OAuth client for authentication (uses stub)
            base_url: API base URL (defaults to http://localhost:8000)
            endpoint: API endpoint path
            timeout: Request timeout in seconds
        """
        self.oauth_client = oauth_client or OAuthClient()
        self.base_url = base_url or "http://localhost:8000"
        self.endpoint = endpoint or "/api/v1/team-members/skill-availability/bulk-upsert"
        self.timeout = timeout
        
        # Configure session with retry logic
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
        
        logger.info(
            "TeamDataClient initialized",
            base_url=self.base_url,
            endpoint=self.endpoint
        )

    def fetch_team_data(self, page: Optional[int] = None) -> Dict[str, Any]:
        """
        Fetch team member data from external endpoint.

        Args:
            page: Optional page number for pagination (1-based)

        Returns:
            Dictionary containing team member data with structure:
            {
                "metadata": {...},
                "team_members": [...]
            }

        Raises:
            requests.RequestException: If API request fails
        """
        correlation_id = get_correlation_id()
        url = f"{self.base_url}{self.endpoint}"
        
        # Add page parameter if specified
        params = {}
        if page is not None:
            params['page'] = page
        
        logger.info(
            "Fetching team data from external API",
            correlation_id=correlation_id,
            url=url,
            page=page
        )
        
        try:
            # Get token (stub always returns valid token)
            access_token = self.oauth_client.get_access_token()
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Correlation-ID": correlation_id,
                "Content-Type": "application/json",
            }
            
            response = self.session.get(
                url,
                headers=headers,
                params=params,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Validate response structure
            if not isinstance(data, dict):
                raise ValueError("Response must be a dictionary")
            if "team_members" not in data:
                raise ValueError("Response missing 'team_members' field")
            
            team_member_count = len(data.get("team_members", []))
            batch_info = data.get("metadata", {})
            logger.info(
                "Team data fetched successfully",
                correlation_id=correlation_id,
                team_member_count=team_member_count,
                batch_number=batch_info.get("batch_number"),
                total_batches=batch_info.get("total_batches")
            )
            
            return data
            
        except requests.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            logger.error(
                "API request failed",
                correlation_id=correlation_id,
                status_code=status_code,
                url=url,
                page=page,
                error=str(e)
            )
            raise
            
        except requests.Timeout as e:
            logger.error(
                "API request timeout",
                correlation_id=correlation_id,
                url=url,
                timeout=self.timeout,
                page=page,
                error=str(e)
            )
            raise
            
        except requests.RequestException as e:
            logger.error(
                "Network error during API request",
                correlation_id=correlation_id,
                url=url,
                page=page,
                error=str(e)
            )
            raise
            
        except (ValueError, KeyError) as e:
            logger.error(
                "Invalid API response format",
                correlation_id=correlation_id,
                url=url,
                page=page,
                error=str(e)
            )
            raise ValueError(f"Invalid API response format: {e}") from e

    # Alias for compatibility with main.py
    async def fetch_team_members(self, page: Optional[int] = None) -> Dict[str, Any]:
        """
        Async wrapper for fetch_team_data().
        
        Args:
            page: Optional page number for pagination (1-based)
        
        Returns:
            Dictionary containing team member data
        """
        return self.fetch_team_data(page=page)

    def fetch_batch_by_id(self, batch_id: str) -> Dict[str, Any]:
        """
        Fetch specific batch data by ID.

        Args:
            batch_id: Batch identifier to fetch

        Returns:
            Dictionary containing batch data

        Raises:
            requests.RequestException: If API request fails
        """
        correlation_id = get_correlation_id()
        url = f"{self.base_url}{self.endpoint}/batch/{batch_id}"
        
        logger.info(
            "Fetching batch data from external API",
            correlation_id=correlation_id,
            batch_id=batch_id,
            url=url
        )
        
        try:
            access_token = self.oauth_client.get_access_token()
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "X-Correlation-ID": correlation_id,
                "Content-Type": "application/json",
            }
            
            response = self.session.get(
                url,
                headers=headers,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            data = response.json()
            
            logger.info(
                "Batch data fetched successfully",
                correlation_id=correlation_id,
                batch_id=batch_id
            )
            
            return data
            
        except requests.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            
            if status_code == 404:
                logger.warning(
                    "Batch not found",
                    correlation_id=correlation_id,
                    batch_id=batch_id,
                    status_code=404
                )
            else:
                logger.error(
                    "API request failed",
                    correlation_id=correlation_id,
                    batch_id=batch_id,
                    status_code=status_code,
                    url=url,
                    error=str(e)
                )
            raise
            
        except Exception as e:
            logger.error(
                "Failed to fetch batch",
                correlation_id=correlation_id,
                batch_id=batch_id,
                url=url,
                error=str(e)
            )
            raise


