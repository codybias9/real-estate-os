"""
SQLAlchemy models for Real Estate OS.

This module defines the complete data model for the pipeline, including:
- Property management and pipeline stages
- User authentication and team management
- Communications (email, SMS, calls) with threading
- Tasks and workflow automation
- Deal tracking and economics
- Templates and smart lists
- Compliance and deliverability tracking
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, TIMESTAMP, Boolean, Float,
    JSON, ForeignKey, Index, CheckConstraint, Enum, DECIMAL, BigInteger
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()


# ============================================================================
# ENUMS
# ============================================================================

class PipelineStageEnum(str, enum.Enum):
    """Pipeline stages for property lifecycle"""
    PROSPECT = "prospect"
    ENRICHMENT = "enrichment"
    SCORED = "scored"
    OUTREACH = "outreach"
    CONTACT_MADE = "contact_made"
    NEGOTIATION = "negotiation"
    PACKET_SENT = "packet_sent"
    OFFER = "offer"
    WON = "won"
    LOST = "lost"
    ARCHIVED = "archived"


class CommunicationTypeEnum(str, enum.Enum):
    """Communication channel types"""
    EMAIL = "email"
    SMS = "sms"
    CALL = "call"
    POSTCARD = "postcard"
    NOTE = "note"


class CommunicationDirectionEnum(str, enum.Enum):
    """Communication direction"""
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class TaskStatusEnum(str, enum.Enum):
    """Task status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"


class TaskPriorityEnum(str, enum.Enum):
    """Task priority"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class DealStatusEnum(str, enum.Enum):
    """Deal status"""
    ACTIVE = "active"
    WON = "won"
    LOST = "lost"
    CANCELLED = "cancelled"


class UserRoleEnum(str, enum.Enum):
    """User roles"""
    ADMIN = "admin"
    MANAGER = "manager"
    AGENT = "agent"
    VIEWER = "viewer"


# ============================================================================
# CORE MODELS
# ============================================================================

class User(Base):
    """User accounts and authentication"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRoleEnum), nullable=False, default=UserRoleEnum.AGENT)
    phone = Column(String(50))
    is_active = Column(Boolean, default=True, nullable=False)

    # Authentication (basic - expand with proper auth later)
    password_hash = Column(String(255))

    # Settings
    settings = Column(JSONB, default={})

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login_at = Column(TIMESTAMP(timezone=True))

    # Relationships
    assigned_properties = relationship("Property", back_populates="assigned_user", foreign_keys="Property.assigned_user_id")
    tasks = relationship("Task", back_populates="assignee", foreign_keys="Task.assignee_id")
    created_tasks = relationship("Task", back_populates="creator", foreign_keys="Task.created_by_id")


