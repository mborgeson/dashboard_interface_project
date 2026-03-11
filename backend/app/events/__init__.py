"""Domain event system for cross-module communication.

Provides an in-process async event bus that decouples publishers from
subscribers.  Modules publish ``DomainEvent`` instances; registered handlers
react independently without the publisher knowing about them.

Usage::

    from app.events.bus import get_event_bus
    from app.events.definitions import DealCreated

    bus = get_event_bus()
    await bus.publish(DealCreated(deal_id=42, property_name="Sunrise Villas"))
"""

from app.events.bus import DomainEvent, EventBus, EventHandler, get_event_bus
from app.events.definitions import (
    DealCreated,
    DealStageChanged,
    ExtractionCompleted,
    MarketDataRefreshed,
    PropertyUpdated,
    UserLoggedIn,
)

__all__ = [
    "DomainEvent",
    "EventBus",
    "EventHandler",
    "get_event_bus",
    "DealCreated",
    "DealStageChanged",
    "ExtractionCompleted",
    "MarketDataRefreshed",
    "PropertyUpdated",
    "UserLoggedIn",
]
