from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "SentinelOps"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Security
    SECRET_KEY: str = "dev-only-change-me-in-production-at-least-32-bytes"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://localhost:80,http://localhost"

    # Database
    DATABASE_URL: str = "postgresql+psycopg://sentinelops:sentinelops_dev_password@localhost:5432/sentinelops"

    # Bootstrap admin
    INITIAL_ADMIN_USERNAME: str = "admin"
    INITIAL_ADMIN_EMAIL: str = "admin@sentinelops.local"
    INITIAL_ADMIN_PASSWORD: str = "Admin@SentinelOps123!"

    # Monitoring defaults
    DEFAULT_MONITORING_INTERVAL_SECONDS: int = 5
    SERVER_OFFLINE_THRESHOLD_SECONDS: int = 30
    DEFAULT_METRIC_RETENTION_DAYS: int = 30
    RATE_LIMIT_AUTH_PER_MINUTE: int = 20
    DISABLE_BACKGROUND_TASKS: bool = False

    # Demo mode flag
    DEMO_MODE: bool = False

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if len(v) < 16:
            raise ValueError("SECRET_KEY must be at least 16 characters long")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()

