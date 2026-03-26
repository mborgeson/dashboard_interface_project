"""
Application configuration using Pydantic Settings.
Loads from environment variables with sensible defaults.

SECURITY NOTE: Secrets must be provided via environment variables.
No hardcoded secrets are used in production.

Configuration is organized into logical groups for clarity:
- AppSettings: Application metadata, server, logging, caching
- AuthSettings: JWT, API keys, rate limiting, demo credentials
- DatabaseSettings: Primary DB, market analysis DB, Redis
- ExternalServiceSettings: Email, SharePoint, external APIs
- ExtractionSettings: File filtering, batch processing, scheduling
- ConstructionSettings: Construction pipeline data sources
- MarketDataSettings: CoStar, FRED schedules
- Settings: Main class composing all groups with cross-cutting validation
"""

import secrets as secrets_module
from functools import lru_cache
from typing import Any, Literal

from loguru import logger
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ── Shared model config ──────────────────────────────────────────────────────
# All settings groups share the same env-file loading behavior.
_SHARED_CONFIG = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
    case_sensitive=False,
    extra="ignore",
    env_nested_delimiter="__",
)


# ── Application Settings ─────────────────────────────────────────────────────


class AppSettings(BaseSettings):
    """Application metadata, server, logging, and caching settings."""

    model_config = _SHARED_CONFIG

    # Application metadata
    APP_NAME: str = "B&R Capital Dashboard API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "staging", "production", "testing"] = (
        "development"
    )

    # Server
    HOST: str = "0.0.0.0"  # nosec B104 — required for container/dev server binding
    PORT: int = 8000
    WORKERS: int = 4

    # Logging
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_RETENTION_DAYS: int = 30
    LOG_ERROR_RETENTION_DAYS: int = 90

    # Slow Query Detection
    SLOW_QUERY_THRESHOLD_MS: int = 500
    SLOW_QUERY_LOG_PARAMS: bool = False

    # Cache TTL (seconds)
    CACHE_SHORT_TTL: int = 300  # 5 minutes — frequently-changing data
    CACHE_LONG_TTL: int = 7200  # 2 hours — rarely-changing aggregates

    # HTTP Client
    HTTP_TIMEOUT: float = 10.0
    HTTP_TIMEOUT_LONG: float = 15.0

    # File Upload Size Limits (MB)
    UPLOAD_MAX_EXCEL_MB: int = 50
    UPLOAD_MAX_PDF_MB: int = 25
    UPLOAD_MAX_CSV_MB: int = 10
    UPLOAD_MAX_DOCX_MB: int = 25

    # PDF Report Limits
    PDF_MAX_PROPERTIES: int = 10
    PDF_MAX_DEALS: int = 10

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MAX_CONNECTIONS: int = 1000

    # ML Model
    ML_MODEL_PATH: str = "./models"
    ML_BATCH_SIZE: int = 32
    ML_PREDICTION_CACHE_TTL: int = 300

    # Geocoding
    GEOCODING_RATE_LIMIT_DELAY: float = 1.1

    # Workflow HTTP Step
    WORKFLOW_HTTP_TIMEOUT: int = 30

    # CORS — configurable via CORS_ORIGINS env var
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
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
            if v.startswith("["):
                import json

                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return [str(origin).strip() for origin in parsed if origin]
                except json.JSONDecodeError:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return []


# ── Auth Settings ─────────────────────────────────────────────────────────────


class AuthSettings(BaseSettings):
    """JWT, API key, rate limiting, and demo credential settings."""

    model_config = _SHARED_CONFIG

    # JWT
    SECRET_KEY: str | None = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    # Separate signing key for refresh tokens. If empty, falls back to SECRET_KEY.
    REFRESH_TOKEN_SECRET: str = ""

    # Demo credentials — must be provided via environment variables
    DEMO_USER_PASSWORD: str = ""
    DEMO_ADMIN_PASSWORD: str = ""
    DEMO_ANALYST_PASSWORD: str = ""

    # API Key Authentication (service-to-service)
    API_KEYS: list[str] = []
    API_KEY_HEADER: str = "X-API-Key"

    @field_validator("API_KEYS", mode="before")
    @classmethod
    def parse_api_keys(cls, v: Any) -> list[str]:
        """Parse API keys from comma-separated string or list."""
        if v is None:
            return []
        if isinstance(v, list):
            return [str(k).strip() for k in v if k and str(k).strip()]
        if isinstance(v, str):
            return [k.strip() for k in v.split(",") if k.strip()]
        return []

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_BACKEND: str = "auto"
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60
    RATE_LIMIT_AUTH_REQUESTS: int = 5
    RATE_LIMIT_AUTH_WINDOW: int = 60
    RATE_LIMIT_REFRESH_REQUESTS: int = 10
    RATE_LIMIT_CLEANUP_WINDOW: int = 3600


