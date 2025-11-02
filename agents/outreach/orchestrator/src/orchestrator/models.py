"""
SQLAlchemy models for outreach tracking
"""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


Base = declarative_base()


class OutreachStatusEnum(str, Enum):
    """Outreach campaign status"""

    SCHEDULED = "scheduled"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    RESPONDED = "responded"
    BOUNCED = "bounced"
    UNSUBSCRIBED = "unsubscribed"
    FAILED = "failed"


class OutreachCampaignModel(Base):
    """
    Outreach campaign tracking table.

    One campaign per property - tracks email outreach to property owner.
    """

    __tablename__ = "outreach_campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)

    # Owner contact information
    owner_name = Column(String(255), nullable=False)
    owner_email = Column(String(255), nullable=False, index=True)

    # Campaign status
    status = Column(String(50), nullable=False, default="scheduled", index=True)

    # Email details
    subject = Column(String(255), nullable=False)
    memo_url = Column(Text, nullable=True)
    sendgrid_message_id = Column(String(255), nullable=True, index=True)

    # Scheduling
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True, index=True)

    # Tracking
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=True)
    clicked_at = Column(DateTime(timezone=True), nullable=True)
    responded_at = Column(DateTime(timezone=True), nullable=True)

    # Response tracking
    response_text = Column(Text, nullable=True)
    is_interested = Column(Boolean, nullable=True)

    # Metadata
    context = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    events = relationship("OutreachEventModel", back_populates="campaign", cascade="all, delete-orphan")


class OutreachEventModel(Base):
    """
    Outreach event log table.

    Immutable audit log of all outreach events (sent, opened, clicked, etc.)
    """

    __tablename__ = "outreach_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("outreach_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)

    # Event details
    event_type = Column(String(50), nullable=False, index=True)  # sent, delivered, opened, clicked, etc.
    event_data = Column(JSON, nullable=True)  # SendGrid webhook data

    # Timestamp
    occurred_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationship
    campaign = relationship("OutreachCampaignModel", back_populates="events")
