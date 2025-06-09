# ChatSnapshot

**Stateful Persistence for the Agentic Internet**

---

## 🧠 What is ChatSnapshot?

ChatSnapshot is a lightweight, framework-agnostic library designed to **persist, restore, and transport full agentic chat sessions**, including:

- Messages
- Agent configurations
- Context variables
- Execution logic
- Conversation transitions

Whether you're using AG2, LangChain, or your own custom framework — ChatSnapshot provides a unified model for saving and restoring intelligent, multi-agent interactions.

---

## 🌍 Why It Matters in the Agentic Stack

The next generation of agent-based systems — including AI-native UIs, orchestration layers, and cooperative agents — all depend on **deep continuity** across time, tools, and tasks.

But today’s tools are **siloed**, and state is often lost at the session level.

ChatSnapshot brings **persistence and state consistency** to this emerging ecosystem by acting as the *persistence layer of the agentic stack* — working in tandem with coordination frameworks like MCP (Multi-Agent Control Plane) and protocols like A2A (Agent-to-Agent).

---

## 🧱 Where It Fits in the Stack

```mermaid
graph TD
  subgraph Client_Layer [Client Layer]
    User[User / UI]
  end

  subgraph App_Layer [App Layer]
    AGUI["Agentic UI
    (e.g. internet-agent-ui)"]
  end

  subgraph Agent_Layer [Agent Layer]
    MCP[Multi-Agent Control Plane MCP]
    A2A[Agent-to-Agent Protocols A2A]
    Frameworks["Agent Frameworks
    (AG2, LangChain, etc.)"]
    Orchestrators["Orchestrators
    (Routing / Patterns)"]
  end

  subgraph Infra_Layer [Infrastructure Layer]
    ChatSnapshot["📦 ChatSnapshot
    (Persistence + Serialization)"]
    Storage["Storage Backend
    (MongoDB / JSON / SQLite)"]
  end

  User --> AGUI
  AGUI --> MCP
  MCP --> A2A
  A2A --> Frameworks
  Frameworks --> Orchestrators
  Orchestrators --> ChatSnapshot
  ChatSnapshot --> Storage
````
---

## 🧬 Core Value

✅ **Universal Format**: ChatSnapshot defines a standardized schema for saving any conversation state across frameworks.

✅ **Adapter-Friendly**: Each framework can implement its own `AgenticAdapter` to plug into the snapshot layer.

✅ **Full Fidelity Restoration**: Includes agent logic, flow transitions, context vars, and message order.

✅ **Built for Interop**: Enables agents, apps, and protocols to share persistent state across platforms.

---

## ✨ Example (AG2 + JSON Backend)

```python
from chatsnapshot import AG2ChatPersistence, StorageBackend
from autogen import GroupChat, GroupChatManager

persistence = AG2ChatPersistence(storage_backend=StorageBackend.JSON)

snapshot = persistence.save_groupchat(
    chat_id="project_sync_001",
    groupchat=groupchat,
    manager=manager,
    metadata={"use_case": "team_collab"}
)

# Restore later
restored = persistence.load_conversation("project_sync_001")
persistence.restore_groupchat(restored, groupchat, manager)
```

---

## 🔌 Plug into Your Stack

Each framework (AG2, LangChain, etc.) simply defines how to:

- Convert its internal agent state & messages into a standardized `ChatSnapshot`
- Restore from the snapshot back to a working state

See [`/docs/agentic-adapter.md`](docs/agentic-adapter.md) to get started.

---

## 📚 Explore the Project

- 📁 `/src/chatsnapshot` – Core logic, adapters, interfaces
- 📁 `/docs` – Developer documentation for extending ChatSnapshot
- 📦 `ChatSnapshot` objects – Full schema for saving groupchat state
- 🧪 `/tests` – Testing framework for adapters and snapshots

---


## ⚙️ Installation

```bash
# Clone the repository
git clone https://github.com/BlocUnited-LLC/ChatSnapshot.git
cd chatsnapshot

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Dependencies

