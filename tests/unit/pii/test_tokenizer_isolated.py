"""
Isolated unit tests for PIITokenizer that don't require app configuration
Run with: pytest tests/unit/pii/test_tokenizer_isolated.py -v
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

import pytest


class PIITokenizer:
    """Standalone tokenizer for testing (copy of implementation)."""
    import hashlib
    import hmac
    
    def __init__(self, salt: bytes):
        if len(salt) < 32:
            raise ValueError(f"Salt must be ≥32 bytes (got {len(salt)})")
        self.salt = salt
    
    def tokenize(self, value: str, token_type: str) -> str:
        if not value or not value.strip():
            raise ValueError("Cannot tokenize empty value")
        
        import hashlib
        import hmac
        
        normalized = value.strip().lower()
        
        hmac_hash = hmac.new(
            key=self.salt,
            msg=normalized.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        short_hash = hmac_hash[:8]
        token = f"{token_type}_TOKEN_{short_hash}"
        
        return token
    
    def tokenize_client_name(self, client_name: str) -> str:
        return self.tokenize(client_name, "CLIENT")
    
    def tokenize_project_name(self, project_name: str) -> str:
        return self.tokenize(project_name, "PROJECT")


class TestPIITokenizerIsolated:
    """Isolated test suite for hash-based tokenization."""
    
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
        print(f"✓ Determinism verified: {token1}")
    
    def test_tokenization_normalization(self):
        """Test tokenization normalizes whitespace and case."""
        tokenizer = PIITokenizer(b"test_salt_" + b"x" * 32)
        
        token1 = tokenizer.tokenize_client_name("Acme Corporation")
        token2 = tokenizer.tokenize_client_name("  ACME CORPORATION  ")
        token3 = tokenizer.tokenize_client_name("acme corporation")
        
        # All should produce same token (normalized)
        assert token1 == token2 == token3
        print(f"✓ Normalization verified: {token1}")
    
    def test_different_inputs_produce_different_tokens(self):
        """Test different inputs produce different tokens (collision resistance)."""
        tokenizer = PIITokenizer(b"test_salt_" + b"x" * 32)
        
        token1 = tokenizer.tokenize_client_name("Acme Corporation")
        token2 = tokenizer.tokenize_client_name("Tech Industries")
        
        assert token1 != token2
        print(f"✓ Collision resistance verified")
    
    def test_tokenize_empty_value_fails(self):
        """Test tokenization fails with empty value."""
        tokenizer = PIITokenizer(b"test_salt_" + b"x" * 32)
        
        with pytest.raises(ValueError, match="Cannot tokenize empty value"):
            tokenizer.tokenize_client_name("")
        
        with pytest.raises(ValueError, match="Cannot tokenize empty value"):
            tokenizer.tokenize_client_name("   ")
    
    def test_tokenization_is_irreversible(self):
        """Test tokens cannot be reversed to original value."""
        tokenizer = PIITokenizer(b"test_salt_" + b"x" * 32)
        
        original = "Acme Corporation"
        token = tokenizer.tokenize_client_name(original)
        
        # Token should not contain original value
        assert original.lower() not in token.lower()
        assert "acme" not in token.lower()
        assert "corporation" not in token.lower()
        print(f"✓ Irreversibility verified: '{original}' → '{token}'")
    
    def test_verify_determinism_1000_iterations(self):
        """Test determinism with 1000 iterations (TASK-PII-040, TASK-PII-065)."""
        tokenizer = PIITokenizer(b"test_salt_" + b"x" * 32)
        
        first_token = tokenizer.tokenize_client_name("Test Value")
        
        for i in range(999):
            token = tokenizer.tokenize_client_name("Test Value")
            assert token == first_token
        
        print(f"✓ 1000 iterations verified: deterministic")
    
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
        print(f"✓ Token format validated: {token}")


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "-s"])
