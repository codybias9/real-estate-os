"""
SQLAlchemy ORM Models for Real Estate CRM Platform
All 35 models organized by domain
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Float,
    Numeric, JSON, ForeignKey, UniqueConstraint, Index, Enum as SQLEnum,
    TIMESTAMP, func, BigInteger
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import JSONB, UUID
import enum
import uuid


Base = declarative_base()


# ============================================================================
# MIXINS AND BASE CLASSES
# ============================================================================

class TimestampMixin:
    """Adds created_at and updated_at timestamps to models"""
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SoftDeleteMixin:
    """Adds soft delete capability via deleted_at timestamp"""
    deleted_at = Column(DateTime(timezone=True), nullable=True)


# ============================================================================
# ENUMS
# ============================================================================

class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class PropertyStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SOLD = "sold"
    PENDING = "pending"
    ARCHIVED = "archived"


class LeadStatus(str, enum.Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    NURTURING = "nurturing"
    CONVERTED = "converted"
    LOST = "lost"
    ARCHIVED = "archived"


class CampaignStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DealStatus(str, enum.Enum):
    PROSPECT = "prospect"
    NEGOTIATION = "negotiation"
    CONTRACT = "contract"
    DUE_DILIGENCE = "due_diligence"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class OutreachStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    REPLIED = "replied"
    BOUNCED = "bounced"
    FAILED = "failed"


class TransactionType(str, enum.Enum):
    PURCHASE = "purchase"
    SALE = "sale"
    REFINANCE = "refinance"
    LEASE = "lease"


# ============================================================================
# USER/AUTH MODELS (5 models)
# ============================================================================

class Organization(Base, TimestampMixin, SoftDeleteMixin):
    """Multi-tenant organization/company"""
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    domain = Column(String(255), nullable=True)
    settings = Column(JSONB, default={}, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    users = relationship("User", back_populates="organization")
    teams = relationship("Team", back_populates="organization")
    properties = relationship("Property", back_populates="organization")
    leads = relationship("Lead", back_populates="organization")
    campaigns = relationship("Campaign", back_populates="organization")

    __table_args__ = (
        Index('ix_organizations_slug', 'slug'),
    )


class User(Base, TimestampMixin, SoftDeleteMixin):
    """User account with authentication"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # Authentication fields
    status = Column(SQLEnum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    phone_verified = Column(Boolean, default=False, nullable=False)

    # Security fields
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    password_changed_at = Column(DateTime(timezone=True), nullable=True)

    # Additional data
    meta = Column(JSONB, default={}, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="users")
    teams = relationship("Team", secondary="user_teams", back_populates="members")
    roles = relationship("Role", secondary="user_roles", back_populates="users")

    __table_args__ = (
        Index('ix_users_email', 'email'),
        Index('ix_users_organization_id', 'organization_id'),
    )


class Team(Base, TimestampMixin, SoftDeleteMixin):
    """Team within an organization"""
    __tablename__ = "teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    settings = Column(JSONB, default={}, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="teams")
    members = relationship("User", secondary="user_teams", back_populates="teams")


class Role(Base, TimestampMixin):
    """Role for RBAC (Role-Based Access Control)"""
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, default=False, nullable=False)  # System roles can't be deleted

    # Relationships
    users = relationship("User", secondary="user_roles", back_populates="roles")
    permissions = relationship("Permission", secondary="role_permissions", back_populates="roles")


class Permission(Base, TimestampMixin):
    """Permission for fine-grained access control"""
    __tablename__ = "permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    resource = Column(String(100), nullable=False)  # e.g., "property", "lead", "campaign"
    action = Column(String(50), nullable=False)  # e.g., "read", "write", "delete"
    description = Column(Text, nullable=True)

    # Relationships
    roles = relationship("Role", secondary="role_permissions", back_populates="permissions")

    __table_args__ = (
        UniqueConstraint('resource', 'action', name='uq_permission_resource_action'),
        Index('ix_permissions_resource_action', 'resource', 'action'),
    )


# Association Tables for Many-to-Many relationships
class UserTeam(Base):
    __tablename__ = "user_teams"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), primary_key=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())


class UserRole(Base):
    __tablename__ = "user_roles"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())


class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True)
    permission_id = Column(UUID(as_uuid=True), ForeignKey("permissions.id"), primary_key=True)


# ============================================================================
# PROPERTY MODELS (8 models)
# ============================================================================

