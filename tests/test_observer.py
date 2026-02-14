# /tests/test_observer.py
# Tests for the Observer-first architecture

import pytest
import asyncio
from datetime import datetime, timedelta

from chatsnapshot import (
    Observer,
    EventEnvelope,
    EventSource,
    EventType,
    EventOrigin,
    RuntimeType,
    MemoryEventStore,
    SnapshotProjection,
    TranscriptProjection,
)


# ========== EventEnvelope Tests ==========

class TestEventEnvelope:
    def test_create_event(self):
        """Test EventEnvelope.create() factory method."""
        event = EventEnvelope.create(
            event_type=EventType.EXECUTION_MESSAGE,
            correlation_id="test_001",
            payload={"content": "Hello"}
        )

        assert event.event_id is not None
        assert event.event_type == EventType.EXECUTION_MESSAGE
        assert event.correlation_id == "test_001"
        assert event.payload == {"content": "Hello"}
        assert event.timestamp is not None
        assert event.causation_id is None

    def test_event_with_source(self):
        """Test creating event with custom source."""
        source = EventSource(
            origin=EventOrigin.AGENT,
            runtime=RuntimeType.AG2,
            agent_name="TestAgent"
        )
        event = EventEnvelope.create(
            event_type=EventType.EXECUTION_MESSAGE,
            correlation_id="test_001",
            payload={"content": "Hello"},
            source=source
        )

        assert event.source.origin == EventOrigin.AGENT
        assert event.source.runtime == RuntimeType.AG2
        assert event.source.agent_name == "TestAgent"

    def test_event_serialization(self):
        """Test to_dict() and from_dict()."""
        event = EventEnvelope.create(
            event_type=EventType.EXECUTION_MESSAGE,
            correlation_id="test_001",
            payload={"content": "Hello"}
        )

        data = event.to_dict()
        restored = EventEnvelope.from_dict(data)

        assert restored.event_id == event.event_id
        assert restored.event_type == event.event_type
        assert restored.correlation_id == event.correlation_id
        assert restored.payload == event.payload

    def test_event_with_causation(self):
        """Test causal linking of events."""
        parent = EventEnvelope.create(
            event_type=EventType.EXECUTION_TOOL_CALL,
            correlation_id="test_001",
            payload={"tool": "test"}
        )

        child = EventEnvelope.create(
            event_type=EventType.EXECUTION_TOOL_RESULT,
            correlation_id="test_001",
            payload={"result": "ok"},
            causation_id=parent.event_id
        )

        assert child.causation_id == parent.event_id


# ========== MemoryEventStore Tests ==========

class TestMemoryEventStore:
    @pytest.mark.asyncio
    async def test_append_and_query(self):
        """Test basic append and query operations."""
        store = MemoryEventStore()
        await store.initialize()

        event = EventEnvelope.create(
            event_type=EventType.EXECUTION_MESSAGE,
            correlation_id="session_001",
            payload={"content": "Hello"}
        )
        await store.append(event)

        events = await store.query("session_001")
        assert len(events) == 1
        assert events[0].event_id == event.event_id

    @pytest.mark.asyncio
    async def test_query_by_type(self):
        """Test querying by event type."""
        store = MemoryEventStore()
        await store.initialize()

        await store.append(EventEnvelope.create(
            event_type=EventType.EXECUTION_MESSAGE,
            correlation_id="session_001",
            payload={"content": "Hello"}
        ))
        await store.append(EventEnvelope.create(
            event_type=EventType.EXECUTION_TOOL_CALL,
            correlation_id="session_001",
            payload={"tool": "test"}
        ))

        messages = await store.query_by_type(EventType.EXECUTION_MESSAGE)
        assert len(messages) == 1

        tool_calls = await store.query_by_type(EventType.EXECUTION_TOOL_CALL)
        assert len(tool_calls) == 1

    @pytest.mark.asyncio
    async def test_count(self):
        """Test event count."""
        store = MemoryEventStore()
        await store.initialize()

        assert await store.count() == 0

        await store.append(EventEnvelope.create(
            event_type=EventType.EXECUTION_MESSAGE,
            correlation_id="session_001",
            payload={"content": "Hello"}
        ))

        assert await store.count() == 1

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        async with MemoryEventStore() as store:
            await store.append(EventEnvelope.create(
                event_type=EventType.EXECUTION_MESSAGE,
                correlation_id="test",
                payload={}
            ))
            assert await store.count() == 1


# ========== Observer Tests ==========

