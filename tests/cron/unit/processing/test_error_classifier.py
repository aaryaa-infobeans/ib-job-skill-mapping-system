"""
Unit tests for error classifier.

Tests error categorization and retry eligibility logic.
"""

import pytest
import requests
import sqlalchemy.exc as sqla_exc
from unittest.mock import MagicMock

from src.app.cron.processing.error_classifier import (
    ErrorCategory,
    classify_error,
    is_retryable,
    get_retry_delay
)


# ===== Test ErrorCategory Enum =====

class TestErrorCategory:
    """Tests for ErrorCategory enum."""
    
    def test_retryable_categories_exist(self):
        """Test all retryable error categories exist."""
        assert ErrorCategory.NETWORK_ERROR
        assert ErrorCategory.API_RATE_LIMIT
        assert ErrorCategory.DATABASE_LOCK
        assert ErrorCategory.TEMPORARY_UNAVAILABLE
    
    def test_non_retryable_categories_exist(self):
        """Test all non-retryable error categories exist."""
        assert ErrorCategory.AUTHENTICATION_ERROR
        assert ErrorCategory.AUTHORIZATION_ERROR
        assert ErrorCategory.VALIDATION_ERROR
        assert ErrorCategory.SCHEMA_MISMATCH
        assert ErrorCategory.CONSTRAINT_VIOLATION
    
    def test_infrastructure_categories_exist(self):
        """Test all infrastructure error categories exist."""
        assert ErrorCategory.DATABASE_CONNECTION_ERROR
        assert ErrorCategory.OUT_OF_MEMORY
        assert ErrorCategory.UNKNOWN_ERROR


# ===== Test classify_error =====

class TestClassifyError:
    """Tests for classify_error function."""
    
    # Network errors
    
    def test_classify_connection_error(self):
        """Test classification of ConnectionError."""
        error = ConnectionError("Network unreachable")
        result = classify_error(error)
        assert result == ErrorCategory.NETWORK_ERROR
    
    def test_classify_timeout_error(self):
        """Test classification of TimeoutError."""
        error = TimeoutError("Connection timed out")
        result = classify_error(error)
        assert result == ErrorCategory.NETWORK_ERROR
    
    def test_classify_requests_connection_error(self):
        """Test classification of requests.ConnectionError."""
        error = requests.exceptions.ConnectionError("Failed to connect")
        result = classify_error(error)
        assert result == ErrorCategory.NETWORK_ERROR
    
    def test_classify_requests_timeout(self):
        """Test classification of requests.Timeout."""
        error = requests.exceptions.Timeout("Request timed out")
        result = classify_error(error)
        assert result == ErrorCategory.NETWORK_ERROR
    
    # HTTP errors
    
    def test_classify_http_429_rate_limit(self):
        """Test classification of HTTP 429 (Rate Limit)."""
        response = MagicMock()
        response.status_code = 429
        error = requests.exceptions.HTTPError()
        error.response = response
        
        result = classify_error(error)
        assert result == ErrorCategory.API_RATE_LIMIT
    
    def test_classify_http_401_authentication(self):
        """Test classification of HTTP 401 (Unauthorized)."""
        response = MagicMock()
        response.status_code = 401
        error = requests.exceptions.HTTPError()
        error.response = response
        
        result = classify_error(error)
        assert result == ErrorCategory.AUTHENTICATION_ERROR
    
    def test_classify_http_403_authorization(self):
        """Test classification of HTTP 403 (Forbidden)."""
        response = MagicMock()
        response.status_code = 403
        error = requests.exceptions.HTTPError()
        error.response = response
        
        result = classify_error(error)
        assert result == ErrorCategory.AUTHORIZATION_ERROR
    
    def test_classify_http_503_temporary_unavailable(self):
        """Test classification of HTTP 503 (Service Unavailable)."""
        response = MagicMock()
        response.status_code = 503
        error = requests.exceptions.HTTPError()
        error.response = response
        
        result = classify_error(error)
        assert result == ErrorCategory.TEMPORARY_UNAVAILABLE
    
    def test_classify_http_500_server_error(self):
        """Test classification of HTTP 500 (Server Error)."""
        response = MagicMock()
        response.status_code = 500
        error = requests.exceptions.HTTPError()
        error.response = response
        
        result = classify_error(error)
        assert result == ErrorCategory.TEMPORARY_UNAVAILABLE
    
    def test_classify_http_502_bad_gateway(self):
        """Test classification of HTTP 502 (Bad Gateway)."""
        response = MagicMock()
        response.status_code = 502
        error = requests.exceptions.HTTPError()
        error.response = response
        
        result = classify_error(error)
        assert result == ErrorCategory.TEMPORARY_UNAVAILABLE
    
    # Database errors
    
    def test_classify_integrity_error(self):
        """Test classification of SQLAlchemy IntegrityError."""
        error = sqla_exc.IntegrityError("statement", "params", "orig")
        result = classify_error(error)
        assert result == ErrorCategory.CONSTRAINT_VIOLATION
    
    def test_classify_operational_error_connection(self):
        """Test classification of OperationalError (connection)."""
        error = sqla_exc.OperationalError("statement", "params", "connection failed")
        result = classify_error(error)
        assert result == ErrorCategory.DATABASE_CONNECTION_ERROR
    
    def test_classify_operational_error_network(self):
        """Test classification of OperationalError (network)."""
        error = sqla_exc.OperationalError("statement", "params", "network timeout")
        result = classify_error(error)
        assert result == ErrorCategory.DATABASE_CONNECTION_ERROR
    
    def test_classify_operational_error_lock(self):
        """Test classification of OperationalError (lock)."""
        error = sqla_exc.OperationalError("statement", "params", "database is locked")
        result = classify_error(error)
        assert result == ErrorCategory.DATABASE_LOCK
    
    def test_classify_operational_error_deadlock(self):
        """Test classification of OperationalError (deadlock)."""
        error = sqla_exc.OperationalError("statement", "params", "deadlock detected")
        result = classify_error(error)
        assert result == ErrorCategory.DATABASE_LOCK
    
    def test_classify_data_error(self):
        """Test classification of SQLAlchemy DataError."""
        error = sqla_exc.DataError("statement", "params", "orig")
        result = classify_error(error)
        assert result == ErrorCategory.SCHEMA_MISMATCH
    
    # Validation errors
    
    def test_classify_value_error(self):
        """Test classification of ValueError."""
        error = ValueError("Invalid value")
        result = classify_error(error)
        assert result == ErrorCategory.VALIDATION_ERROR
    
    def test_classify_type_error(self):
        """Test classification of TypeError."""
        error = TypeError("Invalid type")
        result = classify_error(error)
        assert result == ErrorCategory.VALIDATION_ERROR
    
    def test_classify_key_error(self):
        """Test classification of KeyError."""
        error = KeyError("missing_key")
        result = classify_error(error)
        assert result == ErrorCategory.VALIDATION_ERROR
    
    def test_classify_attribute_error(self):
        """Test classification of AttributeError."""
        error = AttributeError("'dict' object has no attribute 'foo'")
        result = classify_error(error)
        assert result == ErrorCategory.SCHEMA_MISMATCH
    
    # Memory errors
    
    def test_classify_memory_error(self):
        """Test classification of MemoryError."""
        error = MemoryError("Out of memory")
        result = classify_error(error)
        assert result == ErrorCategory.OUT_OF_MEMORY
    
    # Unknown errors
    
    def test_classify_unknown_exception(self):
        """Test classification of unknown exception types."""
        error = Exception("Unknown error")
        result = classify_error(error)
        assert result == ErrorCategory.UNKNOWN_ERROR
    
    def test_classify_custom_exception(self):
        """Test classification of custom exception."""
        class CustomError(Exception):
            pass
        
        error = CustomError("Custom error")
        result = classify_error(error)
        assert result == ErrorCategory.UNKNOWN_ERROR