class Property(Base, TimestampMixin, SoftDeleteMixin):
    """Core property/real estate asset"""
    __tablename__ = "properties"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)

    # Address fields
    address_line1 = Column(String(255), nullable=False)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=False)
    state = Column(String(2), nullable=False)
    zip_code = Column(String(10), nullable=False)
    county = Column(String(100), nullable=True)
    country = Column(String(2), default="US", nullable=False)

    # Property details
    apn = Column(String(50), nullable=True, index=True)  # Assessor Parcel Number
    property_type = Column(String(50), nullable=True)  # SFR, Multi-family, Commercial, etc.
    bedrooms = Column(Integer, nullable=True)
    bathrooms = Column(Float, nullable=True)
    square_feet = Column(Integer, nullable=True)
    lot_size = Column(Integer, nullable=True)
    year_built = Column(Integer, nullable=True)

    # Financial data
    purchase_price = Column(Numeric(12, 2), nullable=True)
    current_value = Column(Numeric(12, 2), nullable=True)
    estimated_rent = Column(Numeric(10, 2), nullable=True)

    # Status and metadata
    status = Column(SQLEnum(PropertyStatus), default=PropertyStatus.ACTIVE, nullable=False)
    source = Column(String(100), nullable=True)  # Source of property data
    source_id = Column(String(255), nullable=True)  # External ID from source

    # Geolocation
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Additional data
    meta = Column(JSONB, default={}, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="properties")
    images = relationship("PropertyImage", back_populates="property", cascade="all, delete-orphan")
    documents = relationship("PropertyDocument", back_populates="property", cascade="all, delete-orphan")
    valuations = relationship("PropertyValuation", back_populates="property", cascade="all, delete-orphan")
    metrics = relationship("PropertyMetrics", back_populates="property", cascade="all, delete-orphan")
    history = relationship("PropertyHistory", back_populates="property", cascade="all, delete-orphan")
    listings = relationship("Listing", back_populates="property", cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="property")

    __table_args__ = (
        Index('ix_properties_organization_id', 'organization_id'),
        Index('ix_properties_apn', 'apn'),
        Index('ix_properties_location', 'city', 'state', 'zip_code'),
        Index('ix_properties_status', 'status'),
    )


class PropertyImage(Base, TimestampMixin):
    """Images associated with a property"""
    __tablename__ = "property_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False)
    url = Column(String(1000), nullable=False)
    thumbnail_url = Column(String(1000), nullable=True)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)

    # Relationships
    property = relationship("Property", back_populates="images")

    __table_args__ = (
        Index('ix_property_images_property_id', 'property_id'),
    )


class PropertyDocument(Base, TimestampMixin):
    """Documents associated with a property (deeds, inspection reports, etc.)"""
    __tablename__ = "property_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False)
    document_type = Column(String(50), nullable=False)  # deed, inspection, appraisal, etc.
    title = Column(String(255), nullable=False)
    file_url = Column(String(1000), nullable=False)
    file_size = Column(BigInteger, nullable=True)
    mime_type = Column(String(100), nullable=True)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    meta = Column(JSONB, default={}, nullable=False)

    # Relationships
    property = relationship("Property", back_populates="documents")

    __table_args__ = (
        Index('ix_property_documents_property_id', 'property_id'),
        Index('ix_property_documents_type', 'document_type'),
    )


class PropertyValuation(Base, TimestampMixin):
    """Property valuation history (AVM, appraisals, CMAs)"""
    __tablename__ = "property_valuations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False)
    valuation_date = Column(DateTime(timezone=True), nullable=False)
    valuation_type = Column(String(50), nullable=False)  # AVM, appraisal, CMA, tax_assessment
    value = Column(Numeric(12, 2), nullable=False)
    confidence_score = Column(Float, nullable=True)
    source = Column(String(100), nullable=True)
    meta = Column(JSONB, default={}, nullable=False)

    # Relationships
    property = relationship("Property", back_populates="valuations")

    __table_args__ = (
        Index('ix_property_valuations_property_id', 'property_id'),
        Index('ix_property_valuations_date', 'valuation_date'),
    )


