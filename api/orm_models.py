"""
SQLAlchemy ORM models mapping to database tables from Migration 001.
"""
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean, Text,
    ForeignKey, Numeric, CheckConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from geoalchemy2 import Geometry
from sqlalchemy.sql import func
from datetime import datetime
import uuid

from api.database import Base


class Tenant(Base):
    """Tenant model (root of multi-tenancy)."""
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    plan = Column(String(50), default="trial")
    status = Column(String(50), default="active")
    settings = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class User(Base):
    """User model with RBAC."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="user")  # admin, analyst, operator, user
    permissions = Column(JSONB, default=[])
    status = Column(String(50), default="active")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_users_tenant_email", "tenant_id", "email", unique=True),
        Index("idx_users_tenant_role", "tenant_id", "role"),
    )


class Property(Base):
    """Property model with PostGIS geometry."""
    __tablename__ = "properties"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    # Address fields
    address = Column(Text, nullable=False)
    address_normalized = Column(Text)
    address_hash = Column(String(16))
    address_components = Column(JSONB)

    # Geolocation
    latitude = Column(Numeric(10, 7))
    longitude = Column(Numeric(11, 7))
    geom = Column(Geometry("POINT", srid=4326))

    # Property details
    property_type = Column(String(50), nullable=False)
    bedrooms = Column(Integer)
    bathrooms = Column(Numeric(4, 1))
    sqft = Column(Integer)
    price = Column(Numeric(15, 2))

    # Additional fields
    hazards = Column(JSONB)
    status = Column(String(50), default="active")
    property_metadata = Column(JSONB, default={})  # Renamed from 'metadata' to avoid SQLAlchemy conflict
    description = Column(Text)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_properties_tenant", "tenant_id"),
        Index("idx_properties_status", "tenant_id", "status"),
        Index("idx_properties_type", "tenant_id", "property_type"),
        Index("idx_properties_geom", "geom", postgresql_using="gist"),
        Index("idx_properties_address_hash", "address_hash"),
    )


class Ownership(Base):
    """Property ownership tracking."""
    __tablename__ = "ownership"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)

    owner_name = Column(String(255), nullable=False)
    owner_type = Column(String(50))  # individual, llc, trust, corporation
    ownership_pct = Column(Numeric(5, 2), default=100.00)
    acquisition_date = Column(DateTime(timezone=True))
    acquisition_price = Column(Numeric(15, 2))

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_ownership_tenant_property", "tenant_id", "property_id"),
        CheckConstraint("ownership_pct >= 0 AND ownership_pct <= 100", name="ck_ownership_pct"),
    )


class Prospect(Base):
    """Deal pipeline prospects."""
    __tablename__ = "prospects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)

    # Source and status
    source = Column(String(100), nullable=False)  # scraper, manual, api, referral
    status = Column(String(50), default="new")  # new, contacted, qualified, negotiating, won, lost

    # Owner contact info
    owner_name = Column(String(255))
    owner_email = Column(String(255))
    owner_phone = Column(String(50))

    # Scoring
    motivation_score = Column(Numeric(3, 2))  # 0.00 to 1.00
    enriched_at = Column(DateTime(timezone=True))
    last_contacted_at = Column(DateTime(timezone=True))

    # Notes and metadata
    notes = Column(Text)
    prospect_metadata = Column(JSONB, default={})  # Renamed from 'metadata' to avoid SQLAlchemy conflict

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_prospects_tenant_status", "tenant_id", "status"),
        Index("idx_prospects_property", "property_id"),
        CheckConstraint("motivation_score >= 0 AND motivation_score <= 1", name="ck_motivation_score"),
    )


class Lease(Base):
    """Lease agreements and rent rolls."""
    __tablename__ = "leases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)

    # Tenant info
    tenant_name = Column(String(255), nullable=False)
    tenant_email = Column(String(255))
    tenant_phone = Column(String(50))

    # Lease terms
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    monthly_rent = Column(Numeric(10, 2), nullable=False)
    security_deposit = Column(Numeric(10, 2))
    status = Column(String(50), default="active")  # active, expired, terminated

    # Additional terms
    terms = Column(JSONB, default={})
    notes = Column(Text)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_leases_tenant_property", "tenant_id", "property_id"),
        Index("idx_leases_status", "tenant_id", "status"),
        Index("idx_leases_dates", "start_date", "end_date"),
    )


class Document(Base):
    """Document storage metadata (MinIO integration)."""
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=True)

    # Document details
    filename = Column(String(255), nullable=False)
    doc_type = Column(String(100), nullable=False)  # lease, deed, inspection, photo, etc.
    mime_type = Column(String(100))
    file_size = Column(Integer)  # bytes

    # Storage
    storage_path = Column(Text, nullable=False)  # MinIO path: {tenant_id}/documents/{id}/{filename}
    storage_bucket = Column(String(100), default="documents")

    # Indexing
    ocr_text = Column(Text)  # Extracted text from OCR
    tags = Column(JSONB, default=[])
    document_metadata = Column(JSONB, default={})  # Renamed from 'metadata' to avoid SQLAlchemy conflict

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_documents_tenant_type", "tenant_id", "doc_type"),
        Index("idx_documents_property", "property_id"),
    )


class Score(Base):
    """ML model outputs and scoring."""
    __tablename__ = "scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)

    # Score details
    score_type = Column(String(100), nullable=False)  # comp_critic, dcf, arv, motivation, etc.
    score_value = Column(Numeric(15, 2))
    confidence = Column(Numeric(3, 2))  # 0.00 to 1.00
    model_version = Column(String(50))

    # Context
    parameters = Column(JSONB, default={})
    results = Column(JSONB, default={})
    computed_at = Column(DateTime(timezone=True), nullable=False)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_scores_tenant_property", "tenant_id", "property_id"),
        Index("idx_scores_type", "score_type"),
        Index("idx_scores_computed", "computed_at"),
    )


class Offer(Base):
    """Offer packets and negotiations."""
    __tablename__ = "offers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)
    prospect_id = Column(UUID(as_uuid=True), ForeignKey("prospects.id", ondelete="SET NULL"), nullable=True)

    # Offer details
    offer_price = Column(Numeric(15, 2), nullable=False)
    earnest_money = Column(Numeric(15, 2))
    closing_days = Column(Integer, nullable=False)
    status = Column(String(50), default="draft")  # draft, sent, accepted, rejected, expired

    # Terms
    contingencies = Column(JSONB, default=[])
    terms = Column(JSONB, default={})
    notes = Column(Text)

    # Timeline
    sent_at = Column(DateTime(timezone=True))
    responded_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_offers_tenant_status", "tenant_id", "status"),
        Index("idx_offers_property", "property_id"),
        Index("idx_offers_prospect", "prospect_id"),
    )


class EventAudit(Base):
    """Audit trail for all changes (compliance)."""
    __tablename__ = "events_audit"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)  # Not FK to allow tenant deletion audit

    # Event details
    event_type = Column(String(100), nullable=False)  # create, update, delete, login, etc.
    entity_type = Column(String(100))  # property, prospect, offer, etc.
    entity_id = Column(UUID(as_uuid=True))

    # Actor
    user_id = Column(UUID(as_uuid=True))
    ip_address = Column(String(45))  # IPv6 max length

    # Changes
    old_values = Column(JSONB)
    new_values = Column(JSONB)
    event_metadata = Column(JSONB, default={})  # Renamed from 'metadata' to avoid SQLAlchemy conflict

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_events_tenant", "tenant_id"),
        Index("idx_events_type", "event_type"),
        Index("idx_events_entity", "entity_type", "entity_id"),
        Index("idx_events_user", "user_id"),
        Index("idx_events_created", "created_at"),
    )