# ===== Test is_retryable =====

class TestIsRetryable:
    """Tests for is_retryable function."""
    
    def test_network_error_is_retryable(self):
        """Test NETWORK_ERROR is retryable."""
        assert is_retryable(ErrorCategory.NETWORK_ERROR) is True
    
    def test_api_rate_limit_is_retryable(self):
        """Test API_RATE_LIMIT is retryable."""
        assert is_retryable(ErrorCategory.API_RATE_LIMIT) is True
    
    def test_database_lock_is_retryable(self):
        """Test DATABASE_LOCK is retryable."""
        assert is_retryable(ErrorCategory.DATABASE_LOCK) is True
    
    def test_temporary_unavailable_is_retryable(self):
        """Test TEMPORARY_UNAVAILABLE is retryable."""
        assert is_retryable(ErrorCategory.TEMPORARY_UNAVAILABLE) is True
    
    def test_authentication_error_not_retryable(self):
        """Test AUTHENTICATION_ERROR is not retryable."""
        assert is_retryable(ErrorCategory.AUTHENTICATION_ERROR) is False
    
    def test_authorization_error_not_retryable(self):
        """Test AUTHORIZATION_ERROR is not retryable."""
        assert is_retryable(ErrorCategory.AUTHORIZATION_ERROR) is False
    
    def test_validation_error_not_retryable(self):
        """Test VALIDATION_ERROR is not retryable."""
        assert is_retryable(ErrorCategory.VALIDATION_ERROR) is False
    
    def test_schema_mismatch_not_retryable(self):
        """Test SCHEMA_MISMATCH is not retryable."""
        assert is_retryable(ErrorCategory.SCHEMA_MISMATCH) is False
    
    def test_constraint_violation_not_retryable(self):
        """Test CONSTRAINT_VIOLATION is not retryable."""
        assert is_retryable(ErrorCategory.CONSTRAINT_VIOLATION) is False
    
    def test_database_connection_error_not_retryable(self):
        """Test DATABASE_CONNECTION_ERROR is not retryable."""
        assert is_retryable(ErrorCategory.DATABASE_CONNECTION_ERROR) is False
    
    def test_out_of_memory_not_retryable(self):
        """Test OUT_OF_MEMORY is not retryable."""
        assert is_retryable(ErrorCategory.OUT_OF_MEMORY) is False
    
    def test_unknown_error_not_retryable(self):
        """Test UNKNOWN_ERROR is not retryable."""
        assert is_retryable(ErrorCategory.UNKNOWN_ERROR) is False