class PropertyMetrics(Base, TimestampMixin):
    """Property performance metrics and analytics"""
    __tablename__ = "property_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False)
    metric_date = Column(DateTime(timezone=True), nullable=False)

    # Investment metrics
    cap_rate = Column(Float, nullable=True)
    cash_on_cash_return = Column(Float, nullable=True)
    gross_yield = Column(Float, nullable=True)
    occupancy_rate = Column(Float, nullable=True)

    # Market metrics
    days_on_market = Column(Integer, nullable=True)
    price_per_sqft = Column(Numeric(10, 2), nullable=True)
    comparable_sales_avg = Column(Numeric(12, 2), nullable=True)

    # Additional metrics
    meta = Column(JSONB, default={}, nullable=False)

    # Relationships
    property = relationship("Property", back_populates="metrics")

    __table_args__ = (
        Index('ix_property_metrics_property_id', 'property_id'),
        Index('ix_property_metrics_date', 'metric_date'),
    )


class PropertyHistory(Base, TimestampMixin):
    """Property transaction and ownership history"""
    __tablename__ = "property_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False)
    event_date = Column(DateTime(timezone=True), nullable=False)
    event_type = Column(String(50), nullable=False)  # sale, listing, price_change, etc.

    # Event details
    price = Column(Numeric(12, 2), nullable=True)
    description = Column(Text, nullable=True)
    source = Column(String(100), nullable=True)
    meta = Column(JSONB, default={}, nullable=False)

    # Relationships
    property = relationship("Property", back_populates="history")

    __table_args__ = (
        Index('ix_property_history_property_id', 'property_id'),
        Index('ix_property_history_date', 'event_date'),
    )


class Listing(Base, TimestampMixin, SoftDeleteMixin):
    """Active property listings (MLS, off-market, etc.)"""
    __tablename__ = "listings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False)

    # Listing details
    listing_type = Column(String(50), nullable=False)  # for_sale, for_rent, auction
    list_price = Column(Numeric(12, 2), nullable=False)
    list_date = Column(DateTime(timezone=True), nullable=False)
    expiration_date = Column(DateTime(timezone=True), nullable=True)

    # Listing source
    source = Column(String(100), nullable=True)  # MLS, FSBO, auction, etc.
    source_id = Column(String(255), nullable=True)
    mls_number = Column(String(50), nullable=True, index=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    status = Column(String(50), nullable=True)

    # Additional data
    description = Column(Text, nullable=True)
    meta = Column(JSONB, default={}, nullable=False)

    # Relationships
    property = relationship("Property", back_populates="listings")
    snapshots = relationship("ListingSnapshot", back_populates="listing", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_listings_property_id', 'property_id'),
        Index('ix_listings_mls_number', 'mls_number'),
        Index('ix_listings_active', 'is_active'),
    )


class ListingSnapshot(Base, TimestampMixin):
    """Point-in-time snapshot of listing data for tracking changes"""
    __tablename__ = "listing_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("listings.id"), nullable=False)
    snapshot_date = Column(DateTime(timezone=True), nullable=False)

    # Snapshot data (JSON blob of listing state at this time)
    data = Column(JSONB, nullable=False)

    # Relationships
    listing = relationship("Listing", back_populates="snapshots")

    __table_args__ = (
        Index('ix_listing_snapshots_listing_id', 'listing_id'),
        Index('ix_listing_snapshots_date', 'snapshot_date'),
    )


# ============================================================================
# LEAD/CRM MODELS (6 models)
# ============================================================================

class Lead(Base, TimestampMixin, SoftDeleteMixin):
    """Lead/prospect in the CRM"""
    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=True)
    lead_source_id = Column(UUID(as_uuid=True), ForeignKey("lead_sources.id"), nullable=True)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Lead information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True, index=True)
    company = Column(String(255), nullable=True)

    # Lead details
    status = Column(SQLEnum(LeadStatus), default=LeadStatus.NEW, nullable=False)
    score = Column(Float, nullable=True)
    tags = Column(JSONB, default=[], nullable=False)

    # Tracking
    last_contact_date = Column(DateTime(timezone=True), nullable=True)
    next_follow_up_date = Column(DateTime(timezone=True), nullable=True)

    # Additional data
    meta = Column(JSONB, default={}, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="leads")
    property = relationship("Property", back_populates="leads")
    source = relationship("LeadSource", back_populates="leads")
    activities = relationship("LeadActivity", back_populates="lead", cascade="all, delete-orphan")
    notes = relationship("LeadNote", back_populates="lead", cascade="all, delete-orphan")
    scores = relationship("LeadScore", back_populates="lead", cascade="all, delete-orphan")
    contacts = relationship("Contact", back_populates="lead")

    __table_args__ = (
        Index('ix_leads_organization_id', 'organization_id'),
        Index('ix_leads_status', 'status'),
        Index('ix_leads_assigned_to', 'assigned_to'),
        Index('ix_leads_email', 'email'),
    )