class PipelineStage(Base):
    """Configurable pipeline stages"""
    __tablename__ = "pipeline_stages"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    order_index = Column(Integer, nullable=False)
    color = Column(String(7))  # Hex color code
    is_active = Column(Boolean, default=True, nullable=False)

    # Stage configuration
    config = Column(JSONB, default={})  # e.g., SLA days, auto-actions

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Property(Base):
    """Enhanced property tracking - extends prospect_queue"""
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True)

    # Link to original prospect queue record
    prospect_queue_id = Column(Integer, index=True)

    # Core property info
    address = Column(String(500), nullable=False)
    city = Column(String(100))
    state = Column(String(2))
    zip_code = Column(String(10))
    county = Column(String(100))

    # Property details
    apn = Column(String(50), index=True)  # Assessor Parcel Number
    beds = Column(Integer)
    baths = Column(Float)
    sqft = Column(Integer)
    lot_size = Column(Integer)
    year_built = Column(Integer)
    property_type = Column(String(50))

    # Pricing
    assessed_value = Column(DECIMAL(12, 2))
    market_value = Column(DECIMAL(12, 2))
    asking_price = Column(DECIMAL(12, 2))
    last_sale_price = Column(DECIMAL(12, 2))
    last_sale_date = Column(TIMESTAMP(timezone=True))

    # Owner info
    owner_name = Column(String(255))
    owner_type = Column(String(50))  # individual, llc, trust, etc.
    owner_occupied = Column(Boolean)
    mailing_address = Column(Text)

    # Contact info
    owner_phone = Column(String(50))
    owner_email = Column(String(255))

    # Pipeline status
    current_stage = Column(String(100), nullable=False, default="prospect", index=True)
    assigned_user_id = Column(Integer, ForeignKey("users.id"), index=True)

    # Scoring
    bird_dog_score = Column(Float)
    probability_close = Column(Float)  # 0-1 probability
    expected_value = Column(DECIMAL(12, 2))

    # Propensity signals
    owner_propensity_score = Column(Float)  # Likely to entertain offer
    propensity_factors = Column(JSONB, default={})  # Reasons/signals

    # Data quality
    data_quality_score = Column(Float)
    data_flags = Column(JSONB, default=[])  # User-reported issues
    data_sources = Column(JSONB, default={})  # Provenance tracking

    # Engagement tracking
    last_contact_date = Column(TIMESTAMP(timezone=True))
    last_reply_date = Column(TIMESTAMP(timezone=True))
    total_touches = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)

    # Documents
    memo_generated_at = Column(TIMESTAMP(timezone=True))
    memo_url = Column(Text)  # MinIO URL
    packet_generated_at = Column(TIMESTAMP(timezone=True))
    packet_url = Column(Text)  # MinIO URL

    # Metadata
    tags = Column(JSONB, default=[])
    custom_fields = Column(JSONB, default={})
    notes = Column(Text)

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    archived_at = Column(TIMESTAMP(timezone=True))

    # Relationships
    assigned_user = relationship("User", back_populates="assigned_properties", foreign_keys=[assigned_user_id])
    stage_history = relationship("PropertyStageHistory", back_populates="property", cascade="all, delete-orphan")
    communications = relationship("Communication", back_populates="property", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="property", cascade="all, delete-orphan")
    timeline_events = relationship("TimelineEvent", back_populates="property", cascade="all, delete-orphan")
    deals = relationship("Deal", back_populates="property", cascade="all, delete-orphan")
    shares = relationship("InvestorShare", back_populates="property", cascade="all, delete-orphan")
    next_best_actions = relationship("NextBestAction", back_populates="property", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_property_stage_assigned', 'current_stage', 'assigned_user_id'),
        Index('idx_property_score', 'bird_dog_score'),
        Index('idx_property_created', 'created_at'),
    )


class PropertyStageHistory(Base):
    """Track property stage transitions"""
    __tablename__ = "property_stage_history"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)

    from_stage = Column(String(100))
    to_stage = Column(String(100), nullable=False)

    changed_by_id = Column(Integer, ForeignKey("users.id"))
    reason = Column(Text)
    metadata = Column(JSONB, default={})

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    property = relationship("Property", back_populates="stage_history")
    changed_by = relationship("User")


class Communication(Base):
    """All communications (email, SMS, calls) with threading support"""
    __tablename__ = "communications"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)

    # Communication details
    type = Column(Enum(CommunicationTypeEnum), nullable=False)
    direction = Column(Enum(CommunicationDirectionEnum), nullable=False)

    # Threading (for emails)
    thread_id = Column(String(255), index=True)  # Email thread ID
    message_id = Column(String(255), unique=True, index=True)  # Email message ID
    in_reply_to = Column(String(255))  # Parent message ID

    # Participants
    from_address = Column(String(255))
    to_addresses = Column(JSONB, default=[])
    cc_addresses = Column(JSONB, default=[])

    # Content
    subject = Column(String(500))
    body_text = Column(Text)
    body_html = Column(Text)

    # Template tracking
    template_id = Column(Integer, ForeignKey("templates.id"))

    # Engagement tracking
    sent_at = Column(TIMESTAMP(timezone=True))
    delivered_at = Column(TIMESTAMP(timezone=True))
    opened_at = Column(TIMESTAMP(timezone=True))
    clicked_at = Column(TIMESTAMP(timezone=True))
    replied_at = Column(TIMESTAMP(timezone=True))
    bounced_at = Column(TIMESTAMP(timezone=True))

    # Call-specific fields
    call_duration_seconds = Column(Integer)
    call_recording_url = Column(Text)
    call_transcription = Column(Text)
    call_summary = Column(Text)
    call_sentiment = Column(String(20))  # positive, neutral, negative
    call_action_items = Column(JSONB, default=[])

    # Metadata
    metadata = Column(JSONB, default={})
    external_id = Column(String(255))  # Twilio SID, Gmail ID, etc.

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    property = relationship("Property", back_populates="communications")
    template = relationship("Template")

    __table_args__ = (
        Index('idx_communication_property_type', 'property_id', 'type'),
        Index('idx_communication_thread', 'thread_id'),
        Index('idx_communication_sent', 'sent_at'),
    )


