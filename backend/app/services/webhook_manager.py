"""
WebhookSubscriptionManager service for Microsoft Graph webhook subscriptions.

Manages the lifecycle of Graph API webhook subscriptions:
- Create subscriptions for SharePoint file change notifications
- Renew subscriptions before expiration (Graph max ~4230 minutes / ~2.9 days)
- Delete subscriptions when no longer needed
- Track active subscriptions in memory with expiration metadata
- APScheduler job for automatic renewal every 2 days
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from app.core.config import settings

if TYPE_CHECKING:
    pass


class SubscriptionInfo:
    """In-memory record of a Graph API webhook subscription."""

    __slots__ = (
        "subscription_id",
        "resource",
        "change_types",
        "notification_url",
        "expiration",
        "created_at",
    )

    def __init__(
        self,
        subscription_id: str,
        resource: str,
        change_types: list[str],
        notification_url: str,
        expiration: datetime,
    ) -> None:
        self.subscription_id = subscription_id
        self.resource = resource
        self.change_types = change_types
        self.notification_url = notification_url
        self.expiration = expiration
        self.created_at = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dictionary."""
        return {
            "subscription_id": self.subscription_id,
            "resource": self.resource,
            "change_types": self.change_types,
            "notification_url": self.notification_url,
            "expiration": self.expiration.isoformat(),
            "created_at": self.created_at.isoformat(),
        }