class LeadSource(Base, TimestampMixin):
    """Source of leads (website, referral, cold outreach, etc.)"""
    __tablename__ = "lead_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True, index=True)
    source_type = Column(String(50), nullable=False)  # web, referral, cold_call, direct_mail, etc.
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    meta = Column(JSONB, default={}, nullable=False)

    # Relationships
    leads = relationship("Lead", back_populates="source")


class LeadScore(Base, TimestampMixin):
    """Lead scoring history"""
    __tablename__ = "lead_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False)
    score = Column(Float, nullable=False)
    score_date = Column(DateTime(timezone=True), nullable=False)
    scoring_model = Column(String(100), nullable=True)
    factors = Column(JSONB, default={}, nullable=False)  # What contributed to the score

    # Relationships
    lead = relationship("Lead", back_populates="scores")

    __table_args__ = (
        Index('ix_lead_scores_lead_id', 'lead_id'),
        Index('ix_lead_scores_date', 'score_date'),
    )


class Contact(Base, TimestampMixin, SoftDeleteMixin):
    """Contact record (can be associated with lead or standalone)"""
    __tablename__ = "contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)

    # Contact details
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True, index=True)
    company = Column(String(255), nullable=True)
    title = Column(String(100), nullable=True)

    # Address
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(2), nullable=True)
    zip_code = Column(String(10), nullable=True)

    # Additional data
    meta = Column(JSONB, default={}, nullable=False)

    # Relationships
    lead = relationship("Lead", back_populates="contacts")

    __table_args__ = (
        Index('ix_contacts_email', 'email'),
        Index('ix_contacts_phone', 'phone'),
    )


class LeadActivity(Base, TimestampMixin):
    """Activity log for leads (calls, emails, meetings, etc.)"""
    __tablename__ = "lead_activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Activity details
    activity_type = Column(String(50), nullable=False)  # call, email, meeting, note, task
    subject = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    activity_date = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, nullable=True)

    # Additional data
    meta = Column(JSONB, default={}, nullable=False)

    # Relationships
    lead = relationship("Lead", back_populates="activities")

    __table_args__ = (
        Index('ix_lead_activities_lead_id', 'lead_id'),
        Index('ix_lead_activities_date', 'activity_date'),
        Index('ix_lead_activities_type', 'activity_type'),
    )


class LeadNote(Base, TimestampMixin):
    """Notes associated with leads"""
    __tablename__ = "lead_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Note content
    content = Column(Text, nullable=False)
    is_pinned = Column(Boolean, default=False, nullable=False)

    # Relationships
    lead = relationship("Lead", back_populates="notes")

    __table_args__ = (
        Index('ix_lead_notes_lead_id', 'lead_id'),
    )


# ============================================================================
# CAMPAIGN MODELS (7 models)
# ============================================================================

class Campaign(Base, TimestampMixin, SoftDeleteMixin):
    """Marketing/outreach campaign"""
    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Campaign details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    campaign_type = Column(String(50), nullable=False)  # email, sms, direct_mail, multi_channel
    status = Column(SQLEnum(CampaignStatus), default=CampaignStatus.DRAFT, nullable=False)

    # Schedule
    scheduled_start = Column(DateTime(timezone=True), nullable=True)
    scheduled_end = Column(DateTime(timezone=True), nullable=True)
    actual_start = Column(DateTime(timezone=True), nullable=True)
    actual_end = Column(DateTime(timezone=True), nullable=True)

    # Tracking
    target_count = Column(Integer, default=0, nullable=False)
    sent_count = Column(Integer, default=0, nullable=False)
    delivered_count = Column(Integer, default=0, nullable=False)
    opened_count = Column(Integer, default=0, nullable=False)
    clicked_count = Column(Integer, default=0, nullable=False)
    replied_count = Column(Integer, default=0, nullable=False)

    # Settings
    settings = Column(JSONB, default={}, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="campaigns")
    targets = relationship("CampaignTarget", back_populates="campaign", cascade="all, delete-orphan")
    outreach_attempts = relationship("OutreachAttempt", back_populates="campaign", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_campaigns_organization_id', 'organization_id'),
        Index('ix_campaigns_status', 'status'),
    )


