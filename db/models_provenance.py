"""SQLAlchemy models for provenance and multi-tenant foundation

This module defines ORM models for:
- Multi-tenant structure
- Deterministic entity IDs (property, owner_entity)
- Field-level provenance tracking
- Score explainability
- Trust ledger
"""
from sqlalchemy import Column, String, Integer, Float, Numeric, Text, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from .models import Base


class Tenant(Base):
    """Tenant / Organization

    Represents a customer organization in the multi-tenant system.
    All data is scoped by tenant_id with RLS enforcement.
    """
    __tablename__ = 'tenant'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    plan_tier = Column(String(50), nullable=False, server_default='free')  # free, professional, enterprise
    status = Column(String(50), nullable=False, server_default='active', index=True)
    settings = Column(JSONB, server_default='{}')
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    properties = relationship('Property', back_populates='tenant', cascade='all, delete-orphan')
    owner_entities = relationship('OwnerEntity', back_populates='tenant', cascade='all, delete-orphan')
    field_provenances = relationship('FieldProvenance', back_populates='tenant', cascade='all, delete-orphan')
    scorecards = relationship('Scorecard', back_populates='tenant', cascade='all, delete-orphan')
    deals = relationship('Deal', back_populates='tenant', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Tenant(id={self.id}, name='{self.name}', slug='{self.slug}')>"


class Property(Base):
    """Property Entity

    Deterministic, tenant-scoped property identifier.
    Canonical address stored as JSONB for flexible parsing.
    """
    __tablename__ = 'property'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenant.id', ondelete='CASCADE'), nullable=False, index=True)
    canonical_address = Column(JSONB, nullable=False)
    parcel = Column(String(255), index=True)
    lat = Column(Float)
    lon = Column(Float)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    tenant = relationship('Tenant', back_populates='properties')
    owner_links = relationship('PropertyOwnerLink', back_populates='property', cascade='all, delete-orphan')
    scorecards = relationship('Scorecard', back_populates='property', cascade='all, delete-orphan')
    deals = relationship('Deal', back_populates='property', cascade='all, delete-orphan')

    # Indexes
    __table_args__ = (
        Index('idx_property_parcel', 'tenant_id', 'parcel'),
        Index('idx_property_location', 'tenant_id', 'lat', 'lon'),
    )

    def __repr__(self):
        return f"<Property(id={self.id}, parcel='{self.parcel}')>"


class OwnerEntity(Base):
    """Owner Entity

    Deterministic owner identifier (person or company).
    Uses identity_hash for deduplication.
    """
    __tablename__ = 'owner_entity'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenant.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # 'person' or 'company'
    identity_hash = Column(String(64), index=True)  # SHA256 for deduplication
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    tenant = relationship('Tenant', back_populates='owner_entities')
    property_links = relationship('PropertyOwnerLink', back_populates='owner', cascade='all, delete-orphan')

    # Constraints
    __table_args__ = (
        CheckConstraint("type IN ('person', 'company')", name='owner_entity_type_check'),
        Index('idx_owner_entity_identity', 'tenant_id', 'identity_hash'),
    )

    def __repr__(self):
        return f"<OwnerEntity(id={self.id}, name='{self.name}', type='{self.type}')>"


class PropertyOwnerLink(Base):
    """Property-Owner Relationship

    Links properties to owners with role and confidence.
    """
    __tablename__ = 'property_owner_link'

    property_id = Column(UUID(as_uuid=True), ForeignKey('property.id', ondelete='CASCADE'), primary_key=True)
    owner_entity_id = Column(UUID(as_uuid=True), ForeignKey('owner_entity.id', ondelete='CASCADE'), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenant.id', ondelete='CASCADE'), nullable=False, index=True)
    role = Column(String(100))  # 'owner', 'trustee', 'beneficiary', etc.
    confidence = Column(Numeric(5, 2))  # 0.00 to 1.00
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    property = relationship('Property', back_populates='owner_links')
    owner = relationship('OwnerEntity', back_populates='property_links')

    def __repr__(self):
        return f"<PropertyOwnerLink(property_id={self.property_id}, owner_id={self.owner_entity_id})>"


class FieldProvenance(Base):
    """Field-Level Provenance Tracking

    Tracks the source, method, and confidence for every field value.
    Enables "Deal Genome" hover tooltips and history tracking.
    """
    __tablename__ = 'field_provenance'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenant.id', ondelete='CASCADE'), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False)  # 'property', 'owner', 'deal', etc.
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    field_path = Column(String(255), nullable=False)  # JSON path notation
    value = Column(JSONB, nullable=False)
    source_system = Column(String(100))  # 'census_api', 'fsbo_scraper', 'manual'
    source_url = Column(Text)
    method = Column(String(50))  # 'scrape', 'api', 'manual', 'computed'
    confidence = Column(Numeric(5, 2))  # 0.00 to 1.00
    version = Column(Integer, nullable=False)  # Incremental per field
    extracted_at = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    tenant = relationship('Tenant', back_populates='field_provenances')

    # Indexes
    __table_args__ = (
        Index('idx_field_provenance_entity', 'tenant_id', 'entity_type', 'entity_id'),
        Index('idx_field_provenance_field', 'tenant_id', 'entity_type', 'entity_id', 'field_path'),
        Index('idx_field_provenance_version', 'tenant_id', 'entity_type', 'entity_id', 'field_path', 'version'),
    )

    def __repr__(self):
        return f"<FieldProvenance(entity_type='{self.entity_type}', field_path='{self.field_path}', version={self.version})>"


class Scorecard(Base):
    """Property Scorecard

    ML-generated score for a property with grade and confidence.
    """
    __tablename__ = 'scorecard'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenant.id', ondelete='CASCADE'), nullable=False, index=True)
    property_id = Column(UUID(as_uuid=True), ForeignKey('property.id', ondelete='CASCADE'), nullable=False)
    model_version = Column(String(100), nullable=False)
    score = Column(Numeric(5, 2), nullable=False)  # 0-100
    grade = Column(String(10))  # A, B, C, D, F
    confidence = Column(Numeric(5, 2))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    tenant = relationship('Tenant', back_populates='scorecards')
    property = relationship('Property', back_populates='scorecards')
    explainability = relationship('ScoreExplainability', back_populates='scorecard', uselist=False, cascade='all, delete-orphan')

    # Indexes
    __table_args__ = (
        Index('idx_scorecard_property', 'tenant_id', 'property_id'),
        Index('idx_scorecard_score', 'tenant_id', 'score'),
    )

    def __repr__(self):
        return f"<Scorecard(id={self.id}, score={self.score}, grade='{self.grade}')>"


class ScoreExplainability(Base):
    """Score Explainability

    SHAP values, drivers, and counterfactuals for a scorecard.
    Enables "What-If" analysis and score transparency.
    """
    __tablename__ = 'score_explainability'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scorecard_id = Column(UUID(as_uuid=True), ForeignKey('scorecard.id', ondelete='CASCADE'), nullable=False, unique=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenant.id', ondelete='CASCADE'), nullable=False, index=True)
    shap_values = Column(JSONB, nullable=False)  # Feature -> SHAP value mapping
    drivers = Column(JSONB, nullable=False)  # Top positive/negative drivers
    counterfactuals = Column(JSONB)  # Minimal changes to flip grade
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    scorecard = relationship('Scorecard', back_populates='explainability')

    def __repr__(self):
        return f"<ScoreExplainability(scorecard_id={self.scorecard_id})>"


class Deal(Base):
    """Deal / Pipeline Stage

    Represents a property in the sales pipeline.
    """
    __tablename__ = 'deal'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenant.id', ondelete='CASCADE'), nullable=False, index=True)
    property_id = Column(UUID(as_uuid=True), ForeignKey('property.id', ondelete='CASCADE'), nullable=False)
    stage = Column(String(50), nullable=False, server_default='lead')
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    tenant = relationship('Tenant', back_populates='deals')
    property = relationship('Property', back_populates='deals')
    packet_events = relationship('PacketEvent', back_populates='deal', cascade='all, delete-orphan')

    # Constraints
    __table_args__ = (
        CheckConstraint("stage IN ('lead', 'qualified', 'offer', 'contract', 'closed', 'lost')", name='deal_stage_check'),
        Index('idx_deal_property', 'tenant_id', 'property_id'),
        Index('idx_deal_stage', 'tenant_id', 'stage'),
    )

    def __repr__(self):
        return f"<Deal(id={self.id}, stage='{self.stage}')>"


class PacketEvent(Base):
    """Packet Telemetry Event

    Tracks opens, clicks, downloads of investor memo packets.
    """
    __tablename__ = 'packet_event'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenant.id', ondelete='CASCADE'), nullable=False, index=True)
    deal_id = Column(UUID(as_uuid=True), ForeignKey('deal.id', ondelete='CASCADE'), nullable=False)
    type = Column(String(50), nullable=False)  # 'generated', 'opened', 'clicked', 'downloaded', 'shared'
    meta = Column(JSONB, server_default='{}')
    occurred_at = Column(TIMESTAMP(timezone=True), nullable=False)

    # Relationships
    deal = relationship('Deal', back_populates='packet_events')

    # Constraints
    __table_args__ = (
        CheckConstraint("type IN ('generated', 'opened', 'clicked', 'downloaded', 'shared')", name='packet_event_type_check'),
        Index('idx_packet_event_deal', 'tenant_id', 'deal_id'),
        Index('idx_packet_event_occurred', 'tenant_id', 'occurred_at'),
    )

    def __repr__(self):
        return f"<PacketEvent(id={self.id}, type='{self.type}')>"


class ContactSuppression(Base):
    """Contact Suppression Registry

    Tracks opt-outs and bounces per channel.
    """
    __tablename__ = 'contact_suppression'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenant.id', ondelete='CASCADE'), nullable=False, index=True)
    channel = Column(String(50), nullable=False)  # 'email', 'sms', 'voice', 'mail'
    identity_hash = Column(String(64), nullable=False)  # SHA256 of contact info
    reason = Column(String(255))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    # Constraints
    __table_args__ = (
        CheckConstraint("channel IN ('email', 'sms', 'voice', 'mail')", name='contact_suppression_channel_check'),
        Index('idx_contact_suppression_lookup', 'tenant_id', 'channel', 'identity_hash'),
    )

    def __repr__(self):
        return f"<ContactSuppression(channel='{self.channel}', reason='{self.reason}')>"


class EvidenceEvent(Base):
    """Trust Ledger / Evidence Event

    Immutable audit trail for rationale, consent, overrides, and claims.
    """
    __tablename__ = 'evidence_event'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenant.id', ondelete='CASCADE'), nullable=False, index=True)
    subject_type = Column(String(50))  # 'property', 'deal', 'offer', etc.
    subject_id = Column(UUID(as_uuid=True))
    kind = Column(String(100), nullable=False)  # 'comps_rationale', 'consent', 'override', 'claim'
    summary = Column(Text)
    uri = Column(Text)  # MinIO path to supporting documents
    created_by = Column(UUID(as_uuid=True))  # User ID
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    # Indexes
    __table_args__ = (
        Index('idx_evidence_event_subject', 'tenant_id', 'subject_type', 'subject_id'),
        Index('idx_evidence_event_created', 'tenant_id', 'created_at'),
    )

    def __repr__(self):
        return f"<EvidenceEvent(id={self.id}, kind='{self.kind}')>"
