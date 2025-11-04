"""
Collab.Timeline - Property activity streams and collaboration

Single-Writer Pattern: Only this agent writes to timeline_events
"""

import asyncio
import markdown
import bleach
from collections import defaultdict
from typing import Optional, Dict, Set, List
from uuid import UUID, uuid4
from datetime import datetime, timezone

from .models import EventTypeEnum, TimelineEventModel


# Allowed HTML tags and attributes for sanitization
ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'blockquote', 'code', 'pre', 'ul', 'ol', 'li', 'a', 'img',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'img': ['src', 'alt', 'title'],
    'code': ['class'],
}


class EventType:
    """Alias for EventTypeEnum for convenience"""

    # System events
    PROPERTY_DISCOVERED = EventTypeEnum.PROPERTY_DISCOVERED
    PROPERTY_ENRICHED = EventTypeEnum.PROPERTY_ENRICHED
    PROPERTY_SCORED = EventTypeEnum.PROPERTY_SCORED
    MEMO_GENERATED = EventTypeEnum.MEMO_GENERATED
    OUTREACH_SENT = EventTypeEnum.OUTREACH_SENT
    OUTREACH_OPENED = EventTypeEnum.OUTREACH_OPENED
    OUTREACH_CLICKED = EventTypeEnum.OUTREACH_CLICKED
    OUTREACH_RESPONDED = EventTypeEnum.OUTREACH_RESPONDED
    STATE_CHANGED = EventTypeEnum.STATE_CHANGED

    # User collaboration events
    COMMENT_ADDED = EventTypeEnum.COMMENT_ADDED
    NOTE_ADDED = EventTypeEnum.NOTE_ADDED
    NOTE_UPDATED = EventTypeEnum.NOTE_UPDATED
    ATTACHMENT_ADDED = EventTypeEnum.ATTACHMENT_ADDED
    TAG_ADDED = EventTypeEnum.TAG_ADDED
    TAG_REMOVED = EventTypeEnum.TAG_REMOVED
    ASSIGNED = EventTypeEnum.ASSIGNED
    UNASSIGNED = EventTypeEnum.UNASSIGNED


class TimelineEvent:
    """
    Timeline event data class.

    Wraps database model with convenient properties and markdown rendering.
    """

    def __init__(self, model: TimelineEventModel):
        self._model = model

    @property
    def id(self) -> str:
        return str(self._model.id)

    @property
    def event_type(self) -> str:
        return self._model.event_type

    @property
    def title(self) -> str:
        return self._model.title

    @property
    def content(self) -> Optional[str]:
        return self._model.content

    @property
    def content_html(self) -> Optional[str]:
        return self._model.content_html

    @property
    def created_at(self) -> datetime:
        return self._model.created_at

    @property
    def is_system_event(self) -> bool:
        return self._model.is_system_event

    @property
    def user_name(self) -> Optional[str]:
        return self._model.user_name

    def to_dict(self) -> dict:
        """Serialize to dict for API/SSE"""
        return {
            "id": self.id,
            "event_type": self.event_type,
            "title": self.title,
            "content": self.content,
            "content_html": self.content_html,
            "is_system_event": self.is_system_event,
            "user_name": self.user_name,
            "created_at": self.created_at.isoformat(),
            "event_data": self._model.event_data,
            "tags": self._model.tags,
        }


