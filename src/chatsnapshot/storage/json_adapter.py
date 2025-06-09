# /src/chatsnapshot/storage/json_adapter.py
# JSON file storage adapter

import json
import logging
from pathlib import Path
from typing import Union, Optional, List, Dict
from ..snapshot import ChatSnapshot
from .base import StorageAdapter

class JSONStorageAdapter(StorageAdapter):
    """JSON file-based storage adapter"""

    def __init__(self, storage_dir: Union[str, Path] = "./ag2_chat_states"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, chat_id: str) -> Path:
        return self.storage_dir / f"{chat_id}.json"

    def save_snapshot(self, snapshot: ChatSnapshot) -> None:
        file_path = self._get_file_path(snapshot.chat_id)
        with open(file_path, 'w') as f:
            json.dump(snapshot.to_dict(), f, indent=2)

    def load_snapshot(self, chat_id: str) -> Optional[ChatSnapshot]:
        file_path = self._get_file_path(chat_id)
        if not file_path.exists():
            return None
        with open(file_path, 'r') as f:
            data = json.load(f)
        return ChatSnapshot.from_dict(data)

    def list_snapshots(self) -> List[Dict[str, any]]:
        snapshots = []
        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                snapshots.append({
                    'chat_id': data['chat_id'],
                    'chat_type': data['chat_type'],
                    'timestamp': data['timestamp'],
                    'message_count': len(data.get('messages', [])),
                    'is_terminated': data.get('is_terminated', False)
                })
            except Exception as e:
                logging.error(f"Error reading snapshot {file_path}: {e}")
        return snapshots

    def delete_snapshot(self, chat_id: str) -> bool:
        file_path = self._get_file_path(chat_id)
        if file_path.exists():
            file_path.unlink()
            return True
        return False
