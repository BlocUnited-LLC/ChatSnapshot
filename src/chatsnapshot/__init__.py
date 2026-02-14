# /src/chatsnapshot/__init__.py
# ChatSnapshot - Observer-first event-driven architecture

from .observer import Observer
from .snapshot import ChatSnapshot

# Events
from .events import (
    EventEnvelope,
    EventSource,
    EventType,
    EventOrigin,
    RuntimeType,
)

# Storage
from .storage import (
    EventStore,
    MemoryEventStore,
    JSONEventStore,
    SQLiteEventStore,
    MongoDBEventStore,
)

# Ingest adapters
from .ingest import (
    IngestAdapter,
    AG2IngestAdapter,
)

# Projections
from .projections import (
    Projection,
    SnapshotProjection,
    TranscriptProjection,
    MarkdownTranscriptProjection,
)

__version__ = "2.0.0"

__all__ = [
    # Core
    "Observer",
    "ChatSnapshot",
    # Events
    "EventEnvelope",
    "EventSource",
    "EventType",
    "EventOrigin",
    "RuntimeType",
    # Storage
    "EventStore",
    "MemoryEventStore",
    "JSONEventStore",
    "SQLiteEventStore",
    "MongoDBEventStore",
    # Ingest
    "IngestAdapter",
    "AG2IngestAdapter",
    # Projections
    "Projection",
    "SnapshotProjection",
    "TranscriptProjection",
    "MarkdownTranscriptProjection",
]
