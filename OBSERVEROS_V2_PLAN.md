# ObserverOS v2 Plan (Clean-Slate)

This document is the authoritative audit of ChatSnapshot v1 and the clean-slate architecture for ObserverOS v2.
It is intentionally blunt and does not preserve backward compatibility.

## Part A ? Architectural Audit (v1)

### 1) Event Model
Answer: Not event-first in a process sense. Identity is `correlation_id`, not `process_id`.
Evidence: `src/chatsnapshot/events/envelope.py` uses `correlation_id` as the primary identity with no `process_id` or `parent_process_id`.

Answer: Implicit process state exists outside projections.
Evidence: `src/chatsnapshot/ingest/base.py` stores `_last_event_id` as mutable adapter state.

Answer: Chat/session fields are embedded as the primary identity.
Evidence: `ChatSnapshot.chat_id` in `src/chatsnapshot/snapshot.py` and `SnapshotProjection` in `src/chatsnapshot/projections/snapshot.py` map `correlation_id` to `chat_id`.

Answer: Causality links are partial and incomplete.
Evidence: `causation_id` exists, but there is no `parent_process_id` or explicit correlation vs process separation in `src/chatsnapshot/events/envelope.py`.

Answer: Mutable state is embedded inside event payloads.
Evidence: `SnapshotProjection` extracts `context_variables` and `llm_config` from event payloads in `src/chatsnapshot/projections/snapshot.py`.

### 2) Observer Layer
Answer: Observer does more than ingestion and persistence.
Evidence: `src/chatsnapshot/observer.py` includes querying and pub/sub subscriptions.

Answer: Observer does not perform projection logic.
Evidence: No projection code inside `src/chatsnapshot/observer.py`.

Answer: Observer is not orchestrating execution, but pub/sub introduces execution coupling.
Evidence: `Observer.record` awaits subscriber callbacks in `src/chatsnapshot/observer.py`.

Answer: Observer accumulates state outside EventStore.
Evidence: Subscriptions and callback registry in `src/chatsnapshot/observer.py`.

### 3) Storage Layer
Answer: Append-only is not enforced.
Evidence: `MemoryEventStore.clear()` allows deletion in `src/chatsnapshot/storage/memory_store.py`.

Answer: Ordering is not deterministic under concurrency.
Evidence: All stores sort by `timestamp` instead of append sequence in `src/chatsnapshot/storage/*`.

Answer: Idempotency is not handled.
Evidence: `JSONEventStore` and `MemoryEventStore` accept duplicates; `SQLiteEventStore` and `MongoDBEventStore` only enforce unique `event_id` but Observer generates new IDs each record.

Answer: Projections do not write back into storage.
Evidence: No projection write paths in `src/chatsnapshot/projections/*`.

### 4) Projection Layer
Answer: Projections are pure reducers, but replay safety depends on ordering.
Evidence: `Projection` is pure in `src/chatsnapshot/projections/base.py`, but inputs are timestamp-ordered by stores.

Answer: No external side effects.
Evidence: `src/chatsnapshot/projections/transcript.py` and `src/chatsnapshot/projections/snapshot.py` are pure.

Answer: Projection versioning is not supported.
Evidence: No versioning fields or interfaces.

### 5) Chat Bias Detection
Answer: Chat is the primary abstraction.
Evidence: `ChatSnapshot` and `SnapshotProjection` are core outputs, and tests/examples center chat sessions.

Answer: `session_id` is effectively synonymous with identity.
Evidence: `correlation_id` is treated as `chat_id`.

Answer: Conversational context is assumed central.
Evidence: Transcript projection is a first-class output in `src/chatsnapshot/projections/transcript.py`.

### 6) Nested Process Support
Answer: No parent/child process modeling.
Evidence: No `parent_process_id` anywhere in v1.

Answer: Flat session structure is assumed.
Evidence: `correlation_id` is a single flat identifier.

### 7) Execution Leakage
Answer: No explicit scheduler, but Observer pub/sub introduces execution coupling.
Evidence: Subscriber callbacks run on record path in `src/chatsnapshot/observer.py`.

### 8) Concurrency and Scaling
Answer: Async model is unsafe under concurrency.
Evidence: `_last_event_id` in `IngestAdapter` is shared mutable state in `src/chatsnapshot/ingest/base.py`.

Answer: Ordering can break under concurrency.
Evidence: All stores rely on timestamp ordering.

Answer: Pub/sub is coupled to storage path.
Evidence: `Observer.record` awaits subscriber callbacks.

## Part B ? What It Actually Is Today

This system is a chat persistence helper with an event wrapper and a timestamp-ordered store.
It is not a process-first canonical ledger.

Chat assumptions are embedded in the core data model and projections.
Session concepts leak into identity.
State is implicitly stored in adapters and payloads.
The Observer mixes write, read, and pub/sub concerns.

## Part C ? Reusable Primitives

Only the following concepts survive a clean rewrite:

- The idea of a pure `Projection` interface from `src/chatsnapshot/projections/base.py`.
- The idea of an async `EventStore` interface from `src/chatsnapshot/storage/base.py`.
- The JSONL append-only format as a storage concept, not the current implementation.

Everything else is chat-biased or lacks deterministic ordering guarantees.

## Part D ? Structural Violations (Explicit Flags)

- Chat-first design: `ChatSnapshot` and `SnapshotProjection` are core types.
- Scope/session coupling: `correlation_id` is used as the primary identity.
- Execution leakage: Observer pub/sub couples persistence to execution timing.
- Non-determinism: timestamp-based ordering in all stores.
- Event envelope weakness: missing `process_id`, `parent_process_id`, and deterministic sequencing.
- Layer coupling: Observer mixes storage and distribution concerns.

