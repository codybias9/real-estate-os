"""Lead and CRM models."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Numeric, Enum as SQLEnum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum
from ..database import Base


class LeadSource(str, Enum):
    """Lead source enum."""
    WEBSITE = "website"
    REFERRAL = "referral"
    SOCIAL_MEDIA = "social_media"
    EMAIL = "email"
    PHONE = "phone"
    WALK_IN = "walk_in"
    EVENT = "event"
    ADVERTISEMENT = "advertisement"
    OTHER = "other"


class LeadStatus(str, Enum):
    """Lead status enum."""
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    UNQUALIFIED = "unqualified"
    NURTURING = "nurturing"
    CONVERTED = "converted"
    LOST = "lost"


class Lead(Base):
    """Lead model."""

    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    # Contact Info
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(20), nullable=True, index=True)
    company = Column(String(200), nullable=True)

    # Lead Details
    source = Column(SQLEnum(LeadSource), nullable=False, index=True)
    status = Column(SQLEnum(LeadStatus), default=LeadStatus.NEW, nullable=False, index=True)
    score = Column(Integer, default=0, nullable=False)  # Lead scoring 0-100
    budget = Column(Numeric(12, 2), nullable=True)
    timeline = Column(String(100), nullable=True)  # e.g., '0-3 months', '3-6 months'
    notes = Column(Text, nullable=True)
    metadata = Column(Text, nullable=True)  # JSON object

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_contacted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="leads")
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_leads")
    assignee = relationship("User", foreign_keys=[assigned_to], back_populates="assigned_leads")
    activities = relationship("LeadActivity", back_populates="lead", cascade="all, delete-orphan")
    lead_notes = relationship("LeadNote", back_populates="lead", cascade="all, delete-orphan")
    documents = relationship("LeadDocument", back_populates="lead", cascade="all, delete-orphan")
    deals = relationship("Deal", back_populates="lead")


class LeadActivity(Base):
    """Lead activity model for tracking interactions."""

    __tablename__ = "lead_activities"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    activity_type = Column(String(50), nullable=False, index=True)  # call, email, meeting, sms, note
    subject = Column(String(200), nullable=True)
    description = Column(Text, nullable=False)
    outcome = Column(String(100), nullable=True)  # success, failed, no_answer, scheduled
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    metadata = Column(Text, nullable=True)  # JSON object
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    lead = relationship("Lead", back_populates="activities")


class LeadNote(Base):
    """Lead note model for collaboration."""

    __tablename__ = "lead_notes"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    is_pinned = Column(Boolean, default=False, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    lead = relationship("Lead", back_populates="lead_notes")


class LeadDocument(Base):
    """Lead document model for attachments."""

    __tablename__ = "lead_documents"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_type = Column(String(100), nullable=True)
    file_size = Column(Integer, nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    lead = relationship("Lead", back_populates="documents")
