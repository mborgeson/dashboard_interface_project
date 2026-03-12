"""Tests for the in-process async event bus."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.events.bus import DomainEvent, EventBus, get_event_bus

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def bus() -> EventBus:
    """Return a fresh EventBus for each test (not the singleton)."""
    return EventBus()


@pytest.fixture()
def sample_event() -> DomainEvent:
    return DomainEvent(event_type="test.event", metadata={"key": "value"})


# ---------------------------------------------------------------------------
# Core publish / subscribe
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_no_subscribers(bus: EventBus) -> None:
    """Publishing with no subscribers should complete without error."""
    event = DomainEvent(event_type="unheard.event")
    await bus.publish(event)  # should not raise


@pytest.mark.asyncio
async def test_single_subscriber_receives_event(bus: EventBus) -> None:
    """A single subscribed handler should be called with the event."""
    handler = AsyncMock()
    bus.subscribe("test.event", handler)

    event = DomainEvent(event_type="test.event")
    await bus.publish(event)

    handler.assert_awaited_once_with(event)


@pytest.mark.asyncio
async def test_multiple_subscribers_receive_same_event(bus: EventBus) -> None:
    """All handlers registered for an event type should be invoked."""
    handler_a = AsyncMock()
    handler_b = AsyncMock()
    bus.subscribe("test.event", handler_a)
    bus.subscribe("test.event", handler_b)

    event = DomainEvent(event_type="test.event")
    await bus.publish(event)

    handler_a.assert_awaited_once_with(event)
    handler_b.assert_awaited_once_with(event)


@pytest.mark.asyncio
async def test_handler_error_does_not_propagate(bus: EventBus) -> None:
    """An exception in one handler must not prevent other handlers or the
    publisher from completing."""
    failing_handler = AsyncMock(side_effect=RuntimeError("boom"))
    good_handler = AsyncMock()

    bus.subscribe("test.event", failing_handler)
    bus.subscribe("test.event", good_handler)

    event = DomainEvent(event_type="test.event")

    with patch("app.events.bus.logger") as mock_logger:
        await bus.publish(event)  # should not raise
        mock_logger.error.assert_called_once()

    # The non-failing handler still ran
    good_handler.assert_awaited_once_with(event)


@pytest.mark.asyncio
async def test_handler_error_is_logged(bus: EventBus) -> None:
    """The error from a failing handler should be logged with event type."""
    failing = AsyncMock(side_effect=ValueError("bad value"))
    bus.subscribe("fail.event", failing)

    with patch("app.events.bus.logger") as mock_logger:
        await bus.publish(DomainEvent(event_type="fail.event"))
        args = mock_logger.error.call_args[0][0]
        assert "fail.event" in args
        assert "bad value" in args


# ---------------------------------------------------------------------------
# Unsubscribe / clear
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unsubscribe_removes_handler(bus: EventBus) -> None:
    """After unsubscribing, the handler should no longer be called."""
    handler = AsyncMock()
    bus.subscribe("test.event", handler)
    bus.unsubscribe("test.event", handler)

    await bus.publish(DomainEvent(event_type="test.event"))
    handler.assert_not_awaited()


def test_unsubscribe_nonexistent_raises(bus: EventBus) -> None:
    """Unsubscribing a handler that was never registered should raise."""
    handler = AsyncMock()
    with pytest.raises(ValueError):
        bus.unsubscribe("test.event", handler)


@pytest.mark.asyncio
async def test_clear_removes_all_handlers(bus: EventBus) -> None:
    """After clear(), no handlers should be invoked for any event type."""
    handler_a = AsyncMock()
    handler_b = AsyncMock()
    bus.subscribe("type.a", handler_a)
    bus.subscribe("type.b", handler_b)

    bus.clear()

    await bus.publish(DomainEvent(event_type="type.a"))
    await bus.publish(DomainEvent(event_type="type.b"))

    handler_a.assert_not_awaited()
    handler_b.assert_not_awaited()


# ---------------------------------------------------------------------------
# Event metadata and timestamp
# ---------------------------------------------------------------------------


def test_event_timestamp_auto_populated() -> None:
    """DomainEvent should have a UTC timestamp set automatically."""
    before = datetime.now(UTC)
    event = DomainEvent(event_type="ts.test")
    after = datetime.now(UTC)

    assert before <= event.timestamp <= after
    assert event.timestamp.tzinfo is not None


def test_event_metadata_defaults_to_empty_dict() -> None:
    event = DomainEvent(event_type="meta.test")
    assert event.metadata == {}


def test_event_metadata_set_correctly() -> None:
    meta = {"source": "api", "version": 2}
    event = DomainEvent(event_type="meta.test", metadata=meta)
    assert event.metadata == meta


# ---------------------------------------------------------------------------
# Concurrent execution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handlers_run_concurrently(bus: EventBus) -> None:
    """Handlers should execute concurrently, not sequentially."""
    call_order: list[str] = []

    async def slow_handler(event: DomainEvent) -> None:
        call_order.append("slow_start")
        await asyncio.sleep(0.05)
        call_order.append("slow_end")

    async def fast_handler(event: DomainEvent) -> None:
        call_order.append("fast_start")
        call_order.append("fast_end")

    bus.subscribe("concurrent.test", slow_handler)
    bus.subscribe("concurrent.test", fast_handler)

    await bus.publish(DomainEvent(event_type="concurrent.test"))

    # Both should have started before slow finished
    assert "fast_end" in call_order
    assert "slow_end" in call_order
    # fast handler completes before slow handler (concurrent, not sequential)
    assert call_order.index("fast_end") < call_order.index("slow_end")


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


def test_get_event_bus_returns_singleton() -> None:
    """get_event_bus() should always return the same instance."""
    assert get_event_bus() is get_event_bus()


# ---------------------------------------------------------------------------
# Event type isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_different_event_types_isolated(bus: EventBus) -> None:
    """A handler for one event_type should not fire for a different type."""
    handler = AsyncMock()
    bus.subscribe("type.a", handler)

    await bus.publish(DomainEvent(event_type="type.b"))
    handler.assert_not_awaited()
