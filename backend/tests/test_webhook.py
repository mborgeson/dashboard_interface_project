"""
Tests for the Microsoft Graph webhook endpoint and subscription manager.

Covers:
- Validation handshake (token echo)
- Notification processing with clientState verification
- Invalid clientState rejection
- Redis-based debounce (duplicate suppression)
- Debounce expiry (notification after window processed)
- Redis unavailable fallback (process all)
- Subscription lifecycle (create, renew, delete, list)
- Scheduler renewal job
- Edge cases and error handling
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# =============================================================================
# Validation Handshake Tests
# =============================================================================


async def test_validation_handshake_returns_token(client):
    """POST with validationToken query param echoes it as text/plain 200."""
    response = await client.post("/api/v1/webhook?validationToken=abc123-test-token")
    assert response.status_code == 200
    assert response.text == "abc123-test-token"
    assert "text/plain" in response.headers.get("content-type", "")


async def test_validation_handshake_preserves_special_characters(client):
    """Validation token with special characters is echoed correctly."""
    from urllib.parse import quote

    token = "token+with/special=chars&more"
    encoded = quote(token, safe="")
    response = await client.post(f"/api/v1/webhook?validationToken={encoded}")
    assert response.status_code == 200
    assert response.text == token


async def test_validation_handshake_empty_token(client):
    """Empty validationToken is still echoed back (Graph may send empty)."""
    response = await client.post("/api/v1/webhook?validationToken=")
    assert response.status_code == 200
    assert response.text == ""


# =============================================================================
# Notification Processing Tests
# =============================================================================


@patch("app.api.v1.endpoints.webhook._queue_file_change", new_callable=AsyncMock)
@patch("app.api.v1.endpoints.webhook._set_debounce", new_callable=AsyncMock)
@patch(
    "app.api.v1.endpoints.webhook._is_debounced",
    new_callable=AsyncMock,
    return_value=False,
)
async def test_valid_notification_processed(
    mock_debounced, mock_set, mock_queue, client
):
    """Valid notification with correct clientState is processed and returns 202."""
    with patch("app.api.v1.endpoints.webhook.settings") as mock_settings:
        mock_settings.WEBHOOK_CLIENT_STATE = "my-secret"
        mock_settings.WEBHOOK_DEBOUNCE_SECONDS = 10

        payload = {
            "value": [
                {
                    "subscriptionId": "sub-1",
                    "changeType": "updated",
                    "resource": "drives/abc/items/123",
                    "clientState": "my-secret",
                }
            ]
        }

        response = await client.post("/api/v1/webhook", json=payload)
        assert response.status_code == 202

        data = response.json()
        assert data["status"] == "accepted"
        assert data["processed"] == 1

        mock_queue.assert_called_once_with("drives/abc/items/123", "updated")


@patch("app.api.v1.endpoints.webhook._queue_file_change", new_callable=AsyncMock)
@patch("app.api.v1.endpoints.webhook._set_debounce", new_callable=AsyncMock)
@patch(
    "app.api.v1.endpoints.webhook._is_debounced",
    new_callable=AsyncMock,
    return_value=False,
)
async def test_multiple_notifications_in_single_payload(
    mock_debounced, mock_set, mock_queue, client
):
    """Multiple notifications in one payload are all processed."""
    with patch("app.api.v1.endpoints.webhook.settings") as mock_settings:
        mock_settings.WEBHOOK_CLIENT_STATE = "secret"
        mock_settings.WEBHOOK_DEBOUNCE_SECONDS = 10

        payload = {
            "value": [
                {
                    "changeType": "created",
                    "resource": "drives/a/items/1",
                    "clientState": "secret",
                },
                {
                    "changeType": "updated",
                    "resource": "drives/a/items/2",
                    "clientState": "secret",
                },
                {
                    "changeType": "deleted",
                    "resource": "drives/a/items/3",
                    "clientState": "secret",
                },
            ]
        }

        response = await client.post("/api/v1/webhook", json=payload)
        assert response.status_code == 202
        assert response.json()["processed"] == 3
        assert mock_queue.call_count == 3


@patch("app.api.v1.endpoints.webhook._queue_file_change", new_callable=AsyncMock)
@patch("app.api.v1.endpoints.webhook._set_debounce", new_callable=AsyncMock)
@patch(
    "app.api.v1.endpoints.webhook._is_debounced",
    new_callable=AsyncMock,
    return_value=False,
)
async def test_empty_client_state_config_allows_all(
    mock_debounced, mock_set, mock_queue, client
):
    """When WEBHOOK_CLIENT_STATE is empty, all notifications pass through."""
    with patch("app.api.v1.endpoints.webhook.settings") as mock_settings:
        mock_settings.WEBHOOK_CLIENT_STATE = ""
        mock_settings.WEBHOOK_DEBOUNCE_SECONDS = 10

        payload = {
            "value": [
                {
                    "changeType": "created",
                    "resource": "drives/x/items/99",
                    "clientState": "anything",
                }
            ]
        }

        response = await client.post("/api/v1/webhook", json=payload)
        assert response.status_code == 202
        assert response.json()["processed"] == 1


# =============================================================================
# Invalid ClientState Tests
# =============================================================================


@patch("app.api.v1.endpoints.webhook._queue_file_change", new_callable=AsyncMock)
@patch("app.api.v1.endpoints.webhook._set_debounce", new_callable=AsyncMock)
@patch(
    "app.api.v1.endpoints.webhook._is_debounced",
    new_callable=AsyncMock,
    return_value=False,
)
async def test_invalid_client_state_rejected(
    mock_debounced, mock_set, mock_queue, client
):
    """Notification with wrong clientState is skipped (not queued)."""
    with patch("app.api.v1.endpoints.webhook.settings") as mock_settings:
        mock_settings.WEBHOOK_CLIENT_STATE = "correct-secret"
        mock_settings.WEBHOOK_DEBOUNCE_SECONDS = 10

        payload = {
            "value": [
                {
                    "changeType": "updated",
                    "resource": "drives/abc/items/456",
                    "clientState": "wrong-secret",
                }
            ]
        }

        response = await client.post("/api/v1/webhook", json=payload)
        assert response.status_code == 202

        data = response.json()
        assert data["processed"] == 0
        mock_queue.assert_not_called()


@patch("app.api.v1.endpoints.webhook._queue_file_change", new_callable=AsyncMock)
@patch("app.api.v1.endpoints.webhook._set_debounce", new_callable=AsyncMock)
@patch(
    "app.api.v1.endpoints.webhook._is_debounced",
    new_callable=AsyncMock,
    return_value=False,
)
async def test_mixed_valid_and_invalid_client_state(
    mock_debounced, mock_set, mock_queue, client
):
    """Payload with both valid and invalid clientState: only valid ones processed."""
    with patch("app.api.v1.endpoints.webhook.settings") as mock_settings:
        mock_settings.WEBHOOK_CLIENT_STATE = "my-secret"
        mock_settings.WEBHOOK_DEBOUNCE_SECONDS = 10

        payload = {
            "value": [
                {
                    "changeType": "updated",
                    "resource": "drives/a/items/1",
                    "clientState": "my-secret",
                },
                {
                    "changeType": "created",
                    "resource": "drives/a/items/2",
                    "clientState": "bad-secret",
                },
            ]
        }

        response = await client.post("/api/v1/webhook", json=payload)
        assert response.status_code == 202

        data = response.json()
        assert data["processed"] == 1
        mock_queue.assert_called_once()


# =============================================================================
# Debounce Tests
# =============================================================================


@patch("app.api.v1.endpoints.webhook._queue_file_change", new_callable=AsyncMock)
@patch("app.api.v1.endpoints.webhook._set_debounce", new_callable=AsyncMock)
@patch(
    "app.api.v1.endpoints.webhook._is_debounced",
    new_callable=AsyncMock,
    return_value=True,
)
async def test_debounce_skips_duplicate(mock_debounced, mock_set, mock_queue, client):
    """Duplicate notification within debounce window is skipped."""
    with patch("app.api.v1.endpoints.webhook.settings") as mock_settings:
        mock_settings.WEBHOOK_CLIENT_STATE = "secret"
        mock_settings.WEBHOOK_DEBOUNCE_SECONDS = 10

        payload = {
            "value": [
                {
                    "changeType": "updated",
                    "resource": "drives/abc/items/123",
                    "clientState": "secret",
                }
            ]
        }

        response = await client.post("/api/v1/webhook", json=payload)
        assert response.status_code == 202
        assert response.json()["processed"] == 0
        mock_queue.assert_not_called()
        mock_set.assert_not_called()


@patch("app.api.v1.endpoints.webhook._queue_file_change", new_callable=AsyncMock)
@patch("app.api.v1.endpoints.webhook._set_debounce", new_callable=AsyncMock)
async def test_debounce_expiry_allows_reprocessing(mock_set, mock_queue, client):
    """After debounce window expires, notification is processed again."""
    with patch("app.api.v1.endpoints.webhook.settings") as mock_settings:
        mock_settings.WEBHOOK_CLIENT_STATE = "secret"
        mock_settings.WEBHOOK_DEBOUNCE_SECONDS = 10

        # First call: not debounced
        with patch(
            "app.api.v1.endpoints.webhook._is_debounced",
            new_callable=AsyncMock,
            return_value=False,
        ):
            payload = {
                "value": [
                    {
                        "changeType": "updated",
                        "resource": "drives/abc/items/123",
                        "clientState": "secret",
                    }
                ]
            }
            response = await client.post("/api/v1/webhook", json=payload)
            assert response.status_code == 202
            assert response.json()["processed"] == 1

        mock_queue.reset_mock()

        # Second call after expiry: not debounced again
        with patch(
            "app.api.v1.endpoints.webhook._is_debounced",
            new_callable=AsyncMock,
            return_value=False,
        ):
            response = await client.post("/api/v1/webhook", json=payload)
            assert response.status_code == 202
            assert response.json()["processed"] == 1

        assert mock_queue.call_count == 1


async def test_debounce_redis_key_set():
    """_set_debounce sets a Redis key with the configured TTL."""
    mock_client = AsyncMock()
    mock_service = MagicMock()
    mock_service._client = mock_client

    with patch("app.services.redis_service._redis_service", mock_service):
        with patch("app.api.v1.endpoints.webhook.settings") as mock_settings:
            mock_settings.WEBHOOK_DEBOUNCE_SECONDS = 15

            from app.api.v1.endpoints.webhook import _set_debounce

            await _set_debounce("drives/x/items/42")
            mock_client.set.assert_called_once_with(
                "webhook:debounce:drives/x/items/42", "1", ex=15
            )


async def test_is_debounced_returns_true_when_key_exists():
    """_is_debounced returns True when the Redis key exists."""
    mock_client = AsyncMock()
    mock_client.get.return_value = "1"
    mock_service = MagicMock()
    mock_service._client = mock_client

    with patch("app.services.redis_service._redis_service", mock_service):
        from app.api.v1.endpoints.webhook import _is_debounced

        result = await _is_debounced("drives/x/items/42")
        assert result is True


async def test_is_debounced_returns_false_when_no_key():
    """_is_debounced returns False when the Redis key does not exist."""
    mock_client = AsyncMock()
    mock_client.get.return_value = None
    mock_service = MagicMock()
    mock_service._client = mock_client

    with patch("app.services.redis_service._redis_service", mock_service):
        from app.api.v1.endpoints.webhook import _is_debounced

        result = await _is_debounced("drives/x/items/42")
        assert result is False


# =============================================================================
# Redis Fallback Tests
# =============================================================================


async def test_redis_unavailable_processes_all():
    """When Redis is unavailable, _is_debounced returns False (process all)."""
    with patch("app.services.redis_service._redis_service", None):
        from app.api.v1.endpoints.webhook import _is_debounced

        result = await _is_debounced("drives/x/items/42")
        assert result is False


async def test_redis_unavailable_set_debounce_no_error():
    """When Redis is unavailable, _set_debounce silently does nothing."""
    with patch("app.services.redis_service._redis_service", None):
        from app.api.v1.endpoints.webhook import _set_debounce

        # Should not raise
        await _set_debounce("drives/x/items/42")


async def test_redis_exception_falls_back():
    """When Redis raises an exception, _is_debounced returns False."""
    mock_client = AsyncMock()
    mock_client.get.side_effect = ConnectionError("Redis down")
    mock_service = MagicMock()
    mock_service._client = mock_client

    with patch("app.services.redis_service._redis_service", mock_service):
        from app.api.v1.endpoints.webhook import _is_debounced

        result = await _is_debounced("drives/x/items/42")
        assert result is False


async def test_redis_service_no_client_processes_all():
    """When Redis service exists but client is None, notifications go through."""
    mock_service = MagicMock()
    mock_service._client = None

    with patch("app.services.redis_service._redis_service", mock_service):
        from app.api.v1.endpoints.webhook import _is_debounced

        result = await _is_debounced("drives/x/items/42")
        assert result is False


# =============================================================================
# Empty / Malformed Payload Tests
# =============================================================================


async def test_empty_value_array(client):
    """Empty value array returns 202 with 0 processed."""
    response = await client.post("/api/v1/webhook", json={"value": []})
    assert response.status_code == 202
    assert response.json()["processed"] == 0


async def test_notification_with_missing_fields(client):
    """Notification with missing optional fields is handled gracefully."""
    with patch("app.api.v1.endpoints.webhook.settings") as mock_settings:
        mock_settings.WEBHOOK_CLIENT_STATE = ""
        mock_settings.WEBHOOK_DEBOUNCE_SECONDS = 10

        with (
            patch(
                "app.api.v1.endpoints.webhook._is_debounced",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch("app.api.v1.endpoints.webhook._set_debounce", new_callable=AsyncMock),
            patch(
                "app.api.v1.endpoints.webhook._queue_file_change",
                new_callable=AsyncMock,
            ),
        ):
            payload = {"value": [{"changeType": "updated"}]}
            response = await client.post("/api/v1/webhook", json=payload)
            assert response.status_code == 202


# =============================================================================
# Subscription Manager Tests
# =============================================================================


async def test_get_active_subscriptions_empty():
    """get_active_subscriptions returns empty list when no subscriptions."""
    from app.services.webhook_manager import WebhookSubscriptionManager

    manager = WebhookSubscriptionManager()
    result = manager.get_active_subscriptions()
    assert result == []


async def test_get_active_subscriptions_filters_expired():
    """Expired subscriptions are excluded from active list."""
    from app.services.webhook_manager import (
        SubscriptionInfo,
        WebhookSubscriptionManager,
    )

    manager = WebhookSubscriptionManager()

    # Add an active subscription
    active_sub = SubscriptionInfo(
        subscription_id="active-1",
        resource="drives/x",
        change_types=["updated"],
        notification_url="https://example.com/webhook",
        expiration=datetime.now(UTC) + timedelta(hours=24),
    )
    manager._subscriptions["active-1"] = active_sub

    # Add an expired subscription
    expired_sub = SubscriptionInfo(
        subscription_id="expired-1",
        resource="drives/y",
        change_types=["created"],
        notification_url="https://example.com/webhook",
        expiration=datetime.now(UTC) - timedelta(hours=1),
    )
    manager._subscriptions["expired-1"] = expired_sub

    result = manager.get_active_subscriptions()
    assert len(result) == 1
    assert result[0]["subscription_id"] == "active-1"

    # Expired entry should have been cleaned up
    assert "expired-1" not in manager._subscriptions


async def test_subscription_info_to_dict():
    """SubscriptionInfo.to_dict() produces the expected shape."""
    from app.services.webhook_manager import SubscriptionInfo

    exp = datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC)
    sub = SubscriptionInfo(
        subscription_id="sub-123",
        resource="drives/abc/root",
        change_types=["created", "updated"],
        notification_url="https://example.com/hook",
        expiration=exp,
    )
    d = sub.to_dict()

    assert d["subscription_id"] == "sub-123"
    assert d["resource"] == "drives/abc/root"
    assert d["change_types"] == ["created", "updated"]
    assert d["notification_url"] == "https://example.com/hook"
    assert "2026-04-01" in d["expiration"]
    assert "created_at" in d


def _make_mock_aiohttp_session(
    method_name: str,
    response_status: int,
    response_json: dict | None = None,
    response_text: str | None = None,
):
    """Helper to create a properly-structured mock aiohttp session.

    aiohttp uses ``async with session.post(...) as resp:`` which requires
    the HTTP method to return an async context manager.
    """
    mock_response = MagicMock()
    mock_response.status = response_status
    if response_json is not None:
        mock_response.json = AsyncMock(return_value=response_json)
    if response_text is not None:
        mock_response.text = AsyncMock(return_value=response_text)

    # The HTTP method returns an async context manager
    method_cm = AsyncMock()
    method_cm.__aenter__ = AsyncMock(return_value=mock_response)
    method_cm.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    setattr(mock_session, method_name, MagicMock(return_value=method_cm))

    # Session itself is an async context manager
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    session_cm.__aexit__ = AsyncMock(return_value=False)

    return session_cm


async def test_create_subscription_calls_graph():
    """create_subscription POSTs to Graph API and stores result."""
    from app.services.webhook_manager import WebhookSubscriptionManager

    manager = WebhookSubscriptionManager()

    session_cm = _make_mock_aiohttp_session(
        "post", 201, response_json={"id": "new-sub-id", "resource": "drives/abc/root"}
    )

    with patch.object(
        manager, "_get_access_token", new_callable=AsyncMock, return_value="fake-token"
    ):
        with patch(
            "app.services.webhook_manager.aiohttp.ClientSession",
            return_value=session_cm,
        ):
            sub = await manager.create_subscription(
                resource="drives/abc/root",
                change_types=["created", "updated"],
                notification_url="https://example.com/hook",
                client_state="my-secret",
            )

    assert sub.subscription_id == "new-sub-id"
    assert "new-sub-id" in manager._subscriptions


async def test_renew_subscription_patches_graph():
    """renew_subscription PATCHes Graph API and updates local state."""
    from app.services.webhook_manager import (
        SubscriptionInfo,
        WebhookSubscriptionManager,
    )

    manager = WebhookSubscriptionManager()
    manager._subscriptions["sub-1"] = SubscriptionInfo(
        subscription_id="sub-1",
        resource="drives/abc",
        change_types=["updated"],
        notification_url="https://example.com/hook",
        expiration=datetime.now(UTC) + timedelta(hours=1),
    )

    session_cm = _make_mock_aiohttp_session("patch", 200)
    new_exp = datetime.now(UTC) + timedelta(days=3)

    with patch.object(
        manager, "_get_access_token", new_callable=AsyncMock, return_value="fake-token"
    ):
        with patch(
            "app.services.webhook_manager.aiohttp.ClientSession",
            return_value=session_cm,
        ):
            sub = await manager.renew_subscription("sub-1", expiration=new_exp)

    assert sub.expiration == new_exp


async def test_delete_subscription_removes_from_graph():
    """delete_subscription DELETEs from Graph API and removes local tracking."""
    from app.services.webhook_manager import (
        SubscriptionInfo,
        WebhookSubscriptionManager,
    )

    manager = WebhookSubscriptionManager()
    manager._subscriptions["sub-1"] = SubscriptionInfo(
        subscription_id="sub-1",
        resource="drives/abc",
        change_types=["updated"],
        notification_url="https://example.com/hook",
        expiration=datetime.now(UTC) + timedelta(hours=1),
    )

    session_cm = _make_mock_aiohttp_session("delete", 204)

    with patch.object(
        manager, "_get_access_token", new_callable=AsyncMock, return_value="fake-token"
    ):
        with patch(
            "app.services.webhook_manager.aiohttp.ClientSession",
            return_value=session_cm,
        ):
            result = await manager.delete_subscription("sub-1")

    assert result is True
    assert "sub-1" not in manager._subscriptions


async def test_delete_subscription_failure_returns_false():
    """delete_subscription returns False when Graph API returns error."""
    from app.services.webhook_manager import WebhookSubscriptionManager

    manager = WebhookSubscriptionManager()

    session_cm = _make_mock_aiohttp_session("delete", 404, response_text="Not found")

    with patch.object(
        manager, "_get_access_token", new_callable=AsyncMock, return_value="fake-token"
    ):
        with patch(
            "app.services.webhook_manager.aiohttp.ClientSession",
            return_value=session_cm,
        ):
            result = await manager.delete_subscription("nonexistent")

    assert result is False


# =============================================================================
# Scheduler Renewal Job Tests
# =============================================================================


async def test_renew_all_subscriptions_renews_each():
    """_renew_all_subscriptions calls renew for each tracked subscription."""
    from app.services.webhook_manager import (
        SubscriptionInfo,
        WebhookSubscriptionManager,
    )

    manager = WebhookSubscriptionManager()
    manager._subscriptions["sub-1"] = SubscriptionInfo(
        subscription_id="sub-1",
        resource="drives/a",
        change_types=["updated"],
        notification_url="https://example.com/hook",
        expiration=datetime.now(UTC) + timedelta(hours=12),
    )
    manager._subscriptions["sub-2"] = SubscriptionInfo(
        subscription_id="sub-2",
        resource="drives/b",
        change_types=["created"],
        notification_url="https://example.com/hook",
        expiration=datetime.now(UTC) + timedelta(hours=12),
    )

    with patch.object(
        manager, "renew_subscription", new_callable=AsyncMock
    ) as mock_renew:
        await manager._renew_all_subscriptions()

    assert mock_renew.call_count == 2
    calls = {call.args[0] for call in mock_renew.call_args_list}
    assert calls == {"sub-1", "sub-2"}


async def test_renew_all_subscriptions_continues_on_failure():
    """If one renewal fails, others still proceed."""
    from app.services.webhook_manager import (
        SubscriptionInfo,
        WebhookSubscriptionManager,
    )

    manager = WebhookSubscriptionManager()
    manager._subscriptions["sub-1"] = SubscriptionInfo(
        subscription_id="sub-1",
        resource="drives/a",
        change_types=["updated"],
        notification_url="https://example.com/hook",
        expiration=datetime.now(UTC) + timedelta(hours=12),
    )
    manager._subscriptions["sub-2"] = SubscriptionInfo(
        subscription_id="sub-2",
        resource="drives/b",
        change_types=["created"],
        notification_url="https://example.com/hook",
        expiration=datetime.now(UTC) + timedelta(hours=12),
    )

    call_count = 0

    async def mock_renew(sub_id, expiration=None):
        nonlocal call_count
        call_count += 1
        if sub_id == "sub-1":
            raise RuntimeError("Graph API error")
        return manager._subscriptions[sub_id]

    with patch.object(manager, "renew_subscription", side_effect=mock_renew):
        await manager._renew_all_subscriptions()

    assert call_count == 2


async def test_renew_all_subscriptions_empty_no_op():
    """_renew_all_subscriptions is a no-op when no subscriptions exist."""
    from app.services.webhook_manager import WebhookSubscriptionManager

    manager = WebhookSubscriptionManager()

    with patch.object(
        manager, "renew_subscription", new_callable=AsyncMock
    ) as mock_renew:
        await manager._renew_all_subscriptions()

    mock_renew.assert_not_called()


# =============================================================================
# Singleton and Config Tests
# =============================================================================


def test_get_webhook_manager_singleton():
    """get_webhook_manager returns the same instance on repeated calls."""
    import app.services.webhook_manager as wm

    # Reset the global for a clean test
    wm._webhook_manager = None
    try:
        m1 = wm.get_webhook_manager()
        m2 = wm.get_webhook_manager()
        assert m1 is m2
    finally:
        wm._webhook_manager = None


def test_webhook_config_defaults():
    """Webhook config settings have correct defaults."""
    from app.core.config import ExtractionSettings

    s = ExtractionSettings()
    assert s.WEBHOOK_ENABLED is False
    assert s.WEBHOOK_CLIENT_STATE == ""
    assert s.WEBHOOK_NOTIFICATION_URL == ""
    assert s.WEBHOOK_DEBOUNCE_SECONDS == 10


# =============================================================================
# Admin Subscription Endpoint Tests (require_manager)
# =============================================================================


async def test_list_subscriptions_requires_auth(client):
    """GET /webhook/subscriptions without auth returns 401."""
    response = await client.get("/api/v1/webhook/subscriptions")
    assert response.status_code == 401


async def test_list_subscriptions_with_auth(client, auto_auth):
    """GET /webhook/subscriptions with admin auth returns subscription list."""
    mock_manager = MagicMock()
    mock_manager.get_active_subscriptions.return_value = []

    with patch(
        "app.services.webhook_manager.get_webhook_manager",
        return_value=mock_manager,
    ):
        response = await client.get("/api/v1/webhook/subscriptions")
        assert response.status_code == 200
        data = response.json()
        assert "subscriptions" in data
        assert "count" in data


async def test_create_subscription_requires_auth(client):
    """POST /webhook/subscriptions without auth returns 401."""
    response = await client.post(
        "/api/v1/webhook/subscriptions",
        json={"resource": "drives/x"},
    )
    assert response.status_code == 401


async def test_delete_subscription_requires_auth(client):
    """DELETE /webhook/subscriptions/{id} without auth returns 401."""
    response = await client.delete("/api/v1/webhook/subscriptions/some-id")
    assert response.status_code == 401


async def test_renew_subscription_requires_auth(client):
    """PATCH /webhook/subscriptions/{id} without auth returns 401."""
    response = await client.patch("/api/v1/webhook/subscriptions/some-id")
    assert response.status_code == 401
