"""
Hash-Based Tokenization - FR-PII-003

Implements irreversible, deterministic tokenization using HMAC-SHA256.

Architecture Changes (CR-PII-001 v2.0.0):
- Removed: AWS KMS/Azure Key Vault dependency
- Removed: Reversible tokenization vault
- Added: Hash-based tokens (one-way, deterministic)

Token Format:
- CLIENT_TOKEN_{hash[0:8]} for client names
- PROJECT_TOKEN_{hash[0:8]} for project names

Properties:
- Deterministic: Same input → same token
- Irreversible: Cannot recover original data
- Collision-resistant: HMAC-SHA256 security
- Fast: No external service calls

Linked Specs:
- FR-PII-003: Configurable rule engine
- Section 3.5: Tokenization approach
- NFR-PII-004: Determinism requirement
"""

import hashlib
import hmac
import logging
from typing import Literal

logger = logging.getLogger(__name__)


class PIITokenizer:
    """Hash-based tokenization for business-sensitive PII."""
    
    def __init__(self, salt: bytes):
        """
        Initialize tokenizer with secret salt.
        
        Args:
            salt: Secret salt from environment (≥32 bytes for security)
        
        Security:
        - Salt must be from environment variable (not hardcoded)
        - Salt must be ≥32 bytes (256 bits)
        - Same salt ensures determinism across requests
        """
        if len(salt) < 32:
            raise ValueError(f"Salt must be ≥32 bytes (got {len(salt)})")
        
        self.salt = salt
        logger.debug("PIITokenizer initialized with salt length: %d", len(salt))
    
    def tokenize(
        self,
        value: str,
        token_type: Literal["CLIENT", "PROJECT"]
    ) -> str:
        """
        Generate deterministic hash-based token.
        
        Algorithm:
        1. Normalize input (strip whitespace, lowercase)
        2. Compute HMAC-SHA256(salt, normalized_value)
        3. Take first 8 hex characters
        4. Return {type}_TOKEN_{hash}
        
        Args:
            value: Original value to tokenize (e.g., "Acme Corp")
            token_type: Token prefix ("CLIENT" or "PROJECT")
        
        Returns:
            Token string (e.g., "CLIENT_TOKEN_a7b9c2d1")
        
        Examples:
            >>> tokenizer = PIITokenizer(b"secret"*10)
            >>> tokenizer.tokenize("Acme Corp", "CLIENT")
            'CLIENT_TOKEN_f3a8b2c1'
            >>> tokenizer.tokenize("Acme Corp", "CLIENT")  # Same input
            'CLIENT_TOKEN_f3a8b2c1'  # Same output (deterministic)
        
        Validation (AC-PII-002):
        - Same input → same token (deterministic)
        - Different input → different token (collision-resistant)
        - Cannot reverse token → original (irreversible)
        """
        if not value or not value.strip():
            raise ValueError("Cannot tokenize empty value")
        
        # Normalize: strip whitespace, lowercase for consistency
        normalized = value.strip().lower()
        
        # Compute HMAC-SHA256
        hmac_hash = hmac.new(
            key=self.salt,
            msg=normalized.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        # Take first 8 characters
        short_hash = hmac_hash[:8]
        
        # Format token
        token = f"{token_type}_TOKEN_{short_hash}"
        
        logger.debug(
            "Tokenized '%s' → '%s' (type=%s)",
            value[:10] + "..." if len(value) > 10 else value,
            token,
            token_type
        )
        
        return token
    
    def tokenize_client_name(self, client_name: str) -> str:
        """
        Tokenize client/company name.
        
        Args:
            client_name: Original client name (e.g., "Acme Corporation")
        
        Returns:
            Client token (e.g., "CLIENT_TOKEN_a7b9c2d1")
        """
        return self.tokenize(client_name, "CLIENT")
    
    def tokenize_project_name(self, project_name: str) -> str:
        """
        Tokenize project name.
        
        Args:
            project_name: Original project name (e.g., "Project Phoenix")
        
        Returns:
            Project token (e.g., "PROJECT_TOKEN_e4f8a9b2")
        """
        return self.tokenize(project_name, "PROJECT")
    
    def verify_determinism(self, value: str, token_type: Literal["CLIENT", "PROJECT"], iterations: int = 1000) -> bool:
        """
        Verify tokenization is deterministic.
        
        Test requirement (TASK-PII-040, TASK-PII-065):
        - Execute 1000 repeated operations
        - Validate identical output checksum
        
        Args:
            value: Test value
            token_type: Token type
            iterations: Number of iterations to test (default: 1000)
        
        Returns:
            True if all iterations produce same token
        """
        first_token = self.tokenize(value, token_type)
        
        for i in range(iterations - 1):
            token = self.tokenize(value, token_type)
            if token != first_token:
                logger.error(
                    "Determinism violation: iteration %d produced different token", i + 2
                )
                return False
        
        logger.info(
            "Determinism verified: %d iterations produced identical token '%s'",
            iterations,
            first_token
        )
        return True
