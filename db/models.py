"""SQLAlchemy models for Real Estate OS database

This module contains all database table models used across the application.
Models are organized by functional area.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Date, Numeric, Boolean,
    TIMESTAMP, ForeignKey, UniqueConstraint, Index, ARRAY
)
from sqlalchemy.dialects.postgresql import JSONB, INET
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import func

Base = declarative_base()


# ============================================================================
# Core Models
# ============================================================================

class Ping(Base):
    """Health check table for database connectivity tests"""
    __tablename__ = "ping"

    id = Column(Integer, primary_key=True)
    ts = Column(TIMESTAMP(timezone=True), server_default=func.now())


class ProspectQueue(Base):
    """Initial ingestion point for all scraped property data"""
    __tablename__ = "prospect_queue"

    id = Column(Integer, primary_key=True)
    source = Column(String(255), nullable=False)
    source_id = Column(String(255), unique=True, nullable=False)
    url = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=False)
    status = Column(String(50), default='new', nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    enrichment = relationship("PropertyEnrichment", back_populates="prospect", uselist=False)
    scores = relationship("PropertyScore", back_populates="prospect", uselist=False)
    packets = relationship("ActionPacket", back_populates="prospect")

    __table_args__ = (
        Index('idx_prospect_queue_status', 'status'),
    )


# ============================================================================
# Enrichment Models (Phase 3)
# ============================================================================

class PropertyEnrichment(Base):
    """Enriched property data from various APIs and public records"""
    __tablename__ = "property_enrichment"

    id = Column(Integer, primary_key=True)
    prospect_id = Column(Integer, ForeignKey('prospect_queue.id', ondelete='CASCADE'), nullable=False)

    # Property characteristics
    apn = Column(String(255))  # Assessor Parcel Number
    square_footage = Column(Integer)
    bedrooms = Column(Integer)
    bathrooms = Column(Numeric(3, 1))
    year_built = Column(Integer)

    # Financial data
    assessed_value = Column(Numeric(12, 2))
    market_value = Column(Numeric(12, 2))
    last_sale_date = Column(Date)
    last_sale_price = Column(Numeric(12, 2))
    tax_amount_annual = Column(Numeric(10, 2))

    # Property details
    zoning = Column(String(100))
    lot_size_sqft = Column(Integer)
    property_type = Column(String(50))

    # Owner information
    owner_name = Column(String(255))
    owner_mailing_address = Column(Text)

    # Metadata
    source_api = Column(String(100))
    raw_response = Column(JSONB)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    prospect = relationship("ProspectQueue", back_populates="enrichment")
    scores = relationship("PropertyScore", back_populates="enrichment")

    __table_args__ = (
        UniqueConstraint('prospect_id', name='unique_prospect_enrichment'),
        Index('idx_property_enrichment_prospect', 'prospect_id'),
        Index('idx_property_enrichment_apn', 'apn'),
    )


# ============================================================================
# Scoring Models (Phase 4)
# ============================================================================

class MLModel(Base):
    """Registry of ML models with versioning and metadata"""
    __tablename__ = "ml_models"

    id = Column(Integer, primary_key=True)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=False)
    model_type = Column(String(50))  # lightgbm, neural_net, etc.
    model_path = Column(String(500), nullable=False)  # MinIO path

    training_date = Column(TIMESTAMP(timezone=True), server_default=func.now())
    metrics = Column(JSONB)  # accuracy, precision, recall, etc.
    hyperparameters = Column(JSONB)
    feature_names = Column(ARRAY(Text))

    is_active = Column(Boolean, default=False)
    created_by = Column(String(100))
    notes = Column(Text)

    __table_args__ = (
        UniqueConstraint('model_name', 'model_version', name='unique_model_version'),
        Index('idx_ml_models_active', 'is_active', postgresql_where=(Column('is_active') == True)),
        Index('idx_ml_models_name', 'model_name'),
    )


class PropertyScore(Base):
    """ML model predictions and vector embeddings for properties"""
    __tablename__ = "property_scores"

    id = Column(Integer, primary_key=True)
    prospect_id = Column(Integer, ForeignKey('prospect_queue.id', ondelete='CASCADE'), nullable=False)
    enrichment_id = Column(Integer, ForeignKey('property_enrichment.id', ondelete='CASCADE'))

    bird_dog_score = Column(Numeric(5, 2), nullable=False)  # 0-100 score
    model_version = Column(String(50), nullable=False)

    # Feature data
    feature_vector = Column(JSONB)  # Stored as JSONB, actual vectors in Qdrant
    feature_importance = Column(JSONB)
    score_breakdown = Column(JSONB)
    confidence_level = Column(Numeric(5, 2))

    # Qdrant reference
    qdrant_point_id = Column(String(100))  # UUID of vector in Qdrant

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    prospect = relationship("ProspectQueue", back_populates="scores")
    enrichment = relationship("PropertyEnrichment", back_populates="scores")
    packets = relationship("ActionPacket", back_populates="score")

    __table_args__ = (
        UniqueConstraint('prospect_id', name='unique_prospect_score'),
        Index('idx_property_scores_prospect', 'prospect_id'),
        Index('idx_property_scores_score', 'bird_dog_score', postgresql_ops={'bird_dog_score': 'DESC'}),
        Index('idx_property_scores_model', 'model_version'),
    )


# ============================================================================
# Document Generation Models (Phase 5)
# ============================================================================

class ActionPacket(Base):
    """Generated investment packets (PDFs) stored in MinIO"""
    __tablename__ = "action_packets"

    id = Column(Integer, primary_key=True)
    prospect_id = Column(Integer, ForeignKey('prospect_queue.id', ondelete='CASCADE'), nullable=False)
    score_id = Column(Integer, ForeignKey('property_scores.id', ondelete='CASCADE'))

    packet_path = Column(String(500), nullable=False)  # MinIO path
    packet_url = Column(Text)  # Pre-signed URL
    packet_type = Column(String(50), default='investor_memo')

    generated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    expires_at = Column(TIMESTAMP(timezone=True))
    template_version = Column(String(50))
    metadata = Column(JSONB)

    # Relationships
    prospect = relationship("ProspectQueue", back_populates="packets")
    score = relationship("PropertyScore", back_populates="packets")
    emails = relationship("EmailQueue", back_populates="packet")

    __table_args__ = (
        Index('idx_action_packets_prospect', 'prospect_id'),
        Index('idx_action_packets_score', 'score_id'),
        Index('idx_action_packets_generated', 'generated_at'),
    )


# ============================================================================
# Email Models (Phase 6)
# ============================================================================

class EmailCampaign(Base):
    """Email campaign management and tracking"""
    __tablename__ = "email_campaigns"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    template_name = Column(String(100), nullable=False)

    status = Column(String(50), default='draft')  # draft, scheduled, sending, sent, failed

    scheduled_at = Column(TIMESTAMP(timezone=True))
    started_at = Column(TIMESTAMP(timezone=True))
    completed_at = Column(TIMESTAMP(timezone=True))

    # Metrics
    total_recipients = Column(Integer, default=0)
    emails_sent = Column(Integer, default=0)
    emails_opened = Column(Integer, default=0)
    emails_clicked = Column(Integer, default=0)
    emails_bounced = Column(Integer, default=0)

    config = Column(JSONB)
    created_by = Column(Integer, ForeignKey('user_accounts.id', ondelete='SET NULL'))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    creator = relationship("UserAccount", back_populates="campaigns")

    __table_args__ = (
        Index('idx_email_campaigns_status', 'status'),
        Index('idx_email_campaigns_scheduled', 'scheduled_at'),
    )


class EmailQueue(Base):
    """Individual email tracking and status"""
    __tablename__ = "email_queue"

    id = Column(Integer, primary_key=True)
    packet_id = Column(Integer, ForeignKey('action_packets.id', ondelete='CASCADE'))

    recipient_email = Column(String(255), nullable=False)
    recipient_name = Column(String(255))
    subject = Column(String(500))

    status = Column(String(50), default='pending')  # pending, sent, failed, bounced

    # Tracking
    sent_at = Column(TIMESTAMP(timezone=True))
    opened_at = Column(TIMESTAMP(timezone=True))
    clicked_at = Column(TIMESTAMP(timezone=True))

    # SendGrid integration
    sendgrid_message_id = Column(String(255))
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    packet = relationship("ActionPacket", back_populates="emails")

    __table_args__ = (
        Index('idx_email_queue_status', 'status'),
        Index('idx_email_queue_recipient', 'recipient_email'),
        Index('idx_email_queue_packet', 'packet_id'),
        Index('idx_email_queue_created', 'created_at'),
    )


# ============================================================================
# Multi-Tenant Models (Phase 8)
# ============================================================================

class UserAccount(Base):
    """User authentication and profile management"""
    __tablename__ = "user_accounts"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    full_name = Column(String(255))
    organization = Column(String(255))
    role = Column(String(50), default='user')  # admin, user, viewer

    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String(255))

    password_reset_token = Column(String(255))
    password_reset_expires = Column(TIMESTAMP(timezone=True))

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    last_login = Column(TIMESTAMP(timezone=True))

    # Relationships
    owned_tenants = relationship("Tenant", back_populates="owner")
    audit_logs = relationship("AuditLog", back_populates="user")
    campaigns = relationship("EmailCampaign", back_populates="creator")

    __table_args__ = (
        Index('idx_user_accounts_email', 'email'),
        Index('idx_user_accounts_active', 'is_active'),
    )


class Tenant(Base):
    """Multi-tenant organization management"""
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True)
    tenant_name = Column(String(255), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False)

    owner_id = Column(Integer, ForeignKey('user_accounts.id', ondelete='SET NULL'))
    plan_tier = Column(String(50), default='free')  # free, professional, enterprise
    status = Column(String(50), default='active')  # active, suspended, deleted

    settings = Column(JSONB)  # Custom tenant configuration

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    owner = relationship("UserAccount", back_populates="owned_tenants")
    audit_logs = relationship("AuditLog", back_populates="tenant")

    __table_args__ = (
        Index('idx_tenants_slug', 'slug'),
        Index('idx_tenants_status', 'status'),
    )


class AuditLog(Base):
    """System-wide audit trail for compliance and debugging"""
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user_accounts.id', ondelete='SET NULL'))
    tenant_id = Column(Integer, ForeignKey('tenants.id', ondelete='SET NULL'))

    action = Column(String(100), nullable=False)
    resource_type = Column(String(100))
    resource_id = Column(Integer)

    details = Column(JSONB)
    ip_address = Column(INET)
    user_agent = Column(Text)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("UserAccount", back_populates="audit_logs")
    tenant = relationship("Tenant", back_populates="audit_logs")

    __table_args__ = (
        Index('idx_audit_log_user', 'user_id'),
        Index('idx_audit_log_tenant', 'tenant_id'),
        Index('idx_audit_log_created', 'created_at', postgresql_ops={'created_at': 'DESC'}),
        Index('idx_audit_log_action', 'action'),
    )
