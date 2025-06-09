# /src/chatsnapshot/manager.py
# AG2ChatPersistence manager logic
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from .snapshot import ChatSnapshot, StorageBackend
from .storage.json_adapter import JSONStorageAdapter
from .storage.sqlite_adapter import SQLiteStorageAdapter
from .storage.memory_adapter import MemoryStorageAdapter

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from autogen import ConversableAgent, GroupChat, GroupChatManager

class AG2ChatPersistence:
    """Main persistence manager for AG2 chats"""

    def __init__(self, 
                 storage_backend: StorageBackend = StorageBackend.JSON,
                 storage_config: Optional[Dict[str, Any]] = None):
        self.storage_backend = storage_backend
        self.storage_adapter = self._create_storage_adapter(storage_config or {})
        self.logger = logging.getLogger(__name__)

    def _create_storage_adapter(self, config: Dict[str, Any]):
        if self.storage_backend == StorageBackend.JSON:
            return JSONStorageAdapter(**config)
        elif self.storage_backend == StorageBackend.SQLITE:
            return SQLiteStorageAdapter(**config)
        elif self.storage_backend == StorageBackend.MEMORY:
            return MemoryStorageAdapter()
        else:
            raise ValueError(f"Unsupported storage backend: {self.storage_backend}")

    def save_conversation(self,
                         chat_id: str,
                         agents: Union[List['ConversableAgent'], 'ConversableAgent'],
                         messages: Optional[List[Dict[str, Any]]] = None,
                         metadata: Optional[Dict[str, Any]] = None,
                         **kwargs) -> ChatSnapshot:
        if isinstance(agents, list):
            chat_type = "group"
            all_messages = self._extract_group_messages(agents, messages)
        else:
            chat_type = "direct"
            all_messages = messages or []

        agent_states = self._extract_agent_states(agents)
        context_vars = self._extract_context_variables(agents)

        snapshot = ChatSnapshot(
            chat_id=chat_id,
            chat_type=chat_type,
            timestamp=datetime.now(),
            messages=all_messages,
            metadata=metadata or {},
            agent_states=agent_states,
            context_variables=context_vars,
            **kwargs
        )

        self.storage_adapter.save_snapshot(snapshot)
        self.logger.info(f"Saved chat snapshot: {chat_id}")

        return snapshot

    def save_groupchat(self,
                      chat_id: str,
                      groupchat: 'GroupChat',
                      manager: Optional['GroupChatManager'] = None,
                      metadata: Optional[Dict[str, Any]] = None) -> ChatSnapshot:
        snapshot = self.save_conversation(
            chat_id=chat_id,
            agents=groupchat.agents,
            messages=groupchat.messages,
            metadata=metadata,
            speaker_selection_method=str(groupchat.speaker_selection_method),
            max_round=groupchat.max_round,
            admin_name=groupchat.admin_name,
            speaker_transitions=groupchat.allowed_speaker_transitions_dict,
            last_speaker=manager.last_speaker.name if manager and hasattr(manager, 'last_speaker') else None,
            round_count=len(groupchat.messages)
        )
        return snapshot

    def load_conversation(self, chat_id: str) -> Optional[ChatSnapshot]:
        snapshot = self.storage_adapter.load_snapshot(chat_id)
        if snapshot:
            self.logger.info(f"Loaded chat snapshot: {chat_id}")
        return snapshot

    def restore_conversation(self,
                           snapshot: ChatSnapshot,
                           agents: Union[List['ConversableAgent'], 'ConversableAgent']) -> None:
        if isinstance(agents, list):
            self._restore_group_chat(snapshot, agents)
        else:
            self._restore_direct_chat(snapshot, agents)
        self._restore_context_variables(snapshot, agents)
        self.logger.info(f"Restored chat state: {snapshot.chat_id}")

    def restore_groupchat(self,
                         snapshot: ChatSnapshot,
                         groupchat: 'GroupChat',
                         manager: 'GroupChatManager') -> None:
        groupchat.reset()
        for agent in groupchat.agents:
            if hasattr(agent, 'clear_history'):
                agent.clear_history()
        groupchat.messages = snapshot.messages.copy()
        self._restore_group_chat(snapshot, groupchat.agents)
        if hasattr(manager, 'resume') and snapshot.messages:
            manager.resume(snapshot.messages)
        self.logger.info(f"Restored GroupChat state: {snapshot.chat_id}")

    def list_conversations(self) -> List[Dict[str, Any]]:
        return self.storage_adapter.list_snapshots()

    def delete_conversation(self, chat_id: str) -> bool:
        result = self.storage_adapter.delete_snapshot(chat_id)
        if result:
            self.logger.info(f"Deleted chat snapshot: {chat_id}")
        return result

    def _extract_group_messages(self, 
                               agents: List['ConversableAgent'],
                               additional_messages: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        all_messages = []
        for agent in agents:
            if hasattr(agent, '_oai_messages'):
                for other_agent, messages in agent._oai_messages.items():
                    for msg in messages:
                        if 'name' not in msg:
                            msg['name'] = agent.name
                        all_messages.append(msg)
        if additional_messages:
            all_messages.extend(additional_messages)
        all_messages.sort(key=lambda x: x.get('timestamp', 0))
        return all_messages

    def _extract_agent_states(self, 
                             agents: Union[List['ConversableAgent'], 'ConversableAgent']) -> Dict[str, Dict[str, Any]]:
        agent_states = {}
        if not isinstance(agents, list):
            agents = [agents]
        for agent in agents:
            state = {
                'name': agent.name,
                'system_message': agent.system_message if hasattr(agent, 'system_message') else None,
                'human_input_mode': agent.human_input_mode if hasattr(agent, 'human_input_mode') else None,
                'max_consecutive_auto_reply': agent.max_consecutive_auto_reply() if hasattr(agent, 'max_consecutive_auto_reply') else None,
                'llm_config': agent.llm_config if hasattr(agent, 'llm_config') else None,
            }
            if hasattr(agent, 'function_map'):
                state['function_names'] = list(agent.function_map.keys())
            agent_states[agent.name] = state
        return agent_states

    def _extract_context_variables(self,
                                  agents: Union[List['ConversableAgent'], 'ConversableAgent']) -> Dict[str, Any]:
        context_vars = {}
        if not isinstance(agents, list):
            agents = [agents]
        for agent in agents:
            if hasattr(agent, 'context_variables'):
                context_vars[agent.name] = dict(agent.context_variables)
        return context_vars

    def _restore_group_chat(self, snapshot: ChatSnapshot, agents: List['ConversableAgent']) -> None:
        agent_map = {agent.name: agent for agent in agents}
        for agent in agents:
            if hasattr(agent, 'clear_history'):
                agent.clear_history()
        for msg in snapshot.messages:
            sender_name = msg.get('name')
            if sender_name and sender_name in agent_map:
                sender = agent_map[sender_name]
                for recipient_name, recipient in agent_map.items():
                    if recipient_name != sender_name:
                        if hasattr(recipient, '_oai_messages'):
                            if sender not in recipient._oai_messages:
                                recipient._oai_messages[sender] = []
                            recipient._oai_messages[sender].append(msg)

    def _restore_direct_chat(self, snapshot: ChatSnapshot, agent: 'ConversableAgent') -> None:
        if hasattr(agent, 'clear_history'):
            agent.clear_history()
        other_agent_name = snapshot.metadata.get('other_agent')
        if other_agent_name and hasattr(agent, '_oai_messages'):
            agent._oai_messages[other_agent_name] = snapshot.messages

    def _restore_context_variables(self,
                                  snapshot: ChatSnapshot,
                                  agents: Union[List['ConversableAgent'], 'ConversableAgent']) -> None:
        if not isinstance(agents, list):
            agents = [agents]
        for agent in agents:
            if hasattr(agent, 'context_variables') and agent.name in snapshot.context_variables:
                for key, value in snapshot.context_variables[agent.name].items():
                    agent.context_variables[key] = value
