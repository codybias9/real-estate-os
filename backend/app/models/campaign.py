"""Campaign, template, and outreach models."""
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, ForeignKey,
    DateTime, JSON, Enum as SQLEnum, Index
)
from sqlalchemy.orm import relationship
import enum
from backend.app.core.database import Base
from .base import TimestampMixin, SoftDeleteMixin


class CampaignStatus(str, enum.Enum):
    """Campaign status enumeration."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class OutreachChannel(str, enum.Enum):
    """Outreach channel enumeration."""
    EMAIL = "email"
    SMS = "sms"
    DIRECT_MAIL = "direct_mail"


class Campaign(Base, TimestampMixin, SoftDeleteMixin):
    """Marketing campaign model."""
    __tablename__ = 'campaigns'

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    created_by_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # Campaign details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SQLEnum(CampaignStatus), default=CampaignStatus.DRAFT, nullable=False, index=True)
    channel = Column(SQLEnum(OutreachChannel), nullable=False, index=True)

    # Scheduling
    scheduled_start = Column(DateTime(timezone=True), nullable=True)
    scheduled_end = Column(DateTime(timezone=True), nullable=True)
    actual_start = Column(DateTime(timezone=True), nullable=True)
    actual_end = Column(DateTime(timezone=True), nullable=True)

    # Template references
    email_template_id = Column(Integer, ForeignKey('email_templates.id', ondelete='SET NULL'), nullable=True)
    sms_template_id = Column(Integer, ForeignKey('sms_templates.id', ondelete='SET NULL'), nullable=True)

    # Metrics
    total_targets = Column(Integer, default=0, nullable=False)
    sent_count = Column(Integer, default=0, nullable=False)
    delivered_count = Column(Integer, default=0, nullable=False)
    opened_count = Column(Integer, default=0, nullable=False)
    clicked_count = Column(Integer, default=0, nullable=False)
    bounced_count = Column(Integer, default=0, nullable=False)
    unsubscribed_count = Column(Integer, default=0, nullable=False)

    # Settings
    settings = Column(JSON, default=dict)  # Rate limits, sending windows, etc.

    # Relationships
    created_by_user = relationship('User', back_populates='campaigns', foreign_keys=[created_by_id])
    email_template = relationship('EmailTemplate', back_populates='campaigns')
    sms_template = relationship('SMSTemplate', back_populates='campaigns')
    targets = relationship('CampaignTarget', back_populates='campaign', cascade='all, delete-orphan')
    outreach_attempts = relationship('OutreachAttempt', back_populates='campaign')


class CampaignTarget(Base, TimestampMixin):
    """Target leads for a campaign."""
    __tablename__ = 'campaign_targets'

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=False)
    lead_id = Column(Integer, ForeignKey('leads.id', ondelete='CASCADE'), nullable=False)

    # Targeting details
    contact_value = Column(String(255), nullable=False)  # Email or phone number to use
    personalization_data = Column(JSON, default=dict)  # Variables for template rendering

    # Status
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=True)
    clicked_at = Column(DateTime(timezone=True), nullable=True)
    bounced_at = Column(DateTime(timezone=True), nullable=True)
    unsubscribed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    campaign = relationship('Campaign', back_populates='targets')
    lead = relationship('Lead', back_populates='campaign_targets')

    __table_args__ = (
        Index('idx_campaign_lead', 'campaign_id', 'lead_id', unique=True),
    )


class EmailTemplate(Base, TimestampMixin, SoftDeleteMixin):
    """Email template model."""
    __tablename__ = 'email_templates'

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)

    name = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    body_html = Column(Text, nullable=False)
    body_text = Column(Text, nullable=True)

    # Template metadata
    category = Column(String(100), nullable=True)
    description = Column(String(500), nullable=True)
    variables = Column(JSON, default=list)  # List of template variables used

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    campaigns = relationship('Campaign', back_populates='email_template')


class SMSTemplate(Base, TimestampMixin, SoftDeleteMixin):
    """SMS template model."""
    __tablename__ = 'sms_templates'

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)

    name = Column(String(255), nullable=False)
    message = Column(String(1600), nullable=False)  # SMS length limits

    # Template metadata
    category = Column(String(100), nullable=True)
    description = Column(String(500), nullable=True)
    variables = Column(JSON, default=list)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    campaigns = relationship('Campaign', back_populates='sms_template')


class OutreachAttempt(Base, TimestampMixin):
    """Log of individual outreach attempts."""
    __tablename__ = 'outreach_attempts'

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    campaign_id = Column(Integer, ForeignKey('campaigns.id', ondelete='SET NULL'), nullable=True)
    lead_id = Column(Integer, ForeignKey('leads.id', ondelete='SET NULL'), nullable=True)

    # Attempt details
    channel = Column(SQLEnum(OutreachChannel), nullable=False, index=True)
    recipient = Column(String(255), nullable=False, index=True)
    subject = Column(String(500), nullable=True)
    message = Column(Text, nullable=True)

    # Status
    status = Column(String(50), nullable=False, index=True)  # sent, delivered, bounced, failed
    sent_at = Column(DateTime(timezone=True), nullable=False, index=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(String(500), nullable=True)

    # Tracking
    external_id = Column(String(255), nullable=True, index=True)  # Provider message ID
    opened_at = Column(DateTime(timezone=True), nullable=True)
    clicked_at = Column(DateTime(timezone=True), nullable=True)

    # Idempotency
    idempotency_key = Column(String(255), nullable=True, index=True)

    # Relationships
    campaign = relationship('Campaign', back_populates='outreach_attempts')
    deliverability_events = relationship('DeliverabilityEvent', back_populates='outreach_attempt', cascade='all, delete-orphan')


class DeliverabilityEvent(Base, TimestampMixin):
    """Deliverability events (bounces, complaints, etc.)."""
    __tablename__ = 'deliverability_events'

    id = Column(Integer, primary_key=True, index=True)
    outreach_attempt_id = Column(Integer, ForeignKey('outreach_attempts.id', ondelete='CASCADE'), nullable=True)

    event_type = Column(String(50), nullable=False, index=True)  # bounce, complaint, spam, block
    event_date = Column(DateTime(timezone=True), nullable=False, index=True)

    # Event details
    recipient = Column(String(255), nullable=False, index=True)
    bounce_type = Column(String(50), nullable=True)  # hard, soft, transient
    reason = Column(String(500), nullable=True)

    # Provider details
    provider = Column(String(100), nullable=True)
    external_id = Column(String(255), nullable=True)
    raw_data = Column(JSON, default=dict)

    # Relationships
    outreach_attempt = relationship('OutreachAttempt', back_populates='deliverability_events')


class UnsubscribeList(Base, TimestampMixin):
    """Do Not Contact (DNC) registry."""
    __tablename__ = 'unsubscribe_list'

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)

    contact_value = Column(String(255), nullable=False, index=True)  # Email or phone
    contact_type = Column(String(20), nullable=False)  # email, sms, all

    # Unsubscribe details
    unsubscribed_at = Column(DateTime(timezone=True), nullable=False, index=True)
    reason = Column(String(500), nullable=True)
    source = Column(String(100), nullable=True)  # 'user_request', 'bounce', 'complaint', etc.

    # Metadata
    campaign_id = Column(Integer, ForeignKey('campaigns.id', ondelete='SET NULL'), nullable=True)
    metadata = Column(JSON, default=dict)

    __table_args__ = (
        Index('idx_unsubscribe_contact', 'organization_id', 'contact_value', 'contact_type', unique=True),
    )
