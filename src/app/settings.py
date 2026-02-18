"""Application settings with secrets management integration."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

# Determine the absolute path to the .env file (root directory)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_PATH = os.path.join(BASE_DIR, ".env")

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
    
    # LLM Configuration
    llm_provider: str
    embedding_provider: str
    openai_api_key: Optional[str] = None
    openai_model: str
    google_api_key: Optional[str] = None
    google_model: str
    groq_api_key: Optional[str] = None
    groq_model: str
    google_embedding_model: str
    openai_embedding_model: str
    max_tokens: int
    
    # Cost Rates (USD per 1M tokens)
    input_cost_openai: float
    output_cost_openai: float
    input_cost_google: float
    output_cost_google: float
    input_cost_groq: float
    output_cost_groq: float

    # Agent Weights
    weight_mandatory_skills: float
    weight_preferred_skills: float
    weight_experience: float
    weight_semantic_similarity: float
    weight_certification: float
    weight_jd_text: float
    weight_location: float
    weight_work_mode: float
    
    # Thresholds
    fit_score_threshold: float
    rag_similarity_threshold: float
    max_llm_explanations: int
    
    # Retry Configuration
    max_retry_attempts: int
    retry_backoff_factor: float
    
    # pgvector Configuration
    pgvector_dimension: int
    
    # Application Configuration
    app_env: str
    host: str
    port: int
    reload: bool
    
    # Security Configuration
    secret_key: Optional[str] = None
    access_token_expire_minutes: int
    
    model_config = ConfigDict(
        extra="ignore",
        env_file=ENV_PATH,
        case_sensitive=False
    )

    
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
            db_url = self.database_url or os.getenv("DATABASE_URL")

        if not db_url:
            logger.error("❌ DATABASE_URL not found in settings, secrets, or environment")
            # In production, we should probably raise here, but for now we'll return None 
            # and let the connection fail downstream with a clear error.
            return None
        
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
