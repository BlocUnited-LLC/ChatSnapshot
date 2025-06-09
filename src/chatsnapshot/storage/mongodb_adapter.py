# MongoDBStorageAdapter for ChatSnapshot (async)
import logging
from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient
from ..snapshot import ChatSnapshot
from .base import StorageAdapter

class MongoDBStorageAdapter(StorageAdapter):
    """MongoDB async storage adapter"""

    def __init__(
        self,
        uri: str = "mongodb://localhost:27017",
        db_name: str = "chatsnapshot",
        collection_name: str = "chat_snapshots",
    ):
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]
        self.logger = logging.getLogger(__name__)

    async def save_snapshot(self, snapshot: ChatSnapshot) -> None:
        doc = snapshot.to_dict()
        doc["_id"] = snapshot.chat_id
        await self.collection.replace_one({"_id": snapshot.chat_id}, doc, upsert=True)
        self.logger.info(f"Saved snapshot {snapshot.chat_id} to MongoDB.")

    async def load_snapshot(self, chat_id: str) -> Optional[ChatSnapshot]:
        doc = await self.collection.find_one({"_id": chat_id})
        if doc:
            doc.pop("_id", None)  # remove _id for from_dict
            return ChatSnapshot.from_dict(doc)
        return None

    async def list_snapshots(self) -> List[Dict[str, Any]]:
        cursor = self.collection.find({}, {"_id": 1, "chat_type": 1, "timestamp": 1, "is_terminated": 1, "messages": 1})
        results = []
        async for doc in cursor:
            results.append({
                "chat_id": doc["_id"],
                "chat_type": doc.get("chat_type"),
                "timestamp": doc.get("timestamp"),
                "is_terminated": doc.get("is_terminated", False),
                "message_count": len(doc.get("messages", [])),
            })
        return results

    async def delete_snapshot(self, chat_id: str) -> bool:
        result = await self.collection.delete_one({"_id": chat_id})
        return result.deleted_count > 0
