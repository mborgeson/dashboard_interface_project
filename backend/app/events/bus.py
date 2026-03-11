"""In-process async event bus for domain events."""

import asyncio
from collections import defaultdict
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from loguru import logger

EventHandler = Callable[["DomainEvent"], Coroutine[Any, Any, None]]


@dataclass
class DomainEvent:
    """Base class for all domain events."""

    event_type: str = "base"
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


class EventBus:
    """Simple in-process async event bus.

    Subscribers register handlers for event types.  When an event is published,
    all registered handlers are called concurrently.  Errors in individual
    handlers are logged but never propagate to the publisher.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Register *handler* to be called when *event_type* is published."""
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Remove *handler* from the subscriber list for *event_type*.

        Raises ``ValueError`` if the handler was not previously subscribed.
        """
        self._handlers[event_type].remove(handler)

    async def publish(self, event: DomainEvent) -> None:
        """Dispatch *event* to all handlers registered for its ``event_type``.

        Handlers run concurrently via :func:`asyncio.gather`.  Any exception
        raised inside a handler is caught and logged so that other handlers
        (and the publisher) are unaffected.
        """
        handlers = self._handlers.get(event.event_type, [])
        if not handlers:
            return
        results = await asyncio.gather(
            *(h(event) for h in handlers),
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Event handler error for {event.event_type}: {result}")

    def clear(self) -> None:
        """Remove all registered handlers."""
        self._handlers.clear()


# Module-level singleton --------------------------------------------------

_bus = EventBus()


def get_event_bus() -> EventBus:
    """Return the application-wide event bus singleton."""
    return _bus
