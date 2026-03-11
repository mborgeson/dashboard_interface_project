"""
Security test fixtures and helpers.

Provides common payloads, auth utilities, and a helper for testing
multiple attack payloads against an endpoint.
"""

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from jose import jwt

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.core.token_blacklist import token_blacklist
from app.models import User


# =============================================================================
# Common SQL injection payloads
# =============================================================================

SQL_INJECTION_PAYLOADS = [
    "' OR 1=1 --",
    "'; DROP TABLE properties; --",
    "' UNION SELECT 1,2,3 --",
    "1; DELETE FROM users --",
    "' OR ''='",
    "admin'--",
    "') OR ('1'='1",
    "1' ORDER BY 1--+",
    "' UNION ALL SELECT NULL,NULL,NULL--",
    "' AND 1=CONVERT(int, (SELECT @@version))--",
    "'; EXEC xp_cmdshell('whoami')--",
    "1 OR 1=1",
    "' OR '1'='1' /*",
    "'; WAITFOR DELAY '0:0:5'--",
]

# =============================================================================
# Common XSS payloads
# =============================================================================

XSS_PAYLOADS = [
    "<script>alert('xss')</script>",
    '<img src=x onerror="alert(1)">',
    "javascript:alert(1)",
    "<svg onload=alert(1)>",
    '"><script>alert(document.cookie)</script>',
    "'-alert(1)-'",
    "<iframe src='javascript:alert(1)'>",
    '"><img src=x onerror=alert(1)//',
    "${7*7}",
    "{{7*7}}",
]

# =============================================================================
# Path traversal payloads
# =============================================================================

PATH_TRAVERSAL_PAYLOADS = [
    "../../../etc/passwd",
    "..\\..\\..\\windows\\system32\\config\\sam",
    "....//....//....//etc/passwd",
    "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    "..%252f..%252f..%252fetc/passwd",
    "/etc/passwd",
    "C:\\Windows\\System32\\config\\SAM",
    "....\\....\\....\\etc\\passwd",
]

# =============================================================================
# Oversized and boundary payloads
# =============================================================================

OVERSIZED_STRING = "A" * 100_000  # 100KB string
VERY_LONG_STRING = "X" * 10_000  # 10KB string
MAX_INT = 2**63 - 1
NEGATIVE_INT = -(2**63)

# =============================================================================
# Error message patterns that should NOT appear in responses
# =============================================================================

INTERNAL_INFO_PATTERNS = [
    "Traceback",
    "File \"/",
    ".py:",
    "line ",
    "SELECT ",
    "INSERT ",
    "UPDATE ",
    "DELETE ",
    "FROM ",
    "WHERE ",
    "sqlalchemy",
    "psycopg",
    "asyncpg",
    "sqlite3",
    "/home/",
    "/app/",
    "at 0x",
    "NoneType",
    "KeyError",
    "AttributeError",
    "ImportError",
]