class CampaignTarget(Base, TimestampMixin):
    """Target (lead/contact) for a campaign"""
    __tablename__ = "campaign_targets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=True)

    # Target details
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)

    # Tracking
    is_sent = Column(Boolean, default=False, nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)

    # Personalization data
    personalization_data = Column(JSONB, default={}, nullable=False)

    # Relationships
    campaign = relationship("Campaign", back_populates="targets")

    __table_args__ = (
        Index('ix_campaign_targets_campaign_id', 'campaign_id'),
        Index('ix_campaign_targets_lead_id', 'lead_id'),
    )


class EmailTemplate(Base, TimestampMixin, SoftDeleteMixin):
    """Email template for campaigns"""
    __tablename__ = "email_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    html_body = Column(Text, nullable=True)
    text_body = Column(Text, nullable=True)

    # Template metadata
    is_active = Column(Boolean, default=True, nullable=False)
    category = Column(String(100), nullable=True)
    variables = Column(JSONB, default=[], nullable=False)  # List of template variables

    __table_args__ = (
        Index('ix_email_templates_name', 'name'),
        Index('ix_email_templates_category', 'category'),
    )


class SMSTemplate(Base, TimestampMixin, SoftDeleteMixin):
    """SMS template for campaigns"""
    __tablename__ = "sms_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)

    # Template metadata
    is_active = Column(Boolean, default=True, nullable=False)
    category = Column(String(100), nullable=True)
    variables = Column(JSONB, default=[], nullable=False)

    __table_args__ = (
        Index('ix_sms_templates_name', 'name'),
        Index('ix_sms_templates_category', 'category'),
    )


class OutreachAttempt(Base, TimestampMixin):
    """Individual outreach attempt (email, SMS, call, etc.)"""
    __tablename__ = "outreach_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=True)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)

    # Outreach details
    outreach_type = Column(String(50), nullable=False)  # email, sms, call, direct_mail
    status = Column(SQLEnum(OutreachStatus), default=OutreachStatus.PENDING, nullable=False)

    # Contact details
    recipient_email = Column(String(255), nullable=True)
    recipient_phone = Column(String(50), nullable=True)

    # Content
    subject = Column(String(500), nullable=True)
    body = Column(Text, nullable=True)

    # Tracking
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=True)
    clicked_at = Column(DateTime(timezone=True), nullable=True)
    replied_at = Column(DateTime(timezone=True), nullable=True)

    # Provider data
    provider = Column(String(100), nullable=True)
    provider_message_id = Column(String(255), nullable=True, index=True)

    # Additional data
    meta = Column(JSONB, default={}, nullable=False)

    # Relationships
    campaign = relationship("Campaign", back_populates="outreach_attempts")
    deliverability_events = relationship("DeliverabilityEvent", back_populates="outreach_attempt", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_outreach_attempts_campaign_id', 'campaign_id'),
        Index('ix_outreach_attempts_lead_id', 'lead_id'),
        Index('ix_outreach_attempts_status', 'status'),
        Index('ix_outreach_attempts_provider_message_id', 'provider_message_id'),
    )


class DeliverabilityEvent(Base, TimestampMixin):
    """Tracking deliverability events (opens, clicks, bounces, etc.)"""
    __tablename__ = "deliverability_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    outreach_attempt_id = Column(UUID(as_uuid=True), ForeignKey("outreach_attempts.id"), nullable=False)

    # Event details
    event_type = Column(String(50), nullable=False)  # sent, delivered, opened, clicked, bounced, complained
    event_date = Column(DateTime(timezone=True), nullable=False)

    # Event metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    link_clicked = Column(String(1000), nullable=True)
    meta = Column(JSONB, default={}, nullable=False)

    # Relationships
    outreach_attempt = relationship("OutreachAttempt", back_populates="deliverability_events")

    __table_args__ = (
        Index('ix_deliverability_events_outreach_attempt_id', 'outreach_attempt_id'),
        Index('ix_deliverability_events_type', 'event_type'),
        Index('ix_deliverability_events_date', 'event_date'),
    )


class UnsubscribeList(Base, TimestampMixin):
    """List of unsubscribed contacts"""
    __tablename__ = "unsubscribe_list"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True, index=True)
    unsubscribed_at = Column(DateTime(timezone=True), nullable=False)
    reason = Column(String(255), nullable=True)
    source = Column(String(100), nullable=True)  # manual, auto, complaint

    __table_args__ = (
        Index('ix_unsubscribe_list_email', 'email'),
        Index('ix_unsubscribe_list_phone', 'phone'),
    )


