"""Tests for audit logging service.

Covers:
- Successful audit log creation
- Request metadata extraction (IP, user-agent)
- Details serialization
- Fire-and-forget error suppression
"""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.permissions import CurrentUser, Role
from app.models.audit_log import AuditLog
from app.services.audit_service import log_action


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    return CurrentUser(
        id=1,
        email="admin@bandrcapital.com",
        role=Role.ADMIN,
        full_name="Test Admin",
    )


@pytest.fixture
def mock_request():
    """Create a mock FastAPI Request."""
    request = MagicMock()
    request.headers = {
        "user-agent": "Mozilla/5.0 TestBrowser",
    }
    request.client = MagicMock()
    request.client.host = "192.168.1.100"
    return request


# =============================================================================
# Successful Logging
# =============================================================================


@pytest.mark.asyncio
async def test_log_action_basic(db_session, mock_user):
    """Basic audit log entry should be created."""
    await log_action(
        db=db_session,
        user=mock_user,
        action="user.create",
        resource_type="user",
        resource_id="42",
    )

    # Verify the entry was flushed to the session
    from sqlalchemy import select

    result = await db_session.execute(select(AuditLog))
    entries = result.scalars().all()

    assert len(entries) == 1
    entry = entries[0]
    assert entry.user_id == 1
    assert entry.user_email == "admin@bandrcapital.com"
    assert entry.action == "user.create"
    assert entry.resource_type == "user"
    assert entry.resource_id == "42"


@pytest.mark.asyncio
async def test_log_action_with_details(db_session, mock_user):
    """Details dict should be JSON-serialized."""
    details = {"old_role": "analyst", "new_role": "manager"}

    await log_action(
        db=db_session,
        user=mock_user,
        action="user.update_role",
        resource_type="user",
        resource_id="5",
        details=details,
    )

    from sqlalchemy import select

    result = await db_session.execute(select(AuditLog))
    entry = result.scalar_one()

    assert entry.details is not None
    parsed = json.loads(entry.details)
    assert parsed["old_role"] == "analyst"
    assert parsed["new_role"] == "manager"


@pytest.mark.asyncio
async def test_log_action_with_request_metadata(db_session, mock_user, mock_request):
    """Request IP and user-agent should be captured."""
    await log_action(
        db=db_session,
        user=mock_user,
        action="settings.update",
        resource_type="settings",
        request=mock_request,
    )

    from sqlalchemy import select

    result = await db_session.execute(select(AuditLog))
    entry = result.scalar_one()

    assert entry.ip_address == "192.168.1.100"
    assert entry.user_agent == "Mozilla/5.0 TestBrowser"


@pytest.mark.asyncio
async def test_log_action_with_forwarded_ip(db_session, mock_user):
    """X-Forwarded-For header should take precedence over client IP."""
    request = MagicMock()
    request.headers = {
        "x-forwarded-for": "10.0.0.1",
        "user-agent": "TestAgent",
    }
    request.client = MagicMock()
    request.client.host = "192.168.1.1"

    await log_action(
        db=db_session,
        user=mock_user,
        action="data.export",
        resource_type="export",
        request=request,
    )

    from sqlalchemy import select

    result = await db_session.execute(select(AuditLog))
    entry = result.scalar_one()

    assert entry.ip_address == "10.0.0.1"


@pytest.mark.asyncio
async def test_log_action_truncates_long_user_agent(db_session, mock_user):
    """User-agent strings over 500 chars should be truncated."""
    request = MagicMock()
    long_ua = "A" * 600
    request.headers = {"user-agent": long_ua}
    request.client = MagicMock()
    request.client.host = "127.0.0.1"

    await log_action(
        db=db_session,
        user=mock_user,
        action="test.action",
        resource_type="test",
        request=request,
    )

    from sqlalchemy import select

    result = await db_session.execute(select(AuditLog))
    entry = result.scalar_one()

    assert len(entry.user_agent) == 500
    assert entry.user_agent.endswith("...")


@pytest.mark.asyncio
async def test_log_action_no_request(db_session, mock_user):
    """Logging without a request should leave IP and user-agent as None."""
    await log_action(
        db=db_session,
        user=mock_user,
        action="batch.start",
        resource_type="batch",
    )

    from sqlalchemy import select

    result = await db_session.execute(select(AuditLog))
    entry = result.scalar_one()

    assert entry.ip_address is None
    assert entry.user_agent is None


@pytest.mark.asyncio
async def test_log_action_none_resource_id(db_session, mock_user):
    """resource_id=None should be stored as None."""
    await log_action(
        db=db_session,
        user=mock_user,
        action="system.startup",
        resource_type="system",
        resource_id=None,
    )

    from sqlalchemy import select

    result = await db_session.execute(select(AuditLog))
    entry = result.scalar_one()

    assert entry.resource_id is None


# =============================================================================
# Error Suppression (Fire-and-Forget)
# =============================================================================


@pytest.mark.asyncio
async def test_log_action_swallows_db_errors(mock_user):
    """Database errors should be suppressed (fire-and-forget)."""
    broken_session = AsyncMock()
    broken_session.add = MagicMock(side_effect=RuntimeError("DB is down"))

    # Should not raise
    await log_action(
        db=broken_session,
        user=mock_user,
        action="should.fail",
        resource_type="test",
    )