class Template(Base):
    """Email/SMS templates with stage awareness"""
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True)

    name = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(Enum(CommunicationTypeEnum), nullable=False)

    # Stage filtering - templates only show for these stages
    allowed_stages = Column(JSONB, default=[])  # Empty = all stages

    # Template content
    subject = Column(String(500))  # Email only
    body_text = Column(Text, nullable=False)
    body_html = Column(Text)  # Email only

    # Variables available: {address}, {owner_name}, {score}, {price}, etc.

    # Performance tracking
    send_count = Column(Integer, default=0)
    open_count = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)
    meeting_count = Column(Integer, default=0)

    # A/B testing
    is_champion = Column(Boolean, default=False)
    variant_group = Column(String(100))  # Group for A/B tests

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    created_by_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    created_by = relationship("User")


class Task(Base):
    """Tasks with SLA and assignment"""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), index=True)

    title = Column(String(500), nullable=False)
    description = Column(Text)

    # Assignment
    assignee_id = Column(Integer, ForeignKey("users.id"), index=True)
    created_by_id = Column(Integer, ForeignKey("users.id"))

    # Status and priority
    status = Column(Enum(TaskStatusEnum), nullable=False, default=TaskStatusEnum.PENDING, index=True)
    priority = Column(Enum(TaskPriorityEnum), nullable=False, default=TaskPriorityEnum.MEDIUM)

    # SLA
    due_date = Column(TIMESTAMP(timezone=True), index=True)
    sla_hours = Column(Integer)  # Hours until due

    # Completion
    completed_at = Column(TIMESTAMP(timezone=True))

    # Source (if auto-generated from event)
    source_type = Column(String(50))  # email_reply, call, open, etc.
    source_id = Column(Integer)  # communication.id

    # Metadata
    metadata = Column(JSONB, default={})

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    property = relationship("Property", back_populates="tasks")
    assignee = relationship("User", back_populates="tasks", foreign_keys=[assignee_id])
    creator = relationship("User", back_populates="created_tasks", foreign_keys=[created_by_id])

    __table_args__ = (
        Index('idx_task_assignee_status', 'assignee_id', 'status'),
        Index('idx_task_due_date', 'due_date'),
    )


class TimelineEvent(Base):
    """Activity timeline for properties"""
    __tablename__ = "timeline_events"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)

    event_type = Column(String(100), nullable=False)  # email_sent, call_made, stage_change, etc.
    title = Column(String(500), nullable=False)
    description = Column(Text)

    # Actor
    user_id = Column(Integer, ForeignKey("users.id"))

    # Related entities
    related_type = Column(String(50))  # communication, task, deal
    related_id = Column(Integer)

    # Metadata
    metadata = Column(JSONB, default={})

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    property = relationship("Property", back_populates="timeline_events")
    user = relationship("User")

    __table_args__ = (
        Index('idx_timeline_property_created', 'property_id', 'created_at'),
    )


class Deal(Base):
    """Deal tracking with economics"""
    __tablename__ = "deals"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(500), nullable=False)
    status = Column(Enum(DealStatusEnum), nullable=False, default=DealStatusEnum.ACTIVE, index=True)

    # Economics
    offer_price = Column(DECIMAL(12, 2))
    assignment_fee = Column(DECIMAL(12, 2))
    estimated_margin = Column(DECIMAL(12, 2))
    expected_value = Column(DECIMAL(12, 2))  # margin × probability

    # Probability drivers (what-if sliders)
    probability_close = Column(Float)  # 0-1
    probability_factors = Column(JSONB, default={})  # Breakdown of factors

    # Timeline
    offer_date = Column(TIMESTAMP(timezone=True))
    expected_close_date = Column(TIMESTAMP(timezone=True))
    actual_close_date = Column(TIMESTAMP(timezone=True))
    days_to_close = Column(Integer)

    # Investor info
    investor_name = Column(String(255))
    investor_email = Column(String(255))
    investor_phone = Column(String(50))

    # Documents
    has_packet = Column(Boolean, default=False)
    packet_sent_at = Column(TIMESTAMP(timezone=True))

    # Metadata
    notes = Column(Text)
    metadata = Column(JSONB, default={})

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    property = relationship("Property", back_populates="deals")
    documents = relationship("DealDocument", back_populates="deal", cascade="all, delete-orphan")


