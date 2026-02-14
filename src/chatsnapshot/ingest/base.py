# /src/chatsnapshot/ingest/base.py
# Abstract IngestAdapter base class

from abc import ABC, abstractmethod
from typing import Any, Optional

from ..observer import Observer
from ..events.envelope import EventEnvelope


class IngestAdapter(ABC):
    """Abstract base class for framework-specific ingest adapters.

    Ingest adapters normalize events from specific agent runtimes
    (AG2, LangGraph, CrewAI, etc.) into canonical EventEnvelopes.

    Each adapter knows how to:
    - Hook into its runtime's event system
    - Normalize runtime-specific events to EventEnvelopes
    - Record events through the Observer
    """

    def __init__(self, observer: Observer, correlation_id: Optional[str] = None):
        """Initialize the adapter.

        Args:
            observer: The Observer to record events to
            correlation_id: Default correlation_id for events (can be overridden per-event)
        """
        self._observer = observer
        self._correlation_id = correlation_id
        self._last_event_id: Optional[str] = None

    @property
    def observer(self) -> Observer:
        """Access the underlying Observer."""
        return self._observer

    @property
    def correlation_id(self) -> Optional[str]:
        """Get the current correlation_id."""
        return self._correlation_id

    def set_correlation_id(self, correlation_id: str) -> None:
        """Set the correlation_id for subsequent events."""
        self._correlation_id = correlation_id

    @property
    def last_event_id(self) -> Optional[str]:
        """Get the last recorded event ID (for causation linking)."""
        return self._last_event_id

    @abstractmethod
    async def record(self, raw_event: Any, correlation_id: Optional[str] = None) -> EventEnvelope:
        """Record a raw runtime event.

        Args:
            raw_event: The runtime-specific event object
            correlation_id: Override the default correlation_id

        Returns:
            The recorded EventEnvelope
        """
        pass

    def _update_last_event(self, event: EventEnvelope) -> None:
        """Update the last event ID for causation tracking."""
        self._last_event_id = event.event_id
