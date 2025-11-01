"""
Database models for Outreach Campaigns

Wave 3.3: Email outreach campaign management

Tables:
- email_templates: Email templates with variables
- campaigns: Outreach campaigns
- campaign_steps: Steps in campaign sequence
- campaign_recipients: Recipients and tracking
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean, JSON, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from .base import Base


class CampaignStatusEnum(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class CampaignTypeEnum(str, enum.Enum):
    SELLER_OUTREACH = "seller_outreach"
    AGENT_NETWORKING = "agent_networking"
    BUYER_NURTURE = "buyer_nurture"
    REFERRAL_REQUEST = "referral_request"
    FOLLOW_UP = "follow_up"


class RecipientStatusEnum(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    REPLIED = "replied"
    UNSUBSCRIBED = "unsubscribed"
    BOUNCED = "bounced"
    COMPLETED = "completed"


class EmailTemplate(Base):
    """Email templates for campaigns"""
    __tablename__ = "email_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    body_html = Column(Text, nullable=False)
    body_text = Column(Text, nullable=True)

    # Template variables (e.g., ['property_address', 'owner_name'])
    variables = Column(JSONB, default=list)

    # Tags for organization
    tags = Column(JSONB, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Campaign(Base):
    """Email outreach campaigns"""
    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    campaign_type = Column(Enum(CampaignTypeEnum), nullable=False)
    status = Column(Enum(CampaignStatusEnum), default=CampaignStatusEnum.DRAFT)

    # Sender info
    from_email = Column(String(255), nullable=False)
    from_name = Column(String(255), nullable=False)
    reply_to = Column(String(255), nullable=True)

    # Scheduling
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)

    # Analytics
    total_recipients = Column(Integer, default=0)
    emails_sent = Column(Integer, default=0)
    emails_delivered = Column(Integer, default=0)
    emails_opened = Column(Integer, default=0)
    emails_clicked = Column(Integer, default=0)
    replies_received = Column(Integer, default=0)
    unsubscribes = Column(Integer, default=0)

    # Metadata
    tags = Column(JSONB, default=list)
    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    steps = relationship("CampaignStep", back_populates="campaign", cascade="all, delete-orphan")
    recipients = relationship("CampaignRecipient", back_populates="campaign", cascade="all, delete-orphan")


class CampaignStep(Base):
    """Steps in campaign sequence"""
    __tablename__ = "campaign_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)

    step_number = Column(Integer, nullable=False)  # 1, 2, 3, ...
    template_id = Column(UUID(as_uuid=True), nullable=False)

    # Delays
    delay_days = Column(Integer, default=0)
    delay_hours = Column(Integer, default=0)
    send_time_hour = Column(Integer, nullable=True)  # Preferred hour (0-23)

    # Conditional logic
    conditions = Column(JSONB, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    campaign = relationship("Campaign", back_populates="steps")


class CampaignRecipient(Base):
    """Recipients in campaigns with tracking"""
    __tablename__ = "campaign_recipients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Recipient info
    email = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)

    # Associated entities
    property_id = Column(UUID(as_uuid=True), nullable=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True)

    # Template data for personalization
    template_data = Column(JSONB, default=dict)

    # Tracking
    status = Column(Enum(RecipientStatusEnum), default=RecipientStatusEnum.PENDING)
    current_step = Column(Integer, default=0)
    last_email_sent_at = Column(DateTime, nullable=True)
    last_opened_at = Column(DateTime, nullable=True)
    last_clicked_at = Column(DateTime, nullable=True)
    bounced_at = Column(DateTime, nullable=True)
    unsubscribed_at = Column(DateTime, nullable=True)

    # Metadata
    tags = Column(JSONB, default=list)
    metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    campaign = relationship("Campaign", back_populates="recipients")
