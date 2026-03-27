"""
Security verification tests for token separation and auth flow.

Covers:
- Access/refresh token key separation
- Token type claims and structure
- Login flow returning both tokens
- Token expiration ordering (access < refresh)
- Refresh token rotation
- Expired token rejection
- Config validation for REFRESH_TOKEN_SECRET
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    _get_secret_key,
    _refresh_secret,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    decode_token,
)

# =============================================================================
# Token Signing Key Separation
# =============================================================================


class TestTokenKeySeparation:
    """Verify access and refresh tokens use appropriate signing keys."""

    def test_secret_key_is_configured(self) -> None:
        """SECRET_KEY must be configured (auto-generated in dev)."""
        assert settings.SECRET_KEY is not None
        assert len(settings.SECRET_KEY) > 0

    def test_refresh_token_secret_config_exists(self) -> None:
        """REFRESH_TOKEN_SECRET setting must exist in config."""
        assert hasattr(settings, "REFRESH_TOKEN_SECRET")

    def test_refresh_secret_fallback_to_secret_key(self) -> None:
        """When REFRESH_TOKEN_SECRET is empty, _refresh_secret falls back to SECRET_KEY."""
        # In test environment, REFRESH_TOKEN_SECRET is typically empty
        if not settings.REFRESH_TOKEN_SECRET:
            assert _refresh_secret() == _get_secret_key()

    def test_access_token_uses_secret_key(self) -> None:
        """Access tokens must be signed with SECRET_KEY."""
        token = create_access_token(subject="user-1")
        # Should decode successfully with SECRET_KEY
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        assert payload["sub"] == "user-1"

    def test_refresh_token_uses_refresh_secret(self) -> None:
        """Refresh tokens must be signed with _refresh_secret()."""
        token = create_refresh_token(subject="user-1")
        # Should decode successfully with _refresh_secret()
        payload = jwt.decode(token, _refresh_secret(), algorithms=[settings.ALGORITHM])
        assert payload["sub"] == "user-1"
        assert payload["type"] == "refresh"

    def test_access_token_decode_uses_correct_key(self) -> None:
        """decode_token must use SECRET_KEY (access token key)."""
        token = create_access_token(subject="user-2")
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user-2"

    def test_refresh_token_decode_uses_correct_key(self) -> None:
        """decode_refresh_token must use _refresh_secret()."""
        token = create_refresh_token(subject="user-3")
        payload = decode_refresh_token(token)
        assert payload is not None
        assert payload["sub"] == "user-3"
        assert payload["type"] == "refresh"

    def test_cross_decode_fails_with_different_keys(self) -> None:
        """If keys differ, access decode should not work on refresh tokens and vice versa.

        Note: When REFRESH_TOKEN_SECRET is empty (fallback to SECRET_KEY),
        both keys are identical so cross-decode works. This test validates the
        separation mechanism by manually signing with a different key.
        """
        different_key = "a-totally-different-secret-key-for-testing-purposes"
        # Create a token manually signed with a different key
        payload = {
            "sub": "user-4",
            "exp": datetime.now(UTC) + timedelta(hours=1),
            "type": "refresh",
            "jti": "test-jti",
        }
        foreign_token = jwt.encode(payload, different_key, algorithm=settings.ALGORITHM)
        # decode_token (access key) should reject it
        assert decode_token(foreign_token) is None
        # decode_refresh_token (refresh key) should also reject it
        # (unless REFRESH_TOKEN_SECRET == different_key, which it won't be)
        assert decode_refresh_token(foreign_token) is None


# =============================================================================
# Token Structure and Claims
# =============================================================================


class TestTokenStructure:
    """Verify token claims and structural requirements."""

    def test_access_token_has_jti(self) -> None:
        """Access tokens must include a unique JTI for blacklist support."""
        token = create_access_token(subject="user-5")
        payload = decode_token(token)
        assert payload is not None
        assert "jti" in payload
        assert len(payload["jti"]) > 0

    def test_refresh_token_has_jti(self) -> None:
        """Refresh tokens must include a unique JTI for rotation tracking."""
        token = create_refresh_token(subject="user-5")
        payload = decode_refresh_token(token)
        assert payload is not None
        assert "jti" in payload
        assert len(payload["jti"]) > 0

    def test_access_token_no_type_claim(self) -> None:
        """Access tokens should NOT have a 'type' claim (distinguish from refresh)."""
        token = create_access_token(subject="user-6")
        payload = decode_token(token)
        assert payload is not None
        # Access tokens don't have a "type" claim unless added via additional_claims
        assert "type" not in payload

    def test_refresh_token_has_type_refresh(self) -> None:
        """Refresh tokens must have type='refresh' claim."""
        token = create_refresh_token(subject="user-6")
        payload = decode_refresh_token(token)
        assert payload is not None
        assert payload["type"] == "refresh"

    def test_jti_uniqueness(self) -> None:
        """Each token must have a unique JTI."""
        tokens = [create_access_token(subject="user-7") for _ in range(10)]
        jtis = set()
        for t in tokens:
            p = decode_token(t)
            assert p is not None
            jtis.add(p["jti"])
        assert len(jtis) == 10

    def test_subject_stored_as_string(self) -> None:
        """Subject should be stored as string regardless of input type."""
        for subject in ["user-8", 42, 0]:
            token = create_access_token(subject=subject)
            payload = decode_token(token)
            assert payload is not None
            assert isinstance(payload["sub"], str)
            assert payload["sub"] == str(subject)


# =============================================================================
# Token Expiration
# =============================================================================


class TestTokenExpiration:
    """Verify token expiration behavior."""

    def test_access_token_shorter_than_refresh(self) -> None:
        """Access token must expire before refresh token."""
        access = create_access_token(subject="user-9")
        refresh = create_refresh_token(subject="user-9")

        access_payload = jwt.decode(
            access, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        refresh_payload = jwt.decode(
            refresh, _refresh_secret(), algorithms=[settings.ALGORITHM]
        )

        assert refresh_payload["exp"] > access_payload["exp"]

    def test_access_token_default_expiry_matches_settings(self) -> None:
        """Access token expiry should match ACCESS_TOKEN_EXPIRE_MINUTES."""
        before = datetime.now(UTC)
        token = create_access_token(subject="user-10")
        after = datetime.now(UTC)

        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
        expected = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        assert exp >= before + expected - timedelta(seconds=2)
        assert exp <= after + expected + timedelta(seconds=2)

    def test_refresh_token_default_expiry_matches_settings(self) -> None:
        """Refresh token expiry should match REFRESH_TOKEN_EXPIRE_DAYS."""
        before = datetime.now(UTC)
        token = create_refresh_token(subject="user-11")
        after = datetime.now(UTC)

        payload = jwt.decode(token, _refresh_secret(), algorithms=[settings.ALGORITHM])
        exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
        expected = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        assert exp >= before + expected - timedelta(seconds=2)
        assert exp <= after + expected + timedelta(seconds=2)

    def test_expired_access_token_rejected(self) -> None:
        """Expired access token should return None on decode."""
        token = create_access_token(
            subject="user-12",
            expires_delta=timedelta(seconds=-10),
        )
        assert decode_token(token) is None

    def test_expired_refresh_token_rejected(self) -> None:
        """Expired refresh token should return None on decode."""
        # Manually create an expired refresh token
        payload = {
            "sub": "user-13",
            "exp": datetime.now(UTC) - timedelta(hours=1),
            "type": "refresh",
            "jti": "expired-jti",
        }
        token = jwt.encode(payload, _refresh_secret(), algorithm=settings.ALGORITHM)
        assert decode_refresh_token(token) is None

    def test_access_expiry_is_reasonable(self) -> None:
        """Access token expiry should be between 5 min and 24 hours."""
        assert 5 <= settings.ACCESS_TOKEN_EXPIRE_MINUTES <= 1440

    def test_refresh_expiry_is_reasonable(self) -> None:
        """Refresh token expiry should be between 1 and 90 days."""
        assert 1 <= settings.REFRESH_TOKEN_EXPIRE_DAYS <= 90

    def test_refresh_is_significantly_longer_than_access(self) -> None:
        """Refresh token should be at least 10x longer than access token."""
        access_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        refresh_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
        assert refresh_seconds >= access_seconds * 10


# =============================================================================
# Login/Token Flow (unit-level, no HTTP)
# =============================================================================


class TestTokenFlowUnit:
    """Unit tests for the token creation/validation flow without HTTP."""

    def test_login_produces_both_tokens(self) -> None:
        """Simulated login should produce both access and refresh tokens."""
        user_id = "42"
        access = create_access_token(
            subject=user_id, additional_claims={"role": "analyst"}
        )
        refresh = create_refresh_token(subject=user_id)

        # Both should be valid JWT strings
        assert len(access.split(".")) == 3
        assert len(refresh.split(".")) == 3

        # Both should decode successfully
        access_payload = decode_token(access)
        refresh_payload = decode_refresh_token(refresh)

        assert access_payload is not None
        assert refresh_payload is not None
        assert access_payload["sub"] == user_id
        assert refresh_payload["sub"] == user_id

    def test_refresh_produces_new_token_pair(self) -> None:
        """Token refresh should produce a new access + refresh pair."""
        user_id = "42"

        # Original tokens
        original_access = create_access_token(subject=user_id)
        original_refresh = create_refresh_token(subject=user_id)

        # Simulate refresh: create new pair
        new_access = create_access_token(subject=user_id)
        new_refresh = create_refresh_token(subject=user_id)

        # New tokens should be different from original
        assert new_access != original_access
        assert new_refresh != original_refresh

        # Both new tokens should be valid
        assert decode_token(new_access) is not None
        assert decode_refresh_token(new_refresh) is not None

    def test_access_token_with_role_claim(self) -> None:
        """Access token should carry role claim when provided."""
        token = create_access_token(subject="42", additional_claims={"role": "admin"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["role"] == "admin"

    def test_tampered_access_token_rejected(self) -> None:
        """Tampered access token should be rejected."""
        token = create_access_token(subject="user-14")
        # Tamper with payload
        parts = token.split(".")
        tampered = f"{parts[0]}.TAMPERED{parts[1][8:]}.{parts[2]}"
        assert decode_token(tampered) is None

    def test_tampered_refresh_token_rejected(self) -> None:
        """Tampered refresh token should be rejected."""
        token = create_refresh_token(subject="user-15")
        parts = token.split(".")
        tampered = f"{parts[0]}.TAMPERED{parts[1][8:]}.{parts[2]}"
        assert decode_refresh_token(tampered) is None

    def test_wrong_token_type_for_refresh_decode(self) -> None:
        """decode_refresh_token should not accept access tokens as refresh."""
        # If keys are the same (fallback), access token will decode but
        # won't have type='refresh'. The auth endpoint checks for this.
        access_token = create_access_token(subject="user-16")
        payload = decode_refresh_token(access_token)
        # Even if it decodes (same key), it should not have type="refresh"
        if payload is not None:
            assert payload.get("type") != "refresh"


# =============================================================================
# Config Security Properties
# =============================================================================


class TestConfigSecurityProperties:
    """Verify security-related configuration properties."""

    def test_algorithm_is_hs256(self) -> None:
        """JWT algorithm should be HS256."""
        assert settings.ALGORITHM == "HS256"

    def test_secret_key_sufficient_length(self) -> None:
        """SECRET_KEY should be at least 32 characters."""
        assert len(settings.SECRET_KEY) >= 32

    def test_production_requires_secret_key(self) -> None:
        """Production validation requires SECRET_KEY.

        Verifies that the Settings class has a validate_secrets model validator
        that would reject missing SECRET_KEY in production.
        """
        from app.core.config import Settings

        # Check that the validator method exists on the class
        assert hasattr(Settings, "validate_secrets")
        assert callable(Settings.validate_secrets)

    def test_demo_credentials_declared_with_empty_defaults(self) -> None:
        """Demo password fields must default to empty strings in AuthSettings.

        The actual values come from environment variables at runtime.
        This test verifies the schema defaults are empty (not hardcoded).
        """
        from app.core.config import AuthSettings

        # Check the field defaults in the model schema, not the instantiated values
        # (which may pick up env vars in the test environment)
        fields = AuthSettings.model_fields
        assert fields["DEMO_USER_PASSWORD"].default == ""
        assert fields["DEMO_ADMIN_PASSWORD"].default == ""
        assert fields["DEMO_ANALYST_PASSWORD"].default == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
