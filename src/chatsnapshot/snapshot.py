# /src/chatsnapshot/snapshot.py
# ChatSnapshot data model - projection output format

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ChatSnapshot:
    """Represents a complete snapshot of a chat state.

    ChatSnapshot is now a projection output - derived from an event stream
    by the SnapshotProjection class. It maintains backwards compatibility
    with the original format while being generated from events.
    """
    chat_id: str
    chat_type: str  # "direct", "group", "nested"
    timestamp: datetime
    messages: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)
    agent_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    context_variables: Dict[str, Any] = field(default_factory=dict)

    # GroupChat specific fields
    speaker_selection_method: Optional[str] = None
    max_round: Optional[int] = None
    admin_name: Optional[str] = None
    speaker_transitions: Optional[Dict[str, List[str]]] = None

    # Execution state
    last_speaker: Optional[str] = None
    round_count: int = 0
    termination_reason: Optional[str] = None
    is_terminated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dictionary."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatSnapshot':
        """Deserialize from dictionary."""
        data = dict(data)  # Copy to avoid mutating input
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)
