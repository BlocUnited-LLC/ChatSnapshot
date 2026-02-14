# /src/chatsnapshot/storage/json_store.py
# JSON file-based EventStore implementation (async with aiofiles)

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

try:
    import aiofiles
    import aiofiles.os
    HAS_AIOFILES = True
except ImportError:
    HAS_AIOFILES = False

from .base import EventStore
from ..events.envelope import EventEnvelope
from ..events.types import EventType


class JSONEventStore(EventStore):
    """JSON file-based event store using append-only JSON Lines format.

    Each event is stored as a single JSON line in the events file.
    This format supports efficient appending and streaming reads.

    Requires: aiofiles (pip install aiofiles)
    """

    def __init__(self, storage_dir: str = "./chatsnapshot_events"):
        if not HAS_AIOFILES:
            raise ImportError("aiofiles is required for JSONEventStore. Install with: pip install aiofiles")
        self._storage_dir = Path(storage_dir)
        self._events_file = self._storage_dir / "events.jsonl"
        self._initialized = False

    async def initialize(self) -> None:
        """Create storage directory if it doesn't exist."""
        await aiofiles.os.makedirs(self._storage_dir, exist_ok=True)
        if not await aiofiles.os.path.exists(self._events_file):
            async with aiofiles.open(self._events_file, "w") as f:
                pass  # Create empty file
        self._initialized = True

    async def close(self) -> None:
        """Close the store (no-op for file-based storage)."""
        pass

    async def append(self, event: EventEnvelope) -> None:
        """Append an event as a JSON line."""
        async with aiofiles.open(self._events_file, "a") as f:
            await f.write(json.dumps(event.to_dict()) + "\n")

    async def _load_all_events(self) -> List[EventEnvelope]:
        """Load all events from the JSON Lines file."""
        events = []
        try:
            async with aiofiles.open(self._events_file, "r") as f:
                async for line in f:
                    line = line.strip()
                    if line:
                        events.append(EventEnvelope.from_dict(json.loads(line)))
        except FileNotFoundError:
            pass
        return events

    async def query(self, correlation_id: str) -> List[EventEnvelope]:
        """Query events by correlation_id."""
        events = await self._load_all_events()
        return sorted(
            [e for e in events if e.correlation_id == correlation_id],
            key=lambda e: e.timestamp
        )

    async def query_by_type(self, event_type: EventType) -> List[EventEnvelope]:
        """Query events by event_type."""
        events = await self._load_all_events()
        return sorted(
            [e for e in events if e.event_type == event_type],
            key=lambda e: e.timestamp
        )

    async def query_since(self, timestamp: datetime) -> List[EventEnvelope]:
        """Query events since a given timestamp."""
        events = await self._load_all_events()
        return sorted(
            [e for e in events if e.timestamp >= timestamp],
            key=lambda e: e.timestamp
        )

    async def get_all(self) -> List[EventEnvelope]:
        """Get all events."""
        events = await self._load_all_events()
        return sorted(events, key=lambda e: e.timestamp)

    async def count(self) -> int:
        """Get total event count."""
        events = await self._load_all_events()
        return len(events)
