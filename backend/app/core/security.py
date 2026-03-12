"""
Security utilities for authentication and authorization.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt.exceptions import PyJWTError
from passlib.context import CryptContext

from .config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _get_secret_key() -> str:
    """Return the primary signing key, asserting it is configured."""
    assert settings.SECRET_KEY, "SECRET_KEY must be configured"
    return settings.SECRET_KEY


def _refresh_secret() -> str:
    """Return the signing key for refresh tokens.

    Uses REFRESH_TOKEN_SECRET if configured, otherwise falls back to SECRET_KEY.
    """
    return settings.REFRESH_TOKEN_SECRET or _get_secret_key()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def create_access_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
    additional_claims: dict | None = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: Token subject (usually user ID)
        expires_delta: Custom expiration time
        additional_claims: Additional JWT claims

    Returns:
        Encoded JWT token
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "jti": str(uuid.uuid4()),  # Unique token ID for blacklist support
    }

    if additional_claims:
        to_encode.update(additional_claims)

    encoded_jwt = jwt.encode(to_encode, _get_secret_key(), algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: str | Any) -> str:
    """Create a JWT refresh token with longer expiration.

    Uses a separate signing key (REFRESH_TOKEN_SECRET) when configured,
    so that access-token keys cannot forge refresh tokens and vice-versa.
    """
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh",
        "jti": str(uuid.uuid4()),  # Unique token ID for blacklist support
    }

    encoded_jwt = jwt.encode(to_encode, _refresh_secret(), algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict | None:
    """
    Decode and validate a JWT access token.

    Args:
        token: JWT token string

    Returns:
        Token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, _get_secret_key(), algorithms=[settings.ALGORITHM])
        return payload
    except (PyJWTError, Exception):
        return None


def decode_refresh_token(token: str) -> dict | None:
    """
    Decode and validate a JWT refresh token.

    Uses the dedicated refresh-token signing key (REFRESH_TOKEN_SECRET)
    when configured, otherwise falls back to SECRET_KEY.

    Args:
        token: JWT refresh token string

    Returns:
        Token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, _refresh_secret(), algorithms=[settings.ALGORITHM])
        return payload
    except (PyJWTError, Exception):
        return None
