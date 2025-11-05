"""Campaign models."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SQLEnum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum
from ..database import Base


class CampaignType(str, Enum):
    """Campaign type enum."""
    EMAIL = "email"
    SMS = "sms"
    DIRECT_MAIL = "direct_mail"
    SOCIAL_MEDIA = "social_media"


class CampaignStatus(str, Enum):
    """Campaign status enum."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class Campaign(Base):
    """Campaign model."""

    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Campaign Details
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    campaign_type = Column(SQLEnum(CampaignType), nullable=False, index=True)
    status = Column(SQLEnum(CampaignStatus), default=CampaignStatus.DRAFT, nullable=False, index=True)

    # Content
    subject = Column(String(500), nullable=True)  # Email subject or SMS preview
    content = Column(Text, nullable=False)
    template_id = Column(Integer, ForeignKey("campaign_templates.id"), nullable=True)

    # Scheduling
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Statistics
    total_recipients = Column(Integer, default=0, nullable=False)
    sent_count = Column(Integer, default=0, nullable=False)
    delivered_count = Column(Integer, default=0, nullable=False)
    opened_count = Column(Integer, default=0, nullable=False)
    clicked_count = Column(Integer, default=0, nullable=False)
    bounced_count = Column(Integer, default=0, nullable=False)
    unsubscribed_count = Column(Integer, default=0, nullable=False)

    # Metadata
    additional_data = Column(Text, nullable=True)  # JSON object (renamed from metadata)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="campaigns")
    template = relationship("CampaignTemplate", back_populates="campaigns")
    recipients = relationship("CampaignRecipient", back_populates="campaign", cascade="all, delete-orphan")


class CampaignTemplate(Base):
    """Campaign template model."""

    __tablename__ = "campaign_templates"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Template Details
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    campaign_type = Column(SQLEnum(CampaignType), nullable=False, index=True)
    subject = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization")
    campaigns = relationship("Campaign", back_populates="template")


class CampaignRecipient(Base):
    """Campaign recipient model for tracking individual sends."""

    __tablename__ = "campaign_recipients"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True, index=True)

    # Recipient Info
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    # Status
    status = Column(String(50), default="pending", nullable=False)  # pending, sent, delivered, opened, clicked, bounced, failed
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=True)
    clicked_at = Column(DateTime(timezone=True), nullable=True)
    bounced_at = Column(DateTime(timezone=True), nullable=True)
    unsubscribed_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    error_message = Column(Text, nullable=True)
    additional_data = Column(Text, nullable=True)  # JSON object (renamed from metadata)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    campaign = relationship("Campaign", back_populates="recipients")
    lead = relationship("Lead")
