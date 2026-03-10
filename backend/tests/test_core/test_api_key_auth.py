"""Tests for API key authentication (service-to-service calls)."""

from unittest.mock import patch

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.api_key_auth import (
    ServiceIdentity,
    require_api_key,
    require_api_key_or_jwt,
    verify_api_key,
)
from app.core.security import create_access_token

# ---------------------------------------------------------------------------
# Test app — isolated from the main app so we don't touch existing endpoints
# ---------------------------------------------------------------------------

_test_app = FastAPI()


@_test_app.get("/api-key-only")
async def api_key_only_endpoint(
    identity: ServiceIdentity = Depends(require_api_key),
):
    return {"service": identity.service_name, "is_service": identity.is_service}


@_test_app.get("/either-auth")
async def either_auth_endpoint(
    auth=Depends(require_api_key_or_jwt),
):
    if isinstance(auth, ServiceIdentity):
        return {"auth_type": "api_key", "service": auth.service_name}
    return {"auth_type": "jwt", "user_id": auth.id, "email": auth.email}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_KEY = "test-api-key-abc123"
VALID_KEY_2 = "test-api-key-def456"


@pytest.fixture
def configured_keys():
    """Patch settings.API_KEYS to include test keys."""
    with patch("app.core.api_key_auth.settings") as mock_settings:
        mock_settings.API_KEYS = [VALID_KEY, VALID_KEY_2]
        mock_settings.API_KEY_HEADER = "X-API-Key"
        yield mock_settings


@pytest.fixture
def no_keys():
    """Patch settings.API_KEYS to be empty (API key auth disabled)."""
    with patch("app.core.api_key_auth.settings") as mock_settings:
        mock_settings.API_KEYS = []
        mock_settings.API_KEY_HEADER = "X-API-Key"
        yield mock_settings


@pytest.fixture
async def test_client():
    transport = ASGITransport(app=_test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# verify_api_key / require_api_key tests
# ---------------------------------------------------------------------------


class TestVerifyApiKey:
    """Tests for the verify_api_key dependency."""

    async def test_valid_api_key(self, test_client: AsyncClient, configured_keys):
        """Valid API key should authenticate successfully."""
        resp = await test_client.get(
            "/api-key-only",
            headers={"X-API-Key": VALID_KEY},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == "api_key_service"
        assert data["is_service"] is True

    async def test_valid_second_key(self, test_client: AsyncClient, configured_keys):
        """Any configured key should be accepted."""
        resp = await test_client.get(
            "/api-key-only",
            headers={"X-API-Key": VALID_KEY_2},
        )
        assert resp.status_code == 200

    async def test_invalid_api_key(self, test_client: AsyncClient, configured_keys):
        """Invalid API key should return 401."""
        resp = await test_client.get(
            "/api-key-only",
            headers={"X-API-Key": "wrong-key"},
        )
        assert resp.status_code == 401
        assert "Invalid API key" in resp.json()["detail"]

    async def test_missing_api_key_header(
        self, test_client: AsyncClient, configured_keys
    ):
        """Missing X-API-Key header should return 401."""
        resp = await test_client.get("/api-key-only")
        assert resp.status_code == 401
        assert "Missing API key" in resp.json()["detail"]

    async def test_empty_api_key_header(
        self, test_client: AsyncClient, configured_keys
    ):
        """Empty X-API-Key header should return 401."""
        resp = await test_client.get(
            "/api-key-only",
            headers={"X-API-Key": ""},
        )
        assert resp.status_code == 401

    async def test_disabled_when_no_keys_configured(
        self, test_client: AsyncClient, no_keys
    ):
        """When API_KEYS is empty, API key auth is disabled — returns 401."""
        resp = await test_client.get(
            "/api-key-only",
            headers={"X-API-Key": "any-key"},
        )
        assert resp.status_code == 401
        assert "not configured" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# require_api_key_or_jwt tests
# ---------------------------------------------------------------------------


class TestRequireApiKeyOrJwt:
    """Tests for the combined API key / JWT dependency."""

    async def test_valid_api_key(self, test_client: AsyncClient, configured_keys):
        """API key should work on combined endpoints."""
        resp = await test_client.get(
            "/either-auth",
            headers={"X-API-Key": VALID_KEY},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["auth_type"] == "api_key"

    async def test_valid_jwt(self, test_client: AsyncClient, configured_keys):
        """JWT Bearer token should work on combined endpoints."""
        token = create_access_token(
            subject="42",
            additional_claims={"email": "svc@test.com", "role": "admin"},
        )
        resp = await test_client.get(
            "/either-auth",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["auth_type"] == "jwt"
        assert data["user_id"] == 42
        assert data["email"] == "svc@test.com"

    async def test_jwt_takes_precedence(
        self, test_client: AsyncClient, configured_keys
    ):
        """When both headers are present, JWT is checked first."""
        token = create_access_token(
            subject="7",
            additional_claims={"email": "user@test.com", "role": "analyst"},
        )
        resp = await test_client.get(
            "/either-auth",
            headers={
                "Authorization": f"Bearer {token}",
                "X-API-Key": VALID_KEY,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["auth_type"] == "jwt"

    async def test_neither_auth_method(self, test_client: AsyncClient, configured_keys):
        """No auth headers at all should return 401."""
        resp = await test_client.get("/either-auth")
        assert resp.status_code == 401

    async def test_invalid_jwt_falls_back_to_api_key(
        self, test_client: AsyncClient, configured_keys
    ):
        """Invalid JWT should fall back to API key check."""
        resp = await test_client.get(
            "/either-auth",
            headers={
                "Authorization": "Bearer invalid-token",
                "X-API-Key": VALID_KEY,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["auth_type"] == "api_key"

    async def test_both_invalid(self, test_client: AsyncClient, configured_keys):
        """Invalid JWT + invalid API key should return 401."""
        resp = await test_client.get(
            "/either-auth",
            headers={
                "Authorization": "Bearer invalid-token",
                "X-API-Key": "wrong-key",
            },
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# ServiceIdentity tests
# ---------------------------------------------------------------------------


class TestServiceIdentity:
    """Tests for the ServiceIdentity dataclass."""

    def test_frozen(self):
        """ServiceIdentity should be immutable."""
        identity = ServiceIdentity(service_name="test")
        with pytest.raises(AttributeError):
            identity.service_name = "changed"  # type: ignore[misc]

    def test_defaults(self):
        identity = ServiceIdentity(service_name="webhook")
        assert identity.is_service is True
        assert identity.service_name == "webhook"
