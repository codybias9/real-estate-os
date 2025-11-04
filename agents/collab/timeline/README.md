# Collab.Timeline

**Single-Writer Agent**: Property activity streams and collaboration timeline.

## Purpose

Collab.Timeline manages property-level activity streams for:
- System event logging (discoveries, enrichments, scores, outreach)
- User collaboration (comments, notes, tags, assignments)
- Real-time SSE broadcasts for live updates
- Audit trail with markdown support

## Usage

```python
from timeline import CollabTimeline, EventType
from timeline.repository import TimelineRepository

# Initialize
repo = TimelineRepository()
timeline = CollabTimeline(repository=repo)

# Log system event
timeline.log_system_event(
    tenant_id="tenant-uuid",
    property_id="prop-uuid",
    event_type=EventType.PROPERTY_SCORED,
    title="Investment score calculated",
    content="Property scored **78/100** based on analysis.",
    event_source="Score.Engine",
)

# Add user comment
timeline.add_comment(
    tenant_id="tenant-uuid",
    property_id="prop-uuid",
    user_id="user-uuid",
    user_name="John Doe",
    content="This property looks promising!",
)

# Add note (mutable)
result = timeline.add_note(
    tenant_id="tenant-uuid",
    property_id="prop-uuid",
    user_id="user-uuid",
    user_name="Jane Smith",
    title="Market Analysis",
    content="# Analysis\n\nStrong growth potential...",
)

# Get timeline
events = timeline.get_timeline(
    tenant_id="tenant-uuid",
    property_id="prop-uuid",
    limit=50,
)
```

## Features

### 1. System Events (Read-Only)
- Property discovered, enriched, scored
- Memo generated
- Outreach sent, opened, clicked
- State changes

### 2. User Collaboration Events
- Comments (immutable)
- Notes (mutable with edit history)
- Attachments
- Tags and assignments

### 3. Markdown Support
- Full markdown rendering
- HTML sanitization (bleach)
- Safe tags: p, strong, em, a, img, code, pre, lists, tables

### 4. SSE Broadcasts
```python
# Subscribe to property timeline
queue = await timeline.subscribe("tenant-uuid", "prop-uuid")

while True:
    event = await queue.get()
    print(f"New: {event.title}")
```

## Database Schema

### timeline_events (Immutable)
- System and user events
- Markdown content + rendered HTML
- Soft delete (user events only)

### timeline_notes (Mutable)
- Editable notes
- Version history via NOTE_UPDATED events
- Private notes support

## Testing
- 18 tests, 100% passing
- 69% coverage (95% for timeline logic)
- Markdown rendering and sanitization tested
- SSE broadcasts tested
