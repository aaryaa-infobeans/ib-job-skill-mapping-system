"""
STUB IMPLEMENTATION - External API Client (API Integration Removed)

This is a minimal stub implementation that maintains API compatibility
but returns mock data instead of calling an external API. The external
API integration specification has been removed.

Original spec: specs/cron/api-integration.md (REMOVED)
"""

from typing import Dict, Any, Optional
from datetime import datetime
import structlog

from app.cron.oauth.token_client import OAuthClient

logger = structlog.get_logger(__name__)


class TeamDataClient:
    """
    STUB client for external team member data API.
    
    This stub maintains API compatibility but returns mock data
    instead of calling an actual external API.
    """

    def __init__(
        self,
        oauth_client: Optional[OAuthClient] = None,
        base_url: Optional[str] = None,
        endpoint: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Initialize stub team data API client (parameters mostly ignored).

        Args:
            oauth_client: Ignored in stub (uses stub OAuth if provided)
            base_url: Ignored in stub
            endpoint: Ignored in stub
            timeout: Ignored in stub
        """
        self.oauth_client = oauth_client or OAuthClient()
        logger.info("Stub TeamDataClient initialized (returns mock data)")

    def fetch_team_data(self) -> Dict[str, Any]:
        """
        Returns mock team member data (does not call external API).

        Returns:
            Dictionary containing mock team member data with structure:
            {
                "metadata": {...},
                "team_members": []
            }

        Note:
            This is a stub implementation returning empty mock data.
        """
        logger.info("Returning stub team data (no external API call)")
        
        # Return minimal valid structure with empty data
        return {
            "metadata": {
                "batch_id": f"STUB-BATCH-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "total_records": 0,
                "batch_number": 1,
                "total_batches": 1,
                "records_in_batch": 0,
                "source_system": "STUB",
                "schema_version": "1.0",
                "status": {
                    "code": 200,
                    "key": "SUCCESS",
                    "message": "Stub data (API integration removed)"
                }
            },
            "team_members": []  # Empty - no real data from external API
        }

    def fetch_batch_by_id(self, batch_id: str) -> Dict[str, Any]:
        """
        Returns mock batch data by ID (does not call external API).

        Args:
            batch_id: Batch identifier (logged but not used)

        Returns:
            Dictionary containing mock batch data

        Note:
            This is a stub implementation returning empty mock data.
        """
        logger.info(
            "Returning stub batch data (no external API call)",
            batch_id=batch_id
        )
        
        return {
            "metadata": {
                "batch_id": batch_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "status": "STUB"
            },
            "team_members": []
        }

