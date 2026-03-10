"""
Tests for WebSocket token blacklist validation (F-004).

Verifies that revoked JWT tokens are rejected during WebSocket authentication.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from jose import jwt

from app.api.v1.endpoints.ws import _authenticate_token
from app.core.config import settings


def _make_token(sub: int = 1, jti: str | None = None) -> str:
    """Create a valid JWT token for testing."""
    payload = {"sub": str(sub)}
    if jti is not None:
        payload["jti"] = jti
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


class TestWebSocketBlacklistCheck:
    """Tests for blacklist checking in WebSocket token authentication."""

    @pytest.mark.asyncio
    async def test_valid_token_returns_user_id(self):
        """A valid, non-blacklisted token returns the user ID."""
        token = _make_token(sub=42, jti=str(uuid.uuid4()))
        result = await _authenticate_token(token)
        assert result == 42

    @pytest.mark.asyncio
    async def test_blacklisted_token_returns_none(self):
        """A blacklisted token is rejected (returns None)."""
        jti = str(uuid.uuid4())
        token = _make_token(sub=42, jti=jti)

        with patch(
            "app.api.v1.endpoints.ws.token_blacklist.is_blacklisted",
            new_callable=AsyncMock,
            return_value=True,
        ):
            result = await _authenticate_token(token)

        assert result is None

    @pytest.mark.asyncio
    async def test_non_blacklisted_token_accepted(self):
        """A token whose jti is NOT in the blacklist is accepted."""
        jti = str(uuid.uuid4())
        token = _make_token(sub=7, jti=jti)

        with patch(
            "app.api.v1.endpoints.ws.token_blacklist.is_blacklisted",
            new_callable=AsyncMock,
            return_value=False,
        ):
            result = await _authenticate_token(token)

        assert result == 7

    @pytest.mark.asyncio
    async def test_blacklist_service_error_fails_closed(self):
        """If the blacklist service raises, we fail closed (reject the token)."""
        jti = str(uuid.uuid4())
        token = _make_token(sub=42, jti=jti)

        with patch(
            "app.api.v1.endpoints.ws.token_blacklist.is_blacklisted",
            new_callable=AsyncMock,
            side_effect=Exception("Redis unavailable"),
        ):
            result = await _authenticate_token(token)

        assert result is None

    @pytest.mark.asyncio
    async def test_token_without_jti_still_works(self):
        """Tokens without a jti skip the blacklist check (backwards compat)."""
        token = _make_token(sub=10)  # no jti
        result = await _authenticate_token(token)
        assert result == 10

    @pytest.mark.asyncio
    async def test_no_token_returns_none(self):
        """No token at all returns None (anonymous)."""
        result = await _authenticate_token(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_token_returns_none(self):
        """An invalid/corrupt token returns None."""
        result = await _authenticate_token("not.a.valid.jwt")
        assert result is None
