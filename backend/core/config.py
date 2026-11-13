"""
Application Settings using Pydantic Settings.
Adheres to fastapi.md & security.md standards.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Interview Coach"
    API_V1_STR: str = "/api/v1"

    # Database Settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "ai_interview_coach"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: Optional[str] = None

    # Environment & Security
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "super-secret-key-change-in-production"
    AUTH_SECRET_KEY: Optional[str] = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        try:
            import asyncpg
            return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        except ImportError:
            return "sqlite+aiosqlite:///:memory:"

settings = Settings()
