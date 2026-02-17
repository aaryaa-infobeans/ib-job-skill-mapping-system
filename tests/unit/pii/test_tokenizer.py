"""Unit tests for PIITokenizer - FR-PII-003, TASK-PII-030"""

import pytest
from app.pii.tokenizer import PIITokenizer


class TestPIITokenizer:
    """Test suite for hash-based tokenization."""
    
    def test_tokenizer_initialization_with_valid_salt(self):
        """Test tokenizer initializes with valid salt."""
        salt = b"test_salt_" + b"x" * 32
        tokenizer = PIITokenizer(salt)
        
        assert tokenizer.salt == salt
    
    def test_tokenizer_fails_with_short_salt(self):
        """Test tokenizer fails with salt < 32 bytes."""
        with pytest.raises(ValueError, match="Salt must be ≥32 bytes"):
            PIITokenizer(b"short")
    
    def test_tokenize_client_name(self):
        """Test client name tokenization."""
        tokenizer = PIITokenizer(b"test_salt_" + b"x" * 32)
        
        token = tokenizer.tokenize_client_name("Acme Corporation")
        
        assert token.startswith("CLIENT_TOKEN_")
        assert len(token) == len("CLIENT_TOKEN_") + 8  # 8-char hex
    
    def test_tokenize_project_name(self):
        """Test project name tokenization."""
        tokenizer = PIITokenizer(b"test_salt_" + b"x" * 32)
        
        token = tokenizer.tokenize_project_name("Project Phoenix")
        
        assert token.startswith("PROJECT_TOKEN_")
        assert len(token) == len("PROJECT_TOKEN_") + 8
    
    def test_tokenization_is_deterministic(self):
        """Test same input produces same token (AC-PII-002)."""
        tokenizer = PIITokenizer(b"test_salt_" + b"x" * 32)
        
        token1 = tokenizer.tokenize_client_name("Acme Corporation")
        token2 = tokenizer.tokenize_client_name("Acme Corporation")
        token3 = tokenizer.tokenize_client_name("Acme Corporation")
        
        assert token1 == token2 == token3
    
    def test_tokenization_normalization(self):
        """Test tokenization normalizes whitespace and case."""
        tokenizer = PIITokenizer(b"test_salt_" + b"x" * 32)
        
        token1 = tokenizer.tokenize_client_name("Acme Corporation")
        token2 = tokenizer.tokenize_client_name("  ACME CORPORATION  ")
        token3 = tokenizer.tokenize_client_name("acme corporation")
        
        # All should produce same token (normalized)
        assert token1 == token2 == token3
    
    def test_different_inputs_produce_different_tokens(self):
        """Test different inputs produce different tokens (collision resistance)."""
        tokenizer = PIITokenizer(b"test_salt_" + b"x" * 32)
        
        token1 = tokenizer.tokenize_client_name("Acme Corporation")
        token2 = tokenizer.tokenize_client_name("Tech Industries")
        
        assert token1 != token2
    
    def test_different_types_produce_different_tokens(self):
        """Test same value with different types produces different tokens."""
        tokenizer = PIITokenizer(b"test_salt_" + b"x" * 32)
        
        client_token = tokenizer.tokenize_client_name("Phoenix")
        project_token = tokenizer.tokenize_project_name("Phoenix")
        
        assert client_token.startswith("CLIENT_TOKEN_")
        assert project_token.startswith("PROJECT_TOKEN_")
        # Hash part will be same due to same input
        assert client_token.split("_")[-1] == project_token.split("_")[-1]
    
    def test_tokenize_empty_value_fails(self):
        """Test tokenization fails with empty value."""
        tokenizer = PIITokenizer(b"test_salt_" + b"x" * 32)
        
        with pytest.raises(ValueError, match="Cannot tokenize empty value"):
            tokenizer.tokenize_client_name("")
        
        with pytest.raises(ValueError, match="Cannot tokenize empty value"):
            tokenizer.tokenize_client_name("   ")
    
    def test_verify_determinism_1000_iterations(self):
        """Test determinism verification (TASK-PII-040, TASK-PII-065)."""
        tokenizer = PIITokenizer(b"test_salt_" + b"x" * 32)
        
        is_deterministic = tokenizer.verify_determinism("Acme Corporation", "CLIENT", iterations=1000)
        
        assert is_deterministic is True
    
    def test_tokenization_is_irreversible(self):
        """Test tokens cannot be reversed to original value."""
        tokenizer = PIITokenizer(b"test_salt_" + b"x" * 32)
        
        original = "Acme Corporation"
        token = tokenizer.tokenize_client_name(original)
        
        # Token should not contain original value
        assert original.lower() not in token.lower()
        assert "acme" not in token.lower()
        assert "corporation" not in token.lower()
    
    def test_different_salts_produce_different_tokens(self):
        """Test different salts produce different tokens for same input."""
        tokenizer1 = PIITokenizer(b"salt1_" + b"x" * 32)
        tokenizer2 = PIITokenizer(b"salt2_" + b"y" * 32)
        
        token1 = tokenizer1.tokenize_client_name("Acme Corporation")
        token2 = tokenizer2.tokenize_client_name("Acme Corporation")
        
        assert token1 != token2
    
    def test_token_format_validation(self):
        """Test token format matches specification."""
        tokenizer = PIITokenizer(b"test_salt_" + b"x" * 32)
        
        token = tokenizer.tokenize_client_name("Acme Corporation")
        
        # Format: CLIENT_TOKEN_{8-char hex}
        parts = token.split("_")
        assert len(parts) == 3
        assert parts[0] == "CLIENT"
        assert parts[1] == "TOKEN"
        assert len(parts[2]) == 8
        assert all(c in "0123456789abcdef" for c in parts[2])
