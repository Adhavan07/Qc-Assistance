"""
Application Configuration & Settings.
Loads environment variables via Pydantic Settings with strong type safety.
"""

from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "Wiring Diagram QC Assistant"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"  # development, staging, production

    # Security & Tokens
    SECRET_KEY: str = Field(
        default="insecure-dev-secret-key-change-in-production-1234567890",
        description="JWT signature secret key",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./qc_assistant.db",
        description="Async database connection string. Use postgresql+asyncpg:// in production",
    )
    DB_ECHO: bool = False

    # Object Storage (S3 / MinIO)
    S3_BUCKET_NAME: str = "qc-assistant-documents"
    S3_REGION: str = "ap-south-1"
    S3_ENDPOINT_URL: str = ""  # For MinIO or LocalStack
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    PRESIGNED_URL_EXPIRE_SECONDS: int = 900  # 15 minutes

    # Redis / Task Queue
    REDIS_URL: str = "redis://localhost:6379/0"

    # AI Provider & Prompt Governance
    AI_PROVIDER: str = Field(default="mock", description="AI Provider: mock, openai, anthropic, gemini")
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-pro"
    AI_TIMEOUT_SECONDS: float = 30.0
    AI_MAX_RETRIES: int = 3
    PROMPT_VERSION_DEFAULT: str = "wiring-qc-prompt-v1.0"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]


settings = Settings()

