# Minimal example of using ChatSnapshot
from datetime import datetime
from chatsnapshot.snapshot import ChatSnapshot, StorageBackend
from chatsnapshot.manager import AG2ChatPersistence

# Example: Basic usage with JSON storage
persistence = AG2ChatPersistence(storage_backend=StorageBackend.JSON)

# Example: SQLite storage with custom path
persistence_sqlite = AG2ChatPersistence(
    storage_backend=StorageBackend.SQLITE,
    storage_config={"db_path": "./my_chats.db"}
)

# Example snapshot creation
example_snapshot = ChatSnapshot(
    chat_id="example_chat_001",
    chat_type="group",
    timestamp=datetime.now(),
    messages=[
        {"role": "user", "content": "Hello", "name": "Agent1"},
        {"role": "assistant", "content": "Hi there!", "name": "Agent2"}
    ],
    metadata={"purpose": "testing", "version": "1.0"}
)

# Save and load example
persistence.storage_adapter.save_snapshot(example_snapshot)
loaded = persistence.load_conversation("example_chat_001")
print(f"Loaded snapshot: {loaded.chat_id if loaded else 'None'}")

# List all conversations
conversations = persistence.list_conversations()
print(f"Saved conversations: {conversations}")
