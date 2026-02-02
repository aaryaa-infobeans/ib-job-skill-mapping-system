"""Application settings."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    database_url: str = "postgresql://user:password@localhost:5432/ib_job_skill_mapping"
    api_v1_prefix: str = "/api/v1"
    project_name: str = "IB Job Skill Mapping System"
    secret_key: str = "change-me-in-production"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"


settings = Settings()
