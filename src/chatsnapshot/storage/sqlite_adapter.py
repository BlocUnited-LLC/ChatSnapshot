# /src/chatsnapshot/storage/sqlite_adapter.py
# SQLite storage adapter
import json
import sqlite3
from pathlib import Path
from typing import Union, Optional, List, Dict
from ..snapshot import ChatSnapshot
from .base import StorageAdapter

class SQLiteStorageAdapter(StorageAdapter):
    """SQLite database storage adapter"""

    def __init__(self, db_path: Union[str, Path] = "./ag2_chat_states.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_snapshots (
                    chat_id TEXT PRIMARY KEY,
                    chat_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    data TEXT NOT NULL,
                    is_terminated BOOLEAN DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON chat_snapshots(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_type ON chat_snapshots(chat_type)
            """)

    def save_snapshot(self, snapshot: ChatSnapshot) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO chat_snapshots (chat_id, chat_type, timestamp, data, is_terminated)
                VALUES (?, ?, ?, ?, ?)
            """, (
                snapshot.chat_id,
                snapshot.chat_type,
                snapshot.timestamp.isoformat(),
                json.dumps(snapshot.to_dict()),
                snapshot.is_terminated
            ))

    def load_snapshot(self, chat_id: str) -> Optional[ChatSnapshot]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT data FROM chat_snapshots WHERE chat_id = ?",
                (chat_id,)
            )
            row = cursor.fetchone()
            if row:
                data = json.loads(row[0])
                return ChatSnapshot.from_dict(data)
        return None

    def list_snapshots(self) -> List[Dict[str, any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT chat_id, chat_type, timestamp, is_terminated, data
                FROM chat_snapshots
                ORDER BY timestamp DESC
            """)
            snapshots = []
            for row in cursor:
                data = json.loads(row[4])
                snapshots.append({
                    'chat_id': row[0],
                    'chat_type': row[1],
                    'timestamp': row[2],
                    'is_terminated': bool(row[3]),
                    'message_count': len(data.get('messages', []))
                })
        return snapshots

    def delete_snapshot(self, chat_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM chat_snapshots WHERE chat_id = ?",
                (chat_id,)
            )
            return cursor.rowcount > 0