# ============================================================================
# DEAL/PORTFOLIO MODELS (6 models)
# ============================================================================

class Deal(Base, TimestampMixin, SoftDeleteMixin):
    """Real estate deal/opportunity"""
    __tablename__ = "deals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Deal details
    deal_name = Column(String(255), nullable=False)
    status = Column(SQLEnum(DealStatus), default=DealStatus.PROSPECT, nullable=False)

    # Financial details
    offer_price = Column(Numeric(12, 2), nullable=True)
    purchase_price = Column(Numeric(12, 2), nullable=True)
    estimated_repair_cost = Column(Numeric(12, 2), nullable=True)
    estimated_arv = Column(Numeric(12, 2), nullable=True)  # After Repair Value

    # Important dates
    contract_date = Column(DateTime(timezone=True), nullable=True)
    inspection_date = Column(DateTime(timezone=True), nullable=True)
    closing_date = Column(DateTime(timezone=True), nullable=True)
    actual_closing_date = Column(DateTime(timezone=True), nullable=True)

    # Additional data
    meta = Column(JSONB, default={}, nullable=False)

    # Relationships
    stages = relationship("DealStage", back_populates="deal", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="deal", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_deals_property_id', 'property_id'),
        Index('ix_deals_status', 'status'),
        Index('ix_deals_assigned_to', 'assigned_to'),
    )


class DealStage(Base, TimestampMixin):
    """Deal stage history for tracking pipeline movement"""
    __tablename__ = "deal_stages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deal_id = Column(UUID(as_uuid=True), ForeignKey("deals.id"), nullable=False)
    stage = Column(SQLEnum(DealStatus), nullable=False)
    entered_at = Column(DateTime(timezone=True), nullable=False)
    exited_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    deal = relationship("Deal", back_populates="stages")

    __table_args__ = (
        Index('ix_deal_stages_deal_id', 'deal_id'),
        Index('ix_deal_stages_stage', 'stage'),
    )


