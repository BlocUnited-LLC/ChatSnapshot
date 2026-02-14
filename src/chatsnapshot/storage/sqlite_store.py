# /src/chatsnapshot/storage/sqlite_store.py
# SQLite-based EventStore implementation (async with aiosqlite)

import json
from datetime import datetime
from typing import List

try:
    import aiosqlite
    HAS_AIOSQLITE = True
except ImportError:
    HAS_AIOSQLITE = False

from .base import EventStore
from ..events.envelope import EventEnvelope
from ..events.types import EventType


class SQLiteEventStore(EventStore):
    """SQLite-based event store with indexed queries.

    Uses an append-only events table with indexes on:
    - correlation_id
    - event_type
    - timestamp

    Requires: aiosqlite (pip install aiosqlite)
    """

    def __init__(self, db_path: str = "./chatsnapshot_events.db"):
        if not HAS_AIOSQLITE:
            raise ImportError("aiosqlite is required for SQLiteEventStore. Install with: pip install aiosqlite")
        self._db_path = db_path
        self._db = None

    async def initialize(self) -> None:
        """Create database and tables if they don't exist."""
        self._db = await aiosqlite.connect(self._db_path)
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                correlation_id TEXT NOT NULL,
                causation_id TEXT,
                source TEXT NOT NULL,
                payload TEXT NOT NULL
            )
        """)
        await self._db.execute("CREATE INDEX IF NOT EXISTS idx_correlation ON events(correlation_id)")
        await self._db.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON events(event_type)")
        await self._db.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)")
        await self._db.commit()

    async def close(self) -> None:
        """Close the database connection."""
        if self._db:
            await self._db.close()
            self._db = None

    async def append(self, event: EventEnvelope) -> None:
        """Append an event to the database."""
        await self._db.execute(
            """
            INSERT INTO events (event_id, event_type, timestamp, correlation_id, causation_id, source, payload)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.event_type.value,
                event.timestamp.isoformat(),
                event.correlation_id,
                event.causation_id,
                json.dumps(event.source.to_dict()),
                json.dumps(event.payload)
            )
        )
        await self._db.commit()

    def _row_to_event(self, row) -> EventEnvelope:
        """Convert a database row to an EventEnvelope."""
        from ..events.envelope import EventSource
        return EventEnvelope(
            event_id=row[1],
            event_type=EventType(row[2]),
            timestamp=datetime.fromisoformat(row[3]),
            correlation_id=row[4],
            causation_id=row[5],
            source=EventSource.from_dict(json.loads(row[6])),
            payload=json.loads(row[7])
        )

    async def query(self, correlation_id: str) -> List[EventEnvelope]:
        """Query events by correlation_id."""
        cursor = await self._db.execute(
            "SELECT * FROM events WHERE correlation_id = ? ORDER BY timestamp",
            (correlation_id,)
        )
        rows = await cursor.fetchall()
        return [self._row_to_event(row) for row in rows]

    async def query_by_type(self, event_type: EventType) -> List[EventEnvelope]:
        """Query events by event_type."""
        cursor = await self._db.execute(
            "SELECT * FROM events WHERE event_type = ? ORDER BY timestamp",
            (event_type.value,)
        )
        rows = await cursor.fetchall()
        return [self._row_to_event(row) for row in rows]

    async def query_since(self, timestamp: datetime) -> List[EventEnvelope]:
        """Query events since a given timestamp."""
        cursor = await self._db.execute(
            "SELECT * FROM events WHERE timestamp >= ? ORDER BY timestamp",
            (timestamp.isoformat(),)
        )
        rows = await cursor.fetchall()
        return [self._row_to_event(row) for row in rows]

    async def get_all(self) -> List[EventEnvelope]:
        """Get all events."""
        cursor = await self._db.execute("SELECT * FROM events ORDER BY timestamp")
        rows = await cursor.fetchall()
        return [self._row_to_event(row) for row in rows]

    async def count(self) -> int:
        """Get total event count."""
        cursor = await self._db.execute("SELECT COUNT(*) FROM events")
        row = await cursor.fetchone()
        return row[0] if row else 0
