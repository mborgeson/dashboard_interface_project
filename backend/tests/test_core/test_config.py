"""Tests for core configuration module."""
import os

import pytest

from app.core.config import Settings, get_settings, settings

# =============================================================================
# Settings Class Tests
# =============================================================================


class TestSettings:
    """Tests for Settings configuration class."""

    def test_settings_loads_defaults(self):
        """Test that settings loads with default values."""
        assert settings is not None
        assert isinstance(settings, Settings)

    def test_settings_app_name(self):
        """Test APP_NAME default value."""
        assert settings.APP_NAME == "B&R Capital Dashboard API"

    def test_settings_app_version(self):
        """Test APP_VERSION is set."""
        assert settings.APP_VERSION is not None
        assert isinstance(settings.APP_VERSION, str)

    def test_settings_environment(self):
        """Test ENVIRONMENT default value."""
        assert settings.ENVIRONMENT in ["development", "staging", "production", "testing"]

    def test_settings_debug_is_boolean(self):
        """Test DEBUG is a boolean value."""
        assert isinstance(settings.DEBUG, bool)

    def test_settings_server_config(self):
        """Test server configuration defaults."""
        assert settings.HOST == "0.0.0.0"
        assert settings.PORT == 8000
        assert settings.WORKERS >= 1

    def test_settings_security_config(self):
        """Test security configuration."""
        assert settings.SECRET_KEY is not None
        # In testing environment, allow shorter keys; production requires >= 32 chars
        if settings.ENVIRONMENT == "testing":
            assert len(settings.SECRET_KEY) >= 16
        else:
            assert len(settings.SECRET_KEY) >= 32
        assert settings.ALGORITHM == "HS256"
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS > 0

    def test_settings_cors_origins(self):
        """Test CORS origins configuration."""
        assert isinstance(settings.CORS_ORIGINS, list)
        assert len(settings.CORS_ORIGINS) > 0
        # Should contain localhost for development
        assert any("localhost" in origin for origin in settings.CORS_ORIGINS)

    def test_settings_database_config(self):
        """Test database configuration."""
        assert settings.DATABASE_URL is not None
        # Allow sqlite for testing, postgresql for other environments
        assert "postgresql" in settings.DATABASE_URL or "sqlite" in settings.DATABASE_URL
        assert settings.DATABASE_POOL_SIZE > 0
        assert settings.DATABASE_MAX_OVERFLOW >= 0
        assert settings.DATABASE_POOL_TIMEOUT > 0

    def test_settings_redis_config(self):
        """Test Redis configuration."""
        assert settings.REDIS_URL is not None
        assert "redis://" in settings.REDIS_URL
        assert settings.REDIS_CACHE_TTL > 0
        assert settings.REDIS_MAX_CONNECTIONS > 0

    def test_settings_email_config(self):
        """Test email configuration."""
        assert settings.SMTP_HOST is not None
        assert settings.SMTP_PORT > 0
        assert settings.EMAIL_FROM_NAME is not None
        assert settings.EMAIL_RATE_LIMIT > 0

    def test_settings_websocket_config(self):
        """Test WebSocket configuration."""
        assert settings.WS_HEARTBEAT_INTERVAL > 0
        assert settings.WS_MAX_CONNECTIONS > 0

    def test_settings_ml_config(self):
        """Test ML model configuration."""
        assert settings.ML_MODEL_PATH is not None
        assert settings.ML_BATCH_SIZE > 0
        assert settings.ML_PREDICTION_CACHE_TTL > 0

    def test_settings_logging_config(self):
        """Test logging configuration."""
        assert settings.LOG_LEVEL in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert settings.LOG_FORMAT is not None


# =============================================================================
# Database URL Property Tests
# =============================================================================


class TestDatabaseUrlProperty:
    """Tests for database_url_async property."""

    def test_database_url_async_conversion(self):
        """Test that async URL is properly converted."""
        async_url = settings.database_url_async

        # Allow sqlite for testing, postgresql+asyncpg for other environments
        if "sqlite" in settings.DATABASE_URL:
            assert "sqlite" in async_url
        else:
            assert "postgresql+asyncpg://" in async_url
            assert "postgresql://" not in async_url

    def test_database_url_async_preserves_credentials(self):
        """Test that async URL preserves database credentials."""
        sync_url = settings.DATABASE_URL
        async_url = settings.database_url_async

        # Skip credential check for SQLite (no credentials to preserve)
        if "sqlite" in sync_url:
            assert "sqlite" in async_url
            return

        # Extract everything after the protocol
        sync_rest = sync_url.replace("postgresql://", "")
        async_rest = async_url.replace("postgresql+asyncpg://", "")

        # The rest should be identical
        assert sync_rest == async_rest


# =============================================================================
# Settings Cache Tests
# =============================================================================


class TestSettingsCache:
    """Tests for settings caching behavior."""

    def test_get_settings_returns_same_instance(self):
        """Test that get_settings returns cached instance."""
        settings1 = get_settings()
        settings2 = get_settings()

        # Should return the same cached instance
        assert settings1 is settings2

    def test_settings_module_level_instance(self):
        """Test that module-level settings is a Settings instance."""
        from app.core.config import settings as module_settings

        # Module-level settings should be a Settings instance
        assert isinstance(module_settings, Settings)
        # Both should have the same configuration values
        assert module_settings.APP_NAME == get_settings().APP_NAME


# =============================================================================
# Settings Type Tests
# =============================================================================


class TestSettingsTypes:
    """Tests for settings value types."""

    def test_integer_settings_are_integers(self):
        """Test that integer settings are actually integers."""
        assert isinstance(settings.PORT, int)
        assert isinstance(settings.WORKERS, int)
        assert isinstance(settings.ACCESS_TOKEN_EXPIRE_MINUTES, int)
        assert isinstance(settings.REFRESH_TOKEN_EXPIRE_DAYS, int)
        assert isinstance(settings.DATABASE_POOL_SIZE, int)
        assert isinstance(settings.REDIS_CACHE_TTL, int)

    def test_string_settings_are_strings(self):
        """Test that string settings are actually strings."""
        assert isinstance(settings.APP_NAME, str)
        assert isinstance(settings.APP_VERSION, str)
        assert isinstance(settings.SECRET_KEY, str)
        assert isinstance(settings.ALGORITHM, str)
        assert isinstance(settings.DATABASE_URL, str)

    def test_boolean_settings_are_booleans(self):
        """Test that boolean settings are actually booleans."""
        assert isinstance(settings.DEBUG, bool)
        assert isinstance(settings.EMAIL_DEV_MODE, bool)

    def test_list_settings_are_lists(self):
        """Test that list settings are actually lists."""
        assert isinstance(settings.CORS_ORIGINS, list)


# =============================================================================
# Settings Boundary Tests
# =============================================================================


class TestSettingsBoundaries:
    """Tests for settings value boundaries."""

    def test_access_token_expiry_reasonable(self):
        """Test access token expiry is within reasonable bounds."""
        # Should be at least 1 minute and at most 24 hours
        assert 1 <= settings.ACCESS_TOKEN_EXPIRE_MINUTES <= 1440

    def test_refresh_token_expiry_reasonable(self):
        """Test refresh token expiry is within reasonable bounds."""
        # Should be at least 1 day and at most 365 days
        assert 1 <= settings.REFRESH_TOKEN_EXPIRE_DAYS <= 365

    def test_pool_size_reasonable(self):
        """Test database pool size is within reasonable bounds."""
        assert 1 <= settings.DATABASE_POOL_SIZE <= 100

    def test_port_valid_range(self):
        """Test port is in valid range."""
        assert 1 <= settings.PORT <= 65535