class CollabTimeline:
    """
    Property timeline for collaboration and activity tracking.

    Features:
    - Single-writer pattern (only this agent writes to timeline)
    - System events from other agents (auto-generated)
    - User collaboration events (comments, notes, tags)
    - Markdown support with HTML sanitization
    - Real-time SSE broadcasts
    - Property-level activity streams
    """

    def __init__(self, repository):
        """
        Initialize timeline.

        Args:
            repository: TimelineRepository for persistence
        """
        self.repository = repository

        # SSE subscribers: (tenant_id, property_id) → set of queues
        self._subscribers: Dict[tuple, Set[asyncio.Queue]] = defaultdict(set)

        # Markdown renderer
        self.md = markdown.Markdown(extensions=[
            'extra',  # Tables, fenced code blocks, etc.
            'nl2br',  # Newline to <br>
            'sane_lists',
        ])

    def log_system_event(
        self,
        tenant_id: str,
        property_id: str,
        event_type: EventTypeEnum,
        title: str,
        content: Optional[str] = None,
        event_source: Optional[str] = None,
        event_data: Optional[dict] = None,
        correlation_id: Optional[str] = None,
    ) -> TimelineEvent:
        """
        Log system event (from other agents).

        Args:
            tenant_id: Tenant UUID
            property_id: Property UUID
            event_type: Event type enum
            title: Event title (e.g., "Property discovered")
            content: Optional markdown-formatted description
            event_source: Which agent triggered this (e.g., "Discovery.Resolver")
            event_data: Structured event data
            correlation_id: Link to related events

        Returns:
            TimelineEvent

        Example:
            >>> timeline.log_system_event(
            ...     tenant_id="tenant-uuid",
            ...     property_id="prop-uuid",
            ...     event_type=EventType.PROPERTY_SCORED,
            ...     title="Investment score calculated",
            ...     content="Property scored **78/100** based on market analysis.",
            ...     event_source="Score.Engine",
            ...     event_data={"score": 78, "model": "deterministic-v1"},
            ... )
        """
        # Render markdown to HTML
        content_html = None
        if content:
            html = self.md.convert(content)
            content_html = bleach.clean(
                html,
                tags=ALLOWED_TAGS,
                attributes=ALLOWED_ATTRIBUTES,
                strip=True,
            )
            self.md.reset()  # Reset for next conversion

        # Create event
        event_model = self.repository.create_event(
            tenant_id=tenant_id,
            property_id=property_id,
            event_type=event_type.value,
            title=title,
            content=content,
            content_html=content_html,
            event_source=event_source,
            event_data=event_data,
            correlation_id=correlation_id,
            is_system_event=True,
        )

        event = TimelineEvent(event_model)

        # Broadcast to subscribers
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._broadcast_event(tenant_id, property_id, event))
        except RuntimeError:
            # No event loop running (sync context)
            pass

        return event

    def add_comment(
        self,
        tenant_id: str,
        property_id: str,
        user_id: str,
        user_name: str,
        content: str,
        attachments: Optional[List[str]] = None,
    ) -> TimelineEvent:
        """
        Add user comment to timeline.

        Args:
            tenant_id: Tenant UUID
            property_id: Property UUID
            user_id: User UUID
            user_name: User name
            content: Markdown-formatted comment
            attachments: Optional list of attachment URLs

        Returns:
            TimelineEvent

        Example:
            >>> timeline.add_comment(
            ...     tenant_id="tenant-uuid",
            ...     property_id="prop-uuid",
            ...     user_id="user-uuid",
            ...     user_name="John Doe",
            ...     content="This property looks promising! Let's schedule a visit.",
            ... )
        """
        # Render markdown
        html = self.md.convert(content)
        content_html = bleach.clean(
            html,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            strip=True,
        )
        self.md.reset()

        # Create event
        event_model = self.repository.create_event(
            tenant_id=tenant_id,
            property_id=property_id,
            event_type=EventTypeEnum.COMMENT_ADDED.value,
            title=f"{user_name} commented",
            content=content,
            content_html=content_html,
            user_id=user_id,
            user_name=user_name,
            attachments=attachments,
            is_system_event=False,
        )

        event = TimelineEvent(event_model)

        # Broadcast
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._broadcast_event(tenant_id, property_id, event))
        except RuntimeError:
            pass

        return event

    def add_note(
        self,
        tenant_id: str,
        property_id: str,
        user_id: str,
        user_name: str,
        title: str,
        content: str,
        is_private: bool = False,
        attachments: Optional[List[str]] = None,
    ) -> dict:
        """
        Add user note (mutable).

        Args:
            tenant_id: Tenant UUID
            property_id: Property UUID
            user_id: User UUID
            user_name: User name
            title: Note title
            content: Markdown-formatted note
            is_private: Private to author only
            attachments: Optional list of attachment URLs

        Returns:
            Dict with note_id and timeline event

        Example:
            >>> result = timeline.add_note(
            ...     tenant_id="tenant-uuid",
            ...     property_id="prop-uuid",
            ...     user_id="user-uuid",
            ...     user_name="Jane Smith",
            ...     title="Property Analysis",
            ...     content="# Market Analysis\n\nThis property is in a high-growth area...",
            ...     is_private=False,
            ... )
        """
        # Render markdown
        html = self.md.convert(content)
        content_html = bleach.clean(
            html,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            strip=True,
        )
        self.md.reset()

        # Create note
        note_model = self.repository.create_note(
            tenant_id=tenant_id,
            property_id=property_id,
            user_id=user_id,
            user_name=user_name,
            title=title,
            content=content,
            content_html=content_html,
            is_private=is_private,
            attachments=attachments,
        )

        # Log event
        event_model = self.repository.create_event(
            tenant_id=tenant_id,
            property_id=property_id,
            event_type=EventTypeEnum.NOTE_ADDED.value,
            title=f"{user_name} added note: {title}",
            content=f"[View note]({note_model.id})",
            user_id=user_id,
            user_name=user_name,
            event_data={"note_id": str(note_model.id), "is_private": is_private},
            is_system_event=False,
        )

        event = TimelineEvent(event_model)

        # Broadcast
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._broadcast_event(tenant_id, property_id, event))
        except RuntimeError:
            pass

        return {
            "note_id": str(note_model.id),
            "event": event,
        }

    def get_timeline(
        self,
        tenant_id: str,
        property_id: str,
        limit: int = 100,
        offset: int = 0,
        event_types: Optional[List[EventTypeEnum]] = None,
        include_system: bool = True,
    ) -> List[TimelineEvent]:
        """
        Get timeline events for a property.

        Args:
            tenant_id: Tenant UUID
            property_id: Property UUID
            limit: Maximum number of events
            offset: Number of events to skip
            event_types: Filter by event types
            include_system: Include system events

        Returns:
            List of TimelineEvent (newest first)

        Example:
            >>> events = timeline.get_timeline(
            ...     tenant_id="tenant-uuid",
            ...     property_id="prop-uuid",
            ...     limit=50,
            ...     event_types=[EventType.COMMENT_ADDED, EventType.NOTE_ADDED],
            ... )
        """
        event_models = self.repository.get_events(
            tenant_id=tenant_id,
            property_id=property_id,
            limit=limit,
            offset=offset,
            event_types=event_types,
            include_system=include_system,
        )

        return [TimelineEvent(m) for m in event_models]

    def get_statistics(self, tenant_id: str, property_id: str) -> dict:
        """
        Get timeline statistics for a property.

        Args:
            tenant_id: Tenant UUID
            property_id: Property UUID

        Returns:
            Dict with counts per event type
        """
        return self.repository.count_by_type(tenant_id, property_id)

    # SSE Subscription Management

    async def subscribe(self, tenant_id: str, property_id: str) -> asyncio.Queue:
        """
        Subscribe to timeline events for a property.

        Args:
            tenant_id: Tenant UUID
            property_id: Property UUID

        Returns:
            Queue that will receive TimelineEvent updates

        Example:
            >>> queue = await timeline.subscribe("tenant-uuid", "prop-uuid")
            >>> while True:
            ...     event = await queue.get()
            ...     print(f"New event: {event.title}")
        """
        queue = asyncio.Queue(maxsize=100)
        key = (tenant_id, property_id)
        self._subscribers[key].add(queue)
        return queue

    async def unsubscribe(self, tenant_id: str, property_id: str, queue: asyncio.Queue):
        """
        Unsubscribe from timeline events.

        Args:
            tenant_id: Tenant UUID
            property_id: Property UUID
            queue: Queue to remove
        """
        key = (tenant_id, property_id)
        if key in self._subscribers:
            self._subscribers[key].discard(queue)

    async def _broadcast_event(
        self, tenant_id: str, property_id: str, event: TimelineEvent
    ):
        """
        Broadcast event to all subscribers for a property.

        Args:
            tenant_id: Tenant UUID
            property_id: Property UUID
            event: TimelineEvent to broadcast
        """
        key = (tenant_id, property_id)
        if key not in self._subscribers:
            return

        # Send to all queues for this property
        for queue in list(self._subscribers[key]):
            try:
                # Non-blocking put, drop if queue is full
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # Queue is full, drop event
                pass