class WebhookSubscriptionManager:
    """
    Manages Microsoft Graph webhook subscriptions.

    Stores subscription state in an in-memory dict with expiration tracking.
    Provides methods to create, renew, delete, and list subscriptions.
    Includes an APScheduler job for automatic renewal every 2 days.
    """

    GRAPH_SUBSCRIPTIONS_URL = "https://graph.microsoft.com/v1.0/subscriptions"
    RENEWAL_JOB_ID = "webhook_subscription_renewal"
    # Renew every 2 days (Graph max expiration is ~4230 min / ~2.9 days)
    RENEWAL_INTERVAL_DAYS = 2
    # Default subscription lifetime: 2.9 days (~4176 minutes, under the 4230 limit)
    DEFAULT_EXPIRATION_MINUTES = 4176

    def __init__(self) -> None:
        self._subscriptions: dict[str, SubscriptionInfo] = {}
        self._scheduler: AsyncIOScheduler | None = None
        self._initialized: bool = False

    async def _get_access_token(self) -> str:
        """Acquire an Azure AD access token via client credentials flow."""
        import msal

        authority = f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}"
        app = msal.ConfidentialClientApplication(
            settings.AZURE_CLIENT_ID,
            authority=authority,
            client_credential=settings.AZURE_CLIENT_SECRET,
        )
        result = app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        if "access_token" not in result:
            raise RuntimeError(
                f"Failed to acquire Graph access token: {result.get('error_description', 'unknown error')}"
            )
        return result["access_token"]

    async def create_subscription(
        self,
        resource: str,
        change_types: list[str],
        notification_url: str,
        client_state: str,
        expiration: datetime | None = None,
    ) -> SubscriptionInfo:
        """Create a new webhook subscription via Microsoft Graph API.

        Args:
            resource: Graph resource path (e.g., "/drives/{id}/root").
            change_types: List of change types (e.g., ["created", "updated", "deleted"]).
            notification_url: Public HTTPS URL for Graph to POST notifications to.
            client_state: Secret string Graph will echo back for verification.
            expiration: When the subscription expires. Defaults to ~2.9 days from now.

        Returns:
            SubscriptionInfo for the newly created subscription.
        """
        if expiration is None:
            expiration = datetime.now(UTC) + timedelta(
                minutes=self.DEFAULT_EXPIRATION_MINUTES
            )

        token = await self._get_access_token()
        payload = {
            "changeType": ",".join(change_types),
            "notificationUrl": notification_url,
            "resource": resource,
            "expirationDateTime": expiration.isoformat(),
            "clientState": client_state,
        }

        async with (
            aiohttp.ClientSession() as session,
            session.post(
                self.GRAPH_SUBSCRIPTIONS_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            ) as resp,
        ):
            if resp.status not in (200, 201):
                body = await resp.text()
                raise RuntimeError(
                    f"Graph subscription creation failed ({resp.status}): {body}"
                )
            data = await resp.json()

        sub = SubscriptionInfo(
            subscription_id=data["id"],
            resource=resource,
            change_types=change_types,
            notification_url=notification_url,
            expiration=expiration,
        )
        self._subscriptions[sub.subscription_id] = sub
        logger.info(
            "Webhook subscription created",
            subscription_id=sub.subscription_id,
            resource=resource,
            expiration=expiration.isoformat(),
        )
        return sub

    async def renew_subscription(
        self,
        subscription_id: str,
        expiration: datetime | None = None,
    ) -> SubscriptionInfo:
        """Renew (extend) an existing subscription via PATCH.

        Args:
            subscription_id: The subscription to renew.
            expiration: New expiration datetime. Defaults to ~2.9 days from now.

        Returns:
            Updated SubscriptionInfo.
        """
        if expiration is None:
            expiration = datetime.now(UTC) + timedelta(
                minutes=self.DEFAULT_EXPIRATION_MINUTES
            )

        token = await self._get_access_token()
        url = f"{self.GRAPH_SUBSCRIPTIONS_URL}/{subscription_id}"
        payload = {"expirationDateTime": expiration.isoformat()}

        async with (
            aiohttp.ClientSession() as session,
            session.patch(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            ) as resp,
        ):
            if resp.status != 200:
                body = await resp.text()
                raise RuntimeError(
                    f"Graph subscription renewal failed ({resp.status}): {body}"
                )

        # Update local tracking
        if subscription_id in self._subscriptions:
            self._subscriptions[subscription_id].expiration = expiration
        else:
            # Re-add if we lost track (e.g., after restart)
            self._subscriptions[subscription_id] = SubscriptionInfo(
                subscription_id=subscription_id,
                resource="unknown",
                change_types=[],
                notification_url=settings.WEBHOOK_NOTIFICATION_URL,
                expiration=expiration,
            )

        logger.info(
            "Webhook subscription renewed",
            subscription_id=subscription_id,
            new_expiration=expiration.isoformat(),
        )
        return self._subscriptions[subscription_id]

    async def delete_subscription(self, subscription_id: str) -> bool:
        """Delete a subscription via the Graph API.

        Args:
            subscription_id: ID of the subscription to delete.

        Returns:
            True if deletion succeeded, False otherwise.
        """
        token = await self._get_access_token()
        url = f"{self.GRAPH_SUBSCRIPTIONS_URL}/{subscription_id}"

        async with (
            aiohttp.ClientSession() as session,
            session.delete(
                url,
                headers={"Authorization": f"Bearer {token}"},
            ) as resp,
        ):
            if resp.status not in (200, 204):
                body = await resp.text()
                logger.error(
                    "Webhook subscription deletion failed",
                    subscription_id=subscription_id,
                    status=resp.status,
                    body=body,
                )
                return False

        self._subscriptions.pop(subscription_id, None)
        logger.info(
            "Webhook subscription deleted",
            subscription_id=subscription_id,
        )
        return True

    def get_active_subscriptions(self) -> list[dict[str, Any]]:
        """Return all locally tracked subscriptions as dicts.

        Filters out subscriptions that have already expired.
        """
        now = datetime.now(UTC)
        active: list[dict[str, Any]] = []
        expired_ids: list[str] = []

        for sub_id, sub in self._subscriptions.items():
            if sub.expiration > now:
                active.append(sub.to_dict())
            else:
                expired_ids.append(sub_id)

        # Clean up expired entries
        for sub_id in expired_ids:
            del self._subscriptions[sub_id]

        return active

    # ── Scheduler integration ──────────────────────────────────────────────

    async def initialize_scheduler(
        self,
        timezone: str = "America/Phoenix",
    ) -> None:
        """Start the APScheduler job for automatic subscription renewal."""
        if self._initialized:
            logger.warning("Webhook subscription scheduler already initialized")
            return

        self._scheduler = AsyncIOScheduler(timezone=ZoneInfo(timezone))
        self._scheduler.add_job(
            self._renew_all_subscriptions,
            trigger=IntervalTrigger(days=self.RENEWAL_INTERVAL_DAYS),
            id=self.RENEWAL_JOB_ID,
            name="Webhook Subscription Renewal",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        self._scheduler.start()
        self._initialized = True
        logger.info(
            "Webhook subscription renewal scheduler started",
            interval_days=self.RENEWAL_INTERVAL_DAYS,
        )

    async def shutdown_scheduler(self) -> None:
        """Stop the renewal scheduler."""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Webhook subscription renewal scheduler stopped")
        self._initialized = False

    async def _renew_all_subscriptions(self) -> None:
        """Renew every tracked subscription. Called by APScheduler."""
        if not self._subscriptions:
            logger.debug("No webhook subscriptions to renew")
            return

        logger.info(
            "Starting bulk webhook subscription renewal",
            count=len(self._subscriptions),
        )

        for sub_id in list(self._subscriptions.keys()):
            try:
                await self.renew_subscription(sub_id)
            except Exception as e:
                logger.error(
                    "Webhook subscription renewal failed",
                    subscription_id=sub_id,
                    error=str(e),
                )


# ── Singleton ──────────────────────────────────────────────────────────────

_webhook_manager: WebhookSubscriptionManager | None = None


def get_webhook_manager() -> WebhookSubscriptionManager:
    """Get or create the WebhookSubscriptionManager singleton."""
    global _webhook_manager
    if _webhook_manager is None:
        _webhook_manager = WebhookSubscriptionManager()
    return _webhook_manager
