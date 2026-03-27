"""
Microsoft Graph webhook endpoint for SharePoint file change notifications.

Handles:
- Validation handshake (Graph sends validationToken as query param on subscription creation)
- Incoming change notifications with clientState verification
- Redis-based debounce to suppress duplicate notifications (10-second window)
- Queuing file change processing via the existing file monitor infrastructure
- Admin endpoints for managing webhook subscriptions (require_manager)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from loguru import logger
from pydantic import BaseModel

from app.core.config import settings
from app.core.permissions import CurrentUser, require_manager

if TYPE_CHECKING:
    pass

router = APIRouter()


# ── Pydantic schemas for notification payload ────────────────────────────────


class ResourceData(BaseModel):
    """Resource data from a Graph notification."""

    id: str | None = None


class NotificationItem(BaseModel):
    """A single notification from Microsoft Graph."""

    subscriptionId: str | None = None
    changeType: str | None = None
    resource: str | None = None
    clientState: str | None = None
    resourceData: ResourceData | None = None
    tenantId: str | None = None


class NotificationPayload(BaseModel):
    """The top-level payload Graph sends to the notification URL."""

    value: list[NotificationItem] = []


# ── Webhook notification endpoint (unauthenticated) ─────────────────────────


@router.post(
    "",
    summary="Receive Microsoft Graph webhook notifications",
    status_code=202,
    response_description="Accepted",
)
async def receive_webhook(
    request: Request,
    validationToken: str | None = Query(default=None),
) -> Any:
    """Handle incoming Microsoft Graph webhook notifications.

    Two modes:
    1. **Validation handshake**: When Graph creates a subscription, it POSTs with
       a ``validationToken`` query parameter. We must echo it back as text/plain
       within 10 seconds.
    2. **Change notification**: Graph POSTs a JSON body with one or more
       notification items. We verify ``clientState``, debounce duplicates, and
       queue processing. Must respond within 30 seconds (we return 202 immediately).
    """
    # ── Validation handshake ──────────────────────────────────────────────
    if validationToken is not None:
        logger.info("Webhook validation handshake received")
        return PlainTextResponse(content=validationToken, status_code=200)

    # ── Change notification ───────────────────────────────────────────────
    try:
        body = await request.json()
    except Exception as exc:
        logger.warning("Webhook received non-JSON body")
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc

    payload = NotificationPayload(**body)

    processed = 0
    skipped_auth = 0
    skipped_debounce = 0

    for notification in payload.value:
        # Verify clientState matches our configured secret
        expected = settings.WEBHOOK_CLIENT_STATE
        if expected and notification.clientState != expected:
            logger.warning(
                "Webhook notification rejected: invalid clientState",
                subscription_id=notification.subscriptionId,
            )
            skipped_auth += 1
            continue

        resource = notification.resource or ""
        change_type = notification.changeType or ""

        # Debounce: skip if the same resource was notified in the last N seconds
        if await _is_debounced(resource):
            logger.debug(
                "Webhook notification debounced",
                resource=resource,
                change_type=change_type,
            )
            skipped_debounce += 1
            continue

        # Mark this resource in the debounce window
        await _set_debounce(resource)

        # Queue processing via file monitor infrastructure
        await _queue_file_change(resource, change_type)
        processed += 1

    logger.info(
        "Webhook notifications processed",
        total=len(payload.value),
        processed=processed,
        skipped_auth=skipped_auth,
        skipped_debounce=skipped_debounce,
    )

    # Graph requires a 2xx response within 30 seconds
    return {"status": "accepted", "processed": processed}


# ── Debounce helpers ─────────────────────────────────────────────────────────


async def _is_debounced(resource: str) -> bool:
    """Check if a resource notification is within the debounce window.

    Uses Redis SET with EX if available; falls back to allowing all
    notifications through if Redis is unavailable.
    """
    try:
        from app.services.redis_service import _redis_service

        if _redis_service is None or _redis_service._client is None:
            return False

        key = f"webhook:debounce:{resource}"
        result = await _redis_service._client.get(key)
        return result is not None
    except Exception:
        # Redis unavailable -- process all notifications (no debounce)
        logger.debug("Redis unavailable for webhook debounce, processing notification")
        return False


async def _set_debounce(resource: str) -> None:
    """Mark a resource in the debounce window."""
    try:
        from app.services.redis_service import _redis_service

        if _redis_service is None or _redis_service._client is None:
            return

        key = f"webhook:debounce:{resource}"
        ttl = settings.WEBHOOK_DEBOUNCE_SECONDS
        await _redis_service._client.set(key, "1", ex=ttl)
    except Exception:
        # Redis unavailable -- skip debounce silently
        pass


# ── File change processing ───────────────────────────────────────────────────


async def _queue_file_change(resource: str, change_type: str) -> None:
    """Queue a file change for processing by the file monitor infrastructure.

    This creates a background task that feeds into the existing
    SharePointFileMonitor pipeline.

    Args:
        resource: Graph resource path (e.g., "drives/{id}/items/{itemId}").
        change_type: Type of change ("created", "updated", "deleted").
    """
    logger.info(
        "Queuing webhook file change",
        resource=resource,
        change_type=change_type,
    )

    # The actual extraction is handled asynchronously by the file monitor.
    # For now, log the change and let the next scheduled monitor check pick it up.
    # A more advanced implementation could trigger an immediate check.
    try:
        from app.db.session import AsyncSessionLocal
        from app.services.extraction.file_monitor import SharePointFileMonitor

        async with AsyncSessionLocal() as db:
            monitor = SharePointFileMonitor(db)
            await monitor.check_for_changes(auto_trigger_extraction=True)
    except Exception as e:
        # Don't fail the webhook response -- log and continue
        logger.error(
            "Failed to process webhook file change",
            resource=resource,
            change_type=change_type,
            error=str(e),
        )


# ── Admin endpoints for subscription management ─────────────────────────────


class CreateSubscriptionRequest(BaseModel):
    """Request body for creating a webhook subscription."""

    resource: str
    change_types: list[str] = ["created", "updated", "deleted"]
    notification_url: str | None = None
    client_state: str | None = None
    expiration_minutes: int | None = None


@router.get(
    "/subscriptions",
    summary="List active webhook subscriptions",
)
async def list_subscriptions(
    current_user: CurrentUser = Depends(require_manager),
) -> dict[str, Any]:
    """List all locally tracked active webhook subscriptions."""
    from app.services.webhook_manager import get_webhook_manager

    manager = get_webhook_manager()
    subscriptions = manager.get_active_subscriptions()

    return {
        "subscriptions": subscriptions,
        "count": len(subscriptions),
    }


@router.post(
    "/subscriptions",
    summary="Create a new webhook subscription",
    status_code=201,
)
async def create_subscription(
    body: CreateSubscriptionRequest,
    current_user: CurrentUser = Depends(require_manager),
) -> dict[str, Any]:
    """Create a new Microsoft Graph webhook subscription."""
    from app.services.webhook_manager import get_webhook_manager

    manager = get_webhook_manager()

    notification_url = body.notification_url or settings.WEBHOOK_NOTIFICATION_URL
    client_state = body.client_state or settings.WEBHOOK_CLIENT_STATE

    if not notification_url:
        raise HTTPException(
            status_code=400,
            detail="notification_url is required (or set WEBHOOK_NOTIFICATION_URL)",
        )
    if not client_state:
        raise HTTPException(
            status_code=400,
            detail="client_state is required (or set WEBHOOK_CLIENT_STATE)",
        )

    expiration = None
    if body.expiration_minutes:
        from datetime import timedelta

        expiration = datetime.now(UTC) + timedelta(minutes=body.expiration_minutes)

    sub = await manager.create_subscription(
        resource=body.resource,
        change_types=body.change_types,
        notification_url=notification_url,
        client_state=client_state,
        expiration=expiration,
    )

    return {"subscription": sub.to_dict()}


@router.patch(
    "/subscriptions/{subscription_id}",
    summary="Renew a webhook subscription",
)
async def renew_subscription(
    subscription_id: str,
    current_user: CurrentUser = Depends(require_manager),
) -> dict[str, Any]:
    """Renew (extend) an existing webhook subscription."""
    from app.services.webhook_manager import get_webhook_manager

    manager = get_webhook_manager()
    sub = await manager.renew_subscription(subscription_id)

    return {"subscription": sub.to_dict()}


@router.delete(
    "/subscriptions/{subscription_id}",
    summary="Delete a webhook subscription",
)
async def delete_subscription(
    subscription_id: str,
    current_user: CurrentUser = Depends(require_manager),
) -> dict[str, Any]:
    """Delete an existing webhook subscription."""
    from app.services.webhook_manager import get_webhook_manager

    manager = get_webhook_manager()
    success = await manager.delete_subscription(subscription_id)

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete subscription from Graph API",
        )

    return {"deleted": True, "subscription_id": subscription_id}
