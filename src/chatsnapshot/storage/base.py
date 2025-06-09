# /src/chatsnapshot/storage/base.py
# Abstract StorageAdapter base class
from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from ..snapshot import ChatSnapshot

class StorageAdapter(ABC):
    """Abstract base class for storage adapters"""

    @abstractmethod
    def save_snapshot(self, snapshot: ChatSnapshot) -> None:
        pass

    @abstractmethod
    def load_snapshot(self, chat_id: str) -> Optional[ChatSnapshot]:
        pass

    @abstractmethod
    def list_snapshots(self) -> List[Dict[str, any]]:
        pass

    @abstractmethod
    def delete_snapshot(self, chat_id: str) -> bool:
        pass
