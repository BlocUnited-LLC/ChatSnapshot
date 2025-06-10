"""Compatibility package that re-exports ChatSnapshot modules."""

import os
import sys

# Ensure the project `src` directory is on the import path so that the
# `chatsnapshot` package can be imported even when this repository is used
# without installation (e.g. during tests).
SRC_PATH = os.path.join(os.path.dirname(__file__), "src")
if not os.path.isdir(SRC_PATH):
    SRC_PATH = os.path.join(os.path.dirname(__file__), "..", "src")
if SRC_PATH not in sys.path:
    sys.path.append(SRC_PATH)

from chatsnapshot.snapshot import ChatSnapshot, StorageBackend
from chatsnapshot.manager import AG2ChatPersistence
from chatsnapshot.persistent_mixin import PersistentChatMixin
from chatsnapshot.storage.json_adapter import JSONStorageAdapter
from chatsnapshot.storage.sqlite_adapter import SQLiteStorageAdapter
from chatsnapshot.storage.memory_adapter import MemoryStorageAdapter
from chatsnapshot.storage.mongodb_adapter import MongoDBStorageAdapter

__all__ = [
    "ChatSnapshot",
    "StorageBackend",
    "AG2ChatPersistence",
    "PersistentChatMixin",
    "JSONStorageAdapter",
    "SQLiteStorageAdapter",
    "MemoryStorageAdapter",
    "MongoDBStorageAdapter",
]
