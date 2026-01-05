"""
Authentication schemas for login, tokens, and session management.
"""

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Login request with email and password."""

    email: EmailStr
    password: str


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

    refresh_token: str


class PasswordResetRequest(BaseModel):
    """Request to reset password."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Confirm password reset with token."""

    token: str
    new_password: str


class PasswordChange(BaseModel):
    """Change password for authenticated user."""

    current_password: str
    new_password: str