class DealDocument(Base):
    """Documents attached to deals (deal room)"""
    __tablename__ = "deal_documents"

    id = Column(Integer, primary_key=True)
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(500), nullable=False)
    document_type = Column(String(100))  # memo, comps, disclosure, photo, contract
    file_url = Column(Text, nullable=False)  # MinIO URL
    file_size_bytes = Column(BigInteger)
    mime_type = Column(String(100))

    # Metadata
    uploaded_by_id = Column(Integer, ForeignKey("users.id"))
    metadata = Column(JSONB, default={})

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    deal = relationship("Deal", back_populates="documents")
    uploaded_by = relationship("User")


class InvestorShare(Base):
    """Secure share links for investors"""
    __tablename__ = "investor_shares"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)

    # Share link
    share_token = Column(String(100), unique=True, nullable=False, index=True)
    share_url = Column(Text)

    # Access control
    investor_email = Column(String(255))
    requires_email = Column(Boolean, default=False)
    password_hash = Column(String(255))

    # Expiration
    expires_at = Column(TIMESTAMP(timezone=True))
    is_active = Column(Boolean, default=True, nullable=False)

    # Watermark and security
    watermark_text = Column(String(255))
    allow_download = Column(Boolean, default=True)

    # Tracking
    view_count = Column(Integer, default=0)
    last_viewed_at = Column(TIMESTAMP(timezone=True))

    # Q&A posts (stored as events)
    has_questions = Column(Boolean, default=False)

    # Metadata
    metadata = Column(JSONB, default={})

    created_by_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    property = relationship("Property", back_populates="shares")
    created_by = relationship("User")


class DataFlag(Base):
    """User-reported data quality issues"""
    __tablename__ = "data_flags"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)

    field_name = Column(String(100), nullable=False)
    issue_type = Column(String(100), nullable=False)  # incorrect, outdated, missing
    description = Column(Text)

    suggested_value = Column(Text)

    # Resolution
    status = Column(String(50), default="open", nullable=False, index=True)  # open, resolved, dismissed
    resolved_at = Column(TIMESTAMP(timezone=True))
    resolved_by_id = Column(Integer, ForeignKey("users.id"))
    resolution_notes = Column(Text)

    reported_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    reported_by = relationship("User", foreign_keys=[reported_by_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])


class SmartList(Base):
    """Saved search criteria (smart lists)"""
    __tablename__ = "smart_lists"

    id = Column(Integer, primary_key=True)

    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Filter criteria (JSON query)
    filters = Column(JSONB, nullable=False)
    # Example: {"current_stage": ["outreach", "contact_made"], "bird_dog_score__gte": 0.7}

    # Display
    icon = Column(String(50))
    color = Column(String(7))
    order_index = Column(Integer)

    # Sharing
    is_shared = Column(Boolean, default=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Stats (cached)
    property_count = Column(Integer, default=0)
    last_refreshed_at = Column(TIMESTAMP(timezone=True))

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    created_by = relationship("User")


class NextBestAction(Base):
    """AI-generated next best action recommendations"""
    __tablename__ = "next_best_actions"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)

    # Recommendation
    action_type = Column(String(100), nullable=False)  # send_intro, regenerate_memo, move_to_negotiation, etc.
    title = Column(String(500), nullable=False)
    description = Column(Text)

    # Context
    reasoning = Column(Text)  # Why this action is recommended
    priority_score = Column(Float)  # 0-1, higher = more urgent

    # Signals used
    signals = Column(JSONB, default={})
    # Example: {"stage": "outreach", "days_in_stage": 7, "no_reply": true}

    # Execution
    is_completed = Column(Boolean, default=False)
    completed_at = Column(TIMESTAMP(timezone=True))
    dismissed_at = Column(TIMESTAMP(timezone=True))

    # Metadata
    metadata = Column(JSONB, default={})

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    property = relationship("Property", back_populates="next_best_actions")

    __table_args__ = (
        Index('idx_nba_property_completed', 'property_id', 'is_completed'),
    )


