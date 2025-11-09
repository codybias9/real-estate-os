"""
Repository for timeline event persistence
"""

import os
from typing import Optional, List
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import create_engine, and_, or_, text
from sqlalchemy.orm import sessionmaker, Session

from .models import Base, TimelineEventModel, TimelineNoteModel, EventTypeEnum


class TimelineRepository:
    """
    Repository for timeline operations.

    Provides event logging, note management, and timeline queries.
    """

    def __init__(self, db_dsn: Optional[str] = None):
        """
        Initialize repository with database connection.

        Args:
            db_dsn: Database connection string. If None, reads from DB_DSN env var.
        """
        self.db_dsn = db_dsn or os.getenv("DB_DSN")
        if not self.db_dsn:
            raise ValueError("DB_DSN must be provided or set in environment")

        self.engine = create_engine(self.db_dsn)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Detect if we're using PostgreSQL (for RLS support)
        self.is_postgresql = "postgresql" in self.db_dsn.lower()

    def create_tables(self):
        """Create all tables (for testing only, use Alembic in production)"""
        Base.metadata.create_all(self.engine)

    def set_tenant_context(self, session: Session, tenant_id: str):
        """Set the current tenant context for RLS policies (PostgreSQL only)"""
        if self.is_postgresql:
            session.execute(text(f"SET app.current_tenant_id = '{tenant_id}';"))

    def reset_tenant_context(self, session: Session):
        """Reset the tenant context (PostgreSQL only)"""
        if self.is_postgresql:
            session.execute(text("RESET app.current_tenant_id;"))

    def create_event(
        self,
        tenant_id: str,
        property_id: str,
        event_type: str,
        title: str,
        content: Optional[str] = None,
        content_html: Optional[str] = None,
        event_source: Optional[str] = None,
        event_data: Optional[dict] = None,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        attachments: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        is_system_event: bool = False,
    ) -> TimelineEventModel:
        """
        Create timeline event.

        Args:
            tenant_id: Tenant UUID
            property_id: Property UUID
            event_type: Event type string
            title: Event title
            content: Markdown content
            content_html: Rendered HTML content
            event_source: Source agent/service
            event_data: Structured event data
            correlation_id: Link to related events
            user_id: User who triggered event
            user_name: User name
            attachments: List of attachment URLs
            tags: List of tags
            is_system_event: Whether this is a system-generated event

        Returns:
            Created TimelineEventModel
        """
        with self.SessionLocal() as session:
            self.set_tenant_context(session, tenant_id)

            try:
                event = TimelineEventModel(
                    tenant_id=tenant_id,
                    property_id=property_id,
                    event_type=event_type,
                    title=title,
                    content=content,
                    content_html=content_html,
                    event_source=event_source,
                    event_data=event_data,
                    correlation_id=correlation_id,
                    user_id=user_id,
                    user_name=user_name,
                    attachments=attachments,
                    tags=tags,
                    is_system_event=is_system_event,
                    created_at=datetime.now(timezone.utc),
                )

                session.add(event)
                session.commit()
                session.refresh(event)

                return event
            finally:
                self.reset_tenant_context(session)

    def get_events(
        self,
        tenant_id: str,
        property_id: str,
        limit: int = 100,
        offset: int = 0,
        event_types: Optional[List[EventTypeEnum]] = None,
        include_system: bool = True,
    ) -> List[TimelineEventModel]:
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
            List of TimelineEventModel (newest first)
        """
        with self.SessionLocal() as session:
            self.set_tenant_context(session, tenant_id)

            try:
                query = session.query(TimelineEventModel).filter(
                    and_(
                        TimelineEventModel.tenant_id == tenant_id,
                        TimelineEventModel.property_id == property_id,
                        TimelineEventModel.deleted_at.is_(None),
                    )
                )

                # Filter by event types
                if event_types:
                    type_values = [t.value for t in event_types]
                    query = query.filter(TimelineEventModel.event_type.in_(type_values))

                # Filter system events
                if not include_system:
                    query = query.filter(TimelineEventModel.is_system_event == False)

                # Order and paginate
                events = (
                    query.order_by(TimelineEventModel.created_at.desc())
                    .limit(limit)
                    .offset(offset)
                    .all()
                )

                return events
            finally:
                self.reset_tenant_context(session)

    def count_by_type(self, tenant_id: str, property_id: str) -> dict[str, int]:
        """
        Count events by type for a property.

        Args:
            tenant_id: Tenant UUID
            property_id: Property UUID

        Returns:
            Dict mapping event type to count
        """
        with self.SessionLocal() as session:
            self.set_tenant_context(session, tenant_id)

            try:
                results = (
                    session.query(
                        TimelineEventModel.event_type,
                        TimelineEventModel.id,
                    )
                    .filter(
                        and_(
                            TimelineEventModel.tenant_id == tenant_id,
                            TimelineEventModel.property_id == property_id,
                            TimelineEventModel.deleted_at.is_(None),
                        )
                    )
                    .all()
                )

                counts = {}
                for event_type, _ in results:
                    counts[event_type] = counts.get(event_type, 0) + 1

                return counts
            finally:
                self.reset_tenant_context(session)

    def create_note(
        self,
        tenant_id: str,
        property_id: str,
        user_id: str,
        user_name: str,
        title: str,
        content: str,
        content_html: Optional[str] = None,
        is_private: bool = False,
        attachments: Optional[List[str]] = None,
    ) -> TimelineNoteModel:
        """
        Create timeline note.

        Args:
            tenant_id: Tenant UUID
            property_id: Property UUID
            user_id: User UUID
            user_name: User name
            title: Note title
            content: Markdown content
            content_html: Rendered HTML
            is_private: Private to author only
            attachments: List of attachment URLs

        Returns:
            Created TimelineNoteModel
        """
        with self.SessionLocal() as session:
            self.set_tenant_context(session, tenant_id)

            try:
                note = TimelineNoteModel(
                    tenant_id=tenant_id,
                    property_id=property_id,
                    user_id=user_id,
                    user_name=user_name,
                    title=title,
                    content=content,
                    content_html=content_html,
                    is_private=is_private,
                    attachments=attachments,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )

                session.add(note)
                session.commit()
                session.refresh(note)

                return note
            finally:
                self.reset_tenant_context(session)

    def get_note(
        self, note_id: str, tenant_id: str
    ) -> Optional[TimelineNoteModel]:
        """
        Get note by ID.

        Args:
            note_id: Note UUID
            tenant_id: Tenant UUID

        Returns:
            TimelineNoteModel if found, None otherwise
        """
        with self.SessionLocal() as session:
            self.set_tenant_context(session, tenant_id)

            try:
                return (
                    session.query(TimelineNoteModel)
                    .filter(
                        and_(
                            TimelineNoteModel.id == note_id,
                            TimelineNoteModel.tenant_id == tenant_id,
                            TimelineNoteModel.deleted_at.is_(None),
                        )
                    )
                    .first()
                )
            finally:
                self.reset_tenant_context(session)

    def update_note(
        self,
        note_id: str,
        tenant_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        content_html: Optional[str] = None,
    ) -> TimelineNoteModel:
        """
        Update note content.

        Args:
            note_id: Note UUID
            tenant_id: Tenant UUID
            title: New title (optional)
            content: New markdown content (optional)
            content_html: New HTML content (optional)

        Returns:
            Updated TimelineNoteModel

        Raises:
            ValueError: If note not found
        """
        with self.SessionLocal() as session:
            self.set_tenant_context(session, tenant_id)

            try:
                note = (
                    session.query(TimelineNoteModel)
                    .filter(
                        and_(
                            TimelineNoteModel.id == note_id,
                            TimelineNoteModel.tenant_id == tenant_id,
                            TimelineNoteModel.deleted_at.is_(None),
                        )
                    )
                    .first()
                )

                if not note:
                    raise ValueError(f"Note not found: {note_id}")

                # Update fields
                if title is not None:
                    note.title = title
                if content is not None:
                    note.content = content
                if content_html is not None:
                    note.content_html = content_html

                note.updated_at = datetime.now(timezone.utc)

                session.commit()
                session.refresh(note)

                return note
            finally:
                self.reset_tenant_context(session)

    def delete_event(self, event_id: str, tenant_id: str) -> bool:
        """
        Soft delete event (user events only).

        Args:
            event_id: Event UUID
            tenant_id: Tenant UUID

        Returns:
            True if deleted, False if not found or is system event
        """
        with self.SessionLocal() as session:
            self.set_tenant_context(session, tenant_id)

            try:
                event = (
                    session.query(TimelineEventModel)
                    .filter(
                        and_(
                            TimelineEventModel.id == event_id,
                            TimelineEventModel.tenant_id == tenant_id,
                            TimelineEventModel.is_system_event == False,
                            TimelineEventModel.deleted_at.is_(None),
                        )
                    )
                    .first()
                )

                if not event:
                    return False

                event.deleted_at = datetime.now(timezone.utc)
                session.commit()

                return True
            finally:
                self.reset_tenant_context(session)
