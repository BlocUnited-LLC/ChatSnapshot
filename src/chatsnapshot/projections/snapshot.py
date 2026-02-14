# /src/chatsnapshot/projections/snapshot.py
# SnapshotProjection - derives ChatSnapshot from events

from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from .base import Projection
from ..events.envelope import EventEnvelope
from ..events.types import EventType
from ..snapshot import ChatSnapshot


class SnapshotProjection(Projection[ChatSnapshot]):
    """Project events into a ChatSnapshot.

    This projection reconstructs a ChatSnapshot from the event stream,
    preserving the original ChatSnapshot format for backwards compatibility.
    """

    def project(self, events: List[EventEnvelope]) -> ChatSnapshot:
        """Project events into a ChatSnapshot.

        Args:
            events: List of EventEnvelopes (should be sorted by timestamp)

        Returns:
            A ChatSnapshot containing the projected state
        """
        if not events:
            raise ValueError("Cannot project empty event list")

        # Extract correlation_id from first event
        correlation_id = events[0].correlation_id

        # Determine chat type from agents involved
        agents = self._extract_agents(events)
        chat_type = "group" if len(agents) > 2 else "direct"

        # Convert events to messages
        messages = self._events_to_messages(events)

        # Extract agent states from events
        agent_states = self._extract_agent_states(events)

        # Extract context variables
        context_variables = self._extract_context_variables(events)

        # Determine timestamp range
        first_timestamp = events[0].timestamp
        last_timestamp = events[-1].timestamp

        # Extract termination info
        termination_reason, is_terminated = self._extract_termination(events)

        # Build metadata
        metadata = {
            "event_count": len(events),
            "first_event": events[0].event_id,
            "last_event": events[-1].event_id,
            "start_time": first_timestamp.isoformat(),
            "end_time": last_timestamp.isoformat()
        }

        return ChatSnapshot(
            chat_id=correlation_id,
            chat_type=chat_type,
            timestamp=last_timestamp,
            messages=messages,
            metadata=metadata,
            agent_states=agent_states,
            context_variables=context_variables,
            last_speaker=self._extract_last_speaker(events),
            round_count=self._count_rounds(events),
            termination_reason=termination_reason,
            is_terminated=is_terminated
        )

    def _extract_agents(self, events: List[EventEnvelope]) -> Set[str]:
        """Extract unique agent names from events."""
        agents = set()
        for event in events:
            if event.source.agent_name:
                agents.add(event.source.agent_name)
            # Also check payload
            payload = event.payload
            if "agent_name" in payload:
                agents.add(payload["agent_name"])
            if "name" in payload:
                agents.add(payload["name"])
        return agents

    def _events_to_messages(self, events: List[EventEnvelope]) -> List[Dict[str, Any]]:
        """Convert events to message format."""
        messages = []

        for event in events:
            # Only include message-related events
            if event.event_type not in (
                EventType.EXECUTION_MESSAGE,
                EventType.EXECUTION_TOOL_CALL,
                EventType.EXECUTION_TOOL_RESULT
            ):
                continue

            msg = dict(event.payload)
            msg["_event_id"] = event.event_id
            msg["_event_type"] = event.event_type.value
            msg["_timestamp"] = event.timestamp.isoformat()

            # Ensure name is set
            if "name" not in msg and event.source.agent_name:
                msg["name"] = event.source.agent_name

            messages.append(msg)

        return messages

    def _extract_agent_states(self, events: List[EventEnvelope]) -> Dict[str, Dict[str, Any]]:
        """Extract agent states from events."""
        agent_states: Dict[str, Dict[str, Any]] = {}

        for event in events:
            agent_name = event.source.agent_name
            if not agent_name:
                continue

            if agent_name not in agent_states:
                agent_states[agent_name] = {"name": agent_name}

            # Update state from payload if it contains agent config
            payload = event.payload
            if "system_message" in payload:
                agent_states[agent_name]["system_message"] = payload["system_message"]
            if "llm_config" in payload:
                agent_states[agent_name]["llm_config"] = payload["llm_config"]

        return agent_states

    def _extract_context_variables(self, events: List[EventEnvelope]) -> Dict[str, Any]:
        """Extract context variables from events."""
        context_vars: Dict[str, Any] = {}

        for event in events:
            if event.event_type == EventType.EXECUTION_STATE_CHANGE:
                if "context_variables" in event.payload:
                    context_vars.update(event.payload["context_variables"])

        return context_vars

    def _extract_termination(self, events: List[EventEnvelope]) -> tuple:
        """Extract termination info from events."""
        for event in reversed(events):
            if event.event_type == EventType.EXECUTION_COMPLETED:
                reason = event.payload.get("reason")
                return (reason, True)
            if event.event_type == EventType.SYSTEM_WORKFLOW_COMPLETED:
                reason = event.payload.get("reason")
                return (reason, True)

        return (None, False)

    def _extract_last_speaker(self, events: List[EventEnvelope]) -> Optional[str]:
        """Extract the last speaker from events."""
        for event in reversed(events):
            if event.event_type == EventType.EXECUTION_MESSAGE:
                return event.source.agent_name or event.payload.get("name")
        return None

    def _count_rounds(self, events: List[EventEnvelope]) -> int:
        """Count the number of message rounds."""
        return len([
            e for e in events
            if e.event_type == EventType.EXECUTION_MESSAGE
        ])
