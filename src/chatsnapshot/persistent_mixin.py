# /src/chatsnapshot/persistent_mixin.py
# PersistentChatMixin for agent integration
from typing import Optional, Dict
from .manager import AG2ChatPersistence
from .snapshot import ChatSnapshot

class PersistentChatMixin:
    """Mixin class to add persistence capabilities to AG2 agents"""

    def __init__(self, *args, persistence_manager: Optional[AG2ChatPersistence] = None, **kwargs):
        # Do not call super().__init__ here to avoid interfering with
        # multiple inheritance initialization order.
        self._persistence_manager = persistence_manager or AG2ChatPersistence()
        self._chat_id = None

    def set_chat_id(self, chat_id: str):
        self._chat_id = chat_id

    def save_state(self, metadata: Optional[Dict[str, any]] = None) -> ChatSnapshot:
        if not self._chat_id:
            raise ValueError("Chat ID not set. Call set_chat_id() first.")
        return self._persistence_manager.save_conversation(
            chat_id=self._chat_id,
            agents=self,
            messages=self.chat_messages if hasattr(self, 'chat_messages') else [],
            metadata=metadata
        )

    def load_state(self, chat_id: Optional[str] = None) -> Optional[ChatSnapshot]:
        chat_id = chat_id or self._chat_id
        if not chat_id:
            raise ValueError("No chat ID provided")
        snapshot = self._persistence_manager.load_conversation(chat_id)
        if snapshot:
            self._persistence_manager.restore_conversation(snapshot, self)
            self._chat_id = chat_id
        return snapshot