# =============================================================================
# Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def analyst_user(db_session) -> User:
    """Create an analyst user for security tests."""
    user = User(
        email="sec_analyst@example.com",
        hashed_password=get_password_hash("AnalystPass123!"),
        full_name="Security Analyst",
        role="analyst",
        is_active=True,
        is_verified=True,
        department="Testing",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user_sec(db_session) -> User:
    """Create an admin user for security tests."""
    user = User(
        email="sec_admin@example.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Security Admin",
        role="admin",
        is_active=True,
        is_verified=True,
        department="Executive",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def viewer_user_sec(db_session) -> User:
    """Create a viewer (read-only) user for security tests."""
    user = User(
        email="sec_viewer@example.com",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Security Viewer",
        role="viewer",
        is_active=True,
        is_verified=True,
        department="Reporting",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def inactive_user_sec(db_session) -> User:
    """Create an inactive user for security tests."""
    user = User(
        email="sec_inactive@example.com",
        hashed_password=get_password_hash("InactivePass123!"),
        full_name="Inactive User",
        role="analyst",
        is_active=False,
        is_verified=True,
        department="Testing",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def analyst_token(analyst_user) -> str:
    """Generate an analyst-level JWT token."""
    return create_access_token(subject=str(analyst_user.id))


@pytest.fixture
def admin_token(admin_user_sec) -> str:
    """Generate an admin-level JWT token."""
    return create_access_token(subject=str(admin_user_sec.id))


@pytest.fixture
def viewer_token(viewer_user_sec) -> str:
    """Generate a viewer-level JWT token."""
    return create_access_token(subject=str(viewer_user_sec.id))


@pytest.fixture
def analyst_headers(analyst_token) -> dict:
    """Authorization headers for analyst user."""
    return {"Authorization": f"Bearer {analyst_token}"}


@pytest.fixture
def admin_headers(admin_token) -> dict:
    """Authorization headers for admin user."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def viewer_headers(viewer_token) -> dict:
    """Authorization headers for viewer user."""
    return {"Authorization": f"Bearer {viewer_token}"}


@pytest.fixture
def expired_token() -> str:
    """Generate an expired JWT token."""
    return create_access_token(
        subject="999",
        expires_delta=timedelta(seconds=-10),
    )


@pytest.fixture
def tampered_token(analyst_user) -> str:
    """Generate a JWT with a modified payload but original signature.

    Creates a valid token then modifies the subject claim.
    """
    # Create a legitimate token
    token = create_access_token(subject=str(analyst_user.id))
    # Split JWT parts
    parts = token.split(".")
    # Decode header and payload to tamper
    import base64
    import json

    # Pad and decode the payload
    payload_b64 = parts[1]
    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding
    payload = json.loads(base64.urlsafe_b64decode(payload_b64))
    # Tamper: change the user id
    payload["sub"] = "99999"
    # Re-encode without proper signature
    new_payload = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).rstrip(b"=").decode()
    return f"{parts[0]}.{new_payload}.{parts[2]}"


@pytest.fixture
def wrong_key_token() -> str:
    """Generate a JWT signed with the wrong secret key."""
    expire = datetime.now(UTC) + timedelta(minutes=30)
    payload = {"exp": expire, "sub": "1", "jti": "test-wrong-key"}
    return jwt.encode(payload, "COMPLETELY_WRONG_SECRET_KEY", algorithm="HS256")


# =============================================================================
# Helpers
# =============================================================================


async def assert_safe_response(response, *, allow_statuses=None):
    """Assert the response does not leak internal information.

    Checks that:
    - Status code is in allowed set (defaults to any 2xx/4xx)
    - Response body does not contain file paths, SQL, stack traces, etc.
    """
    if allow_statuses is None:
        allow_statuses = set(range(200, 500))  # 2xx, 3xx, 4xx are OK

    assert response.status_code in allow_statuses, (
        f"Unexpected status {response.status_code}: {response.text[:500]}"
    )

    body_text = response.text.lower()
    for pattern in INTERNAL_INFO_PATTERNS:
        # Only flag exact-case matches for SQL keywords to reduce false positives
        if pattern.isupper():
            assert pattern not in response.text, (
                f"Response leaked internal info ({pattern!r}): {response.text[:300]}"
            )
        else:
            assert pattern not in body_text, (
                f"Response leaked internal info ({pattern!r}): {response.text[:300]}"
            )


async def check_payloads_against_endpoint(
    client,
    method: str,
    url: str,
    payloads: list[str],
    *,
    param_name: str = "search",
    headers: dict | None = None,
    allow_statuses: set[int] | None = None,
):
    """Send multiple attack payloads to an endpoint and verify safe responses.

    Args:
        client: httpx AsyncClient
        method: HTTP method (get, post, etc.)
        url: Endpoint URL
        payloads: List of malicious strings to test
        param_name: Query parameter name to inject into
        headers: Auth headers to include
        allow_statuses: Set of acceptable status codes
    """
    if allow_statuses is None:
        allow_statuses = set(range(200, 500))

    for payload in payloads:
        if method.lower() == "get":
            response = await client.get(
                url, params={param_name: payload}, headers=headers
            )
        elif method.lower() == "post":
            response = await client.post(
                url, json={param_name: payload}, headers=headers
            )
        else:
            response = await client.request(
                method, url, params={param_name: payload}, headers=headers
            )

        assert response.status_code in allow_statuses, (
            f"Payload {payload!r} caused status {response.status_code}: "
            f"{response.text[:300]}"
        )
        # Verify no internal info leaked
        await assert_safe_response(response, allow_statuses=allow_statuses)
