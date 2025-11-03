"""
Comprehensive database models for Real Estate OS
Supports: Pipeline, Communication, Deals, Sharing, Compliance, Propensity, and more
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey,
    JSON, Enum as SQLEnum, Index, UniqueConstraint, CheckConstraint, TIMESTAMP, func
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import JSONB, UUID
import enum
import uuid

Base = declarative_base()

# ============================================================================
# ENUMS
# ============================================================================

class UserRole(str, enum.Enum):
    """User roles in the system"""
    ADMIN = "admin"
    MANAGER = "manager"
    AGENT = "agent"
    VIEWER = "viewer"

class PropertyStage(str, enum.Enum):
    """Pipeline stages for properties"""
    NEW = "new"
    OUTREACH = "outreach"
    QUALIFIED = "qualified"
    NEGOTIATION = "negotiation"
    UNDER_CONTRACT = "under_contract"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"
    ARCHIVED = "archived"

class CommunicationType(str, enum.Enum):
    """Types of communication"""
    EMAIL = "email"
    SMS = "sms"
    CALL = "call"
    POSTCARD = "postcard"
    NOTE = "note"

class CommunicationDirection(str, enum.Enum):
    """Direction of communication"""
    INBOUND = "inbound"
    OUTBOUND = "outbound"

class TaskStatus(str, enum.Enum):
    """Task statuses"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"

class TaskPriority(str, enum.Enum):
    """Task priorities"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class DealStatus(str, enum.Enum):
    """Deal statuses"""
    PROPOSED = "proposed"
    NEGOTIATING = "negotiating"
    ACCEPTED = "accepted"
    CLOSED = "closed"
    DEAD = "dead"

class ShareLinkStatus(str, enum.Enum):
    """Share link statuses"""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"

class ComplianceStatus(str, enum.Enum):
    """Compliance check statuses"""
    PASSED = "passed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"

class DataFlagStatus(str, enum.Enum):
    """Data flag statuses"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    WONT_FIX = "wont_fix"

class InvestorReadinessLevel(str, enum.Enum):
    """Investor readiness levels"""
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"

# ============================================================================
# CORE MODELS
# ============================================================================

