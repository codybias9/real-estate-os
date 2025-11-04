# PR8: Pipeline.State + SSE Broadcasts - Evidence Pack

**PR**: `feat/pipeline-state-sse`
**Date**: 2025-11-02
**Branch**: `claude/realestate-audit-canvas-011CUjnrkmyeMSTozDmpy6xx`

## Summary

Implemented Pipeline.State agent for property lifecycle state machine with Server-Sent Events (SSE) broadcasts for real-time state change notifications.

## What Was Built

### 1. State Machine

**File**: `agents/pipeline/state/src/state/state.py` (333 lines)

**States**:
- `discovered` → `enriched` → `scored` → `memo_generated` → `outreach_pending` → `contacted` → `responded`
- Any state → `archived` (terminal)

**Event Mapping**:
| Event Subject | Target State |
|---------------|--------------|
| event.discovery.intake | discovered |
| event.enrichment.features | enriched |
| event.score.created | scored |
| event.docgen.memo | memo_generated |
| event.outreach.scheduled | outreach_pending |
| event.outreach.sent | contacted |
| event.outreach.response | responded |

**Features**:
- State transition validation (only valid transitions allowed)
- Idempotent event handling (duplicate events ignored)
- Out-of-order event handling (creates state even if intermediate steps missing)
- SSE broadcasts to subscribers
- Tenant isolation

### 2. Database Models

**File**: `agents/pipeline/state/src/state/models.py` (95 lines)

**Tables**:
- `property_states`: Current state per property
- `state_transitions`: Immutable audit trail of all transitions

### 3. State Repository

**File**: `agents/pipeline/state/src/state/repository.py` (321 lines)

**Methods**:
- `get_state()`: Get current state for property
- `create_state()`: Initialize state for new property
- `transition_state()`: Perform state transition + log to audit trail
- `get_transitions()`: Query transition history
- `get_properties_by_state()`: Filter properties by state
- `count_by_state()`: State statistics per tenant

### 4. SSE Broadcasts

**Implementation**:
- Async queue-based pub/sub
- Per-tenant subscription isolation
- Non-blocking broadcasts (drops events if queue full)
- Graceful degradation (skips broadcast if no event loop)

**Usage**:
```python
# Subscribe
queue = await pipeline.subscribe("tenant-uuid")

# Receive transitions
while True:
    transition = await queue.get()
    print(f"{transition.property_id}: {transition.from_state} → {transition.to_state}")
```

## Test Results

**Test Suite**: 21 tests, 100% passing
**Coverage**: 68% total (95% for state machine logic, 22% for repository due to mocking)

**Tests**:
- ✓ State creation on discovery event
- ✓ Valid state transitions
- ✓ Invalid transition rejection
- ✓ Idempotent event handling
- ✓ Unknown event ignored
- ✓ SSE subscription/unsubscription
- ✓ SSE broadcast to subscribers
- ✓ Tenant isolation for broadcasts
- ✓ Queue overflow handling

## Files Created

- `agents/pipeline/state/pyproject.toml` (49 lines)
- `agents/pipeline/state/README.md` (221 lines)
- `agents/pipeline/state/src/state/__init__.py` (6 lines)
- `agents/pipeline/state/src/state/models.py` (95 lines)
- `agents/pipeline/state/src/state/repository.py` (321 lines)
- `agents/pipeline/state/src/state/state.py` (333 lines)
- `agents/pipeline/state/tests/conftest.py` (66 lines)
- `agents/pipeline/state/tests/test_state.py` (381 lines)

**Total**: 1,472 lines

## Architectural Decisions

### 1. Single-Writer Pattern
Only Pipeline.State updates property states - ensures consistency

### 2. Event Loop Detection
Broadcasts only when async event loop is running - enables sync usage in tests

### 3. Queue Overflow Strategy
Drop events when subscriber queue is full - prevents slow subscribers from blocking system

### 4. Tenant Isolation
Subscribers only receive events for their tenant

### 5. Audit Trail
All transitions logged immutably in `state_transitions` table

## Next Steps

**PR9**: Outreach.Orchestrator with SendGrid integration
- Email template rendering
- SendGrid API integration
- Outreach scheduling logic
- Event publishing (event.outreach.*)
