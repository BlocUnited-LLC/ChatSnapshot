# /src/chatsnapshot/storage/memory_store.py
# In-memory EventStore implementation (async)

from datetime import datetime
from typing import List

from .base import EventStore
from ..events.envelope import EventEnvelope
from ..events.types import EventType


class MemoryEventStore(EventStore):
    """In-memory event store for testing and development.

    Events are stored in a list and lost when the process exits.
    Thread-safe for single-threaded async contexts.
    """

    def __init__(self):
        self._events: List[EventEnvelope] = []
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the store (no-op for memory)."""
        self._initialized = True

    async def close(self) -> None:
        """Close the store (no-op for memory)."""
        pass

    async def append(self, event: EventEnvelope) -> None:
        """Append an event to the in-memory list."""
        self._events.append(event)

    async def query(self, correlation_id: str) -> List[EventEnvelope]:
        """Query events by correlation_id."""
        return sorted(
            [e for e in self._events if e.correlation_id == correlation_id],
            key=lambda e: e.timestamp
        )

    async def query_by_type(self, event_type: EventType) -> List[EventEnvelope]:
        """Query events by event_type."""
        return sorted(
            [e for e in self._events if e.event_type == event_type],
            key=lambda e: e.timestamp
        )

    async def query_since(self, timestamp: datetime) -> List[EventEnvelope]:
        """Query events since a given timestamp."""
        return sorted(
            [e for e in self._events if e.timestamp >= timestamp],
            key=lambda e: e.timestamp
        )

    async def get_all(self) -> List[EventEnvelope]:
        """Get all events."""
        return sorted(self._events, key=lambda e: e.timestamp)

    async def count(self) -> int:
        """Get total event count."""
        return len(self._events)

    def clear(self) -> None:
        """Clear all events (for testing)."""
        self._events.clear()
