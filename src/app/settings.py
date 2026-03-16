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
    log_level: str
    
    # Database Configuration
    database_url: Optional[str] = None
    
    # JWT/OAuth2 Configuration
    jwt_secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    
    # Secrets Manager Configuration
    secrets_backend: str

    
    # LLM Configuration
    llm_provider: str = "openai"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-turbo-preview"
    openai_embedding_model: str = "text-embedding-ada-002"
    openai_input_rate: Optional[float] = None
    openai_output_rate: Optional[float] = None
    
    groq_api_key: Optional[str] = None
    groq_model: str = "llama3-70b-8192"
    input_cost_groq: Optional[float] = None
    output_cost_groq: Optional[float] = None
    
    google_api_key: Optional[str] = None
    google_model: str = "gemini-2.5-flash"
    input_cost_google: Optional[float] = None
    output_cost_google: Optional[float] = None
    
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.1


    
    # Agent Weights
    weight_mandatory_skills: float
    weight_preferred_skills: float
    weight_experience: float
    weight_semantic_fit: float = 0.15
    weight_certification: float = 0.10
    weight_context_boost: float = 0.05
    weight_jd_text: float = 0.10
    weight_location: float
    weight_work_mode: float


    
    # Thresholds
    fit_score_threshold: float
    rag_similarity_threshold: float
    
    # Retry Configuration
    max_retry_attempts: int
    retry_backoff_factor: float
    
    # pgvector Configuration
    pgvector_dimension: int

    # CR-EMB-002: Embedding model settings
    embedding_model_name: str = "google/embedding-gemma-300m"
    embedding_model: Optional[str] = None  # Alias for EMBEDDING_MODEL in .env
    gemma_model_path: Optional[str] = None
    embedding_device: str = "cpu"
    mcp_gdrive_server_path: str = "src/mcp_servers/gdrive/server.py"
    google_service_account_file: Optional[str] = None
    
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
        """
        from app.secrets import get_secret
        
        # Try secrets manager first
        db_url = get_secret("DB_URL") or get_secret("DATABASE_URL")
        
        # Fall back to config (loaded from .env)
        return db_url or self.database_url
    
    def get_jwt_secret_key(self) -> Optional[str]:
        """
        Get JWT secret key from secrets manager or fallback to settings.
        """
        from app.secrets import get_secret
        
        # Try secrets manager
        secret = get_secret("JWT_SECRET_KEY") or get_secret("SECRET_KEY")
        
        # Fall back to config (loaded from .env)
        return secret or self.jwt_secret_key



settings = Settings()
