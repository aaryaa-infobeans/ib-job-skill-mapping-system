"""Configuration management for nightly batch ingestion service."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Database Configuration
    db_host: str = "localhost"
    db_port: int = 5433
    db_name: str = "ib_job_skill_mapping"
    db_user: str = "user"
    db_password: str = "password"  # Default for unit tests
    
    # OAuth Configuration
    oauth_token_url: str = "http://localhost/oauth/token"
    oauth_client_id: str = "test-client"
    oauth_client_secret: str = "test-secret"
    oauth_scope: str = "read:team-data"
    
    # External API Configuration
    api_base_url: str = "http://localhost/api"
    external_api_endpoint: str = "/api/v1/team-members/skill-availability"
    api_timeout: int = 30
    
    # Batch Processing Configuration
    batch_size: int = 100
    max_retries: int = 3
    retry_base_delay: int = 60  # seconds
    
    # Logging Configuration
    log_level: str = "INFO"
    log_dir: str = "logs"
    
    # Runtime Configuration
    dry_run: bool = False

    # CR-EMB-002: Embedding & MCP settings (TASK-EMB-024)
    embedding_model: str = "embedding-gemma-300m"
    mcp_server_script: str = "src/mcp_servers/gdrive/server.py"
    mcp_server_env: dict = {}
    embedding_batch_size: int = 32
    force_re_embed: bool = False
    mcp_client_max_retries: int = 3
    
    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection URL."""
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )
    
    @property
    def external_api_full_url(self) -> str:
        """Construct full external API URL."""
        base = self.api_base_url.rstrip("/")
        endpoint = self.external_api_endpoint.lstrip("/")
        return f"{base}/{endpoint}"


# Global settings instance
settings = Settings()
