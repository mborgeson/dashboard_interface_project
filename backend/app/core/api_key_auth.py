"""API Key authentication for service-to-service calls.

Provides FastAPI dependencies for validating API keys passed via
the X-API-Key header. Designed as an alternative to JWT auth for
external services and webhooks calling into the API.

Usage:
    @router.post("/webhook", dependencies=[Depends(require_api_key)])
    async def webhook_handler(identity: ServiceIdentity = Depends(verify_api_key)):
        ...

    @router.get("/data")
    async def data_endpoint(
        auth: CurrentUser | ServiceIdentity = Depends(require_api_key_or_jwt),
    ):
        ...
"""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from loguru import logger

from app.core.config import settings
from app.core.security import decode_token

if TYPE_CHECKING:
    from app.core.permissions import CurrentUser

# Reuse the same scheme as permissions.py — auto_error=False so we can
# fall back to API key auth without raising immediately on missing Bearer token.
_oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login", auto_error=False
)


@dataclass(frozen=True)
class ServiceIdentity:
    """Represents an authenticated service caller (via API key)."""

    service_name: str
    """Descriptive name — currently 'api_key_service' for all key-based callers."""

    is_service: bool = True
    """Always True; distinguishes from human CurrentUser objects."""


def _validate_api_key(provided_key: str) -> bool:
    """Check provided key against configured keys using constant-time comparison.

    Returns True if the key matches any configured key, False otherwise.
    """
    for valid_key in settings.API_KEYS:
        if hmac.compare_digest(provided_key.encode("utf-8"), valid_key.encode("utf-8")):
            return True
    return False


async def verify_api_key(request: Request) -> ServiceIdentity:
    """FastAPI dependency: validate the X-API-Key header.

    Raises:
        HTTPException 401: If API key auth is disabled (no keys configured),
            the header is missing, or the key is invalid.
    """
    if not settings.API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key authentication is not configured",
        )

    api_key = request.headers.get(settings.API_KEY_HEADER)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not _validate_api_key(api_key):
        logger.warning(
            f"Invalid API key attempt from {request.client.host if request.client else 'unknown'}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return ServiceIdentity(service_name="api_key_service")


# Alias for use as a simple dependency guard
require_api_key = verify_api_key


async def require_api_key_or_jwt(
    request: Request,
    token: str | None = Depends(_oauth2_scheme_optional),
) -> CurrentUser | ServiceIdentity:
    """FastAPI dependency: accept either a valid JWT Bearer token or API key.

    Tries JWT first (if an Authorization header is present), then falls back
    to API key validation.  If neither succeeds, raises 401.

    Returns:
        CurrentUser (from JWT) or ServiceIdentity (from API key).
    """
    # --- Attempt JWT auth first ---
    if token is not None:
        payload = decode_token(token)
        if payload is not None:
            user_id = payload.get("sub")
            if user_id is not None:
                # Import here to avoid circular dependency with permissions.py
                from app.core.permissions import CurrentUser, Role

                role_str = payload.get("role", "viewer")
                try:
                    role = Role(role_str)
                except ValueError:
                    role = Role.VIEWER

                return CurrentUser(
                    id=int(user_id),
                    email=payload.get("email", ""),
                    role=role,
                    full_name=payload.get("full_name"),
                    is_active=True,
                )

    # --- Fall back to API key ---
    if settings.API_KEYS:
        api_key = request.headers.get(settings.API_KEY_HEADER)
        if api_key and _validate_api_key(api_key):
            return ServiceIdentity(service_name="api_key_service")

    # Neither auth method succeeded
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Valid JWT token or API key required",
        headers={"WWW-Authenticate": "Bearer, ApiKey"},
    )
