from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "sqlite:///./llm_router.db"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # LLM Provider API Keys
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None

    # Base URLs
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # Security
    secret_key: str = "change-this-secret-key-in-production"
    api_key_prefix: str = "llm-router-"

    # Server Settings (these were missing!)
    debug: bool = False
    log_level: str = "info"
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    allowed_origins: str = '["*"]'
    default_rate_limit: int = 1000

    class Config:
        env_file = ".env"
        case_sensitive = False
        # Allow extra fields to prevent validation errors
        extra = "ignore"


# Global settings instance
settings = Settings()
