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
    llm_provider: str = "openai"  # Options: openai, google
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"
    google_api_key: Optional[str] = None
    google_model: str = "gemini-flash-latest"
    google_embedding_model: str = "models/gemini-embedding-001"
    openai_embedding_model: str = "text-embedding-3-large"
    max_tokens: int = 2000
    openai_input_rate: Optional[float] = None
    openai_output_rate: Optional[float] = None
    
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
    max_llm_explanations: int = 3
    
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
            db_url = self.database_url or os.getenv(
                "DATABASE_URL",
                "postgresql+psycopg2://user:password@localhost:5433/ib_job_skill_mapping"
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
