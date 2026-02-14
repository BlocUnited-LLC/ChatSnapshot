# /src/chatsnapshot/projections/transcript.py
# TranscriptProjection - derives readable transcript from events

from datetime import datetime
from typing import List, Optional

from .base import Projection
from ..events.envelope import EventEnvelope
from ..events.types import EventType


class TranscriptProjection(Projection[str]):
    """Project events into a readable transcript.

    This projection creates a human-readable transcript from
    the event stream, suitable for display or logging.
    """

    def __init__(
        self,
        include_timestamps: bool = True,
        include_tool_calls: bool = True,
        include_metadata: bool = False,
        timestamp_format: str = "%H:%M:%S"
    ):
        """Initialize the projection.

        Args:
            include_timestamps: Whether to include timestamps
            include_tool_calls: Whether to include tool call details
            include_metadata: Whether to include event metadata
            timestamp_format: strftime format for timestamps
        """
        self.include_timestamps = include_timestamps
        self.include_tool_calls = include_tool_calls
        self.include_metadata = include_metadata
        self.timestamp_format = timestamp_format

    def project(self, events: List[EventEnvelope]) -> str:
        """Project events into a transcript string.

        Args:
            events: List of EventEnvelopes (should be sorted by timestamp)

        Returns:
            A formatted transcript string
        """
        if not events:
            return ""

        lines = []
        correlation_id = events[0].correlation_id

        # Header
        lines.append(f"=== Transcript: {correlation_id} ===")
        lines.append(f"Events: {len(events)}")
        if events:
            lines.append(f"Start: {events[0].timestamp.isoformat()}")
            lines.append(f"End: {events[-1].timestamp.isoformat()}")
        lines.append("")

        # Process each event
        for event in events:
            line = self._format_event(event)
            if line:
                lines.append(line)

        lines.append("")
        lines.append("=== End Transcript ===")

        return "\n".join(lines)

    def _format_event(self, event: EventEnvelope) -> Optional[str]:
        """Format a single event as a transcript line."""
        timestamp_str = ""
        if self.include_timestamps:
            timestamp_str = f"[{event.timestamp.strftime(self.timestamp_format)}] "

        agent = event.source.agent_name or "System"

        if event.event_type == EventType.EXECUTION_MESSAGE:
            content = event.payload.get("content", "")
            if not content:
                return None
            return f"{timestamp_str}{agent}: {content}"

        if event.event_type == EventType.EXECUTION_TOOL_CALL and self.include_tool_calls:
            tool_name = event.payload.get("tool_name", "unknown")
            args = event.payload.get("arguments", {})
            return f"{timestamp_str}{agent} -> [TOOL: {tool_name}] {args}"

        if event.event_type == EventType.EXECUTION_TOOL_RESULT and self.include_tool_calls:
            tool_name = event.payload.get("tool_name", "unknown")
            result = event.payload.get("result", "")
            # Truncate long results
            result_str = str(result)
            if len(result_str) > 200:
                result_str = result_str[:200] + "..."
            return f"{timestamp_str}[TOOL RESULT: {tool_name}] {result_str}"

        if event.event_type == EventType.EXECUTION_HANDOFF:
            from_agent = event.payload.get("from_agent", "?")
            to_agent = event.payload.get("to_agent", "?")
            return f"{timestamp_str}[HANDOFF] {from_agent} -> {to_agent}"

        if event.event_type == EventType.SYSTEM_WORKFLOW_STARTED:
            return f"{timestamp_str}[WORKFLOW STARTED]"

        if event.event_type == EventType.SYSTEM_WORKFLOW_COMPLETED:
            reason = event.payload.get("reason", "")
            return f"{timestamp_str}[WORKFLOW COMPLETED] {reason}"

        if event.event_type == EventType.EXECUTION_COMPLETED:
            reason = event.payload.get("reason", "")
            return f"{timestamp_str}[EXECUTION COMPLETED] {reason}"

        if self.include_metadata:
            return f"{timestamp_str}[{event.event_type.value}] {event.payload}"

        return None


class MarkdownTranscriptProjection(Projection[str]):
    """Project events into a Markdown-formatted transcript."""

    def project(self, events: List[EventEnvelope]) -> str:
        """Project events into Markdown format."""
        if not events:
            return ""

        lines = []
        correlation_id = events[0].correlation_id

        # Header
        lines.append(f"# Transcript: {correlation_id}")
        lines.append("")
        lines.append(f"**Events:** {len(events)}")
        if events:
            lines.append(f"**Start:** {events[0].timestamp.isoformat()}")
            lines.append(f"**End:** {events[-1].timestamp.isoformat()}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Process each event
        for event in events:
            line = self._format_event(event)
            if line:
                lines.append(line)
                lines.append("")

        return "\n".join(lines)

    def _format_event(self, event: EventEnvelope) -> Optional[str]:
        """Format a single event as Markdown."""
        agent = event.source.agent_name or "System"
        timestamp = event.timestamp.strftime("%H:%M:%S")

        if event.event_type == EventType.EXECUTION_MESSAGE:
            content = event.payload.get("content", "")
            if not content:
                return None
            return f"**{agent}** ({timestamp}):\n> {content}"

        if event.event_type == EventType.EXECUTION_TOOL_CALL:
            tool_name = event.payload.get("tool_name", "unknown")
            args = event.payload.get("arguments", {})
            return f"**{agent}** ({timestamp}) called `{tool_name}`:\n```json\n{args}\n```"

        if event.event_type == EventType.EXECUTION_TOOL_RESULT:
            tool_name = event.payload.get("tool_name", "unknown")
            result = event.payload.get("result", "")
            return f"**Tool Result** (`{tool_name}`):\n```\n{result}\n```"

        if event.event_type == EventType.EXECUTION_HANDOFF:
            from_agent = event.payload.get("from_agent", "?")
            to_agent = event.payload.get("to_agent", "?")
            return f"*Handoff: {from_agent} → {to_agent}*"

        return None
