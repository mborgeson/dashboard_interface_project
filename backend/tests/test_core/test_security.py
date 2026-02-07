"""Tests for core security module."""

from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)

# =============================================================================
# Password Hashing Tests
# =============================================================================


class TestPasswordHashing:
    """Tests for password hashing functionality."""

    def test_get_password_hash_returns_hash(self):
        """Test that get_password_hash returns a hash string."""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert hashed is not None
        assert isinstance(hashed, str)
        assert hashed != password  # Hash should be different from plain password

    def test_get_password_hash_different_for_same_password(self):
        """Test that hashing same password twice produces different hashes (bcrypt salt)."""
        password = "testpassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # Bcrypt uses different salts, so hashes should be different
        assert hash1 != hash2

    def test_verify_password_correct_password(self):
        """Test that verify_password returns True for correct password."""
        password = "testpassword123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect_password(self):
        """Test that verify_password returns False for incorrect password."""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty_password(self):
        """Test verify_password with empty password."""
        password = ""
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True
        assert verify_password("notempty", hashed) is False

    def test_verify_password_special_characters(self):
        """Test password hashing with special characters."""
        password = "p@$$w0rd!#$%^&*()"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_unicode_characters(self):
        """Test password hashing with unicode characters."""
        password = "пароль密码🔐"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True


# =============================================================================
# Access Token Tests
# =============================================================================


class TestAccessToken:
    """Tests for access token creation and validation."""

    def test_create_access_token_returns_string(self):
        """Test that create_access_token returns a JWT string."""
        token = create_access_token(subject="123")

        assert token is not None
        assert isinstance(token, str)
        # JWT format: header.payload.signature
        assert len(token.split(".")) == 3

    def test_create_access_token_contains_subject(self):
        """Test that token contains the correct subject."""
        subject = "user_123"
        token = create_access_token(subject=subject)

        # Decode to verify
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert payload["sub"] == subject

    def test_create_access_token_contains_expiration(self):
        """Test that token contains expiration claim."""
        token = create_access_token(subject="123")

        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert "exp" in payload

    def test_create_access_token_custom_expiration(self):
        """Test token with custom expiration delta."""
        custom_delta = timedelta(hours=2)
        before_creation = datetime.now(UTC)
        token = create_access_token(subject="123", expires_delta=custom_delta)
        after_creation = datetime.now(UTC)

        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        exp_time = datetime.fromtimestamp(payload["exp"], tz=UTC)

        # Expiration should be within the custom delta range
        # JWT exp is in seconds, so we need to account for sub-second timing
        expected_min = (before_creation + custom_delta).replace(
            microsecond=0
        ) - timedelta(seconds=1)
        expected_max = after_creation + custom_delta + timedelta(seconds=2)

        assert exp_time >= expected_min
        assert exp_time <= expected_max

    def test_create_access_token_additional_claims(self):
        """Test token with additional claims."""
        additional_claims = {"role": "admin", "department": "IT"}
        token = create_access_token(subject="123", additional_claims=additional_claims)

        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert payload["role"] == "admin"
        assert payload["department"] == "IT"

    def test_create_access_token_integer_subject(self):
        """Test token with integer subject (should be converted to string)."""
        token = create_access_token(subject=123)

        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert payload["sub"] == "123"

    def test_create_access_token_default_expiration(self):
        """Test token uses default expiration from settings."""
        before_creation = datetime.now(UTC)
        token = create_access_token(subject="123")
        after_creation = datetime.now(UTC)

        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        exp_time = datetime.fromtimestamp(payload["exp"], tz=UTC)

        expected_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        # JWT exp is in seconds, so we need to account for sub-second timing
        expected_min = (before_creation + expected_delta).replace(
            microsecond=0
        ) - timedelta(seconds=1)
        expected_max = after_creation + expected_delta + timedelta(seconds=2)

        assert exp_time >= expected_min
        assert exp_time <= expected_max


# =============================================================================
# Refresh Token Tests
# =============================================================================


class TestRefreshToken:
    """Tests for refresh token creation."""

    def test_create_refresh_token_returns_string(self):
        """Test that create_refresh_token returns a JWT string."""
        token = create_refresh_token(subject="123")

        assert token is not None
        assert isinstance(token, str)
        assert len(token.split(".")) == 3

    def test_create_refresh_token_contains_type(self):
        """Test that refresh token contains type claim."""
        token = create_refresh_token(subject="123")

        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert payload.get("type") == "refresh"

    def test_create_refresh_token_contains_subject(self):
        """Test that refresh token contains the correct subject."""
        subject = "user_456"
        token = create_refresh_token(subject=subject)

        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert payload["sub"] == subject

    def test_create_refresh_token_longer_expiration(self):
        """Test that refresh token has longer expiration than access token."""
        access_token = create_access_token(subject="123")
        refresh_token = create_refresh_token(subject="123")

        access_payload = jwt.decode(
            access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        refresh_payload = jwt.decode(
            refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        # Refresh token should expire later than access token
        assert refresh_payload["exp"] > access_payload["exp"]


# =============================================================================
# Token Decode Tests
# =============================================================================


class TestDecodeToken:
    """Tests for token decoding functionality."""

    def test_decode_valid_access_token(self):
        """Test decoding a valid access token."""
        subject = "user_789"
        token = create_access_token(subject=subject)

        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == subject

    def test_decode_valid_refresh_token(self):
        """Test decoding a valid refresh token."""
        subject = "user_789"
        token = create_refresh_token(subject=subject)

        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == subject
        assert payload["type"] == "refresh"

    def test_decode_invalid_token(self):
        """Test decoding an invalid token returns None."""
        invalid_token = "invalid.token.string"

        payload = decode_token(invalid_token)

        assert payload is None

    def test_decode_tampered_token(self):
        """Test decoding a tampered token returns None."""
        token = create_access_token(subject="123")
        # Tamper with the token
        parts = token.split(".")
        tampered_token = f"{parts[0]}.modified{parts[1]}.{parts[2]}"

        payload = decode_token(tampered_token)

        assert payload is None

    def test_decode_expired_token(self):
        """Test decoding an expired token returns None."""
        # Create token that expires immediately
        expired_delta = timedelta(seconds=-1)  # Already expired
        token = create_access_token(subject="123", expires_delta=expired_delta)

        # Tokens created with negative delta are already expired
        # We need to create a valid one, then wait - but that's slow
        # Instead, we can check that expired tokens fail validation
        # The token was created with exp in the past
        payload = decode_token(token)

        assert payload is None

    def test_decode_token_wrong_algorithm(self):
        """Test that token with wrong algorithm fails."""
        # Create a token with a different (but valid) algorithm
        to_encode = {"sub": "123", "exp": datetime.now(UTC) + timedelta(hours=1)}
        # This creates a token that won't decode with our expected algorithm
        wrong_token = jwt.encode(to_encode, "different_secret", algorithm="HS256")

        payload = decode_token(wrong_token)

        assert payload is None

    def test_decode_empty_token(self):
        """Test decoding empty string returns None."""
        payload = decode_token("")

        assert payload is None

    def test_decode_token_with_additional_claims(self):
        """Test decoding token preserves additional claims."""
        claims = {"role": "admin", "permissions": ["read", "write"]}
        token = create_access_token(subject="123", additional_claims=claims)

        payload = decode_token(token)

        assert payload is not None
        assert payload["role"] == "admin"
        assert payload["permissions"] == ["read", "write"]
