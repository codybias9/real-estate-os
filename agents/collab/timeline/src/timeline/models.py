"""
SQLAlchemy models for timeline events
"""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


Base = declarative_base()


class EventTypeEnum(str, Enum):
    """Timeline event types"""

    # System events
    PROPERTY_DISCOVERED = "property_discovered"
    PROPERTY_ENRICHED = "property_enriched"
    PROPERTY_SCORED = "property_scored"
    MEMO_GENERATED = "memo_generated"
    OUTREACH_SENT = "outreach_sent"
    OUTREACH_OPENED = "outreach_opened"
    OUTREACH_CLICKED = "outreach_clicked"
    OUTREACH_RESPONDED = "outreach_responded"
    STATE_CHANGED = "state_changed"

    # User collaboration events
    COMMENT_ADDED = "comment_added"
    NOTE_ADDED = "note_added"
    NOTE_UPDATED = "note_updated"
    ATTACHMENT_ADDED = "attachment_added"
    TAG_ADDED = "tag_added"
    TAG_REMOVED = "tag_removed"
    ASSIGNED = "assigned"
    UNASSIGNED = "unassigned"


class TimelineEventModel(Base):
    """
    Timeline event table.

    Immutable log of all property-related events for collaboration and audit.
    Single-writer: Only Collab.Timeline writes to this table.
    """

    __tablename__ = "timeline_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)

    # Event metadata
    event_type = Column(String(50), nullable=False, index=True)
    event_source = Column(String(100), nullable=True)  # Which agent/user triggered this
    correlation_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Link related events

    # User who triggered event (for collaboration events)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    user_name = Column(String(255), nullable=True)

    # Event content
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)  # Markdown-formatted content
    content_html = Column(Text, nullable=True)  # Rendered HTML (cached)

    # Event data
    event_data = Column(JSON, nullable=True)  # Structured event data

    # System event flag
    is_system_event = Column(Boolean, nullable=False, default=False, index=True)

    # Attachments and tags
    attachments = Column(JSON, nullable=True)  # List of attachment URLs
    tags = Column(JSON, nullable=True)  # List of tags

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    # Soft delete (for user events only, system events are immutable)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class TimelineNoteModel(Base):
    """
    Timeline note table (mutable).

    Notes can be edited, unlike events which are immutable.
    When a note is updated, a NOTE_UPDATED event is added to timeline.
    """

    __tablename__ = "timeline_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)

    # Note content
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)  # Markdown-formatted
    content_html = Column(Text, nullable=True)  # Rendered HTML

    # Author
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_name = Column(String(255), nullable=False)

    # Visibility
    is_private = Column(Boolean, nullable=False, default=False)  # Private to author only

    # Attachments
    attachments = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    # Soft delete
    deleted_at = Column(DateTime(timezone=True), nullable=True)
