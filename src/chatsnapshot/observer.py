# /src/chatsnapshot/observer.py
# Core Observer class - async-first with pub/sub support

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional

from .events.envelope import EventEnvelope, EventSource
from .events.types import EventType, EventOrigin
from .storage.base import EventStore


# Type alias for subscription callbacks
SubscriptionCallback = Callable[[EventEnvelope], Awaitable[None]]


class Observer:
    """Core Observer for the ChatSnapshot event-driven architecture.

    The Observer is the central component that:
    - Records events to an EventStore (append-only)
    - Supports real-time subscriptions (pub/sub)
    - Provides async query methods

    This is the fundamental building block of the system.
    Everything flows through the Observer.
    """

    def __init__(self, event_store: EventStore):
        self._store = event_store
        self._subscriptions: Dict[str, SubscriptionCallback] = {}
        self._logger = logging.getLogger(__name__)

    @property
    def store(self) -> EventStore:
        """Access the underlying event store."""
        return self._store

    # ========== Recording ==========

    async def record(
        self,
        event_type: EventType,
        correlation_id: str,
        payload: Dict[str, Any],
        source: Optional[EventSource] = None,
        causation_id: Optional[str] = None
    ) -> EventEnvelope:
        """Record an event and notify subscribers.

        Args:
            event_type: The type of event
            correlation_id: Links related events (session_id, run_id, etc.)
            payload: Event-specific data
            source: Where the event originated (optional)
            causation_id: The event that caused this one (optional)

        Returns:
            The created EventEnvelope
        """
        event = EventEnvelope.create(
            event_type=event_type,
            correlation_id=correlation_id,
            payload=payload,
            source=source or EventSource(origin=EventOrigin.SYSTEM),
            causation_id=causation_id
        )

        # Append to store
        await self._store.append(event)
        self._logger.debug(f"Recorded event: {event.event_id} ({event.event_type})")

        # Notify subscribers (fire and forget, don't block)
        await self._notify_subscribers(event)

        return event

    async def record_raw(self, event: EventEnvelope) -> None:
        """Record a pre-constructed event.

        Useful when replaying events or ingesting from external sources.
        """
        await self._store.append(event)
        self._logger.debug(f"Recorded raw event: {event.event_id}")
        await self._notify_subscribers(event)

    # ========== Querying ==========

    async def get_events(self, correlation_id: str) -> List[EventEnvelope]:
        """Get all events for a correlation_id, ordered by timestamp."""
        return await self._store.query(correlation_id)

    async def get_events_by_type(self, event_type: EventType) -> List[EventEnvelope]:
        """Get all events of a specific type, ordered by timestamp."""
        return await self._store.query_by_type(event_type)

    async def get_events_since(self, timestamp: datetime) -> List[EventEnvelope]:
        """Get all events since a timestamp, ordered by timestamp."""
        return await self._store.query_since(timestamp)

    async def get_all_events(self) -> List[EventEnvelope]:
        """Get all events, ordered by timestamp."""
        return await self._store.get_all()

    async def count(self) -> int:
        """Get total event count."""
        return await self._store.count()

    # ========== Subscriptions (Pub/Sub) ==========

    def subscribe(self, callback: SubscriptionCallback) -> str:
        """Subscribe to real-time events.

        Args:
            callback: Async function called for each new event

        Returns:
            Subscription ID (use to unsubscribe)
        """
        subscription_id = str(uuid.uuid4())
        self._subscriptions[subscription_id] = callback
        self._logger.debug(f"New subscription: {subscription_id}")
        return subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events.

        Args:
            subscription_id: The ID returned from subscribe()

        Returns:
            True if successfully unsubscribed, False if not found
        """
        if subscription_id in self._subscriptions:
            del self._subscriptions[subscription_id]
            self._logger.debug(f"Unsubscribed: {subscription_id}")
            return True
        return False

    async def _notify_subscribers(self, event: EventEnvelope) -> None:
        """Notify all subscribers of a new event."""
        if not self._subscriptions:
            return

        # Create tasks for all callbacks
        tasks = []
        for sub_id, callback in self._subscriptions.items():
            tasks.append(self._safe_callback(sub_id, callback, event))

        # Run all callbacks concurrently
        if tasks:
            await asyncio.gather(*tasks)

    async def _safe_callback(
        self,
        subscription_id: str,
        callback: SubscriptionCallback,
        event: EventEnvelope
    ) -> None:
        """Safely invoke a subscription callback, catching exceptions."""
        try:
            await callback(event)
        except Exception as e:
            self._logger.error(f"Subscription {subscription_id} callback failed: {e}")

    # ========== Lifecycle ==========

    async def initialize(self) -> None:
        """Initialize the Observer and underlying store."""
        await self._store.initialize()

    async def close(self) -> None:
        """Close the Observer and underlying store."""
        self._subscriptions.clear()
        await self._store.close()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
