"""
Authentication schemas for login, tokens, and session management.
"""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Login request with email and password."""

    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenPayload(BaseModel):
    """JWT token payload data."""

    sub: str  # User ID
    exp: int  # Expiration timestamp
    type: str | None = None  # "access" or "refresh"


class RefreshTokenRequest(BaseModel):
    """Request to refresh access token."""

    refresh_token: str = Field(..., min_length=1)


class PasswordResetRequest(BaseModel):
    """Request to reset password."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Confirm password reset with token."""

    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)


class PasswordChange(BaseModel):
    """Change password for authenticated user."""

    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)
