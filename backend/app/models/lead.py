"""Lead, contact, and CRM models."""
from sqlalchemy import (
    Column, Integer, String, Text, Numeric, Boolean, ForeignKey,
    DateTime, JSON, Enum as SQLEnum, Index
)
from sqlalchemy.orm import relationship
import enum
from backend.app.core.database import Base
from .base import TimestampMixin, SoftDeleteMixin


class LeadStatus(str, enum.Enum):
    """Lead status enumeration."""
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    NURTURING = "nurturing"
    CONVERTED = "converted"
    LOST = "lost"


class Lead(Base, TimestampMixin, SoftDeleteMixin):
    """Lead model for potential customers."""
    __tablename__ = 'leads'

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    assigned_user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    lead_source_id = Column(Integer, ForeignKey('lead_sources.id', ondelete='SET NULL'), nullable=True)

    # Lead details
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    company = Column(String(255), nullable=True)
    title = Column(String(100), nullable=True)

    # Status and scoring
    status = Column(SQLEnum(LeadStatus), default=LeadStatus.NEW, nullable=False, index=True)
    score = Column(Integer, default=0, nullable=False, index=True)  # 0-100
    temperature = Column(String(20), default='cold', nullable=False)  # cold, warm, hot

    # Interest and intent
    interested_in = Column(JSON, default=list)  # Property types or specific properties
    budget_min = Column(Numeric(12, 2), nullable=True)
    budget_max = Column(Numeric(12, 2), nullable=True)
    preferred_locations = Column(JSON, default=list)

    # Tracking
    first_contact_date = Column(DateTime(timezone=True), nullable=True)
    last_contact_date = Column(DateTime(timezone=True), nullable=True, index=True)
    next_follow_up_date = Column(DateTime(timezone=True), nullable=True, index=True)

    # Metadata
    notes = Column(Text, nullable=True)
    tags = Column(JSON, default=list)
    custom_fields = Column(JSON, default=dict)

    # Relationships
    assigned_user = relationship('User', back_populates='leads', foreign_keys=[assigned_user_id])
    source = relationship('LeadSource', back_populates='leads')
    contacts = relationship('Contact', back_populates='lead', cascade='all, delete-orphan')
    activities = relationship('LeadActivity', back_populates='lead', cascade='all, delete-orphan', order_by='LeadActivity.activity_date.desc()')
    scores = relationship('LeadScore', back_populates='lead', cascade='all, delete-orphan', order_by='LeadScore.scored_at.desc()')
    notes_records = relationship('LeadNote', back_populates='lead', cascade='all, delete-orphan', order_by='LeadNote.created_at.desc()')
    campaign_targets = relationship('CampaignTarget', back_populates='lead')


class LeadSource(Base, TimestampMixin):
    """Lead acquisition source/channel."""
    __tablename__ = 'lead_sources'

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)

    name = Column(String(100), nullable=False)
    source_type = Column(String(50), nullable=False)  # web, referral, event, purchase, etc.
    description = Column(String(500), nullable=True)

    # Tracking
    is_active = Column(Boolean, default=True, nullable=False)
    cost_per_lead = Column(Numeric(10, 2), nullable=True)

    # Metadata
    metadata = Column(JSON, default=dict)

    # Relationships
    leads = relationship('Lead', back_populates='source')


class LeadScore(Base, TimestampMixin):
    """Lead scoring history."""
    __tablename__ = 'lead_scores'

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey('leads.id', ondelete='CASCADE'), nullable=False)

    score = Column(Integer, nullable=False)
    scored_at = Column(DateTime(timezone=True), nullable=False, index=True)
    model_version = Column(String(50), nullable=True)

    # Scoring factors
    factors = Column(JSON, default=dict)  # Breakdown of score components
    confidence = Column(Numeric(3, 2), nullable=True)  # 0.0 to 1.0

    # Relationships
    lead = relationship('Lead', back_populates='scores')


class Contact(Base, TimestampMixin, SoftDeleteMixin):
    """Contact information for leads."""
    __tablename__ = 'contacts'

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey('leads.id', ondelete='CASCADE'), nullable=False)

    contact_type = Column(String(20), nullable=False)  # email, phone, address
    value = Column(String(255), nullable=False, index=True)
    label = Column(String(50), nullable=True)  # work, home, mobile, etc.

    is_primary = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)

    # DNC and opt-out tracking
    is_unsubscribed = Column(Boolean, default=False, nullable=False, index=True)
    unsubscribed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    lead = relationship('Lead', back_populates='contacts')


class LeadActivity(Base, TimestampMixin):
    """Lead activity and interaction log."""
    __tablename__ = 'lead_activities'

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey('leads.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    activity_type = Column(String(50), nullable=False, index=True)  # call, email, meeting, note, etc.
    activity_date = Column(DateTime(timezone=True), nullable=False, index=True)

    # Activity details
    subject = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    outcome = Column(String(100), nullable=True)  # successful, no-answer, callback-requested, etc.

    # Duration for calls/meetings
    duration_minutes = Column(Integer, nullable=True)

    # Metadata
    metadata = Column(JSON, default=dict)

    # Relationships
    lead = relationship('Lead', back_populates='activities')


class LeadNote(Base, TimestampMixin, SoftDeleteMixin):
    """Manual notes on leads."""
    __tablename__ = 'lead_notes'

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey('leads.id', ondelete='CASCADE'), nullable=False)
    created_by_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    content = Column(Text, nullable=False)
    is_pinned = Column(Boolean, default=False, nullable=False)

    # Relationships
    lead = relationship('Lead', back_populates='notes_records')