# ── Database Settings ─────────────────────────────────────────────────────────


class DatabaseSettings(BaseSettings):
    """Primary DB, market analysis DB, and Redis settings."""

    model_config = _SHARED_CONFIG

    # Primary database — no default in production (validated in Settings)
    DATABASE_URL: str = "sqlite:///./test.db"  # Dev/test only; see Settings validator
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30

    # Market Analysis Database (separate PostgreSQL DB)
    MARKET_ANALYSIS_DB_URL: str | None = None

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 3600
    REDIS_MAX_CONNECTIONS: int = 50
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 5
    REDIS_REQUIRED: bool = False
    REDIS_PASSWORD: str = ""

    # Interest Rate Service DB
    INTEREST_RATE_CACHE_TTL: int = 300
    INTEREST_RATE_DB_POOL_SIZE: int = 2
    INTEREST_RATE_DB_MAX_OVERFLOW: int = 1


# ── External Service Settings ────────────────────────────────────────────────


class ExternalServiceSettings(BaseSettings):
    """Email, SharePoint/Azure AD, and external API settings."""

    model_config = _SHARED_CONFIG

    # Email (Gmail SMTP)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 465
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAIL_FROM_NAME: str = "Dashboard Interface (B&R Capital)"
    EMAIL_FROM_ADDRESS: str | None = None
    EMAIL_RATE_LIMIT: int = 60
    EMAIL_MAX_RETRIES: int = 3
    EMAIL_RETRY_DELAY: int = 300
    EMAIL_BATCH_SIZE: int = 10
    EMAIL_DEV_MODE: bool = False

    # SharePoint/Azure AD
    AZURE_CLIENT_ID: str | None = None
    AZURE_CLIENT_SECRET: str | None = None
    AZURE_TENANT_ID: str | None = None
    SHAREPOINT_SITE_URL: str | None = None
    SHAREPOINT_SITE: str | None = "BRCapital-Internal"
    SHAREPOINT_LIBRARY: str = "Real Estate"
    SHAREPOINT_DEALS_FOLDER: str = "Deals"
    DEALS_FOLDER: str = "Real Estate/Deals"  # Legacy alias
    LOCAL_DEALS_ROOT: str = ""

    # External APIs
    FRED_API_KEY: str | None = None
    CENSUS_API_KEY: str | None = None
    BLS_API_KEY: str | None = None

    # Interest Rate Scheduler
    INTEREST_RATE_SCHEDULE_ENABLED: bool = False
    INTEREST_RATE_SCHEDULE_CRON_AM: str = "0 8 * * *"
    INTEREST_RATE_SCHEDULE_CRON_PM: str = "0 15 * * *"


# ── Extraction Settings ──────────────────────────────────────────────────────


class ExtractionSettings(BaseSettings):
    """File filtering, batch processing, group extraction, and scheduling."""

    model_config = _SHARED_CONFIG

    # File Filtering
    FILE_PATTERN: str = r".*UW\s*Model.*vCurrent.*"
    EXCLUDE_PATTERNS: str = "~$,.tmp,backup,old,archive,Speedboat,vOld"
    FILE_EXTENSIONS: str = ".xlsb,.xlsm,.xlsx"
    CUTOFF_DATE: str = "2024-07-15"
    MAX_FILE_SIZE_MB: int = 100

    # Batch Processing
    EXTRACTION_BATCH_SIZE: int = 10
    EXTRACTION_MAX_WORKERS: int = 4

    # Scheduler
    EXTRACTION_SCHEDULE_ENABLED: bool = True
    EXTRACTION_SCHEDULE_CRON: str = "0 17 * * *"
    EXTRACTION_SCHEDULE_TIMEZONE: str = "America/Phoenix"

    # Group Extraction
    GROUP_EXTRACTION_DATA_DIR: str = "data/extraction_groups"
    GROUP_FINGERPRINT_WORKERS: int = 4
    GROUP_IDENTITY_THRESHOLD: float = 0.95
    GROUP_VARIANT_THRESHOLD: float = 0.80
    GROUP_EMPTY_TEMPLATE_THRESHOLD: int = 20
    GROUP_MAX_BATCH_SIZE: int = 500

    # File Monitoring
    FILE_MONITOR_ENABLED: bool = False
    FILE_MONITOR_INTERVAL_MINUTES: int = 30
    AUTO_EXTRACT_ON_CHANGE: bool = True
    MONITOR_CHECK_CRON: str = "*/30 * * * *"


