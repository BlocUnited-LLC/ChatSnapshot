# 📦 ChatSnapshot Architecture

ChatSnapshot records what actually happened, durably and causally, across agents, applications, and infrastructure.

- It does not execute agents.
- It does not schedule workflows.
- It does not interpret semantics.

It records reality.

## 🧠 Core Idea

Modern agent systems are:

- **Cognitively stateful** (inside the LLM conversation)
- **Systemically ephemeral** (no durable record of execution truth)

ChatSnapshot provides a durable, append-only ledger of execution facts across the entire stack.

## 🏗 What ChatSnapshot Observes

ChatSnapshot observes two categories of facts:

### 1️⃣ Agent Execution Facts

Captured directly from an agent runtime (e.g. via iteration APIs like `run_iter()`):

- Agent message emitted
- Tool call requested
- Tool result returned
- Human input requested
- Run resumed
- Run completed
- Agent handoff
- Structured output produced

These are runtime execution facts.

They describe what the agent actually did — not what it intended.

### 2️⃣ Application & System Facts

Captured at service boundaries:

- Workflow started
- Task scheduled
- Task completed
- User interaction received
- API call triggered
- External integration invoked
- System state transitioned

These describe what happened outside the agent itself.

## 🧾 Canonical EventEnvelope

All facts are normalized into a single durable envelope.

```json
{
  "event_id": "uuid",
  "event_type": "execution.message | execution.tool_call | system.workflow_started | ui.input_received",
  "timestamp": "ISO8601",
  "source": {
    "origin": "agent | system | ui | integration",
    "runtime": "ag2 | custom | none"
  },
  "correlation_id": "run_id | workflow_id | session_id",
  "causation_id": "parent_event_id | null",
  "payload": {}
}
```

### Properties

- Append-only
- Immutable
- Causally linked
- Ordered per correlation scope
- JSON serializable

## 🔄 Deterministic Replay

Replay means:

- Reconstructing ordered execution history
- Rebuilding transcripts
- Rebuilding workflow timelines
- Auditing causality chains
- Feeding downstream systems

Replay does **not** mean re-executing an agent runtime.

It means replaying execution truth.

## 🔌 Ingest Model

ChatSnapshot does not depend on a specific agent framework.

Instead, runtimes expose iteration or event hooks, and applications record system-level events at boundaries.

### Example (agent runtime)

```python
for event in agent.run_iter(...):
    snapshot.record(
        event_type=map_event(event),
        correlation_id=run_id,
        payload=normalize(event)
    )
```

### Example (application boundary)

```python
snapshot.record(
    event_type="system.workflow_started",
    correlation_id=workflow_id,
    payload=data
)
```

ChatSnapshot does not assume how agents work internally.

It only records what they emit.

## 🗺 Layered Architecture (Mermaid)

```mermaid
flowchart TB
  F[Frontend Layer<br/>(AG-UI / Web / App)]
  A[Application Layer<br/>(Workflow Manager / Scheduler)]
  R[Agent Runtime Layer<br/>(AG2 / LangGraph / CrewAI)]
  CS[ChatSnapshot<br/>(Truth / Event Ledger)]
  P[Event Projections<br/>(Replay / Audit / Analytics)]

  F --> A
  A --> R
  R -->|execution facts| CS
  CS --> P
```

## 🧩 Event Primitives

To remain stable across evolving runtimes, events are categorized into a small set of primitives:

- `execution.message`
- `execution.tool_call`
- `execution.tool_result`
- `execution.state_change`
- `system.workflow_event`
- `ui.interaction`
- `integration.call`

Framework-specific details remain inside `payload`.

## 🧮 Projections

ChatSnapshot can derive projections from recorded events:

- Run transcript
- Workflow timeline
- Task graph reconstruction
- Audit trail
- Billing metrics
- Compliance logs
- Analytics streams

Projections do not change the underlying truth.

They are derived views.

## 🚫 What ChatSnapshot Is Not

It is not:

- An agent runtime
- A workflow scheduler
- A semantic reasoning engine
- A knowledge graph
- A policy engine
- A telemetry replacement

It is a durable execution ledger.

## 🧠 Architectural Separation

| Concern | Owned By |
|---|---|
| Agent cognition | Agent runtime |
| Workflow scheduling | Application layer |
| Execution durability | ChatSnapshot |
| Semantic interpretation | External systems |
| Learning systems | External systems |
| Policy enforcement | External systems |

## 🏁 Summary

ChatSnapshot records:

- What happened.
- When it happened.
- What caused it.
- Across agents, applications, and infrastructure.

It does not decide what should happen.

It preserves what did.
