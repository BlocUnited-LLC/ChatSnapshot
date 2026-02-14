# /src/chatsnapshot/events/types.py
# Event type definitions for the Observer pattern

from enum import Enum


class EventType(str, Enum):
    """Canonical event types for the ChatSnapshot observer system.

    Events are categorized into primitives that remain stable across
    evolving runtimes. Framework-specific details belong in payload.
    """

    # Execution events (from agent runtime)
    EXECUTION_MESSAGE = "execution.message"
    EXECUTION_TOOL_CALL = "execution.tool_call"
    EXECUTION_TOOL_RESULT = "execution.tool_result"
    EXECUTION_STATE_CHANGE = "execution.state_change"
    EXECUTION_HANDOFF = "execution.handoff"
    EXECUTION_COMPLETED = "execution.completed"

    # System events (from application layer)
    SYSTEM_WORKFLOW_STARTED = "system.workflow_started"
    SYSTEM_WORKFLOW_COMPLETED = "system.workflow_completed"
    SYSTEM_TASK_SCHEDULED = "system.task_scheduled"
    SYSTEM_TASK_COMPLETED = "system.task_completed"
    SYSTEM_ERROR = "system.error"

    # UI events
    UI_INPUT_RECEIVED = "ui.input_received"
    UI_OUTPUT_DISPLAYED = "ui.output_displayed"

    # Integration events
    INTEGRATION_CALL = "integration.call"
    INTEGRATION_RESPONSE = "integration.response"


class EventOrigin(str, Enum):
    """Origin of the event - where it came from."""
    AGENT = "agent"
    SYSTEM = "system"
    UI = "ui"
    INTEGRATION = "integration"


class RuntimeType(str, Enum):
    """The runtime that produced the event."""
    AG2 = "ag2"
    LANGGRAPH = "langgraph"
    CREWAI = "crewai"
    CUSTOM = "custom"
    NONE = "none"
