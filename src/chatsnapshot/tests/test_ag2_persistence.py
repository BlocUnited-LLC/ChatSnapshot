# /src/chatsnapshot/tests/test_ag2_persistence.py
# Comprehensive test suite for AG2 Chat Persistence System

import unittest
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import json
import sqlite3
import sys
from pathlib import Path as _Path

# Ensure project root is on the path for local imports
sys.path.append(str(_Path(__file__).resolve().parents[2]))
from dotenv import load_dotenv
load_dotenv()

# Import the persistence system
from ag2_persistence import (
    ChatSnapshot, StorageBackend, JSONStorageAdapter, 
    SQLiteStorageAdapter, MemoryStorageAdapter, AG2ChatPersistence,
    PersistentChatMixin
)


class TestChatSnapshot(unittest.TestCase):
    """Test the ChatSnapshot data model"""
    
    def test_snapshot_creation(self):
        """Test creating a basic snapshot"""
        snapshot = ChatSnapshot(
            chat_id="test_001",
            chat_type="direct",
            timestamp=datetime.now(),
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        self.assertEqual(snapshot.chat_id, "test_001")
        self.assertEqual(snapshot.chat_type, "direct")
        self.assertEqual(len(snapshot.messages), 1)
        self.assertFalse(snapshot.is_terminated)
    
    def test_snapshot_serialization(self):
        """Test converting snapshot to/from dict"""
        original = ChatSnapshot(
            chat_id="test_002",
            chat_type="group",
            timestamp=datetime.now(),
            messages=[{"role": "assistant", "content": "Hi", "name": "Agent1"}],
            metadata={"session": "test"},
            last_speaker="Agent1",
            round_count=5
        )
        
        # Convert to dict and back
        data = original.to_dict()
        restored = ChatSnapshot.from_dict(data)
        
        self.assertEqual(original.chat_id, restored.chat_id)
        self.assertEqual(original.chat_type, restored.chat_type)
        self.assertEqual(original.messages, restored.messages)
        self.assertEqual(original.metadata, restored.metadata)
        self.assertEqual(original.round_count, restored.round_count)


class TestStorageAdapters(unittest.TestCase):
    """Test different storage adapter implementations"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_snapshot = ChatSnapshot(
            chat_id="adapter_test_001",
            chat_type="direct",
            timestamp=datetime.now(),
            messages=[
                {"role": "user", "content": "Test message 1"},
                {"role": "assistant", "content": "Test response 1"}
            ],
            metadata={"test": True}
        )
    
    def test_memory_adapter(self):
        """Test in-memory storage adapter"""
        adapter = MemoryStorageAdapter()
        
        # Test save
        adapter.save_snapshot(self.test_snapshot)
        
        # Test load
        loaded = adapter.load_snapshot("adapter_test_001")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.chat_id, self.test_snapshot.chat_id)
        
        # Test list
        snapshots = adapter.list_snapshots()
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0]['chat_id'], "adapter_test_001")
        
        # Test delete
        result = adapter.delete_snapshot("adapter_test_001")
        self.assertTrue(result)
        self.assertIsNone(adapter.load_snapshot("adapter_test_001"))
    
    def test_json_adapter(self):
        """Test JSON file storage adapter"""
        with tempfile.TemporaryDirectory() as temp_dir:
            adapter = JSONStorageAdapter(storage_dir=temp_dir)
            
            # Test save
            adapter.save_snapshot(self.test_snapshot)
            
            # Verify file exists
            file_path = Path(temp_dir) / "adapter_test_001.json"
            self.assertTrue(file_path.exists())
            
            # Test load
            loaded = adapter.load_snapshot("adapter_test_001")
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.messages, self.test_snapshot.messages)
            
            # Test list
            snapshots = adapter.list_snapshots()
            self.assertEqual(len(snapshots), 1)
            
            # Test delete
            result = adapter.delete_snapshot("adapter_test_001")
            self.assertTrue(result)
            self.assertFalse(file_path.exists())
    
    def test_sqlite_adapter(self):
        """Test SQLite storage adapter"""
        with tempfile.NamedTemporaryFile(suffix='.db') as temp_db:
            adapter = SQLiteStorageAdapter(db_path=temp_db.name)
            
            # Test save
            adapter.save_snapshot(self.test_snapshot)
            
            # Test load
            loaded = adapter.load_snapshot("adapter_test_001")
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.metadata, self.test_snapshot.metadata)
            
            # Test update (save with same ID)
            self.test_snapshot.messages.append({"role": "user", "content": "Another message"})
            adapter.save_snapshot(self.test_snapshot)
            
            loaded = adapter.load_snapshot("adapter_test_001")
            self.assertEqual(len(loaded.messages), 3)
            
            # Test list
            snapshots = adapter.list_snapshots()
            self.assertEqual(len(snapshots), 1)
            self.assertEqual(snapshots[0]['message_count'], 3)


class TestAG2ChatPersistence(unittest.TestCase):
    """Test the main persistence manager"""
    
    def setUp(self):
        """Set up test fixtures with mock AG2 agents"""
        # Mock ConversableAgent
        self.mock_agent1 = Mock()
        self.mock_agent1.name = "Agent1"
        self.mock_agent1.system_message = "I am Agent 1"
        self.mock_agent1.human_input_mode = "NEVER"
        self.mock_agent1._oai_messages = {}
        self.mock_agent1.llm_config = {"model": "gpt-4"}
        self.mock_agent1.context_variables = {"key1": "value1"}
        
        self.mock_agent2 = Mock()
        self.mock_agent2.name = "Agent2"
        self.mock_agent2.system_message = "I am Agent 2"
        self.mock_agent2._oai_messages = {
            self.mock_agent1: [
                {"role": "user", "content": "Hello from Agent1", "name": "Agent1"},
                {"role": "assistant", "content": "Hi Agent1!", "name": "Agent2"}
            ]
        }
        
        # Mock GroupChat
        self.mock_groupchat = Mock()
        self.mock_groupchat.agents = [self.mock_agent1, self.mock_agent2]
        self.mock_groupchat.messages = [
            {"role": "user", "content": "Start discussion", "name": "Agent1"},
            {"role": "assistant", "content": "Let's begin", "name": "Agent2"}
        ]
        self.mock_groupchat.max_round = 10
        self.mock_groupchat.admin_name = "Admin"
        self.mock_groupchat.speaker_selection_method = "auto"
        self.mock_groupchat.allowed_speaker_transitions_dict = {
            "Agent1": ["Agent2"],
            "Agent2": ["Agent1"]
        }
        
        # Mock GroupChatManager
        self.mock_manager = Mock()
        self.mock_manager.last_speaker = self.mock_agent2
    
    def test_save_and_load_conversation(self):
        """Test saving and loading a basic conversation"""
        persistence = AG2ChatPersistence(storage_backend=StorageBackend.MEMORY)
        
        # Save conversation
        snapshot = persistence.save_conversation(
            chat_id="test_conv_001",
            agents=self.mock_agent1,
            messages=[{"role": "user", "content": "Test"}],
            metadata={"session": "test"}
        )
        
        self.assertEqual(snapshot.chat_id, "test_conv_001")
        self.assertEqual(snapshot.chat_type, "direct")
        
        # Load conversation
        loaded = persistence.load_conversation("test_conv_001")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.messages[0]["content"], "Test")
    
    def test_save_and_load_groupchat(self):
        """Test saving and loading a group chat"""
        persistence = AG2ChatPersistence(storage_backend=StorageBackend.MEMORY)
        
        # Save group chat
        snapshot = persistence.save_groupchat(
            chat_id="test_group_001",
            groupchat=self.mock_groupchat,
            manager=self.mock_manager,
            metadata={"project": "test"}
        )
        
        self.assertEqual(snapshot.chat_type, "group")
        self.assertEqual(snapshot.speaker_selection_method, "auto")
        self.assertEqual(snapshot.last_speaker, "Agent2")
        self.assertEqual(len(snapshot.messages), 2)
        
        # Verify speaker transitions saved
        self.assertIn("Agent1", snapshot.speaker_transitions)
        self.assertEqual(snapshot.speaker_transitions["Agent1"], ["Agent2"])
    
    def test_restore_conversation(self):
        """Test restoring conversation state to agents"""
        persistence = AG2ChatPersistence(storage_backend=StorageBackend.MEMORY)
        
        # Create a snapshot
        snapshot = ChatSnapshot(
            chat_id="restore_test_001",
            chat_type="group",
            timestamp=datetime.now(),
            messages=[
                {"role": "user", "content": "Message 1", "name": "Agent1"},
                {"role": "assistant", "content": "Response 1", "name": "Agent2"}
            ],
            context_variables={
                "Agent1": {"restored_key": "restored_value"}
            }
        )
        
        # Mock agents with clear_history method
        mock_agent1 = Mock()
        mock_agent1.name = "Agent1"
        mock_agent1.clear_history = Mock()
        mock_agent1._oai_messages = {}
        mock_agent1.context_variables = {}
        
        mock_agent2 = Mock()
        mock_agent2.name = "Agent2"
        mock_agent2.clear_history = Mock()
        mock_agent2._oai_messages = {}
        
        # Restore conversation
        persistence.restore_conversation(snapshot, [mock_agent1, mock_agent2])
        
        # Verify clear_history was called
        mock_agent1.clear_history.assert_called_once()
        mock_agent2.clear_history.assert_called_once()
        
        # Verify messages were restored
        self.assertIn(mock_agent1, mock_agent2._oai_messages)
        self.assertEqual(len(mock_agent2._oai_messages[mock_agent1]), 2)
        
        # Verify context variables restored
        self.assertEqual(mock_agent1.context_variables.get("restored_key"), "restored_value")
    
    def test_list_and_delete_conversations(self):
        """Test listing and deleting conversations"""
        persistence = AG2ChatPersistence(storage_backend=StorageBackend.MEMORY)
        
        # Save multiple conversations
        for i in range(3):
            persistence.save_conversation(
                chat_id=f"list_test_{i:03d}",
                agents=self.mock_agent1,
                messages=[{"content": f"Message {i}"}]
            )
        
        # List conversations
        conversations = persistence.list_conversations()
        self.assertEqual(len(conversations), 3)
        
        # Delete one conversation
        result = persistence.delete_conversation("list_test_001")
        self.assertTrue(result)
        
        # Verify deletion
        conversations = persistence.list_conversations()
        self.assertEqual(len(conversations), 2)
        self.assertIsNone(persistence.load_conversation("list_test_001"))


class TestPersistentChatMixin(unittest.TestCase):
    """Test the PersistentChatMixin functionality"""
    
    def test_mixin_integration(self):
        """Test integrating persistence mixin with mock agent"""
        
        # Create a test class using the mixin
        class TestPersistentAgent(PersistentChatMixin):
            def __init__(self, name, **kwargs):
                self.name = name
                self.chat_messages = []
                super().__init__(**kwargs)
        
        # Create agent with persistence
        agent = TestPersistentAgent(
            name="TestAgent",
            persistence_manager=AG2ChatPersistence(storage_backend=StorageBackend.MEMORY)
        )
        
        # Set chat ID
        agent.set_chat_id("mixin_test_001")
        
        # Add some messages
        agent.chat_messages = [
            {"role": "user", "content": "Test message"},
            {"role": "assistant", "content": "Test response"}
        ]
        
        # Save state
        snapshot = agent.save_state(metadata={"test": True})
        self.assertEqual(snapshot.chat_id, "mixin_test_001")
        self.assertEqual(len(snapshot.messages), 2)
        
        # Clear messages
        agent.chat_messages = []
        
        # Load state
        loaded_snapshot = agent.load_state()
        self.assertIsNotNone(loaded_snapshot)
        # Note: In real implementation, messages would be restored


class TestIntegrationScenarios(unittest.TestCase):
    """Integration tests simulating real AG2 usage scenarios"""
    
    @patch('autogen.ConversableAgent')
    @patch('autogen.GroupChat')
    @patch('autogen.GroupChatManager')
    def test_full_groupchat_scenario(self, MockManager, MockGroupChat, MockAgent):
        """Test a complete group chat save and restore scenario"""
        
        # Setup mock agents
        agent1 = Mock()
        agent1.name = "Coder"
        agent1.system_message = "I write code"
        agent1._oai_messages = {}
        agent1.clear_history = Mock()
        
        agent2 = Mock()
        agent2.name = "Reviewer"
        agent2.system_message = "I review code"
        agent2._oai_messages = {}
        agent2.clear_history = Mock()
        
        # Setup mock group chat
        groupchat = Mock()
        groupchat.agents = [agent1, agent2]
        groupchat.messages = [
            {"role": "user", "content": "Write hello world", "name": "Coder"},
            {"role": "assistant", "content": "print('Hello, World!')", "name": "Coder"},
            {"role": "user", "content": "Looks good!", "name": "Reviewer"}
        ]
        groupchat.max_round = 20
        groupchat.speaker_selection_method = "round_robin"
        groupchat.reset = Mock()
        
        # Setup manager
        manager = Mock()
        manager.last_speaker = agent2
        manager.resume = Mock()
        
        # Initialize persistence
        with tempfile.TemporaryDirectory() as temp_dir:
            persistence = AG2ChatPersistence(
                storage_backend=StorageBackend.JSON,
                storage_config={"storage_dir": temp_dir}
            )
            
            # Save the group chat
            snapshot = persistence.save_groupchat(
                chat_id="code_review_session_001",
                groupchat=groupchat,
                manager=manager,
                metadata={
                    "project": "HelloWorld",
                    "date": datetime.now().isoformat(),
                    "participants": ["Coder", "Reviewer"]
                }
            )
            
            # Verify save
            self.assertEqual(snapshot.chat_type, "group")
            self.assertEqual(len(snapshot.messages), 3)
            self.assertEqual(snapshot.last_speaker, "Reviewer")
            
            # Simulate new session - create fresh instances
            new_groupchat = Mock()
            new_groupchat.agents = [agent1, agent2]
            new_groupchat.messages = []
            new_groupchat.reset = Mock()
            
            new_manager = Mock()
            new_manager.resume = Mock()
            
            # Restore the group chat
            loaded_snapshot = persistence.load_conversation("code_review_session_001")
            self.assertIsNotNone(loaded_snapshot)
            
            persistence.restore_groupchat(loaded_snapshot, new_groupchat, new_manager)
            
            # Verify restoration
            new_groupchat.reset.assert_called_once()
            agent1.clear_history.assert_called()
            agent2.clear_history.assert_called()
            new_manager.resume.assert_called_once_with(loaded_snapshot.messages)


# Example usage functions for documentation
def example_basic_usage():
    """Example: Basic persistence usage"""
    print("=== Basic Persistence Example ===")
    
    # Initialize persistence with JSON storage
    persistence = AG2ChatPersistence(
        storage_backend=StorageBackend.JSON,
        storage_config={"storage_dir": "./chat_history"}
    )
    
    # Create a test snapshot
    snapshot = ChatSnapshot(
        chat_id="example_chat_001",
        chat_type="direct",
        timestamp=datetime.now(),
        messages=[
            {"role": "user", "content": "What's the weather?"},
            {"role": "assistant", "content": "I don't have access to weather data."}
        ],
        metadata={"topic": "weather", "user": "test_user"}
    )
    
    # Save it
    persistence.storage_adapter.save_snapshot(snapshot)
    print(f"Saved chat: {snapshot.chat_id}")
    
    # Load it back
    loaded = persistence.load_conversation("example_chat_001")
    if loaded:
        print(f"Loaded {len(loaded.messages)} messages")
        print(f"Metadata: {loaded.metadata}")
    
    # List all chats
    all_chats = persistence.list_conversations()
    print(f"\nAll saved chats: {len(all_chats)}")
    for chat in all_chats:
        print(f"  - {chat['chat_id']}: {chat['message_count']} messages")


def example_with_mock_agents():
    """Example: Using persistence with mock AG2 agents"""
    print("\n=== Mock Agent Persistence Example ===")
    
    # Create mock agents
    agent1 = Mock()
    agent1.name = "Assistant"
    agent1.system_message = "I am a helpful assistant"
    agent1._oai_messages = {}
    agent1.clear_history = Mock()
    
    agent2 = Mock()
    agent2.name = "User"
    agent2._oai_messages = {
        agent1: [
            {"role": "user", "content": "Hello!", "name": "User"},
            {"role": "assistant", "content": "Hi there!", "name": "Assistant"}
        ]
    }
    agent2.clear_history = Mock()
    
    # Create persistence manager
    persistence = AG2ChatPersistence(storage_backend=StorageBackend.MEMORY)
    
    # Save conversation
    snapshot = persistence.save_conversation(
        chat_id="mock_chat_001",
        agents=[agent1, agent2],
        metadata={"session": "test"}
    )
    
    print(f"Saved conversation with {len(snapshot.messages)} messages")
    print(f"Agent states captured: {list(snapshot.agent_states.keys())}")
    
    # Restore to new agents
    new_agent1 = Mock()
    new_agent1.name = "Assistant"
    new_agent1._oai_messages = {}
    new_agent1.clear_history = Mock()
    
    new_agent2 = Mock()
    new_agent2.name = "User"
    new_agent2._oai_messages = {}
    new_agent2.clear_history = Mock()
    
    persistence.restore_conversation(snapshot, [new_agent1, new_agent2])
    print("Conversation restored to new agents")


# Run tests and examples
if __name__ == "__main__":
    # Run unit tests
    print("Running unit tests...\n")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run examples
    print("\n" + "="*50 + "\n")
    example_basic_usage()
    example_with_mock_agents()