# ===== Test get_retry_delay =====

class TestGetRetryDelay:
    """Tests for get_retry_delay function."""
    
    def test_network_error_base_delay(self):
        """Test base delay for NETWORK_ERROR."""
        delay = get_retry_delay(ErrorCategory.NETWORK_ERROR, attempt=1)
        assert delay == 2.0
    
    def test_api_rate_limit_base_delay(self):
        """Test base delay for API_RATE_LIMIT (longer)."""
        delay = get_retry_delay(ErrorCategory.API_RATE_LIMIT, attempt=1)
        assert delay == 60.0
    
    def test_database_lock_base_delay(self):
        """Test base delay for DATABASE_LOCK."""
        delay = get_retry_delay(ErrorCategory.DATABASE_LOCK, attempt=1)
        assert delay == 1.0
    
    def test_temporary_unavailable_base_delay(self):
        """Test base delay for TEMPORARY_UNAVAILABLE."""
        delay = get_retry_delay(ErrorCategory.TEMPORARY_UNAVAILABLE, attempt=1)
        assert delay == 5.0
    
    def test_exponential_backoff_network_error(self):
        """Test exponential backoff for NETWORK_ERROR."""
        delay1 = get_retry_delay(ErrorCategory.NETWORK_ERROR, attempt=1)
        delay2 = get_retry_delay(ErrorCategory.NETWORK_ERROR, attempt=2)
        delay3 = get_retry_delay(ErrorCategory.NETWORK_ERROR, attempt=3)
        
        assert delay1 == 2.0
        assert delay2 == 4.0
        assert delay3 == 8.0
    
    def test_exponential_backoff_capped(self):
        """Test exponential backoff is capped at 300 seconds."""
        # With base delay of 2.0, attempt 8 would be 256, attempt 9 would be 512
        delay = get_retry_delay(ErrorCategory.NETWORK_ERROR, attempt=10)
        assert delay == 300.0  # Capped at max
    
    def test_non_retryable_returns_none(self):
        """Test non-retryable errors return None."""
        delay = get_retry_delay(ErrorCategory.AUTHENTICATION_ERROR, attempt=1)
        assert delay is None
    
    def test_validation_error_returns_none(self):
        """Test VALIDATION_ERROR returns None."""
        delay = get_retry_delay(ErrorCategory.VALIDATION_ERROR, attempt=1)
        assert delay is None
    
    def test_unknown_error_returns_none(self):
        """Test UNKNOWN_ERROR returns None."""
        delay = get_retry_delay(ErrorCategory.UNKNOWN_ERROR, attempt=1)
        assert delay is None


# ===== Integration Tests =====

class TestErrorClassificationIntegration:
    """Integration tests for error classification workflow."""
    
    def test_classify_and_check_retryable_network(self):
        """Test full workflow for network error."""
        error = requests.exceptions.ConnectionError()
        category = classify_error(error)
        retryable = is_retryable(category)
        delay = get_retry_delay(category, attempt=1)
        
        assert category == ErrorCategory.NETWORK_ERROR
        assert retryable is True
        assert delay == 2.0
    
    def test_classify_and_check_retryable_auth(self):
        """Test full workflow for authentication error."""
        response = MagicMock()
        response.status_code = 401
        error = requests.exceptions.HTTPError()
        error.response = response
        
        category = classify_error(error)
        retryable = is_retryable(category)
        delay = get_retry_delay(category, attempt=1)
        
        assert category == ErrorCategory.AUTHENTICATION_ERROR
        assert retryable is False
        assert delay is None
    
    def test_classify_and_check_retryable_rate_limit(self):
        """Test full workflow for rate limit error."""
        response = MagicMock()
        response.status_code = 429
        error = requests.exceptions.HTTPError()
        error.response = response
        
        category = classify_error(error)
        retryable = is_retryable(category)
        delay = get_retry_delay(category, attempt=1)
        
        assert category == ErrorCategory.API_RATE_LIMIT
        assert retryable is True
        assert delay == 60.0  # Longer delay for rate limits
    
    def test_classify_database_errors(self):
        """Test classification of various database errors."""
        # Integrity error
        integrity_error = sqla_exc.IntegrityError("stmt", "params", "orig")
        assert classify_error(integrity_error) == ErrorCategory.CONSTRAINT_VIOLATION
        assert is_retryable(classify_error(integrity_error)) is False
        
        # Connection error
        conn_error = sqla_exc.OperationalError("stmt", "params", "connection failed")
        assert classify_error(conn_error) == ErrorCategory.DATABASE_CONNECTION_ERROR
        assert is_retryable(classify_error(conn_error)) is False
        
        # Lock error
        lock_error = sqla_exc.OperationalError("stmt", "params", "locked")
        assert classify_error(lock_error) == ErrorCategory.DATABASE_LOCK
        assert is_retryable(classify_error(lock_error)) is True
