"""Simple in-memory cache for requisition results.

In production, this should be replaced with Redis or database storage.
"""

from typing import Dict, Optional

# In-memory storage: correlation_id -> {"results": List, "metrics": Dict}
_execution_cache: Dict[str, dict] = {}


def store_results(correlation_id: str, final_results: list, metrics: Optional[dict] = None) -> None:
    """Store final results and metrics for a correlation ID.
    
    Args:
        correlation_id: Unique correlation ID
        final_results: List of formatted match results
        metrics: Dictionary of execution metrics (tokens, qualified count, etc.)
    """
    _execution_cache[correlation_id] = {
        "results": final_results,
        "metrics": metrics or {}
    }


def get_results(correlation_id: str) -> Optional[dict]:
    """Retrieve execution data for a correlation ID.
    
    Args:
        correlation_id: Unique correlation ID
    
    Returns:
        Dictionary with "results" and "metrics", or None if not found
    """
    return _execution_cache.get(correlation_id)


def clear_results(correlation_id: str) -> None:
    """Clear cached data for a correlation ID.
    
    Args:
        correlation_id: Unique correlation ID
    """
    _execution_cache.pop(correlation_id, None)
