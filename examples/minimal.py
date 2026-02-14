# /examples/minimal.py
# Minimal example of using ChatSnapshot with Observer-first architecture

import asyncio
from chatsnapshot import (
    Observer,
    EventType,
    MemoryEventStore,
    SQLiteEventStore,
    SnapshotProjection,
    TranscriptProjection,
)


async def basic_example():
    """Basic example using in-memory storage."""
    print("=== Basic Example (Memory Storage) ===\n")

    # Create Observer with in-memory storage
    async with Observer(MemoryEventStore()) as observer:

        # Record some events
        await observer.record(
            event_type=EventType.EXECUTION_MESSAGE,
            correlation_id="session_001",
            payload={"role": "user", "content": "Hello!", "name": "User"}
        )

        await observer.record(
            event_type=EventType.EXECUTION_MESSAGE,
            correlation_id="session_001",
            payload={"role": "assistant", "content": "Hi there! How can I help?", "name": "Assistant"}
        )

        await observer.record(
            event_type=EventType.EXECUTION_MESSAGE,
            correlation_id="session_001",
            payload={"role": "user", "content": "What's the weather?", "name": "User"}
        )

        await observer.record(
            event_type=EventType.EXECUTION_TOOL_CALL,
            correlation_id="session_001",
            payload={"tool_name": "get_weather", "arguments": {"location": "NYC"}, "name": "Assistant"}
        )

        await observer.record(
            event_type=EventType.EXECUTION_TOOL_RESULT,
            correlation_id="session_001",
            payload={"tool_name": "get_weather", "result": "Sunny, 72°F"}
        )

        await observer.record(
            event_type=EventType.EXECUTION_MESSAGE,
            correlation_id="session_001",
            payload={"role": "assistant", "content": "The weather in NYC is sunny and 72°F!", "name": "Assistant"}
        )

        # Get events and project to different formats
        events = await observer.get_events("session_001")
        print(f"Total events recorded: {len(events)}\n")

        # Project to transcript
        transcript = TranscriptProjection().project(events)
        print(transcript)
        print()

        # Project to ChatSnapshot
        snapshot = SnapshotProjection().project(events)
        print(f"ChatSnapshot ID: {snapshot.chat_id}")
        print(f"Chat type: {snapshot.chat_type}")
        print(f"Messages: {len(snapshot.messages)}")
        print(f"Round count: {snapshot.round_count}")


async def sqlite_example():
    """Example using SQLite persistent storage."""
    print("\n=== SQLite Example ===\n")

    # Create Observer with SQLite storage
    store = SQLiteEventStore("./example_events.db")

    async with Observer(store) as observer:
        # Record an event
        event = await observer.record(
            event_type=EventType.SYSTEM_WORKFLOW_STARTED,
            correlation_id="workflow_001",
            payload={"workflow_name": "data_processing", "input_files": 3}
        )

        print(f"Recorded event: {event.event_id}")
        print(f"Event type: {event.event_type.value}")
        print(f"Timestamp: {event.timestamp.isoformat()}")

        # Query events
        total = await observer.count()
        print(f"Total events in database: {total}")


async def subscription_example():
    """Example using pub/sub subscriptions."""
    print("\n=== Subscription Example ===\n")

    async with Observer(MemoryEventStore()) as observer:

        # Subscribe to events
        async def on_event(event):
            print(f"[SUBSCRIBER] Received: {event.event_type.value} - {event.payload.get('content', event.payload)}")

        subscription_id = observer.subscribe(on_event)
        print(f"Subscribed with ID: {subscription_id}\n")

        # Record events - subscribers will be notified
        await observer.record(
            event_type=EventType.EXECUTION_MESSAGE,
            correlation_id="live_session",
            payload={"content": "First message", "name": "Agent1"}
        )

        await observer.record(
            event_type=EventType.EXECUTION_MESSAGE,
            correlation_id="live_session",
            payload={"content": "Second message", "name": "Agent2"}
        )

        # Unsubscribe
        observer.unsubscribe(subscription_id)
        print(f"\nUnsubscribed: {subscription_id}")


async def main():
    """Run all examples."""
    await basic_example()
    await sqlite_example()
    await subscription_example()

    print("\n=== All examples completed ===")


if __name__ == "__main__":
    asyncio.run(main())