class ComplianceRecord(Base):
    """DNC, opt-outs, and consent tracking"""
    __tablename__ = "compliance_records"

    id = Column(Integer, primary_key=True)

    # Contact info
    phone = Column(String(50), index=True)
    email = Column(String(255), index=True)

    # Compliance type
    record_type = Column(String(50), nullable=False)  # dnc, opt_out_email, opt_out_sms, consent

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Source
    source = Column(String(100))  # user_request, automated, import
    notes = Column(Text)

    # Timestamps
    effective_date = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(TIMESTAMP(timezone=True))

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_compliance_phone_active', 'phone', 'is_active'),
        Index('idx_compliance_email_active', 'email', 'is_active'),
    )


class DeliverabilityMetric(Base):
    """Email deliverability and reputation tracking"""
    __tablename__ = "deliverability_metrics"

    id = Column(Integer, primary_key=True)

    # Time period
    date = Column(TIMESTAMP(timezone=True), nullable=False, index=True)

    # Sender (email address or domain)
    sender = Column(String(255), nullable=False, index=True)

    # Metrics
    sent_count = Column(Integer, default=0)
    delivered_count = Column(Integer, default=0)
    bounced_count = Column(Integer, default=0)
    opened_count = Column(Integer, default=0)
    clicked_count = Column(Integer, default=0)
    spam_count = Column(Integer, default=0)
    unsubscribed_count = Column(Integer, default=0)

    # Rates (calculated)
    delivery_rate = Column(Float)  # delivered / sent
    bounce_rate = Column(Float)  # bounced / sent
    open_rate = Column(Float)  # opened / delivered
    click_rate = Column(Float)  # clicked / delivered
    spam_rate = Column(Float)  # spam / delivered

    # Reputation indicators
    reputation_score = Column(Float)  # 0-100
    warmup_status = Column(String(50))  # warming, warmed, healthy, at_risk, poor

    # Alerts
    has_alerts = Column(Boolean, default=False)
    alerts = Column(JSONB, default=[])

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_deliverability_sender_date', 'sender', 'date'),
    )


class CadenceRule(Base):
    """Automated cadence rules and governors"""
    __tablename__ = "cadence_rules"

    id = Column(Integer, primary_key=True)

    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Trigger conditions
    trigger_type = Column(String(100), nullable=False)  # reply, no_open, stage_change, time_elapsed
    trigger_config = Column(JSONB, nullable=False)

    # Actions
    action_type = Column(String(100), nullable=False)  # pause, switch_channel, send_template, create_task
    action_config = Column(JSONB, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Stats
    triggered_count = Column(Integer, default=0)
    last_triggered_at = Column(TIMESTAMP(timezone=True))

    created_by_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    created_by = relationship("User")


class BudgetMonitor(Base):
    """Real-time spend tracking vs caps"""
    __tablename__ = "budget_monitors"

    id = Column(Integer, primary_key=True)

    # Budget period
    period_start = Column(TIMESTAMP(timezone=True), nullable=False)
    period_end = Column(TIMESTAMP(timezone=True), nullable=False)

    # Budget caps
    email_cap = Column(Integer)
    sms_cap = Column(Integer)
    call_minutes_cap = Column(Integer)
    data_cost_cap = Column(DECIMAL(10, 2))

    # Current spend
    email_sent = Column(Integer, default=0)
    sms_sent = Column(Integer, default=0)
    call_minutes_used = Column(Integer, default=0)
    data_cost = Column(DECIMAL(10, 2), default=0)

    # Alerts
    alert_threshold = Column(Float, default=0.8)  # Alert at 80%
    alerts_sent = Column(JSONB, default=[])

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index('idx_budget_period', 'period_start', 'period_end'),
    )


# ============================================================================
# LEGACY/COMPATIBILITY
# ============================================================================

class Ping(Base):
    """Health check table"""
    __tablename__ = "ping"

    id = Column(Integer, primary_key=True)
    ts = Column(TIMESTAMP(timezone=True), server_default=func.now())
