"""
Error classification for retry eligibility determination.

Categorizes exceptions into retryable, non-retryable, and infrastructure errors
to support intelligent retry logic in batch processing.
"""

from enum import Enum
from typing import Type, Optional
import requests
import sqlalchemy.exc as sqla_exc


class ErrorCategory(Enum):
    """
    Error categories for retry eligibility.
    
    - RETRYABLE: Temporary errors that may succeed on retry
    - NON_RETRYABLE: Permanent errors that won't succeed on retry
    - INFRASTRUCTURE: Infrastructure-level issues requiring investigation
    """
    
    # Retryable errors (temporary failures)
    NETWORK_ERROR = "network_error"
    API_RATE_LIMIT = "api_rate_limit"
    DATABASE_LOCK = "database_lock"
    TEMPORARY_UNAVAILABLE = "temporary_unavailable"
    
    # Non-retryable errors (permanent failures)
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"
    VALIDATION_ERROR = "validation_error"
    SCHEMA_MISMATCH = "schema_mismatch"
    CONSTRAINT_VIOLATION = "constraint_violation"
    
    # Infrastructure errors (require investigation)
    DATABASE_CONNECTION_ERROR = "database_connection_error"
    OUT_OF_MEMORY = "out_of_memory"
    UNKNOWN_ERROR = "unknown_error"


def classify_error(exception: Exception) -> ErrorCategory:
    """
    Classify an exception into an error category.
    
    Classification rules:
    - Network errors (ConnectionError, Timeout) → NETWORK_ERROR
    - HTTP 429 → API_RATE_LIMIT
    - HTTP 401 → AUTHENTICATION_ERROR
    - HTTP 403 → AUTHORIZATION_ERROR
    - HTTP 503 → TEMPORARY_UNAVAILABLE
    - IntegrityError → CONSTRAINT_VIOLATION
    - OperationalError → DATABASE_CONNECTION_ERROR
    - ValueError, TypeError → VALIDATION_ERROR
    - MemoryError → OUT_OF_MEMORY
    - Unknown → UNKNOWN_ERROR
    
    Args:
        exception: Exception to classify
    
    Returns:
        ErrorCategory enum value
    
    Examples:
        >>> classify_error(requests.exceptions.ConnectionError())
        ErrorCategory.NETWORK_ERROR
        
        >>> classify_error(ValueError("Invalid data"))
        ErrorCategory.VALIDATION_ERROR
    """
    # Network errors
    if isinstance(exception, (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        ConnectionError,
        TimeoutError
    )):
        return ErrorCategory.NETWORK_ERROR
    
    # HTTP errors (from requests library)
    if isinstance(exception, requests.exceptions.HTTPError):
        if hasattr(exception, 'response') and exception.response is not None:
            status_code = exception.response.status_code
            
            if status_code == 429:
                return ErrorCategory.API_RATE_LIMIT
            elif status_code == 401:
                return ErrorCategory.AUTHENTICATION_ERROR
            elif status_code == 403:
                return ErrorCategory.AUTHORIZATION_ERROR
            elif status_code == 503:
                return ErrorCategory.TEMPORARY_UNAVAILABLE
            elif 500 <= status_code < 600:
                return ErrorCategory.TEMPORARY_UNAVAILABLE
    
    # Database errors (SQLAlchemy)
    if isinstance(exception, sqla_exc.IntegrityError):
        return ErrorCategory.CONSTRAINT_VIOLATION
    
    if isinstance(exception, sqla_exc.OperationalError):
        # Check if it's a connection error
        error_message = str(exception).lower()
        if any(keyword in error_message for keyword in [
            'connection', 'connect', 'network', 'timeout', 'unreachable'
        ]):
            return ErrorCategory.DATABASE_CONNECTION_ERROR
        
        # Check if it's a lock error (retryable)
        if any(keyword in error_message for keyword in ['lock', 'locked', 'deadlock']):
            return ErrorCategory.DATABASE_LOCK
        
        # Default to connection error for operational issues
        return ErrorCategory.DATABASE_CONNECTION_ERROR
    
    if isinstance(exception, sqla_exc.DataError):
        return ErrorCategory.SCHEMA_MISMATCH
    
    # Validation errors
    if isinstance(exception, (ValueError, TypeError, KeyError)):
        return ErrorCategory.VALIDATION_ERROR
    
    # Memory errors
    if isinstance(exception, MemoryError):
        return ErrorCategory.OUT_OF_MEMORY
    
    # Attribute errors (schema mismatch)
    if isinstance(exception, AttributeError):
        return ErrorCategory.SCHEMA_MISMATCH
    
    # Default for unknown errors
    return ErrorCategory.UNKNOWN_ERROR


def is_retryable(error_category: ErrorCategory) -> bool:
    """
    Determine if an error category is retryable.
    
    Retryable errors:
    - NETWORK_ERROR: Network might recover
    - API_RATE_LIMIT: Rate limit might reset
    - DATABASE_LOCK: Lock might be released
    - TEMPORARY_UNAVAILABLE: Service might recover
    
    Non-retryable errors:
    - AUTHENTICATION_ERROR: Credentials won't change
    - AUTHORIZATION_ERROR: Permissions won't change
    - VALIDATION_ERROR: Data is invalid
    - SCHEMA_MISMATCH: Schema incompatibility
    - CONSTRAINT_VIOLATION: Data violates constraints
    
    Infrastructure errors (not retryable by default):
    - DATABASE_CONNECTION_ERROR: Requires intervention
    - OUT_OF_MEMORY: Requires resource adjustment
    - UNKNOWN_ERROR: Unknown cause
    
    Args:
        error_category: Error category to check
    
    Returns:
        True if error is retryable, False otherwise
    
    Examples:
        >>> is_retryable(ErrorCategory.NETWORK_ERROR)
        True
        
        >>> is_retryable(ErrorCategory.AUTHENTICATION_ERROR)
        False
    """
    retryable_categories = {
        ErrorCategory.NETWORK_ERROR,
        ErrorCategory.API_RATE_LIMIT,
        ErrorCategory.DATABASE_LOCK,
        ErrorCategory.TEMPORARY_UNAVAILABLE,
    }
    
    return error_category in retryable_categories


def get_retry_delay(error_category: ErrorCategory, attempt: int = 1) -> Optional[float]:
    """
    Get recommended retry delay in seconds for an error category.
    
    Uses exponential backoff with jitter for retryable errors.
    
    Args:
        error_category: Error category
        attempt: Retry attempt number (1-based)
    
    Returns:
        Delay in seconds, or None if not retryable
    
    Examples:
        >>> get_retry_delay(ErrorCategory.NETWORK_ERROR, 1)
        2.0
        
        >>> get_retry_delay(ErrorCategory.AUTHENTICATION_ERROR, 1)
        None
    """
    if not is_retryable(error_category):
        return None
    
    # Base delays for different error types
    base_delays = {
        ErrorCategory.NETWORK_ERROR: 2.0,
        ErrorCategory.API_RATE_LIMIT: 60.0,  # Wait longer for rate limits
        ErrorCategory.DATABASE_LOCK: 1.0,
        ErrorCategory.TEMPORARY_UNAVAILABLE: 5.0,
    }
    
    base_delay = base_delays.get(error_category, 2.0)
    
    # Exponential backoff: base_delay * (2 ** (attempt - 1))
    # Capped at 300 seconds (5 minutes)
    delay = min(base_delay * (2 ** (attempt - 1)), 300.0)
    
    return delay
