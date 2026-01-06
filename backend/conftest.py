"""
Root conftest.py for pytest configuration.

This file runs before any test imports, allowing us to set environment
variables that affect the application configuration.
"""
import os

# Set high rate limits for testing BEFORE any app imports
# This ensures rate limiting doesn't interfere with tests
os.environ["RATE_LIMIT_REQUESTS"] = "10000"
os.environ["RATE_LIMIT_AUTH_REQUESTS"] = "10000"
os.environ["RATE_LIMIT_WINDOW"] = "60"
os.environ["RATE_LIMIT_AUTH_WINDOW"] = "60"

# Force pydantic-settings to reload settings when app imports
# by clearing any cached settings

# Clear the settings cache if it exists
try:
    from app.core import config
    if hasattr(config, 'get_settings'):
        config.get_settings.cache_clear()
except ImportError:
    pass  # App not yet importable, which is fine
