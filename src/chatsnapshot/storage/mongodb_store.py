# /src/chatsnapshot/storage/mongodb_store.py
# MongoDB-based EventStore implementation (async with Motor)

from datetime import datetime
from typing import List, Optional

try:
    from motor.motor_asyncio import AsyncIOMotorClient
    HAS_MOTOR = True
except ImportError:
    HAS_MOTOR = False

from .base import EventStore
from ..events.envelope import EventEnvelope, EventSource
from ..events.types import EventType


class MongoDBEventStore(EventStore):
    """MongoDB-based event store using Motor (async driver).

    Stores events in a collection with indexes on:
    - correlation_id
    - event_type
    - timestamp

    Requires: motor (pip install motor)
    """

    def __init__(
        self,
        connection_string: str = "mongodb://localhost:27017",
        database_name: str = "chatsnapshot",
        collection_name: str = "events"
    ):
        if not HAS_MOTOR:
            raise ImportError("motor is required for MongoDBEventStore. Install with: pip install motor")
        self._connection_string = connection_string
        self._database_name = database_name
        self._collection_name = collection_name
        self._client = None
        self._db = None
        self._collection = None

    async def initialize(self) -> None:
        """Connect to MongoDB and create indexes."""
        self._client = AsyncIOMotorClient(self._connection_string)
        self._db = self._client[self._database_name]
        self._collection = self._db[self._collection_name]

        # Create indexes
        await self._collection.create_index("event_id", unique=True)
        await self._collection.create_index("correlation_id")
        await self._collection.create_index("event_type")
        await self._collection.create_index("timestamp")

    async def close(self) -> None:
        """Close the MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            self._collection = None

    async def append(self, event: EventEnvelope) -> None:
        """Append an event to the collection."""
        doc = event.to_dict()
        await self._collection.insert_one(doc)

    def _doc_to_event(self, doc: dict) -> EventEnvelope:
        """Convert a MongoDB document to an EventEnvelope."""
        doc.pop("_id", None)  # Remove MongoDB's _id field
        return EventEnvelope.from_dict(doc)

    async def query(self, correlation_id: str) -> List[EventEnvelope]:
        """Query events by correlation_id."""
        cursor = self._collection.find(
            {"correlation_id": correlation_id}
        ).sort("timestamp", 1)
        docs = await cursor.to_list(length=None)
        return [self._doc_to_event(doc) for doc in docs]

    async def query_by_type(self, event_type: EventType) -> List[EventEnvelope]:
        """Query events by event_type."""
        cursor = self._collection.find(
            {"event_type": event_type.value}
        ).sort("timestamp", 1)
        docs = await cursor.to_list(length=None)
        return [self._doc_to_event(doc) for doc in docs]

    async def query_since(self, timestamp: datetime) -> List[EventEnvelope]:
        """Query events since a given timestamp."""
        cursor = self._collection.find(
            {"timestamp": {"$gte": timestamp.isoformat()}}
        ).sort("timestamp", 1)
        docs = await cursor.to_list(length=None)
        return [self._doc_to_event(doc) for doc in docs]

    async def get_all(self) -> List[EventEnvelope]:
        """Get all events."""
        cursor = self._collection.find().sort("timestamp", 1)
        docs = await cursor.to_list(length=None)
        return [self._doc_to_event(doc) for doc in docs]

    async def count(self) -> int:
        """Get total event count."""
        return await self._collection.count_documents({})
