# /src/chatsnapshot/ingest/__init__.py
# Framework-specific ingest adapters

from .base import IngestAdapter
from .ag2 import AG2IngestAdapter

__all__ = [
    "IngestAdapter",
    "AG2IngestAdapter",
]
