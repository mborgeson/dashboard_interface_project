"""
Application configuration using Pydantic Settings.
Loads from environment variables with sensible defaults.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Application Settings
    APP_NAME: str = "B&R Capital Dashboard API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    # Security Settings
    SECRET_KEY: str = (
        "K$!dL8?jbyHaA&H@RtG6XBQtprn&q4ECHf?sJJsjak9epfMX&q&ohePhakX4Pf5"
        "Ar5gHJ9zDD!8$ejiRLqQcD6oNkFTgLKzs4md@RCJfd65?aYi7iik"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS Settings
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    # Database Settings
    # Simple password for asyncpg compatibility (no special characters)
    DATABASE_URL: str = (
        "postgresql://postgres:postgres123@localhost:5432/dashboard_interface_data"
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30

    # Redis Settings
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 3600  # 1 hour default
    REDIS_MAX_CONNECTIONS: int = 50

    # Email Settings -- General (Gmail SMTP)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 465
    SMTP_USER: str | None = "borgesom68@gmail.com"
    SMTP_PASSWORD: str | None = "dgbrnbtlwrlyljcy"
    EMAIL_FROM_NAME: str = "Dashboard Interface (B&R Capital)"
    EMAIL_FROM_ADDRESS: str | None = "borgesom68@gmail.com"
    # Email Settings -- Advanced Settings (Gmail SMTP)
    EMAIL_RATE_LIMIT: int = 60
    EMAIL_MAX_RETRIES: int = 3
    EMAIL_RETRY_DELAY: int = 300
    EMAIL_BATCH_SIZE: int = 10
    EMAIL_DEV_MODE: bool = False

    # WebSocket Settings
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MAX_CONNECTIONS: int = 1000

    # ML Model Settings
    ML_MODEL_PATH: str = "./models"
    ML_BATCH_SIZE: int = 32
    ML_PREDICTION_CACHE_TTL: int = 300  # 5 minutes

    # External APIs
    FRED_API_KEY: str | None = "d043d26a9a4139438bb2a8d565bc01f7"

    # SharePoint/Azure AD Settings (load from .env)
    AZURE_CLIENT_ID: str | None = None
    AZURE_CLIENT_SECRET: str | None = None
    AZURE_TENANT_ID: str | None = None
    SHAREPOINT_SITE_URL: str | None = None
    SHAREPOINT_SITE: str | None = "BRCapital-Internal"
    SHAREPOINT_LIBRARY: str = "Real Estate"  # Document library name
    SHAREPOINT_DEALS_FOLDER: str = "Deals"  # Folder within library
    DEALS_FOLDER: str = "Real Estate/Deals"  # Legacy alias

    # File Criteria
    FILE_PATTERN: str = "UW Model vCurrent"
    EXCLUDE_PATTERNS: str = "Speedboat,vOld"
    FILE_EXTENSIONS: str = ".xlsb,.xlsm"
    CUTOFF_DATE: str = "2024-07-15"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    @property
    def database_url_async(self) -> str:
        """Convert sync database URL to async."""
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
