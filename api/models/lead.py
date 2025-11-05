"""Lead and CRM models."""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime, Numeric, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from .base import BaseModel, SoftDeleteMixin
import enum


class LeadStatus(str, enum.Enum):
    """Lead status enum."""
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    NEGOTIATING = "negotiating"
    CONVERTED = "converted"
    LOST = "lost"
    ARCHIVED = "archived"


class LeadSource(str, enum.Enum):
    """Lead source enum."""
    WEBSITE = "website"
    REFERRAL = "referral"
    SOCIAL_MEDIA = "social_media"
    COLD_CALL = "cold_call"
    EMAIL_CAMPAIGN = "email_campaign"
    SMS_CAMPAIGN = "sms_campaign"
    EVENT = "event"
    PARTNER = "partner"
    OTHER = "other"


class LeadType(str, enum.Enum):
    """Lead type enum."""
    BUYER = "buyer"
    SELLER = "seller"
    INVESTOR = "investor"
    LANDLORD = "landlord"
    TENANT = "tenant"


class Lead(BaseModel, SoftDeleteMixin):
    """Lead model."""

    __tablename__ = "leads"

    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_to_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Contact Info
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    company = Column(String(255), nullable=True)

    # Lead Details
    lead_type = Column(SQLEnum(LeadType), nullable=False, index=True)
    status = Column(SQLEnum(LeadStatus), nullable=False, default=LeadStatus.NEW, index=True)
    source = Column(SQLEnum(LeadSource), nullable=False, index=True)
    score = Column(Integer, nullable=True)  # Lead scoring 0-100

    # Qualification
    budget_min = Column(Numeric(12, 2), nullable=True)
    budget_max = Column(Numeric(12, 2), nullable=True)
    timeline = Column(String(100), nullable=True)  # immediate, 1-3 months, 3-6 months, etc.
    preferred_locations = Column(JSON, nullable=True)
    requirements = Column(Text, nullable=True)

    # Communication preferences
    preferred_contact_method = Column(String(50), nullable=True)  # email, phone, sms
    contact_time_preference = Column(String(100), nullable=True)
    do_not_contact = Column(Boolean, default=False, nullable=False)

    # Tracking
    last_contacted_at = Column(DateTime(timezone=True), nullable=True)
    next_follow_up_at = Column(DateTime(timezone=True), nullable=True)
    converted_at = Column(DateTime(timezone=True), nullable=True)

    # Custom fields
    custom_fields = Column(JSON, nullable=True, default=dict)
    tags = Column(JSON, nullable=True, default=list)

    # Relationships
    organization = relationship("Organization", back_populates="leads")
    property = relationship("Property", back_populates="leads")
    assigned_to = relationship("User", back_populates="assigned_leads", foreign_keys=[assigned_to_id])
    created_by = relationship("User", back_populates="created_leads", foreign_keys=[created_by_id])
    activities = relationship("LeadActivity", back_populates="lead", cascade="all, delete-orphan")
    notes = relationship("LeadNote", back_populates="lead", cascade="all, delete-orphan")
    documents = relationship("LeadDocument", back_populates="lead", cascade="all, delete-orphan")


class LeadActivity(BaseModel):
    """Lead activity log."""

    __tablename__ = "lead_activities"

    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    activity_type = Column(String(100), nullable=False, index=True)  # call, email, meeting, sms, note, etc.
    subject = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    metadata = Column(JSON, nullable=True)

    # Relationships
    lead = relationship("Lead", back_populates="activities")
    user = relationship("User")


class LeadNote(BaseModel, SoftDeleteMixin):
    """Notes on leads."""

    __tablename__ = "lead_notes"

    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    content = Column(Text, nullable=False)
    is_pinned = Column(Boolean, default=False, nullable=False)

    # Relationships
    lead = relationship("Lead", back_populates="notes")
    created_by = relationship("User")


class LeadDocument(BaseModel, SoftDeleteMixin):
    """Documents attached to leads."""

    __tablename__ = "lead_documents"

    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    uploaded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    filename = Column(String(500), nullable=False)
    file_url = Column(String(1000), nullable=False)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)

    # Relationships
    lead = relationship("Lead", back_populates="documents")
    uploaded_by = relationship("User")
