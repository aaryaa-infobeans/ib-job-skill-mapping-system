"""Simple in-memory cache for requisition results.

In production, this should be replaced with Redis or database storage.
"""

from typing import Dict, Optional

# In-memory storage: correlation_id -> final_results
_results_cache: Dict[str, list] = {}


def store_results(correlation_id: str, final_results: list) -> None:
    """Store final results for a correlation ID.
    
    Args:
        correlation_id: Unique correlation ID
        final_results: List of formatted match results
    """
    _results_cache[correlation_id] = final_results


def get_results(correlation_id: str) -> Optional[list]:
    """Retrieve results for a correlation ID.
    
    Args:
        correlation_id: Unique correlation ID
    
    Returns:
        List of results or None if not found
    """
    return _results_cache.get(correlation_id)


def clear_results(correlation_id: str) -> None:
    """Clear results for a correlation ID.
    
    Args:
        correlation_id: Unique correlation ID
    """
    _results_cache.pop(correlation_id, None)