## Part E ? Clean-Slate v2 ObserverOS Architecture

### High-Level Diagram (v1 vs v2)

```
v1 (actual)
Runtime/AG2 -> IngestAdapter -> Observer (record + query + pubsub)
                                   -> EventStore (timestamp ordered)
                                   -> Projections (chat snapshot, transcript)

v2 (desired)
Runtime -> IngestAdapter -> Observer (ingest + persist only)
                              -> EventStore (append-only, deterministic order)
                              -> ProjectionEngine -> Projection Store -> Query API
```

### Core Modules (Minimum)

1. EventEnvelope v2
- Required: `event_id`, `process_id`, `event_type`, `occurred_at`, `recorded_at`, `source`, `payload`.
- Required: `parent_process_id` (nullable), `causation_id` (nullable).
- Ordering: `process_seq` and `global_seq` assigned by the EventStore.
- Optional: `correlation_id` for distributed tracing only.
- `schema_version` for forward evolution.

2. EventStore
- Append-only with immutable events.
- Deterministic `global_seq` and `process_seq`.
- Idempotency keyed by `event_id` or `idempotency_key`.
- Query by `process_id`, `global_seq` ranges, `event_type`, and time windows.

3. IngestAdapter
- Normalizes runtime events into EventEnvelope v2.
- No shared mutable causation state; causation is explicit per event.

4. Observer
- Write-only. Accepts canonical events and persists them.
- No queries, no pub/sub.

5. ProjectionEngine
- Pure reducers with checkpointed replay by `global_seq`.
- Projection versioning and rebuild support.

6. Query API
- Read-only and projection-backed.
- No direct EventStore reads in production paths.

### Minimal Viable Core

- EventEnvelope v2 + EventStore with deterministic ordering.
- Observer write-only pipeline.
- IngestAdapter base + one reference adapter.
- ProjectionEngine + ProcessRegistry projection.
- Query API for process registry and timelines.

## Part F ? Deletion and Rewrite Plan

### Delete Outright

- `src/chatsnapshot/snapshot.py`
- `src/chatsnapshot/projections/snapshot.py`
- `examples/minimal.py`
- `tests/test_observer.py`
- `README.md` and `infrastructure.md` (rewrite to reflect v2)

### Rewrite Entirely

- `src/chatsnapshot/events/envelope.py`
- `src/chatsnapshot/events/types.py`
- `src/chatsnapshot/observer.py`
- `src/chatsnapshot/ingest/base.py`
- `src/chatsnapshot/ingest/ag2.py`
- `src/chatsnapshot/storage/json_store.py`
- `src/chatsnapshot/storage/sqlite_store.py`
- `src/chatsnapshot/storage/mongodb_store.py`
- `src/chatsnapshot/__init__.py`

### Refactor (Keep Concept, Replace Implementation)

- `src/chatsnapshot/projections/base.py`
- `src/chatsnapshot/storage/base.py`

### Preserve

- `LICENSE`

## Required Deliverables

### List of Architectural Misalignments

- Identity is `correlation_id`, not `process_id`.
- No `parent_process_id` or nested process modeling.
- Timestamp-based ordering is nondeterministic under concurrency.
- Idempotency is not enforced across stores.
- Chat is the core abstraction.
- Observer mixes write, read, and pub/sub concerns.
- Mutable adapter state breaks replay.
- Projection determinism depends on weak ordering guarantees.
- Docs claim capabilities not implemented.

### Critical Refactor/Rewrite Targets (Priority Order)

1. EventEnvelope v2 with process identity and deterministic sequencing.
2. EventStore append-only contract with idempotency and strict ordering.
3. Observer write-only pipeline.
4. IngestAdapter redesign with explicit causation.
5. ProjectionEngine with versioning and checkpoints.
6. Query API and projection-backed reads.
7. Removal of chat-first models and projections.

### Minimal Safe Refactor Path (Phased Rewrite)

1. Freeze v1 and start a new v2 repo with only EventEnvelope v2 + EventStore + Observer write-only.
2. Build one adapter and run shadow ingestion to validate ordering and schema.
3. Add ProjectionEngine + ProcessRegistry projection + Query API.
4. Cut over integrations and retire v1.

### Risk Assessment If Nothing Changes

- Replay will be unreliable under concurrency.
- Chat bias will block non-chat workloads.
- Nested process modeling is impossible.
- Causation chains will be incorrect under async ingestion.
- Duplicates will pollute the ledger.
- The system will not be credible as a canonical system-of-record.

### What It Is vs What It Must Become

- Today: chat persistence helper with a thin event wrapper and timestamp-ordered storage.
- Target: process-first, deterministic, append-only ledger with replayable projections and read-only query API.

### Prioritized Rewrite Roadmap

Phase 1: Core ledger and envelope v2.
Phase 2: Projection engine and query layer.
Phase 3: Adapter ecosystem and operational tooling.

### Clean Module Structure for v2 Repo

```
observeros/
  src/observeros/
    core/
      envelope.py
      ids.py
      validation.py
      clock.py
      types.py
    ingest/
      base.py
      adapters/
        ag2.py
    observer/
      observer.py
    ledger/
      event_store.py
      sqlite_store.py
      jsonl_store.py
      memory_store.py
    projections/
      base.py
      engine.py
      process_state.py
      task_state.py
      dependency.py
    query/
      api.py
      models.py
    schemas/
      envelope.schema.json
  tests/
  examples/
```