class Transaction(Base, TimestampMixin):
    """Financial transactions related to deals/properties"""
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deal_id = Column(UUID(as_uuid=True), ForeignKey("deals.id"), nullable=True)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=True)
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=True)

    # Transaction details
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)
    transaction_date = Column(DateTime(timezone=True), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    description = Column(Text, nullable=True)

    # Payment details
    payment_method = Column(String(50), nullable=True)
    reference_number = Column(String(255), nullable=True)

    # Additional data
    meta = Column(JSONB, default={}, nullable=False)

    # Relationships
    deal = relationship("Deal", back_populates="transactions")

    __table_args__ = (
        Index('ix_transactions_deal_id', 'deal_id'),
        Index('ix_transactions_property_id', 'property_id'),
        Index('ix_transactions_date', 'transaction_date'),
        Index('ix_transactions_type', 'transaction_type'),
    )


class Portfolio(Base, TimestampMixin, SoftDeleteMixin):
    """Investment portfolio"""
    __tablename__ = "portfolios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Portfolio metrics
    total_value = Column(Numeric(15, 2), default=0, nullable=False)
    total_equity = Column(Numeric(15, 2), default=0, nullable=False)
    total_debt = Column(Numeric(15, 2), default=0, nullable=False)

    # Additional data
    meta = Column(JSONB, default={}, nullable=False)

    # Relationships
    holdings = relationship("PortfolioHolding", back_populates="portfolio", cascade="all, delete-orphan")
    reconciliations = relationship("Reconciliation", back_populates="portfolio", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_portfolios_owner_id', 'owner_id'),
    )


class PortfolioHolding(Base, TimestampMixin):
    """Individual property holding within a portfolio"""
    __tablename__ = "portfolio_holdings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False)

    # Acquisition details
    acquisition_date = Column(DateTime(timezone=True), nullable=False)
    acquisition_price = Column(Numeric(12, 2), nullable=False)

    # Current details
    current_value = Column(Numeric(12, 2), nullable=True)
    equity = Column(Numeric(12, 2), nullable=True)
    debt = Column(Numeric(12, 2), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    disposition_date = Column(DateTime(timezone=True), nullable=True)
    disposition_price = Column(Numeric(12, 2), nullable=True)

    # Additional data
    meta = Column(JSONB, default={}, nullable=False)

    # Relationships
    portfolio = relationship("Portfolio", back_populates="holdings")

    __table_args__ = (
        Index('ix_portfolio_holdings_portfolio_id', 'portfolio_id'),
        Index('ix_portfolio_holdings_property_id', 'property_id'),
        UniqueConstraint('portfolio_id', 'property_id', name='uq_portfolio_holding'),
    )


class Reconciliation(Base, TimestampMixin):
    """Portfolio reconciliation record"""
    __tablename__ = "reconciliations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id = Column(UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False)

    # Reconciliation details
    reconciliation_date = Column(DateTime(timezone=True), nullable=False)
    reconciliation_type = Column(String(50), nullable=False)  # manual, automated, scheduled

    # Snapshot data
    total_value = Column(Numeric(15, 2), nullable=False)
    total_equity = Column(Numeric(15, 2), nullable=False)
    total_debt = Column(Numeric(15, 2), nullable=False)
    holding_count = Column(Integer, nullable=False)

    # Differences
    value_change = Column(Numeric(15, 2), nullable=True)
    notes = Column(Text, nullable=True)

    # Status
    is_approved = Column(Boolean, default=False, nullable=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    # Additional data
    meta = Column(JSONB, default={}, nullable=False)

    # Relationships
    portfolio = relationship("Portfolio", back_populates="reconciliations")

    __table_args__ = (
        Index('ix_reconciliations_portfolio_id', 'portfolio_id'),
        Index('ix_reconciliations_date', 'reconciliation_date'),
    )


# ============================================================================
# SYSTEM MODELS (3 models)
# ============================================================================

class IdempotencyKey(Base, TimestampMixin):
    """Idempotency key for preventing duplicate operations"""
    __tablename__ = "idempotency_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(255), unique=True, nullable=False, index=True)
    request_path = Column(String(500), nullable=False)
    request_method = Column(String(10), nullable=False)
    request_body_hash = Column(String(64), nullable=True)

    # Response data
    response_status = Column(Integer, nullable=True)
    response_body = Column(JSONB, nullable=True)

    # Timing
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index('ix_idempotency_keys_key', 'key'),
        Index('ix_idempotency_keys_expires_at', 'expires_at'),
    )


class WebhookLog(Base, TimestampMixin):
    """Webhook delivery log"""
    __tablename__ = "webhook_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    webhook_url = Column(String(1000), nullable=False)
    event_type = Column(String(100), nullable=False)

    # Request data
    payload = Column(JSONB, nullable=False)
    headers = Column(JSONB, default={}, nullable=False)

    # Response data
    status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    response_time_ms = Column(Integer, nullable=True)

    # Retry tracking
    attempt_number = Column(Integer, default=1, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)

    # Status
    is_success = Column(Boolean, default=False, nullable=False)
    error_message = Column(Text, nullable=True)

    __table_args__ = (
        Index('ix_webhook_logs_event_type', 'event_type'),
        Index('ix_webhook_logs_created_at', 'created_at'),
        Index('ix_webhook_logs_next_retry_at', 'next_retry_at'),
    )


class AuditLog(Base, TimestampMixin):
    """Audit log for tracking all system changes"""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Event details
    event_type = Column(String(50), nullable=False)  # create, update, delete, login, etc.
    resource_type = Column(String(100), nullable=False)  # property, lead, campaign, etc.
    resource_id = Column(String(255), nullable=True)

    # Change details
    old_values = Column(JSONB, nullable=True)
    new_values = Column(JSONB, nullable=True)

    # Request metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    request_id = Column(String(255), nullable=True, index=True)

    # Additional data
    meta = Column(JSONB, default={}, nullable=False)

    __table_args__ = (
        Index('ix_audit_logs_user_id', 'user_id'),
        Index('ix_audit_logs_event_type', 'event_type'),
        Index('ix_audit_logs_resource_type', 'resource_type'),
        Index('ix_audit_logs_resource_id', 'resource_id'),
        Index('ix_audit_logs_created_at', 'created_at'),
        Index('ix_audit_logs_request_id', 'request_id'),
    )


# ============================================================================
# LEGACY/UTILITY MODELS
# ============================================================================

class Ping(Base):
    """Test/health check table"""
    __tablename__ = "ping"
    id = Column(Integer, primary_key=True)
    ts = Column(TIMESTAMP(timezone=True), server_default=func.now())
