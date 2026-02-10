"""Logging utilities for nightly batch ingestion service.

This module provides correlation ID generation and re-exports
existing logging configuration from src.app.logging_config.
"""

from datetime import datetime
from app.logging_config import (
    configure_logging,
    set_correlation_id,
    get_correlation_id
)

__all__ = [
    "configure_logging",
    "set_correlation_id",
    "get_correlation_id",
    "generate_correlation_id"
]


def generate_correlation_id() -> str:
    """
    Generate a unique correlation ID for ingestion runs.
    
    Format: ING-YYYYMMDD-HHMMSS
    
    Returns:
        str: Generated correlation ID
        
    Example:
        >>> corr_id = generate_correlation_id()
        >>> print(corr_id)
        ING-20260206-020000
    """
    now = datetime.utcnow()
    return now.strftime("ING-%Y%m%d-%H%M%S")
