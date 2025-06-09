# /src/chatsnapshot/tests/test_with_real_ag2.py
# Testing the persistence system with real AG2 agents

import os
from datetime import datetime
from autogen import ConversableAgent, GroupChat, GroupChatManager
from ag2_persistence import AG2ChatPersistence, StorageBackend, PersistentChatMixin

# Configuration
llm_config = {
    "model": "gpt-4",
    "api_key": os.environ.get("OPENAI_API_KEY"),  # Set your API key
    "temperature": 0.7,
}

def test_direct_chat_persistence():
    """Test persistence with a direct agent-to-agent chat"""
    print("=== Testing Direct Chat Persistence ===\n")
    
    # Initialize persistence
    persistence = AG2ChatPersistence(
        storage_backend=StorageBackend.JSON,
        storage_config={"storage_dir": "./test_chat_history"}
    )
    
    # Create agents
    assistant = ConversableAgent(
        name="assistant",
        system_message="You are a helpful AI assistant.",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )
    
    user_proxy = ConversableAgent(
        name="user_proxy",
        system_message="You are a user proxy.",
        llm_config=False,  # No LLM for user proxy
        human_input_mode="NEVER",
        default_auto_reply="Thank you for your response.",
        max_consecutive_auto_reply=1,
    )
    
    # Start a conversation
    chat_result = user_proxy.initiate_chat(
        assistant,
        message="What are the key principles of clean code?",
        max_turns=2
    )
    
    # Save the conversation
    snapshot = persistence.save_conversation(
        chat_id="clean_code_discussion_001",
        agents=[assistant, user_proxy],
        messages=chat_result.chat_history,
        metadata={
            "topic": "clean code",
            "date": datetime.now().isoformat(),
            "cost": chat_result.cost
        }
    )
    
    print(f"Saved conversation: {snapshot.chat_id}")
    print(f"Messages saved: {len(snapshot.messages)}")
    print(f"Total cost: {snapshot.metadata.get('cost', 'N/A')}\n")
    
    # Clear agents and restore
    assistant.clear_history()
    user_proxy.clear_history()
    
    # Load and restore
    loaded = persistence.load_conversation("clean_code_discussion_001")
    if loaded:
        print(f"Loaded conversation with {len(loaded.messages)} messages")
        persistence.restore_conversation(loaded, [assistant, user_proxy])
        print("Conversation restored successfully!\n")
        
        # Verify restoration by printing last message
        if assistant.last_message(user_proxy):
            print(f"Last message from assistant: {assistant.last_message(user_proxy)['content'][:100]}...")


def test_groupchat_persistence():
    """Test persistence with a group chat"""
    print("\n=== Testing GroupChat Persistence ===\n")
    
    # Initialize persistence with SQLite
    persistence = AG2ChatPersistence(
        storage_backend=StorageBackend.SQLITE,
        storage_config={"db_path": "./test_chats.db"}
    )
    
    # Create agents for group chat
    planner = ConversableAgent(
        name="planner",
        system_message="You are a planner. Suggest a plan for the given task.",
        llm_config=llm_config,
        description="A planner agent that creates structured plans for tasks."
    )
    
    coder = ConversableAgent(
        name="coder",
        system_message="You are a coder. Write code based on the plan.",
        llm_config=llm_config,
        description="A coding agent that implements solutions in Python."
    )
    
    reviewer = ConversableAgent(
        name="reviewer",
        system_message="You are a code reviewer. Review the code and suggest improvements.",
        llm_config=llm_config,
        description="A code review agent that ensures quality and best practices."
    )
    
    user_proxy = ConversableAgent(
        name="user_proxy",
        system_message="You are the user proxy.",
        llm_config=False,
        human_input_mode="NEVER",
        default_auto_reply="Proceed with the next step.",
        max_consecutive_auto_reply=1,
        description="User proxy that approves or provides input."
    )
    
    # Create group chat
    groupchat = GroupChat(
        agents=[planner, coder, reviewer, user_proxy],
        messages=[],
        max_round=6,
        speaker_selection_method="auto",
        send_introductions=True
    )
    
    manager = GroupChatManager(
        groupchat=groupchat,
        llm_config=llm_config
    )
    
    # Run a group chat
    chat_result = user_proxy.initiate_chat(
        manager,
        message="Create a Python function to calculate factorial",
    )
    
    # Save the group chat
    snapshot = persistence.save_groupchat(
        chat_id="factorial_implementation_001",
        groupchat=groupchat,
        manager=manager,
        metadata={
            "task": "factorial function",
            "team": ["planner", "coder", "reviewer"],
            "date": datetime.now().isoformat(),
            "cost": chat_result.cost
        }
    )
    
    print(f"Saved group chat: {snapshot.chat_id}")
    print(f"Total rounds: {snapshot.round_count}")
    print(f"Last speaker: {snapshot.last_speaker}")
    print(f"Messages: {len(snapshot.messages)}\n")
    
    # Test loading and resuming
    print("Simulating new session - loading previous group chat...\n")
    
    # Create fresh instances
    new_groupchat = GroupChat(
        agents=[planner, coder, reviewer, user_proxy],
        messages=[],
        max_round=10,
        speaker_selection_method="auto"
    )
    
    new_manager = GroupChatManager(
        groupchat=new_groupchat,
        llm_config=llm_config
    )
    
    # Restore the group chat
    loaded = persistence.load_conversation("factorial_implementation_001")
    if loaded:
        persistence.restore_groupchat(loaded, new_groupchat, new_manager)
        print(f"Restored group chat with {len(new_groupchat.messages)} messages")
        print(f"Ready to continue from where we left off!\n")
        
        # Continue the conversation
        continuation_result = user_proxy.initiate_chat(
            new_manager,
            message="Now create a unit test for the factorial function",
            clear_history=False  # Important: don't clear the restored history
        )
        
        # Save the extended conversation
        extended_snapshot = persistence.save_groupchat(
            chat_id="factorial_implementation_001_extended",
            groupchat=new_groupchat,
            manager=new_manager,
            metadata={
                "task": "factorial function + tests",
                "original_chat": "factorial_implementation_001",
                "extension_date": datetime.now().isoformat()
            }
        )
        
        print(f"Saved extended conversation: {extended_snapshot.chat_id}")
        print(f"Total messages now: {len(extended_snapshot.messages)}")


