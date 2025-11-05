"""Campaign and marketing models."""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from .base import BaseModel, SoftDeleteMixin
import enum


class CampaignType(str, enum.Enum):
    """Campaign type enum."""
    EMAIL = "email"
    SMS = "sms"
    DIRECT_MAIL = "direct_mail"
    SOCIAL_MEDIA = "social_media"


class CampaignStatus(str, enum.Enum):
    """Campaign status enum."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class Campaign(BaseModel, SoftDeleteMixin):
    """Marketing campaign model."""

    __tablename__ = "campaigns"

    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    template_id = Column(Integer, ForeignKey("campaign_templates.id", ondelete="SET NULL"), nullable=True, index=True)

    # Basic Info
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    campaign_type = Column(SQLEnum(CampaignType), nullable=False, index=True)
    status = Column(SQLEnum(CampaignStatus), nullable=False, default=CampaignStatus.DRAFT, index=True)

    # Scheduling
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Content
    subject = Column(String(500), nullable=True)
    content = Column(Text, nullable=True)
    from_name = Column(String(255), nullable=True)
    from_email = Column(String(255), nullable=True)
    from_phone = Column(String(50), nullable=True)

    # Targeting
    target_filters = Column(JSON, nullable=True)  # Criteria for selecting recipients
    total_recipients = Column(Integer, default=0, nullable=False)

    # Tracking
    sent_count = Column(Integer, default=0, nullable=False)
    delivered_count = Column(Integer, default=0, nullable=False)
    opened_count = Column(Integer, default=0, nullable=False)
    clicked_count = Column(Integer, default=0, nullable=False)
    bounced_count = Column(Integer, default=0, nullable=False)
    unsubscribed_count = Column(Integer, default=0, nullable=False)
    failed_count = Column(Integer, default=0, nullable=False)

    # Settings
    settings = Column(JSON, nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="campaigns")
    created_by = relationship("User")
    template = relationship("CampaignTemplate")
    recipients = relationship("CampaignRecipient", back_populates="campaign", cascade="all, delete-orphan")


class CampaignTemplate(BaseModel, SoftDeleteMixin):
    """Template for campaigns."""

    __tablename__ = "campaign_templates"

    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    campaign_type = Column(SQLEnum(CampaignType), nullable=False, index=True)
    subject = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    variables = Column(JSON, nullable=True)  # Available template variables
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    organization = relationship("Organization")
    created_by = relationship("User")


class CampaignRecipient(BaseModel):
    """Campaign recipient tracking."""

    __tablename__ = "campaign_recipients"

    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)

    # Contact Info (denormalized for tracking even if lead is deleted)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    # Status
    status = Column(String(50), nullable=False, default="pending", index=True)  # pending, sent, delivered, bounced, failed
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=True)
    clicked_at = Column(DateTime(timezone=True), nullable=True)
    bounced_at = Column(DateTime(timezone=True), nullable=True)
    unsubscribed_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)

    # Tracking
    open_count = Column(Integer, default=0, nullable=False)
    click_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)

    # Relationships
    campaign = relationship("Campaign", back_populates="recipients")
    lead = relationship("Lead")
