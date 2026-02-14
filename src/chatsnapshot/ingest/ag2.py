# /src/chatsnapshot/ingest/ag2.py
# AG2 (AutoGen) specific ingest adapter

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import IngestAdapter
from ..observer import Observer
from ..events.envelope import EventEnvelope, EventSource
from ..events.types import EventType, EventOrigin, RuntimeType

if TYPE_CHECKING:
    from autogen import ConversableAgent, GroupChat, GroupChatManager


class AG2IngestAdapter(IngestAdapter):
    """Ingest adapter for AG2 (AutoGen) runtime.

    Converts AG2-specific events into canonical EventEnvelopes.
    Supports both streaming (run_iter) and batch (extract from agents) modes.
    """

    def __init__(self, observer: Observer, correlation_id: Optional[str] = None):
        super().__init__(observer, correlation_id)

    def _create_source(self, agent_name: Optional[str] = None) -> EventSource:
        """Create an EventSource for AG2 events."""
        return EventSource(
            origin=EventOrigin.AGENT,
            runtime=RuntimeType.AG2,
            agent_name=agent_name
        )

    async def record(self, raw_event: Any, correlation_id: Optional[str] = None) -> EventEnvelope:
        """Record a raw AG2 event.

        Handles various AG2 event types from run_iter() or similar APIs.
        """
        corr_id = correlation_id or self._correlation_id
        if not corr_id:
            raise ValueError("correlation_id is required")

        # Determine event type from raw_event structure
        event_type, payload, agent_name = self._normalize_event(raw_event)

        event = await self._observer.record(
            event_type=event_type,
            correlation_id=corr_id,
            payload=payload,
            source=self._create_source(agent_name),
            causation_id=self._last_event_id
        )

        self._update_last_event(event)
        return event

    def _normalize_event(self, raw_event: Any) -> tuple:
        """Normalize an AG2 event into (event_type, payload, agent_name)."""
        # Handle dict events (most common from message passing)
        if isinstance(raw_event, dict):
            return self._normalize_dict_event(raw_event)

        # Handle string events (simple messages)
        if isinstance(raw_event, str):
            return (
                EventType.EXECUTION_MESSAGE,
                {"content": raw_event},
                None
            )

        # Default: wrap as generic payload
        return (
            EventType.EXECUTION_STATE_CHANGE,
            {"raw": str(raw_event)},
            None
        )

    def _normalize_dict_event(self, event: Dict[str, Any]) -> tuple:
        """Normalize a dictionary event."""
        # Extract agent name if present
        agent_name = event.get("name") or event.get("agent_name")

        # Determine event type based on content
        if "tool_calls" in event or "function_call" in event:
            return (EventType.EXECUTION_TOOL_CALL, event, agent_name)

        if "tool_call_id" in event or event.get("role") == "tool":
            return (EventType.EXECUTION_TOOL_RESULT, event, agent_name)

        if "content" in event or "message" in event:
            return (EventType.EXECUTION_MESSAGE, event, agent_name)

        # Default to state change
        return (EventType.EXECUTION_STATE_CHANGE, event, agent_name)

    # ========== Convenience Methods for Common AG2 Events ==========

    async def on_message(
        self,
        message: Dict[str, Any],
        agent_name: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> EventEnvelope:
        """Record a message event."""
        corr_id = correlation_id or self._correlation_id
        if not corr_id:
            raise ValueError("correlation_id is required")

        payload = dict(message)
        if agent_name:
            payload["agent_name"] = agent_name

        event = await self._observer.record(
            event_type=EventType.EXECUTION_MESSAGE,
            correlation_id=corr_id,
            payload=payload,
            source=self._create_source(agent_name),
            causation_id=self._last_event_id
        )

        self._update_last_event(event)
        return event

    async def on_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        agent_name: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> EventEnvelope:
        """Record a tool call event."""
        corr_id = correlation_id or self._correlation_id
        if not corr_id:
            raise ValueError("correlation_id is required")

        event = await self._observer.record(
            event_type=EventType.EXECUTION_TOOL_CALL,
            correlation_id=corr_id,
            payload={
                "tool_name": tool_name,
                "arguments": arguments,
                "agent_name": agent_name
            },
            source=self._create_source(agent_name),
            causation_id=self._last_event_id
        )

        self._update_last_event(event)
        return event

    async def on_tool_result(
        self,
        tool_name: str,
        result: Any,
        agent_name: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> EventEnvelope:
        """Record a tool result event."""
        corr_id = correlation_id or self._correlation_id
        if not corr_id:
            raise ValueError("correlation_id is required")

        event = await self._observer.record(
            event_type=EventType.EXECUTION_TOOL_RESULT,
            correlation_id=corr_id,
            payload={
                "tool_name": tool_name,
                "result": result,
                "agent_name": agent_name
            },
            source=self._create_source(agent_name),
            causation_id=self._last_event_id
        )

        self._update_last_event(event)
        return event

    async def on_handoff(
        self,
        from_agent: str,
        to_agent: str,
        correlation_id: Optional[str] = None
    ) -> EventEnvelope:
        """Record an agent handoff event."""
        corr_id = correlation_id or self._correlation_id
        if not corr_id:
            raise ValueError("correlation_id is required")

        event = await self._observer.record(
            event_type=EventType.EXECUTION_HANDOFF,
            correlation_id=corr_id,
            payload={
                "from_agent": from_agent,
                "to_agent": to_agent
            },
            source=self._create_source(from_agent),
            causation_id=self._last_event_id
        )

        self._update_last_event(event)
        return event

    # ========== Batch Extraction from Agents ==========

    async def extract_from_agents(
        self,
        agents: List['ConversableAgent'],
        correlation_id: Optional[str] = None
    ) -> List[EventEnvelope]:
        """Extract messages from AG2 agents and record as events.

        This is useful for capturing state from agents after a conversation
        has completed (batch mode rather than streaming).
        """
        corr_id = correlation_id or self._correlation_id
        if not corr_id:
            raise ValueError("correlation_id is required")

        events = []

        for agent in agents:
            if not hasattr(agent, "_oai_messages"):
                continue

            for other_agent, messages in agent._oai_messages.items():
                for msg in messages:
                    event_type, payload, _ = self._normalize_dict_event(msg)

                    # Add agent name if not present
                    if "name" not in payload and "agent_name" not in payload:
                        payload["agent_name"] = agent.name

                    event = await self._observer.record(
                        event_type=event_type,
                        correlation_id=corr_id,
                        payload=payload,
                        source=self._create_source(agent.name),
                        causation_id=self._last_event_id
                    )

                    self._update_last_event(event)
                    events.append(event)

        return events

    async def extract_from_groupchat(
        self,
        groupchat: 'GroupChat',
        correlation_id: Optional[str] = None
    ) -> List[EventEnvelope]:
        """Extract messages from a GroupChat and record as events."""
        corr_id = correlation_id or self._correlation_id
        if not corr_id:
            raise ValueError("correlation_id is required")

        events = []

        for msg in groupchat.messages:
            event_type, payload, agent_name = self._normalize_dict_event(msg)

            event = await self._observer.record(
                event_type=event_type,
                correlation_id=corr_id,
                payload=payload,
                source=self._create_source(agent_name),
                causation_id=self._last_event_id
            )

            self._update_last_event(event)
            events.append(event)

        return events