- Python 3.8+  
- AG2 (AutoGen) >= 0.2.0  
- Standard library modules: `json`, `sqlite3`, `datetime`, `pathlib`, `mongo`, `pymongo`

---

## 🚀 Quick Start

```python
from chatsnapshot import ChatSnapshot, AG2ChatPersistence, StorageBackend
from autogen import ConversableAgent, GroupChat, GroupChatManager

# Initialize persistence
persistence = AG2ChatPersistence(storage_backend=StorageBackend.JSON)

# Create and run your AG2 agents
agent1 = ConversableAgent(name="assistant", llm_config=llm_config)
agent2 = ConversableAgent(name="coder", llm_config=llm_config)

# Save conversation
snapshot = persistence.save_conversation(
    chat_id="my_chat_001",
    agents=[agent1, agent2],
    messages=chat_history
)

# Later, restore conversation
loaded = persistence.load_conversation("my_chat_001")
persistence.restore_conversation(loaded, [agent1, agent2])
```

---

## 🧱 Architecture

```
chatsnapshot/
├── __init__.py              # Package initialization
├── enums.py                 # StorageBackend enum
├── snapshot.py              # ChatSnapshot data model
├── storage/
│   ├── __init__.py
│   ├── base.py             # Abstract storage interface
│   ├── json_adapter.py     # JSON file storage
│   ├── sqlite_adapter.py   # SQLite database storage
│   ├── mongodb_adapter.py  # MonbgoDB database storage
│   └── memory_adapter.py   # In-memory storage
├── manager.py              # Main persistence manager
└── persistent_mixin.py     # Mixin for AG2 agents
```

---

## 📦 Module Documentation

### Core Modules

- `snapshot.py` - Data model for conversation snapshots  
- `enums.py` - Enumeration types  
- `manager.py` - Main persistence manager  
- `persistent_mixin.py` - Agent integration mixin  

### Storage Adapters

- `base.py` - Abstract storage interface  
- `json_adapter.py` - JSON file storage implementation  
- `sqlite_adapter.py` - SQLite database implementation  
- `mongodb_adapter.py` - MonbgoDB database implementation  
- `memory_adapter.py` - In-memory storage implementation  

---

## 🔍 API Reference

### `ChatSnapshot`

The core data model representing a conversation state.

```python
@dataclass
class ChatSnapshot:
    chat_id: str
    chat_type: str
    timestamp: datetime
    messages: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    agent_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # ... additional fields
```

### `AG2ChatPersistence`

The main interface for managing conversation persistence.

```python
class AG2ChatPersistence:
    def __init__(self, storage_backend: StorageBackend, storage_config: Optional[Dict] = None)
    def save_conversation(self, chat_id: str, agents, messages, metadata) -> ChatSnapshot
    def load_conversation(self, chat_id: str) -> Optional[ChatSnapshot]
    def restore_conversation(self, snapshot: ChatSnapshot, agents) -> None
    def list_conversations(self) -> List[Dict[str, Any]]
    def delete_conversation(self, chat_id: str) -> bool
```

---

## 💾 Storage Backends

Choose from multiple storage backends:

- **JSON**: Human-readable file storage  
- **SQLite**: Structured database with query capabilities 
- **MongoDB**: NoSQL database for flexible storage 
- **Memory**: Fast in-memory storage for testing  

---

## 📚 Examples

See the `examples/` directory for complete working examples:

- `minimal.py` - Basic usage example  
- `group_chat.py` - GroupChat persistence  
- `analytics.py` - Conversation analytics  
- `custom_storage.py` - Implementing custom storage  

---

## 💡 Roadmap

- ✅ AG2 Adapter
- ✅ JSON / SQLite / Memory Backends
- 🔄 MongoDB Async Adapter
- 🔌 LangChain Adapter
- 🌐 Web-native Protocol Support (e.g. A2A protocol bridge)
- 🧠 Versioned State Transition Snapshots

---

## 🤝 Contributing

We welcome contributions! Please see our **Contributing Guide** for details.

---

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details.
