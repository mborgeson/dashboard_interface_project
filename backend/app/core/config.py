"""
Application configuration using Pydantic Settings.
Loads from environment variables with sensible defaults.

SECURITY NOTE: Secrets must be provided via environment variables.
No hardcoded secrets are used in production.
"""

import secrets as secrets_module
from functools import lru_cache
from typing import Any

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        # Parse nested settings like CORS_ORIGINS from JSON or comma-separated strings
        env_nested_delimiter="__",
    )

    # Application Settings
    APP_NAME: str = "B&R Capital Dashboard API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Server Settings
    HOST: str = "0.0.0.0"  # nosec B104 — required for container/dev server binding
    PORT: int = 8000
    WORKERS: int = 4

    # Security Settings - SECRET_KEY MUST be set via environment variable in production
    SECRET_KEY: str | None = None  # No hardcoded default - validated below
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS Settings - configurable via CORS_ORIGINS env var
    # Supports both JSON array ["url1", "url2"] and comma-separated "url1,url2" formats
    # Development origins are defaults; production origins should be set via CORS_ORIGINS env var
    CORS_ORIGINS: list[str] = [
        # Development origins (defaults)
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        # Production origins - also set via CORS_ORIGINS env var for flexibility
        "https://dashboard.bandrcapital.com",
        "https://app.bandrcapital.com",
        "https://bandrcapital.com",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Parse CORS origins from comma-separated string, JSON array, or list.

        Environment variable formats supported:
        - Comma-separated: CORS_ORIGINS="https://example.com,https://app.example.com"
        - JSON array: CORS_ORIGINS='["https://example.com","https://app.example.com"]'
        """
        if v is None:
            return []
        if isinstance(v, list):
            return [str(origin).strip() for origin in v if origin]
        if isinstance(v, str):
            v = v.strip()
            # Try JSON parse first (for ["url1", "url2"] format)
            if v.startswith("["):
                import json

                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return [str(origin).strip() for origin in parsed if origin]
                except json.JSONDecodeError:
                    pass
            # Fall back to comma-separated parsing
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return []

    @model_validator(mode="after")
    def validate_secrets(self) -> "Settings":
        """Validate that required secrets are set appropriately for the environment."""
        # SECRET_KEY validation
        if self.ENVIRONMENT == "production":
            if not self.SECRET_KEY:
                raise ValueError(
                    "SECRET_KEY environment variable must be set in production. "
                    'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(64))"'
                )
            if len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "SECRET_KEY must be at least 32 characters in production"
                )
            # DATABASE_URL validation - must be PostgreSQL in production
            if "sqlite" in self.DATABASE_URL.lower():
                raise ValueError(
                    "DATABASE_URL must use PostgreSQL in production. "
                    "SQLite is only allowed for development/testing."
                )
        else:
            # For development/testing, generate a random key if not provided
            if not self.SECRET_KEY:
                object.__setattr__(self, "SECRET_KEY", secrets_module.token_urlsafe(64))

        return self

    # Database Settings - use SQLite for dev, PostgreSQL URL via env var for production
    DATABASE_URL: str = "sqlite:///./test.db"  # Safe default for development only
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
    SMTP_USER: str | None = None  # Set via environment variable
    SMTP_PASSWORD: str | None = None  # NEVER hardcode - set via SMTP_PASSWORD env var
    EMAIL_FROM_NAME: str = "Dashboard Interface (B&R Capital)"
    EMAIL_FROM_ADDRESS: str | None = None  # Set via environment variable
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

    # Market Analysis Database (separate PostgreSQL DB with CoStar + FRED data)
    # Set via MARKET_ANALYSIS_DB_URL env var, e.g.:
    #   postgresql://user:pass@localhost:5432/market_analysis
    MARKET_ANALYSIS_DB_URL: str | None = None

    # External APIs - set via environment variables, no hardcoded keys
    FRED_API_KEY: str | None = None  # Set via FRED_API_KEY env var
    CENSUS_API_KEY: str | None = None  # Set via CENSUS_API_KEY env var

    # Construction Pipeline Settings
    CONSTRUCTION_DATA_DIR: str = "data/construction"
    CONSTRUCTION_API_ENABLED: bool = False
    CONSTRUCTION_CENSUS_CRON: str = "0 4 15 * *"  # Monthly 15th 4 AM
    CONSTRUCTION_FRED_CRON: str = "0 4 15 * *"  # Monthly 15th 4 AM
    CONSTRUCTION_BLS_CRON: str = "0 5 15 * *"  # Monthly 15th 5 AM
    BLS_API_KEY: str | None = None  # Optional — increases rate limit
    CONSTRUCTION_MUNICIPAL_CRON: str = "0 6 16 * *"  # Monthly 16th 6 AM
    MESA_SODA_DATASET_ID: str = "h2sj-gt3d"
    MESA_SODA_APP_TOKEN: str | None = None  # Optional Socrata app token
    TEMPE_BLDS_LAYER_URL: str | None = None  # Tempe ArcGIS feature layer URL
    GILBERT_ARCGIS_LAYER_URL: str | None = None  # Gilbert ArcGIS feature layer URL

    # Market Data Extraction Settings
    COSTAR_DATA_DIR: str = "data/costar"
    MARKET_DATA_EXTRACTION_ENABLED: bool = False
    MARKET_FRED_SCHEDULE_CRON: str = "0 10 * * *"  # Daily 10 AM
    MARKET_COSTAR_SCHEDULE_CRON: str = "0 10 15 * *"  # Monthly 15th 10 AM (reminder)
    MARKET_CENSUS_SCHEDULE_CRON: str = "0 10 15 1 *"  # Annual Jan 15th 10 AM

    # Interest Rate Scheduler (twice-daily FRED fetch)
    INTEREST_RATE_SCHEDULE_ENABLED: bool = False
    INTEREST_RATE_SCHEDULE_CRON_AM: str = "0 8 * * *"  # Daily 8 AM
    INTEREST_RATE_SCHEDULE_CRON_PM: str = "0 15 * * *"  # Daily 3 PM

    # SharePoint/Azure AD Settings (load from .env)
    AZURE_CLIENT_ID: str | None = None
    AZURE_CLIENT_SECRET: str | None = None
    AZURE_TENANT_ID: str | None = None
    SHAREPOINT_SITE_URL: str | None = None
    SHAREPOINT_SITE: str | None = "BRCapital-Internal"
    SHAREPOINT_LIBRARY: str = "Real Estate"  # Document library name
    SHAREPOINT_DEALS_FOLDER: str = "Deals"  # Folder within library
    DEALS_FOLDER: str = "Real Estate/Deals"  # Legacy alias

    # File Filtering Settings
    # Regex pattern for matching UW model filenames (supports regex or simple substring)
    FILE_PATTERN: str = r".*UW\s*Model.*vCurrent.*"
    # Comma-separated list of substrings to exclude from processing
    EXCLUDE_PATTERNS: str = "~$,.tmp,backup,old,archive,Speedboat,vOld"
    # Comma-separated list of valid file extensions
    FILE_EXTENSIONS: str = ".xlsb,.xlsm,.xlsx"
    # Skip files older than this date (YYYY-MM-DD format, empty to disable)
    CUTOFF_DATE: str = "2024-07-15"
    # Skip files larger than this size in MB
    MAX_FILE_SIZE_MB: int = 100

    # Rate Limiting Settings
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_BACKEND: str = "auto"  # "memory", "redis", or "auto"
    RATE_LIMIT_REQUESTS: int = 100  # Default requests per window for API endpoints
    RATE_LIMIT_WINDOW: int = 60  # Default window in seconds
    RATE_LIMIT_AUTH_REQUESTS: int = 5  # Stricter limit for auth endpoints
    RATE_LIMIT_AUTH_WINDOW: int = 60  # Window for auth rate limiting

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Extraction Scheduler Settings
    EXTRACTION_SCHEDULE_ENABLED: bool = True
    EXTRACTION_SCHEDULE_CRON: str = "0 17 * * *"  # Daily at 5 PM
    EXTRACTION_SCHEDULE_TIMEZONE: str = "America/Phoenix"

    # Group Extraction Settings (UW Model File Grouping & Data Extraction)
    GROUP_EXTRACTION_DATA_DIR: str = "data/extraction_groups"
    GROUP_FINGERPRINT_WORKERS: int = 4
    GROUP_IDENTITY_THRESHOLD: float = 0.95
    GROUP_VARIANT_THRESHOLD: float = 0.80
    GROUP_EMPTY_TEMPLATE_THRESHOLD: int = 20
    GROUP_MAX_BATCH_SIZE: int = 500

    # File Monitoring Settings
    FILE_MONITOR_ENABLED: bool = False
    FILE_MONITOR_INTERVAL_MINUTES: int = 30
    AUTO_EXTRACT_ON_CHANGE: bool = True
    MONITOR_CHECK_CRON: str = "*/30 * * * *"  # Every 30 minutes

    @property
    def database_url_async(self) -> str:
        """Convert sync database URL to async."""
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

    @property
    def sharepoint_configured(self) -> bool:
        """Check if SharePoint/Azure AD credentials are configured."""
        return all(
            [
                self.AZURE_TENANT_ID,
                self.AZURE_CLIENT_ID,
                self.AZURE_CLIENT_SECRET,
                self.SHAREPOINT_SITE_URL,
            ]
        )

    def get_sharepoint_config_errors(self) -> list[str]:
        """Get list of missing SharePoint configuration items."""
        errors = []
        if not self.AZURE_TENANT_ID:
            errors.append("AZURE_TENANT_ID")
        if not self.AZURE_CLIENT_ID:
            errors.append("AZURE_CLIENT_ID")
        if not self.AZURE_CLIENT_SECRET:
            errors.append("AZURE_CLIENT_SECRET")
        if not self.SHAREPOINT_SITE_URL:
            errors.append("SHAREPOINT_SITE_URL")
        return errors


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