class TestObserver:
    @pytest.mark.asyncio
    async def test_record_event(self):
        """Test recording an event."""
        async with Observer(MemoryEventStore()) as observer:
            event = await observer.record(
                event_type=EventType.EXECUTION_MESSAGE,
                correlation_id="session_001",
                payload={"content": "Hello"}
            )

            assert event.event_id is not None
            assert event.event_type == EventType.EXECUTION_MESSAGE

    @pytest.mark.asyncio
    async def test_get_events(self):
        """Test retrieving events by correlation_id."""
        async with Observer(MemoryEventStore()) as observer:
            await observer.record(
                event_type=EventType.EXECUTION_MESSAGE,
                correlation_id="session_001",
                payload={"content": "Hello"}
            )
            await observer.record(
                event_type=EventType.EXECUTION_MESSAGE,
                correlation_id="session_001",
                payload={"content": "World"}
            )
            await observer.record(
                event_type=EventType.EXECUTION_MESSAGE,
                correlation_id="session_002",
                payload={"content": "Other"}
            )

            events = await observer.get_events("session_001")
            assert len(events) == 2

    @pytest.mark.asyncio
    async def test_subscription(self):
        """Test pub/sub subscriptions."""
        received_events = []

        async def callback(event):
            received_events.append(event)

        async with Observer(MemoryEventStore()) as observer:
            sub_id = observer.subscribe(callback)

            await observer.record(
                event_type=EventType.EXECUTION_MESSAGE,
                correlation_id="session_001",
                payload={"content": "Hello"}
            )

            assert len(received_events) == 1
            assert received_events[0].payload["content"] == "Hello"

            observer.unsubscribe(sub_id)

            await observer.record(
                event_type=EventType.EXECUTION_MESSAGE,
                correlation_id="session_001",
                payload={"content": "World"}
            )

            # Should still be 1 since we unsubscribed
            assert len(received_events) == 1

    @pytest.mark.asyncio
    async def test_multiple_subscriptions(self):
        """Test multiple subscribers."""
        received_1 = []
        received_2 = []

        async def callback_1(event):
            received_1.append(event)

        async def callback_2(event):
            received_2.append(event)

        async with Observer(MemoryEventStore()) as observer:
            observer.subscribe(callback_1)
            observer.subscribe(callback_2)

            await observer.record(
                event_type=EventType.EXECUTION_MESSAGE,
                correlation_id="session_001",
                payload={"content": "Hello"}
            )

            assert len(received_1) == 1
            assert len(received_2) == 1


# ========== Projection Tests ==========

class TestSnapshotProjection:
    @pytest.mark.asyncio
    async def test_project_to_snapshot(self):
        """Test projecting events to ChatSnapshot."""
        async with Observer(MemoryEventStore()) as observer:
            await observer.record(
                event_type=EventType.EXECUTION_MESSAGE,
                correlation_id="session_001",
                payload={"role": "user", "content": "Hello", "name": "User"},
                source=EventSource(origin=EventOrigin.AGENT, agent_name="User")
            )
            await observer.record(
                event_type=EventType.EXECUTION_MESSAGE,
                correlation_id="session_001",
                payload={"role": "assistant", "content": "Hi there!", "name": "Assistant"},
                source=EventSource(origin=EventOrigin.AGENT, agent_name="Assistant")
            )

            events = await observer.get_events("session_001")
            snapshot = SnapshotProjection().project(events)

            assert snapshot.chat_id == "session_001"
            assert len(snapshot.messages) == 2
            assert snapshot.round_count == 2

    @pytest.mark.asyncio
    async def test_empty_events_raises(self):
        """Test that empty event list raises error."""
        projection = SnapshotProjection()
        with pytest.raises(ValueError):
            projection.project([])


class TestTranscriptProjection:
    @pytest.mark.asyncio
    async def test_project_to_transcript(self):
        """Test projecting events to transcript."""
        async with Observer(MemoryEventStore()) as observer:
            await observer.record(
                event_type=EventType.EXECUTION_MESSAGE,
                correlation_id="session_001",
                payload={"content": "Hello"},
                source=EventSource(origin=EventOrigin.AGENT, agent_name="User")
            )
            await observer.record(
                event_type=EventType.EXECUTION_MESSAGE,
                correlation_id="session_001",
                payload={"content": "Hi there!"},
                source=EventSource(origin=EventOrigin.AGENT, agent_name="Assistant")
            )

            events = await observer.get_events("session_001")
            transcript = TranscriptProjection().project(events)

            assert "session_001" in transcript
            assert "User" in transcript
            assert "Hello" in transcript
            assert "Assistant" in transcript
            assert "Hi there!" in transcript


# ========== Integration Tests ==========

class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_flow(self):
        """Test complete flow: record -> query -> project."""
        async with Observer(MemoryEventStore()) as observer:
            # Simulate a conversation
            await observer.record(
                event_type=EventType.SYSTEM_WORKFLOW_STARTED,
                correlation_id="workflow_001",
                payload={"name": "test_workflow"}
            )

            for i in range(5):
                await observer.record(
                    event_type=EventType.EXECUTION_MESSAGE,
                    correlation_id="workflow_001",
                    payload={"content": f"Message {i}", "name": f"Agent{i % 2}"},
                    source=EventSource(origin=EventOrigin.AGENT, agent_name=f"Agent{i % 2}")
                )

            await observer.record(
                event_type=EventType.SYSTEM_WORKFLOW_COMPLETED,
                correlation_id="workflow_001",
                payload={"status": "success", "reason": "All tasks completed"}
            )

            # Query and project
            events = await observer.get_events("workflow_001")
            assert len(events) == 7

            snapshot = SnapshotProjection().project(events)
            assert snapshot.chat_id == "workflow_001"
            assert snapshot.is_terminated
            assert snapshot.termination_reason == "All tasks completed"

            transcript = TranscriptProjection().project(events)
            assert "WORKFLOW STARTED" in transcript
            assert "WORKFLOW COMPLETED" in transcript
