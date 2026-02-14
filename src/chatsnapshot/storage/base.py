# /src/chatsnapshot/storage/base.py
# Abstract EventStore base class (async-first)

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from ..events.envelope import EventEnvelope
from ..events.types import EventType


class EventStore(ABC):
    """Abstract base class for async event storage.

    All implementations must be append-only and support
    querying by correlation_id, event_type, and timestamp.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the storage (create tables, files, etc.)."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the storage connection."""
        pass

    @abstractmethod
    async def append(self, event: EventEnvelope) -> None:
        """Append an event to the store (append-only)."""
        pass

    @abstractmethod
    async def query(self, correlation_id: str) -> List[EventEnvelope]:
        """Query events by correlation_id, ordered by timestamp."""
        pass

    @abstractmethod
    async def query_by_type(self, event_type: EventType) -> List[EventEnvelope]:
        """Query events by event_type, ordered by timestamp."""
        pass

    @abstractmethod
    async def query_since(self, timestamp: datetime) -> List[EventEnvelope]:
        """Query events since a given timestamp, ordered by timestamp."""
        pass

    @abstractmethod
    async def get_all(self) -> List[EventEnvelope]:
        """Get all events, ordered by timestamp."""
        pass

    @abstractmethod
    async def count(self) -> int:
        """Get total event count."""
        pass

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
