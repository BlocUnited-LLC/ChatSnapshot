# /src/chatsnapshot/storage/memory_adapter.py
# In-memory storage adapter
from typing import Dict, Optional, List
from ..snapshot import ChatSnapshot
from .base import StorageAdapter

class MemoryStorageAdapter(StorageAdapter):
    """In-memory storage adapter for testing and temporary storage"""

    def __init__(self):
        self._storage: Dict[str, ChatSnapshot] = {}

    def save_snapshot(self, snapshot: ChatSnapshot) -> None:
        self._storage[snapshot.chat_id] = snapshot

    def load_snapshot(self, chat_id: str) -> Optional[ChatSnapshot]:
        return self._storage.get(chat_id)

    def list_snapshots(self) -> List[Dict[str, any]]:
        return [{
            'chat_id': s.chat_id,
            'chat_type': s.chat_type,
            'timestamp': s.timestamp.isoformat(),
            'message_count': len(s.messages),
            'is_terminated': s.is_terminated
        } for s in self._storage.values()]

    def delete_snapshot(self, chat_id: str) -> bool:
        if chat_id in self._storage:
            del self._storage[chat_id]
            return True
        return False
