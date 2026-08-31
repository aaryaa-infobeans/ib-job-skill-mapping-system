"""Application settings with secrets management integration."""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with secure secrets handling."""

    # API Configuration
    api_v1_prefix: str = "/api/v1"
    project_name: str = "IB Job Skill Mapping System"
    
    # Logging
    log_level: str = "INFO"
    
    # Database Configuration (fallback values)
    database_url: Optional[str] = None
    
    # JWT/OAuth2 Configuration (fallback values)
    jwt_secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    
    # Secrets Manager Configuration
    secrets_backend: str = "env"  # Options: env, aws, vault
    
    class Config:
        env_file = ".env"
        # .env also carries keys consumed elsewhere (e.g. OPENAI_API_KEY);
        # ignore them instead of failing validation
        extra = "ignore"
    
    def get_database_url(self) -> str:
        """
        Get database URL from secrets manager or fallback to settings.
        
        Priority:
        1. Secrets manager (DB_URL or DATABASE_URL)
        2. Environment variable
        3. Settings default
        """
        from app.secrets import get_secret
        
        # Try secrets manager first
        db_url = get_secret("DB_URL") or get_secret("DATABASE_URL")
        
        # Fall back to config
        if not db_url:
            db_url = self.database_url or os.getenv(
                "DATABASE_URL",
                "postgresql://user:password@localhost:5432/ib_job_skill_mapping"
            )
        
        return db_url
    
    def get_jwt_secret_key(self) -> Optional[str]:
        """
        Get JWT secret key from secrets manager.
        
        Returns None in development to allow unsigned token validation.
        """
        from app.secrets import get_secret
        
        # Try secrets manager
        secret = get_secret("JWT_SECRET_KEY") or get_secret("SECRET_KEY")
        
        # Fall back to config
        if not secret:
            secret = self.jwt_secret_key or os.getenv("JWT_SECRET_KEY")
        
        return secret


settings = Settings()