# ── Construction Pipeline Settings ───────────────────────────────────────────


class ConstructionSettings(BaseSettings):
    """Construction pipeline data sources and cron schedules."""

    model_config = _SHARED_CONFIG

    CONSTRUCTION_DATA_DIR: str = "data/construction"
    CONSTRUCTION_API_ENABLED: bool = False
    CONSTRUCTION_CENSUS_CRON: str = "0 4 15 * *"
    CONSTRUCTION_FRED_CRON: str = "0 4 15 * *"
    CONSTRUCTION_BLS_CRON: str = "0 5 15 * *"
    CONSTRUCTION_MUNICIPAL_CRON: str = "0 6 16 * *"
    CONSTRUCTION_MIN_UNITS: int = 50

    # Municipal data sources
    MESA_SODA_DATASET_ID: str = "h2sj-gt3d"
    MESA_SODA_APP_TOKEN: str | None = None
    TEMPE_BLDS_LAYER_URL: str | None = None
    GILBERT_ARCGIS_LAYER_URL: str | None = None


# ── Market Data Settings ─────────────────────────────────────────────────────


class MarketDataSettings(BaseSettings):
    """CoStar and market data extraction schedules."""

    model_config = _SHARED_CONFIG

    COSTAR_DATA_DIR: str = "data/costar"
    MARKET_DATA_EXTRACTION_ENABLED: bool = False
    MARKET_FRED_SCHEDULE_CRON: str = "0 10 * * *"
    MARKET_COSTAR_SCHEDULE_CRON: str = "0 10 15 * *"
    MARKET_CENSUS_SCHEDULE_CRON: str = "0 10 15 1 *"


# ── Main Settings (composes all groups) ──────────────────────────────────────


class Settings(
    AppSettings,
    AuthSettings,
    DatabaseSettings,
    ExternalServiceSettings,
    ExtractionSettings,
    ConstructionSettings,
    MarketDataSettings,
):
    """Application settings loaded from environment variables.

    Inherits all setting fields from the logical sub-groups above.
    This keeps backward compatibility — all attributes remain accessible
    via ``settings.FIELD_NAME`` as before.
    """

    @model_validator(mode="after")
    def validate_secrets(self) -> "Settings":
        """Validate that required secrets are set appropriately for the environment."""
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
            # DATABASE_URL validation — must be PostgreSQL in production
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

    @model_validator(mode="after")
    def validate_demo_credentials(self) -> "Settings":
        """Validate demo credential configuration for the environment.

        - Production: demo passwords must NOT be set (raises error if present)
        - Development/testing: logs a warning if demo passwords are empty
        """
        demo_passwords = [
            self.DEMO_USER_PASSWORD,
            self.DEMO_ADMIN_PASSWORD,
            self.DEMO_ANALYST_PASSWORD,
        ]
        any_set = any(pwd for pwd in demo_passwords)

        if self.ENVIRONMENT == "production" and any_set:
            raise ValueError(
                "Demo passwords must not be set in production. "
                "Remove DEMO_USER_PASSWORD, DEMO_ADMIN_PASSWORD, and "
                "DEMO_ANALYST_PASSWORD from environment variables."
            )

        if self.ENVIRONMENT == "development" and not any_set:
            logger.warning(
                "Demo passwords are empty. Set DEMO_USER_PASSWORD, "
                "DEMO_ADMIN_PASSWORD, and DEMO_ANALYST_PASSWORD via "
                "environment variables to enable demo user login."
            )

        return self

    @model_validator(mode="after")
    def validate_redis_config(self) -> "Settings":
        """Validate Redis configuration consistency.

        Warns if REDIS_PASSWORD is set but not included in REDIS_URL,
        which likely indicates a misconfiguration.
        """
        if (
            self.REDIS_PASSWORD
            and self.REDIS_URL
            and f":{self.REDIS_PASSWORD}@" not in self.REDIS_URL
        ):
            logger.warning(
                "REDIS_PASSWORD is set but does not appear in REDIS_URL. "
                "Ensure REDIS_URL includes the password "
                "(e.g., redis://:password@localhost:6379/0) or remove "
                "REDIS_PASSWORD to suppress this warning."
            )

        return self

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
