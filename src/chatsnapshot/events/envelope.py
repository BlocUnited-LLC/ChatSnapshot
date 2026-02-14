# /src/chatsnapshot/events/envelope.py
# EventEnvelope - the canonical event structure

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, Optional

from .types import EventType, EventOrigin, RuntimeType


@dataclass
class EventSource:
    """Source metadata for an event."""
    origin: EventOrigin
    runtime: RuntimeType = RuntimeType.NONE
    agent_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "origin": self.origin.value,
            "runtime": self.runtime.value,
            "agent_name": self.agent_name
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EventSource":
        return cls(
            origin=EventOrigin(data["origin"]),
            runtime=RuntimeType(data.get("runtime", "none")),
            agent_name=data.get("agent_name")
        )


@dataclass
class EventEnvelope:
    """Canonical event envelope for the ChatSnapshot observer system.

    All facts are normalized into this single durable envelope.
    Properties:
    - Append-only
    - Immutable
    - Causally linked
    - Ordered per correlation scope
    - JSON serializable
    """
    event_id: str
    event_type: EventType
    timestamp: datetime
    source: EventSource
    correlation_id: str
    payload: Dict[str, Any] = field(default_factory=dict)
    causation_id: Optional[str] = None

    @classmethod
    def create(
        cls,
        event_type: EventType,
        correlation_id: str,
        payload: Dict[str, Any],
        source: Optional[EventSource] = None,
        causation_id: Optional[str] = None
    ) -> "EventEnvelope":
        """Factory method to create a new EventEnvelope with auto-generated ID and timestamp."""
        return cls(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.now(),
            source=source or EventSource(origin=EventOrigin.SYSTEM),
            correlation_id=correlation_id,
            payload=payload,
            causation_id=causation_id
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source.to_dict(),
            "correlation_id": self.correlation_id,
            "payload": self.payload,
            "causation_id": self.causation_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EventEnvelope":
        """Deserialize from dictionary."""
        return cls(
            event_id=data["event_id"],
            event_type=EventType(data["event_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source=EventSource.from_dict(data["source"]),
            correlation_id=data["correlation_id"],
            payload=data.get("payload", {}),
            causation_id=data.get("causation_id")
        )
