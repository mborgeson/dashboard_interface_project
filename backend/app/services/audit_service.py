"""
Audit logging service for admin actions.

Provides fire-and-forget audit logging that never blocks the main request.
Errors are swallowed and logged as warnings.
"""

import json
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser
from app.models.audit_log import AuditLog

slog = structlog.get_logger("app.services.audit")


async def log_action(
    db: AsyncSession,
    user: CurrentUser,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
    request: Request | None = None,
) -> None:
    """
    Log an admin action to the audit trail.

    This function is fire-and-forget: it will never raise an exception
    or block the caller. Errors are logged as warnings.

    Args:
        db: Async database session.
        user: The authenticated user performing the action.
        action: Action identifier (e.g., "extract.trigger", "user.create").
        resource_type: Entity type (e.g., "extraction", "user", "settings").
        resource_id: Optional ID of the affected resource.
        details: Optional dict of additional context (serialized to JSON).
        request: Optional FastAPI Request for IP/user-agent extraction.
    """
    try:
        ip_address: str | None = None
        user_agent: str | None = None

        if request is not None:
            # X-Forwarded-For for reverse proxies, fall back to client host
            ip_address = request.headers.get(
                "x-forwarded-for", request.client.host if request.client else None
            )
            user_agent = request.headers.get("user-agent")
            # Truncate user agent if excessively long
            if user_agent and len(user_agent) > 500:
                user_agent = user_agent[:497] + "..."

        details_json: str | None = None
        if details is not None:
            details_json = json.dumps(details, default=str)

        now = datetime.now(UTC)
        entry = AuditLog(
            timestamp=now,
            user_id=user.id,
            user_email=user.email,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            details=details_json,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=now,
        )
        db.add(entry)
        await db.flush()

        slog.info(
            "audit_action_logged",
            user_id=user.id,
            user_email=user.email,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
        )
    except Exception:
        slog.warning(
            "audit_log_write_failed",
            user_email=user.email if user else "unknown",
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            exc_info=True,
        )
