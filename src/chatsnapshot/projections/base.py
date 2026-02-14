# /src/chatsnapshot/projections/base.py
# Abstract Projection base class

from abc import ABC, abstractmethod
from typing import Any, Generic, List, TypeVar

from ..events.envelope import EventEnvelope

T = TypeVar("T")


class Projection(ABC, Generic[T]):
    """Abstract base class for event projections.

    Projections derive views from event streams. They transform
    a list of EventEnvelopes into a specific output format.

    Projections are pure functions - they don't modify the events
    or have side effects. They just derive views.

    Examples:
    - SnapshotProjection: Derives a ChatSnapshot from events
    - TranscriptProjection: Derives a readable transcript
    - TimelineProjection: Derives a workflow timeline
    """

    @abstractmethod
    def project(self, events: List[EventEnvelope]) -> T:
        """Project events into the target format.

        Args:
            events: List of EventEnvelopes (should be sorted by timestamp)

        Returns:
            The projected output
        """
        pass

    def __call__(self, events: List[EventEnvelope]) -> T:
        """Allow calling projection as a function."""
        return self.project(events)
