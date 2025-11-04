"""
SQLAlchemy models for property state tracking
"""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


Base = declarative_base()


class PropertyStateEnum(str, Enum):
    """
    Property lifecycle states.

    State machine flow:
    discovered → enriched → scored → memo_generated → outreach_pending → contacted → responded
    """

    DISCOVERED = "discovered"
    ENRICHED = "enriched"
    SCORED = "scored"
    MEMO_GENERATED = "memo_generated"
    OUTREACH_PENDING = "outreach_pending"
    CONTACTED = "contacted"
    RESPONDED = "responded"
    ARCHIVED = "archived"


class PropertyStateModel(Base):
    """
    Property state tracking table.

    Stores current state and transition history for each property.
    """

    __tablename__ = "property_states"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)

    # Current state
    current_state = Column(String(50), nullable=False, default="discovered", index=True)

    # Last transition metadata
    last_event_id = Column(UUID(as_uuid=True), nullable=True)
    last_event_subject = Column(String(100), nullable=True)
    last_transition_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Additional context
    context = Column(JSON, nullable=True)  # Free-form context data

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationship
    transitions = relationship("StateTransitionModel", back_populates="property_state", cascade="all, delete-orphan")


class StateTransitionModel(Base):
    """
    State transition history table.

    Immutable audit log of all state changes.
    """

    __tablename__ = "state_transitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    property_state_id = Column(UUID(as_uuid=True), ForeignKey("property_states.id", ondelete="CASCADE"), nullable=False, index=True)

    # Transition details
    from_state = Column(String(50), nullable=False)
    to_state = Column(String(50), nullable=False, index=True)

    # Event that triggered transition
    event_id = Column(UUID(as_uuid=True), nullable=False)
    event_subject = Column(String(100), nullable=False, index=True)
    event_payload = Column(JSON, nullable=True)

    # Metadata
    reason = Column(Text, nullable=True)
    transitioned_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationship
    property_state = relationship("PropertyStateModel", back_populates="transitions")
