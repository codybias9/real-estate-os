# Pipeline.State

**Single-Writer Agent**: Tracks property lifecycle states and broadcasts changes via SSE.

## Purpose

Pipeline.State is responsible for:
- Managing property lifecycle state machine
- Validating state transitions
- Logging transition history (immutable audit trail)
- Broadcasting state changes to subscribers via Server-Sent Events (SSE)
- Providing state statistics and queries

## State Machine

```
discovered → enriched → scored → memo_generated → outreach_pending → contacted → responded

Any state → archived (terminal)
```

### States

| State | Description | Triggered By |
|-------|-------------|--------------|
| `discovered` | Property ingested from source | `event.discovery.intake` |
| `enriched` | Additional data fetched | `event.enrichment.features` |
| `scored` | Investment score computed | `event.score.created` |
| `memo_generated` | PDF memo created | `event.docgen.memo` |
| `outreach_pending` | Outreach scheduled | `event.outreach.scheduled` |
| `contacted` | Outreach email sent | `event.outreach.sent` |
| `responded` | Property owner responded | `event.outreach.response` |
| `archived` | Property archived | (manual/policy) |

## Architecture

**Single-Writer Pattern**: Only Pipeline.State updates property states

**Event-Driven**: Listens to events from all agents and updates states accordingly

**SSE Broadcasts**: Real-time state change notifications to connected clients

## Usage

### Initialize State Machine

```python
from state import PipelineState, PropertyState
from state.repository import StateRepository

# Initialize repository
repo = StateRepository()  # Reads DB_DSN from environment

# Initialize state machine
pipeline = PipelineState(repository=repo)
```

### Handle Events

```python
# Handle discovery event
transition = pipeline.handle_event(
    event_id="event-uuid",
    event_subject="event.discovery.intake",
    tenant_id="tenant-uuid",
    payload={"property_id": "prop-uuid", "apn": "123-456-789"}
)

if transition:
    print(f"Property {transition.property_id}: {transition.from_state} → {transition.to_state}")
```

### Query State

```python
# Get current state for a property
state = pipeline.get_state("property-uuid", "tenant-uuid")
print(f"Current state: {state.value}")

# Get all properties in a specific state
properties = pipeline.get_properties_by_state(
    PropertyState.SCORED,
    "tenant-uuid",
    limit=10
)

# Get state statistics
stats = pipeline.get_statistics("tenant-uuid")
print(f"Discovered: {stats.get('discovered', 0)}")
print(f"Scored: {stats.get('scored', 0)}")
```

### SSE Subscription

```python
import asyncio

async def watch_state_changes():
    # Subscribe to state transitions
    queue = await pipeline.subscribe("tenant-uuid")

    while True:
        # Wait for next transition
        transition = await queue.get()

        print(f"Property {transition.property_id}:")
        print(f"  {transition.from_state} → {transition.to_state}")
        print(f"  Event: {transition.event_subject}")

asyncio.run(watch_state_changes())
```

## Features

### 1. State Validation

Only valid transitions are allowed:
- `discovered → enriched` ✓
- `discovered → scored` ✗ (must go through enriched)
- Any state → `archived` ✓

### 2. Idempotency

Duplicate events are ignored:
- Receiving `event.enrichment.features` twice → state remains `enriched`
- No duplicate transitions logged

### 3. Out-of-Order Events

Gracefully handles event replay and out-of-order delivery:
- If `event.score.created` arrives before `event.enrichment.features`, state is created anyway
- Transition validation prevents invalid state changes

### 4. Immutable Audit Trail

All transitions are logged in `state_transitions` table:
- From state, to state
- Event ID, subject, payload
- Timestamp

### 5. SSE Broadcasts

State changes are broadcast to all subscribers for a tenant:
- Non-blocking (drops events if subscriber is slow)
- Per-tenant isolation
- JSON-serializable transition events

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=state --cov-report=html

# Run specific test
pytest tests/test_state.py::test_state_transition -v
```

## Database Schema

### property_states

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| tenant_id | UUID | Tenant isolation |
| property_id | UUID | Property reference |
| current_state | String | Current state |
| last_event_id | UUID | Last event that updated state |
| last_event_subject | String | Last event subject |
| last_transition_at | Timestamp | Last transition time |
| context | JSON | Additional context |

### state_transitions

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| property_state_id | UUID | Property state reference |
| from_state | String | Previous state |
| to_state | String | New state |
| event_id | UUID | Event that triggered transition |
| event_subject | String | Event subject |
| event_payload | JSON | Event payload (audit) |
| reason | Text | Human-readable reason |
| transitioned_at | Timestamp | Transition time |

## Dependencies

- **sqlalchemy**: ORM for state persistence
- **python-dateutil**: Timezone handling
- **sse-starlette**: SSE support for FastAPI (optional)