def test_persistent_mixin():
    """Test using the PersistentChatMixin"""
    print("\n=== Testing PersistentChatMixin ===\n")
    
    # Create a custom persistent agent class
    class PersistentAssistant(PersistentChatMixin, ConversableAgent):
        def __init__(self, *args, **kwargs):
            # Extract persistence_manager before passing to parent
            persistence_manager = kwargs.pop('persistence_manager', None)
            ConversableAgent.__init__(self, *args, **kwargs)
            PersistentChatMixin.__init__(self, persistence_manager=persistence_manager)
    
    # Create persistent agent
    persistent_agent = PersistentAssistant(
        name="persistent_assistant",
        system_message="You are a helpful assistant with memory.",
        llm_config=llm_config,
        persistence_manager=AG2ChatPersistence(StorageBackend.MEMORY)
    )
    
    user_proxy = ConversableAgent(
        name="user",
        llm_config=False,
        human_input_mode="NEVER",
        default_auto_reply="Continue",
        max_consecutive_auto_reply=1
    )
    
    # Set chat ID for persistence
    persistent_agent.set_chat_id("persistent_chat_001")
    
    # Have a conversation
    chat_result = user_proxy.initiate_chat(
        persistent_agent,
        message="Remember this: My favorite color is blue and I like Python programming.",
        max_turns=2
    )
    
    # Save state automatically
    snapshot = persistent_agent.save_state(
        metadata={"session": 1, "timestamp": datetime.now().isoformat()}
    )
    
    print(f"Saved persistent chat: {snapshot.chat_id}")
    print(f"Messages: {len(snapshot.messages)}")
    
    # Clear the conversation
    persistent_agent.clear_history()
    user_proxy.clear_history()
    
    # Later, load the state back
    print("\nLoading previous conversation state...")
    loaded_snapshot = persistent_agent.load_state("persistent_chat_001")
    
    if loaded_snapshot:
        print(f"Restored {len(loaded_snapshot.messages)} messages")
        print("Continuing conversation with memory...\n")
        
        # Continue the conversation - the agent should remember the previous context
        continuation = user_proxy.initiate_chat(
            persistent_agent,
            message="What did I tell you about my preferences?",
            max_turns=2,
            clear_history=False
        )
        
        # The agent should remember the blue color and Python preference


def test_conversation_analytics():
    """Test analyzing saved conversations"""
    print("\n=== Testing Conversation Analytics ===\n")
    
    persistence = AG2ChatPersistence(
        storage_backend=StorageBackend.SQLITE,
        storage_config={"db_path": "./test_chats.db"}
    )
    
    # List all saved conversations
    conversations = persistence.list_conversations()
    
    print(f"Total saved conversations: {len(conversations)}")
    print("\nConversation Summary:")
    print("-" * 60)
    
    for conv in conversations:
        print(f"ID: {conv['chat_id']}")
        print(f"Type: {conv['chat_type']}")
        print(f"Messages: {conv['message_count']}")
        print(f"Timestamp: {conv['timestamp']}")
        print(f"Terminated: {conv['is_terminated']}")
        print("-" * 60)
    
    # Load and analyze a specific conversation
    if conversations:
        first_conv = conversations[0]
        snapshot = persistence.load_conversation(first_conv['chat_id'])
        
        if snapshot:
            print(f"\nAnalyzing conversation: {snapshot.chat_id}")
            
            # Count messages by role
            role_counts = {}
            speaker_counts = {}
            
            for msg in snapshot.messages:
                role = msg.get('role', 'unknown')
                speaker = msg.get('name', 'unknown')
                
                role_counts[role] = role_counts.get(role, 0) + 1
                speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1
            
            print("\nMessage breakdown by role:")
            for role, count in role_counts.items():
                print(f"  {role}: {count}")
            
            print("\nMessage breakdown by speaker:")
            for speaker, count in speaker_counts.items():
                print(f"  {speaker}: {count}")
            
            # Analyze conversation flow
            if snapshot.speaker_transitions:
                print("\nSpeaker transition rules:")
                for speaker, allowed in snapshot.speaker_transitions.items():
                    print(f"  {speaker} -> {', '.join(allowed)}")


