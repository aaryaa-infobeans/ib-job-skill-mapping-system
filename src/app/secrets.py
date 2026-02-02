"""Secrets management integration for secure credential storage.

This module provides abstraction for retrieving secrets from:
- Environment variables (development)
- AWS Secrets Manager (production)
- HashiCorp Vault (alternative production option)

Usage:
    from app.secrets import get_secret
    
    db_password = get_secret("DB_PASSWORD")
    jwt_secret = get_secret("JWT_SECRET_KEY")
"""

import logging
import os
from typing import Optional, Dict, Any
import json

logger = logging.getLogger(__name__)


class SecretsManager:
    """
    Abstraction layer for secrets retrieval.
    
    Supports multiple backends:
    - Environment variables (default)
    - AWS Secrets Manager (when AWS_SECRETS_ENABLED=true)
    - HashiCorp Vault (when VAULT_ENABLED=true)
    """
    
    def __init__(self):
        self.backend = self._determine_backend()
        self._cache: Dict[str, str] = {}
        logger.info(f"Secrets manager initialized with backend: {self.backend}")
    
    def _determine_backend(self) -> str:
        """Determine which secrets backend to use."""
        if os.getenv("AWS_SECRETS_ENABLED", "false").lower() == "true":
            return "aws"
        elif os.getenv("VAULT_ENABLED", "false").lower() == "true":
            return "vault"
        else:
            return "env"
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Retrieve secret value.
        
        Args:
            key: Secret key/name
            default: Default value if secret not found
            
        Returns:
            Secret value or default
        """
        # Check cache first
        if key in self._cache:
            return self._cache[key]
        
        # Retrieve from backend
        if self.backend == "aws":
            value = self._get_from_aws(key)
        elif self.backend == "vault":
            value = self._get_from_vault(key)
        else:
            value = self._get_from_env(key)
        
        # Use default if not found
        if value is None:
            value = default
        
        # Cache the value
        if value is not None:
            self._cache[key] = value
        
        return value
    
    def _get_from_env(self, key: str) -> Optional[str]:
        """Retrieve secret from environment variable."""
        value = os.getenv(key)
        if value:
            logger.debug(f"Retrieved secret '{key}' from environment")
        return value
    
    def _get_from_aws(self, key: str) -> Optional[str]:
        """
        Retrieve secret from AWS Secrets Manager.
        
        Requires:
            - boto3 installed
            - AWS credentials configured
            - AWS_REGION environment variable
            - AWS_SECRET_NAME environment variable (optional, defaults to key)
        """
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            region = os.getenv("AWS_REGION", "us-east-1")
            secret_name = os.getenv("AWS_SECRET_NAME", "ib-job-skill-mapping-secrets")
            
            client = boto3.client("secretsmanager", region_name=region)
            
            try:
                response = client.get_secret_value(SecretId=secret_name)
                
                # Secrets Manager stores secrets as JSON string
                if "SecretString" in response:
                    secrets_dict = json.loads(response["SecretString"])
                    value = secrets_dict.get(key)
                    
                    if value:
                        logger.info(f"Retrieved secret '{key}' from AWS Secrets Manager")
                    return value
                
            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                if error_code == "ResourceNotFoundException":
                    logger.warning(f"AWS secret '{secret_name}' not found")
                else:
                    logger.error(f"AWS Secrets Manager error: {error_code}")
                return None
                
        except ImportError:
            logger.warning("boto3 not installed, falling back to environment variables")
            return self._get_from_env(key)
        except Exception as e:
            logger.error(f"Error retrieving secret from AWS: {str(e)}")
            return None
    
    def _get_from_vault(self, key: str) -> Optional[str]:
        """
        Retrieve secret from HashiCorp Vault.
        
        Requires:
            - hvac installed
            - VAULT_ADDR environment variable
            - VAULT_TOKEN environment variable
            - VAULT_PATH environment variable (optional, defaults to secret/data/ib-job-skill-mapping)
        """
        try:
            import hvac
            
            vault_addr = os.getenv("VAULT_ADDR")
            vault_token = os.getenv("VAULT_TOKEN")
            vault_path = os.getenv("VAULT_PATH", "secret/data/ib-job-skill-mapping")
            
            if not vault_addr or not vault_token:
                logger.warning("Vault credentials not configured, falling back to environment")
                return self._get_from_env(key)
            
            client = hvac.Client(url=vault_addr, token=vault_token)
            
            if not client.is_authenticated():
                logger.error("Vault authentication failed")
                return None
            
            try:
                response = client.secrets.kv.v2.read_secret_version(path=vault_path)
                secrets_dict = response["data"]["data"]
                value = secrets_dict.get(key)
                
                if value:
                    logger.info(f"Retrieved secret '{key}' from HashiCorp Vault")
                return value
                
            except Exception as e:
                logger.error(f"Error reading from Vault: {str(e)}")
                return None
                
        except ImportError:
            logger.warning("hvac not installed, falling back to environment variables")
            return self._get_from_env(key)
        except Exception as e:
            logger.error(f"Error retrieving secret from Vault: {str(e)}")
            return None
    
    def require(self, key: str) -> str:
        """
        Retrieve required secret, raising error if not found.
        
        Args:
            key: Secret key/name
            
        Returns:
            Secret value
            
        Raises:
            ValueError: If secret not found
        """
        value = self.get(key)
        if value is None:
            raise ValueError(f"Required secret '{key}' not found")
        return value


# Global secrets manager instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get or create global secrets manager instance."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Convenience function to retrieve a secret.
    
    Args:
        key: Secret key/name
        default: Default value if not found
        
    Returns:
        Secret value or default
    """
    manager = get_secrets_manager()
    return manager.get(key, default)


def require_secret(key: str) -> str:
    """
    Convenience function to retrieve a required secret.
    
    Args:
        key: Secret key/name
        
    Returns:
        Secret value
        
    Raises:
        ValueError: If secret not found
    """
    manager = get_secrets_manager()
    return manager.require(key)