class User(Base):
    """Users in the system"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.AGENT)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"))
    is_active = Column(Boolean, default=True)

    # Settings
    settings = Column(JSONB, default={})  # notification prefs, display options, etc.

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime)

    # Relationships
    team = relationship("Team", back_populates="members")
    assigned_properties = relationship("Property", back_populates="assigned_user", foreign_keys="Property.assigned_user_id")
    tasks = relationship("Task", back_populates="assigned_user", foreign_keys="Task.assigned_user_id")
    communications = relationship("Communication", back_populates="user", foreign_keys="Communication.user_id")

    __table_args__ = (
        Index('idx_user_email', 'email'),
        Index('idx_user_role', 'role'),
    )

class Team(Base):
    """Teams/Organizations"""
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    name = Column(String(255), nullable=False)

    # Billing & limits
    subscription_tier = Column(String(50), default="starter")
    monthly_budget_cap = Column(Float, default=500.0)  # for data costs

    # Settings
    settings = Column(JSONB, default={})

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    members = relationship("User", back_populates="team")
    properties = relationship("Property", back_populates="team")

# ============================================================================
# PROPERTY PIPELINE MODELS
# ============================================================================

class Property(Base):
    """Core property tracking with scoring and engagement"""
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    assigned_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Core property data
    address = Column(String(500), nullable=False)
    city = Column(String(255))
    state = Column(String(50))
    zip_code = Column(String(20))
    county = Column(String(255))
    apn = Column(String(100))  # Assessor Parcel Number

    # Location
    latitude = Column(Float)
    longitude = Column(Float)

    # Owner info
    owner_name = Column(String(500))
    owner_mailing_address = Column(Text)

    # Property characteristics
    beds = Column(Integer)
    baths = Column(Float)
    sqft = Column(Integer)
    lot_size = Column(Float)
    year_built = Column(Integer)
    property_type = Column(String(50))
    land_use = Column(String(100))

    # Valuation
    assessed_value = Column(Float)
    market_value_estimate = Column(Float)
    arv = Column(Float)  # After Repair Value
    repair_estimate = Column(Float)

    # Pipeline tracking
    current_stage = Column(SQLEnum(PropertyStage), nullable=False, default=PropertyStage.NEW, index=True)
    previous_stage = Column(SQLEnum(PropertyStage))
    stage_changed_at = Column(DateTime)

    # Engagement tracking
    last_contact_date = Column(DateTime, index=True)
    last_reply_date = Column(DateTime, index=True)
    touch_count = Column(Integer, default=0)
    email_opens = Column(Integer, default=0)
    email_clicks = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)

    # Scoring & signals
    bird_dog_score = Column(Float, index=True)  # 0.0 - 1.0
    score_reasons = Column(JSONB, default=[])  # List of score factors
    propensity_to_sell = Column(Float)  # 0.0 - 1.0
    propensity_signals = Column(JSONB, default=[])

    # Deal tracking
    expected_value = Column(Float)  # EV = expected fee/margin × probability
    probability_of_close = Column(Float)  # 0.0 - 1.0

    # Documents & artifacts
    memo_url = Column(String(500))
    memo_generated_at = Column(DateTime)
    packet_url = Column(String(500))

    # Data quality
    data_quality_score = Column(Float, default=1.0)
    provenance_summary = Column(JSONB, default={})  # {field: source}

    # Compliance & cadence
    is_on_dnc = Column(Boolean, default=False)
    has_opted_out = Column(Boolean, default=False)
    cadence_paused = Column(Boolean, default=False)
    cadence_pause_reason = Column(String(255))

    # Metadata
    tags = Column(JSONB, default=[])
    custom_fields = Column(JSONB, default={})

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    archived_at = Column(DateTime)

    # Relationships
    team = relationship("Team", back_populates="properties")
    assigned_user = relationship("User", back_populates="assigned_properties", foreign_keys=[assigned_user_id])
    communications = relationship("Communication", back_populates="property", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="property", cascade="all, delete-orphan")
    timeline_events = relationship("PropertyTimeline", back_populates="property", cascade="all, delete-orphan")
    provenance_records = relationship("PropertyProvenance", back_populates="property", cascade="all, delete-orphan")
    deals = relationship("Deal", back_populates="property", cascade="all, delete-orphan")
    data_flags = relationship("DataFlag", back_populates="property", cascade="all, delete-orphan")
    propensity_signals_rel = relationship("PropensitySignal", back_populates="property", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_property_stage', 'current_stage'),
        Index('idx_property_assigned', 'assigned_user_id'),
        Index('idx_property_score', 'bird_dog_score'),
        Index('idx_property_last_contact', 'last_contact_date'),
        Index('idx_property_team', 'team_id'),
        Index('idx_property_address', 'address'),
        Index('idx_property_city_state', 'city', 'state'),
    )

class PropertyProvenance(Base):
    """Tracks data source for each field (Open Data Ladder)"""
    __tablename__ = "property_provenance"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)

    field_name = Column(String(100), nullable=False)
    source_name = Column(String(255), nullable=False)  # e.g., "OpenAddresses", "ATTOM", "Regrid"
    source_tier = Column(String(50))  # "government", "community", "derived", "paid"
    license_type = Column(String(100))  # e.g., "ODbL", "CC0", "Proprietary"

    cost = Column(Float, default=0.0)
    confidence = Column(Float)  # 0.0 - 1.0

    fetched_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime)

    # Relationships
    property = relationship("Property", back_populates="provenance_records")

    __table_args__ = (
        Index('idx_provenance_property', 'property_id'),
        Index('idx_provenance_source', 'source_name'),
    )

class PropertyTimeline(Base):
    """Activity feed for properties"""
    __tablename__ = "property_timeline"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)

    event_type = Column(String(50), nullable=False, index=True)  # "email_sent", "stage_changed", "score_updated", etc.
    event_title = Column(String(255), nullable=False)
    event_description = Column(Text)

    metadata = Column(JSONB, default={})

    # Related entities
    communication_id = Column(Integer, ForeignKey("communications.id", ondelete="SET NULL"))
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"))
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="SET NULL"))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    property = relationship("Property", back_populates="timeline_events")

    __table_args__ = (
        Index('idx_timeline_property', 'property_id'),
        Index('idx_timeline_type', 'event_type'),
        Index('idx_timeline_created', 'created_at'),
    )

# ============================================================================
# COMMUNICATION MODELS
# ============================================================================

class Communication(Base):
    """Emails, SMS, calls, postcards, notes"""
    __tablename__ = "communications"

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    thread_id = Column(Integer, ForeignKey("communication_threads.id", ondelete="SET NULL"))
    template_id = Column(Integer, ForeignKey("templates.id", ondelete="SET NULL"))

    # Communication details
    type = Column(SQLEnum(CommunicationType), nullable=False, index=True)
    direction = Column(SQLEnum(CommunicationDirection), nullable=False)

    # Contact info
    from_address = Column(String(500))  # email or phone
    to_address = Column(String(500))

    # Content
    subject = Column(String(500))
    body = Column(Text)

    # Tracking
    sent_at = Column(DateTime, index=True)
    opened_at = Column(DateTime)
    clicked_at = Column(DateTime)
    replied_at = Column(DateTime)
    bounced_at = Column(DateTime)

    # Call-specific
    duration_seconds = Column(Integer)
    call_recording_url = Column(String(500))
    call_transcript = Column(Text)
    call_sentiment = Column(String(50))
    call_key_points = Column(JSONB, default=[])

    # Email-specific
    email_message_id = Column(String(500))  # for threading
    email_thread_position = Column(Integer)

    # Metadata
    metadata = Column(JSONB, default={})

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    property = relationship("Property", back_populates="communications")
    user = relationship("User", back_populates="communications", foreign_keys=[user_id])
    thread = relationship("CommunicationThread", back_populates="communications")
    template = relationship("Template", back_populates="communications")

    __table_args__ = (
        Index('idx_comm_property', 'property_id'),
        Index('idx_comm_type', 'type'),
        Index('idx_comm_direction', 'direction'),
        Index('idx_comm_sent', 'sent_at'),
    )

class CommunicationThread(Base):
    """Groups related communications (email threads, call series)"""
    __tablename__ = "communication_threads"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)

    subject = Column(String(500))
    first_communication_at = Column(DateTime)
    last_communication_at = Column(DateTime)
    message_count = Column(Integer, default=0)

    # Relationships
    communications = relationship("Communication", back_populates="thread")

class Template(Base):
    """Stage-aware templates with performance tracking"""
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False)
    type = Column(SQLEnum(CommunicationType), nullable=False)

    # Stage filtering
    applicable_stages = Column(JSONB, default=[])  # List of PropertyStage values

    # Content
    subject_template = Column(String(500))
    body_template = Column(Text, nullable=False)

    # Performance tracking
    times_used = Column(Integer, default=0)
    open_rate = Column(Float)
    reply_rate = Column(Float)
    meeting_rate = Column(Float)

    # A/B testing
    is_champion = Column(Boolean, default=False)
    challenger_for = Column(Integer, ForeignKey("templates.id", ondelete="SET NULL"))

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    communications = relationship("Communication", back_populates="template")

    __table_args__ = (
        Index('idx_template_team', 'team_id'),
        Index('idx_template_type', 'type'),
    )

# ============================================================================
# WORKFLOW MODELS
# ============================================================================

class Task(Base):
    """SLA-based task management"""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"))
    assigned_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    title = Column(String(500), nullable=False)
    description = Column(Text)

    status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING, index=True)
    priority = Column(SQLEnum(TaskPriority), nullable=False, default=TaskPriority.MEDIUM, index=True)

    # SLA tracking
    due_at = Column(DateTime, index=True)
    sla_hours = Column(Integer)  # e.g., 24 for "reply within 24 hours"
    completed_at = Column(DateTime)

    # Source event (if created from timeline)
    source_event_type = Column(String(50))
    source_communication_id = Column(Integer, ForeignKey("communications.id", ondelete="SET NULL"))

    # Metadata
    metadata = Column(JSONB, default={})

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    property = relationship("Property", back_populates="tasks")
    assigned_user = relationship("User", back_populates="tasks", foreign_keys=[assigned_user_id])

    __table_args__ = (
        Index('idx_task_property', 'property_id'),
        Index('idx_task_assigned', 'assigned_user_id'),
        Index('idx_task_status', 'status'),
        Index('idx_task_due', 'due_at'),
    )

class NextBestAction(Base):
    """AI-generated recommendations for next steps"""
    __tablename__ = "next_best_actions"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)

    action_type = Column(String(100), nullable=False)  # "send_follow_up", "generate_memo", etc.
    action_title = Column(String(255), nullable=False)
    action_description = Column(Text)

    priority = Column(Float, nullable=False, index=True)  # 0.0 - 1.0

    # Rule/model that generated it
    rule_name = Column(String(255))
    reasoning = Column(Text)

    # Metadata for action execution
    action_params = Column(JSONB, default={})

    # Status
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime)
    dismissed_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    expires_at = Column(DateTime)

    __table_args__ = (
        Index('idx_nba_property', 'property_id'),
        Index('idx_nba_priority', 'priority'),
        Index('idx_nba_completed', 'is_completed'),
    )

class SmartList(Base):
    """Saved queries with intent"""
    __tablename__ = "smart_lists"

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Query filters (stored as JSONB)
    filters = Column(JSONB, nullable=False)

    # Auto-refresh
    is_dynamic = Column(Boolean, default=True)
    cached_count = Column(Integer)
    last_refreshed_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_smartlist_team', 'team_id'),
    )

# ============================================================================
# DEAL MANAGEMENT MODELS
# ============================================================================

class Deal(Base):
    """Deal economics tracking"""
    __tablename__ = "deals"

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)

    status = Column(SQLEnum(DealStatus), nullable=False, default=DealStatus.PROPOSED, index=True)

    # Deal structure
    offer_price = Column(Float)
    arv = Column(Float)
    repair_cost = Column(Float)
    assignment_fee = Column(Float)
    expected_margin = Column(Float)

    # Probability & EV
    probability_of_close = Column(Float)  # 0.0 - 1.0
    expected_value = Column(Float)  # margin × probability

    # Top drivers
    ev_drivers = Column(JSONB, default=[])  # List of factors affecting EV

    # Investor
    investor_id = Column(Integer, ForeignKey("investors.id", ondelete="SET NULL"))

    # Dates
    proposed_at = Column(DateTime)
    accepted_at = Column(DateTime)
    closed_at = Column(DateTime)
    dead_at = Column(DateTime)

    # Metadata
    notes = Column(Text)
    metadata = Column(JSONB, default={})

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    property = relationship("Property", back_populates="deals")
    scenarios = relationship("DealScenario", back_populates="deal", cascade="all, delete-orphan")
    investor = relationship("Investor", back_populates="deals")

    __table_args__ = (
        Index('idx_deal_property', 'property_id'),
        Index('idx_deal_status', 'status'),
    )

class DealScenario(Base):
    """What-if scenarios for deals"""
    __tablename__ = "deal_scenarios"

    id = Column(Integer, primary_key=True)
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False)

    # Scenario parameters
    offer_price = Column(Float)
    arv = Column(Float)
    repair_cost = Column(Float)
    days_to_close = Column(Integer)

    # Calculated results
    expected_margin = Column(Float)
    probability_of_close = Column(Float)
    expected_value = Column(Float)

    # Impact analysis
    impact_summary = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    deal = relationship("Deal", back_populates="scenarios")

# ============================================================================
# COLLABORATION MODELS
# ============================================================================

class ShareLink(Base):
    """Secure share links for memos/deal rooms"""
    __tablename__ = "share_links"

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False, index=True)

    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"))
    deal_room_id = Column(Integer, ForeignKey("deal_rooms.id", ondelete="CASCADE"))

    # Link configuration
    short_code = Column(String(20), unique=True, nullable=False, index=True)
    status = Column(SQLEnum(ShareLinkStatus), nullable=False, default=ShareLinkStatus.ACTIVE)

    # Security
    password_hash = Column(String(255))
    watermark_text = Column(String(255))

    # Expiry
    expires_at = Column(DateTime, index=True)
    max_views = Column(Integer)
    view_count = Column(Integer, default=0)

    # Tracking
    viewer_name = Column(String(255))  # optional, for known viewers
    viewer_email = Column(String(255))

    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_viewed_at = Column(DateTime)

    # Relationships
    views = relationship("ShareLinkView", back_populates="share_link", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_sharelink_code', 'short_code'),
        Index('idx_sharelink_property', 'property_id'),
    )

class ShareLinkView(Base):
    """Track individual views of share links"""
    __tablename__ = "share_link_views"

    id = Column(Integer, primary_key=True)
    share_link_id = Column(Integer, ForeignKey("share_links.id", ondelete="CASCADE"), nullable=False)

    viewed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    viewer_ip = Column(String(50))
    viewer_user_agent = Column(String(500))

    # Activity tracking
    time_spent_seconds = Column(Integer)
    pages_viewed = Column(JSONB, default=[])

    # Relationships
    share_link = relationship("ShareLink", back_populates="views")

    __table_args__ = (
        Index('idx_shareview_link', 'share_link_id'),
    )

class DealRoom(Base):
    """Deal rooms for collaboration"""
    __tablename__ = "deal_rooms"

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Investor readiness
    readiness_level = Column(SQLEnum(InvestorReadinessLevel), default=InvestorReadinessLevel.RED)
    readiness_factors = Column(JSONB, default={})  # {"memo": True, "comps": True, "disclosures": False}

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    artifacts = relationship("DealRoomArtifact", back_populates="deal_room", cascade="all, delete-orphan")
    share_links = relationship("ShareLink", cascade="all, delete-orphan")

class DealRoomArtifact(Base):
    """Documents in deal rooms"""
    __tablename__ = "deal_room_artifacts"

    id = Column(Integer, primary_key=True)
    deal_room_id = Column(Integer, ForeignKey("deal_rooms.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # "memo", "comps", "photos", "inspection", "disclosure"
    file_url = Column(String(500), nullable=False)
    file_size = Column(Integer)

    uploaded_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    deal_room = relationship("DealRoom", back_populates="artifacts")

# ============================================================================
# INVESTOR MODELS
# ============================================================================

class Investor(Base):
    """Investor directory"""
    __tablename__ = "investors"

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    company = Column(String(255))

    # Preferences
    preferred_property_types = Column(JSONB, default=[])
    min_arv = Column(Float)
    max_arv = Column(Float)
    preferred_locations = Column(JSONB, default=[])

    # Performance
    deals_closed = Column(Integer, default=0)
    avg_response_time_hours = Column(Float)

    notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    deals = relationship("Deal", back_populates="investor")
    engagements = relationship("InvestorEngagement", back_populates="investor", cascade="all, delete-orphan")

class InvestorEngagement(Base):
    """Track investor engagement with properties"""
    __tablename__ = "investor_engagements"

    id = Column(Integer, primary_key=True)
    investor_id = Column(Integer, ForeignKey("investors.id", ondelete="CASCADE"), nullable=False)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)
    share_link_id = Column(Integer, ForeignKey("share_links.id", ondelete="SET NULL"))

    # Engagement metrics
    first_viewed_at = Column(DateTime)
    last_viewed_at = Column(DateTime)
    view_count = Column(Integer, default=0)
    time_spent_seconds = Column(Integer, default=0)

    # Interest level
    expressed_interest = Column(Boolean, default=False)
    questions_asked = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    investor = relationship("Investor", back_populates="engagements")

# ============================================================================
# COMPLIANCE & OPERATIONS MODELS
# ============================================================================

class ComplianceCheck(Base):
    """DNC checks, opt-outs, compliance tracking"""
    __tablename__ = "compliance_checks"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)

    check_type = Column(String(50), nullable=False)  # "dnc", "opt_out", "state_law", etc.
    status = Column(SQLEnum(ComplianceStatus), nullable=False)

    details = Column(Text)
    checked_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_compliance_property', 'property_id'),
    )

class CadenceRule(Base):
    """Cadence governor rules"""
    __tablename__ = "cadence_rules"

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False)

    # Trigger conditions
    trigger_on = Column(String(100), nullable=False)  # "reply_detected", "no_opens_after_3", etc.

    # Actions
    action_type = Column(String(100), nullable=False)  # "pause", "switch_to_sms", "switch_to_postcard"
    action_params = Column(JSONB, default={})

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class DeliverabilityMetrics(Base):
    """Track email deliverability"""
    __tablename__ = "deliverability_metrics"

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)

    date = Column(DateTime, nullable=False, index=True)

    # Metrics
    emails_sent = Column(Integer, default=0)
    emails_delivered = Column(Integer, default=0)
    emails_bounced = Column(Integer, default=0)
    emails_opened = Column(Integer, default=0)
    emails_clicked = Column(Integer, default=0)

    # Rates
    bounce_rate = Column(Float)
    open_rate = Column(Float)
    click_rate = Column(Float)

    # Domain health
    domain_warmup_status = Column(String(50))
    suppression_list_size = Column(Integer)

    __table_args__ = (
        Index('idx_deliverability_team', 'team_id'),
        Index('idx_deliverability_date', 'date'),
    )

class BudgetTracking(Base):
    """Track data provider costs"""
    __tablename__ = "budget_tracking"

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)

    provider = Column(String(100), nullable=False)  # "ATTOM", "Regrid", etc.
    date = Column(DateTime, nullable=False, index=True)

    # Usage
    requests_made = Column(Integer, default=0)
    cost = Column(Float, default=0.0)

    # Limits
    monthly_cap = Column(Float)
    remaining_budget = Column(Float)

    # Forecasting
    projected_end_of_month_cost = Column(Float)

    __table_args__ = (
        Index('idx_budget_team', 'team_id'),
        Index('idx_budget_provider', 'provider'),
    )

class DataFlag(Base):
    """Crowdsourced data quality flags"""
    __tablename__ = "data_flags"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)
    reported_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    field_name = Column(String(100), nullable=False)
    issue_type = Column(String(100), nullable=False)  # "incorrect", "outdated", "missing", etc.
    description = Column(Text)

    status = Column(SQLEnum(DataFlagStatus), nullable=False, default=DataFlagStatus.OPEN)

    resolved_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    resolved_at = Column(DateTime)
    resolution_notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    property = relationship("Property", back_populates="data_flags")

    __table_args__ = (
        Index('idx_dataflag_property', 'property_id'),
        Index('idx_dataflag_status', 'status'),
    )

# ============================================================================
# PROPENSITY & SCORING MODELS
# ============================================================================

class PropensitySignal(Base):
    """Signals that indicate likelihood to sell"""
    __tablename__ = "propensity_signals"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)

    signal_type = Column(String(100), nullable=False)  # "long_tenure", "tax_lien", "absentee", etc.
    signal_value = Column(String(255))
    weight = Column(Float)  # contribution to overall propensity

    reasoning = Column(Text)

    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    property = relationship("Property", back_populates="propensity_signals_rel")

    __table_args__ = (
        Index('idx_propsignal_property', 'property_id'),
    )

# ============================================================================
# ONBOARDING MODELS
# ============================================================================

class UserOnboarding(Base):
    """Track user onboarding progress"""
    __tablename__ = "user_onboarding"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Checklist steps
    steps_completed = Column(JSONB, default=[])

    # Progress
    is_complete = Column(Boolean, default=False)
    completed_at = Column(DateTime)

    # Selected preset
    persona_preset = Column(String(100))  # "wholesaler_starter", "fix_and_flip", "institutional"

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class PresetTemplate(Base):
    """Starter presets by persona"""
    __tablename__ = "preset_templates"

    id = Column(Integer, primary_key=True)

    persona = Column(String(100), nullable=False, unique=True)  # "wholesaler_starter", etc.
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Configuration
    default_filters = Column(JSONB, default={})
    default_templates = Column(JSONB, default=[])
    dashboard_tiles = Column(JSONB, default=[])

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

# ============================================================================
# OPEN DATA INTEGRATIONS
# ============================================================================

class OpenDataSource(Base):
    """Catalog of open data sources"""
    __tablename__ = "open_data_sources"

    id = Column(Integer, primary_key=True)

    name = Column(String(255), nullable=False, unique=True)
    source_type = Column(String(100), nullable=False)  # "government", "community", "derived"

    # Coverage
    data_types = Column(JSONB, default=[])  # ["addresses", "parcels", "flood_zones"]
    coverage_areas = Column(JSONB, default=[])  # ["US_nationwide", "CA_only"]

    # Access
    api_endpoint = Column(String(500))
    license_type = Column(String(100))
    cost_per_request = Column(Float, default=0.0)

    # Quality
    data_quality_rating = Column(Float)  # 0.0 - 1.0
    freshness_days = Column(Integer)  # how often updated

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ============================================================================
# IDEMPOTENCY
# ============================================================================

class IdempotencyKey(Base):
    """
    Idempotency keys for preventing duplicate operations

    Prevents duplicate side-effects from:
    - User double-clicks
    - Network retries
    - Webhook replays
    - API client retries

    Key features:
    - Unique constraint on (key, endpoint)
    - Response caching for consistent replay
    - Automatic expiration (TTL)
    - Scoped to user/team

    Usage:
        POST /api/v1/properties
        Idempotency-Key: unique-client-generated-key-123

        If same key used again:
        - Within TTL: Returns cached response (409 if processing, 200 if complete)
        - After TTL: Treated as new request
    """
    __tablename__ = "idempotency_keys"

    id = Column(Integer, primary_key=True)

    # Idempotency key (client-provided or server-generated)
    idempotency_key = Column(String(255), nullable=False, index=True)

    # Endpoint that was called
    endpoint = Column(String(255), nullable=False)
    request_method = Column(String(10), nullable=False)  # POST, PUT, PATCH, DELETE

    # Request details (for debugging)
    request_params = Column(JSONB)

    # Cached response
    response_status = Column(Integer)  # HTTP status code
    response_body = Column(JSONB)      # Response JSON

    # Ownership
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)  # TTL for cleanup

    # Unique constraint: same key + endpoint = idempotent
    __table_args__ = (
        UniqueConstraint('idempotency_key', 'endpoint', name='uq_idempotency_key_endpoint'),
        Index('idx_idempotency_user_id', 'user_id'),
        Index('idx_idempotency_team_id', 'team_id'),
        Index('idx_idempotency_expires_at', 'expires_at'),
    )

# ============================================================================
# PORTFOLIO RECONCILIATION MODELS
# ============================================================================

class ReconciliationHistory(Base):
    """
    Portfolio reconciliation audit trail

    Tracks nightly reconciliation runs comparing database metrics
    against CSV truth data.

    Alert Conditions:
    - Any metric drift > 0.5%
    - Alert fires when alert_triggered = True

    Use Cases:
    - Data integrity verification
    - Detect migration errors
    - Audit compliance
    - Financial accuracy
    """
    __tablename__ = "reconciliation_history"

    id = Column(Integer, primary_key=True)

    # Optional team filter
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"))

    # Reconciliation date
    reconciliation_date = Column(DateTime, nullable=False)

    # Summary metrics
    total_metrics = Column(Integer, nullable=False, default=0)
    passing_metrics = Column(Integer, nullable=False, default=0)
    failing_metrics = Column(Integer, nullable=False, default=0)
    max_drift_percentage = Column(Float, nullable=False, default=0.0)

    # Alert status
    alert_triggered = Column(Boolean, nullable=False, default=False)

    # Full results JSON
    results_json = Column(JSONB)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Indexes
    __table_args__ = (
        Index('idx_reconciliation_team', 'team_id'),
        Index('idx_reconciliation_date', 'reconciliation_date'),
        Index('idx_reconciliation_alert', 'alert_triggered'),
    )

# ============================================================================
# DEAD LETTER QUEUE (DLQ) MODELS
# ============================================================================

class FailedTask(Base):
    """
    Failed Celery tasks for Dead Letter Queue (DLQ) management

    Tracks tasks that failed after exhausting retries, allowing:
    - Admin inspection of failures
    - Manual replay with idempotency
    - Monitoring and alerting
    - Failure analytics

    Lifecycle:
    1. Task fails → recorded with status="failed"
    2. Admin replays → status="replaying"
    3. Replay succeeds → status="replayed"
    4. Manual archive → status="archived"
    """
    __tablename__ = "failed_tasks"

    id = Column(Integer, primary_key=True)

    # Task identification
    task_id = Column(String(255), nullable=False, unique=True)  # Original Celery task ID
    task_name = Column(String(255), nullable=False)  # e.g., "api.tasks.memo_tasks.generate_memo_async"
    queue_name = Column(String(100), nullable=False, default="default")

    # Task arguments (for replay)
    args = Column(JSONB, default=[])
    kwargs = Column(JSONB, default={})

    # Failure details
    exception_type = Column(String(255))
    exception_message = Column(Text)
    traceback = Column(Text)
    retries_attempted = Column(Integer, default=0)

    # Timestamps
    failed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    replayed_at = Column(DateTime)

    # Replay tracking
    status = Column(String(50), nullable=False, default="failed")  # failed, replaying, replayed, archived
    replayed_task_id = Column(String(255))  # New task ID if replayed
    replay_count = Column(Integer, default=0)

    # Indexes
    __table_args__ = (
        Index('idx_failedtask_status', 'status'),
        Index('idx_failedtask_queue', 'queue_name'),
        Index('idx_failedtask_task_name', 'task_name'),
        Index('idx_failedtask_failed_at', 'failed_at'),
    )

# ============================================================================
# EMAIL DELIVERABILITY & COMPLIANCE MODELS
# ============================================================================

class EmailUnsubscribe(Base):
    """
    Email unsubscribe list

    Compliance:
    - CAN-SPAM: Must honor within 10 business days
    - GDPR: Must honor immediately
    - Permanent suppression

    Use Cases:
    - User unsubscribe requests
    - Spam complaints
    - Hard bounces
    """
    __tablename__ = "email_unsubscribes"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    unsubscribed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reason = Column(Text)
    source = Column(String(50), nullable=False, default="user_request")  # user_request, complaint, bounce

    __table_args__ = (
        Index('idx_unsubscribe_email', 'email'),
    )


class DoNotCall(Base):
    """
    Do Not Call (DNC) list

    Compliance:
    - TCPA: Must honor DNC requests
    - Permanent suppression for calls/SMS

    Use Cases:
    - User DNC requests
    - Regulatory DNC lists
    - Litigation protection
    """
    __tablename__ = "do_not_call"

    id = Column(Integer, primary_key=True)
    phone = Column(String(20), nullable=False, unique=True, index=True)  # Normalized (digits only)
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reason = Column(Text)
    source = Column(String(50), nullable=False, default="user_request")

    __table_args__ = (
        Index('idx_dnc_phone', 'phone'),
    )


class CommunicationConsent(Base):
    """
    Communication consent tracking

    Compliance:
    - GDPR: Requires explicit consent with audit trail
    - TCPA: Requires prior express written consent for calls/SMS
    - Full audit trail for litigation defense

    Consent Types:
    - email: Email marketing consent
    - sms: SMS/text message consent
    - call: Phone call consent
    - recording: Call recording consent
    """
    __tablename__ = "communication_consents"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)

    # Consent details
    consent_type = Column(String(50), nullable=False)  # email, sms, call, recording
    consented = Column(Boolean, nullable=False)  # True = consent given, False = declined

    # Audit trail
    consent_method = Column(String(50), nullable=False)  # web_form, verbal, written, implied
    consent_text = Column(Text)  # Exact text of consent
    ip_address = Column(String(45))  # IPv4 or IPv6
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    property = relationship("Property", backref="consents")

    __table_args__ = (
        Index('idx_consent_property', 'property_id'),
        Index('idx_consent_type', 'consent_type'),
        Index('idx_consent_recorded', 'recorded_at'),
    )

# ============================================================================
# LEGACY MODEL (keep for compatibility)
# ============================================================================

class Ping(Base):
    """Legacy ping model"""
    __tablename__ = "ping"
    id = Column(Integer, primary_key=True)
    ts = Column(TIMESTAMP(timezone=True), server_default=func.now())