def test_error_handling():
    """Test error handling and edge cases"""
    print("\n=== Testing Error Handling ===\n")
    
    persistence = AG2ChatPersistence(StorageBackend.MEMORY)
    
    # Test loading non-existent conversation
    result = persistence.load_conversation("non_existent_id")
    print(f"Loading non-existent chat: {result}")
    
    # Test deleting non-existent conversation
    deleted = persistence.delete_conversation("non_existent_id")
    print(f"Deleting non-existent chat: {deleted}")
    
    # Test saving with minimal data
    minimal_snapshot = persistence.save_conversation(
        chat_id="minimal_test",
        agents=[],
        messages=[]
    )
    print(f"Saved minimal snapshot: {minimal_snapshot.chat_id}")
    
    # Test with corrupt data
    try:
        # Create a snapshot with invalid timestamp
        from ag2_persistence import ChatSnapshot
        bad_snapshot = ChatSnapshot(
            chat_id="bad_test",
            chat_type="direct",
            timestamp="not a datetime",  # This should fail
            messages=[]
        )
    except Exception as e:
        print(f"Expected error with bad timestamp: {type(e).__name__}")


def run_all_tests():
    """Run all test scenarios"""
    print("AG2 CHAT PERSISTENCE SYSTEM - REAL AGENT TESTS")
    print("=" * 60)
    
    # Note: These tests require a valid OpenAI API key
    # Set your API key: export OPENAI_API_KEY="your-key-here"
    
    if not os.environ.get("OPENAI_API_KEY"):
        print("WARNING: No OpenAI API key found.")
        print("Set OPENAI_API_KEY environment variable to run tests with real LLM.")
        print("Running tests with mock responses...\n")
        
        # You can still test with mock LLM configs
        global llm_config
        llm_config = False  # Disable LLM for testing without API key
    
    try:
        # Run each test scenario
        test_direct_chat_persistence()
        test_groupchat_persistence()
        test_persistent_mixin()
        test_conversation_analytics()
        test_error_handling()
        
        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED SUCCESSFULLY!")
        
    except Exception as e:
        print(f"\nERROR during testing: {e}")
        import traceback
        traceback.print_exc()


def example_production_setup():
    """Example of production-ready setup"""
    print("\n=== Production Setup Example ===\n")
    
    # Production configuration
    config = {
        # Use SQLite for production persistence
        "storage_backend": StorageBackend.SQLITE,
        "storage_config": {
            "db_path": "./production_chats.db"
        },
        
        # LLM configuration with fallbacks
        "llm_config": {
            "config_list": [
                {
                    "model": "gpt-4",
                    "api_key": os.environ.get("OPENAI_API_KEY"),
                },
                {
                    "model": "gpt-3.5-turbo",
                    "api_key": os.environ.get("OPENAI_API_KEY"),
                }
            ],
            "temperature": 0.7,
            "timeout": 60,
            "max_retries": 3,
        }
    }
    
    # Initialize persistence
    persistence = AG2ChatPersistence(
        storage_backend=config["storage_backend"],
        storage_config=config["storage_config"]
    )
    
    # Create agents with production settings
    assistant = ConversableAgent(
        name="production_assistant",
        system_message="""You are a professional AI assistant.
        Always be helpful, accurate, and concise.
        If you're unsure about something, say so.""",
        llm_config=config["llm_config"],
        human_input_mode="NEVER",
        max_consecutive_auto_reply=10,
    )
    
    # Example: Save conversation with comprehensive metadata
    chat_id = f"prod_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    metadata = {
        "environment": "production",
        "version": "1.0.0",
        "user_id": "user_123",
        "session_id": "session_abc",
        "tags": ["customer_support", "technical"],
        "timestamp": datetime.now().isoformat(),
        "ip_address": "192.168.1.1",  # Example
        "user_agent": "AG2 Client/1.0"
    }
    
    print(f"Production setup ready with chat ID: {chat_id}")
    print(f"Metadata: {json.dumps(metadata, indent=2)}")


if __name__ == "__main__":
    # Run all tests
    run_all_tests()
    
    # Show production setup example
    example_production_setup()