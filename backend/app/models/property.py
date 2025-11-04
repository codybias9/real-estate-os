"""Property, listing, and related models."""
from sqlalchemy import (
    Column, Integer, String, Text, Numeric, Boolean, ForeignKey,
    DateTime, JSON, Enum as SQLEnum, Index
)
from sqlalchemy.orm import relationship
import enum
from backend.app.core.database import Base
from .base import TimestampMixin, SoftDeleteMixin


class PropertyType(str, enum.Enum):
    """Property type enumeration."""
    SINGLE_FAMILY = "single_family"
    MULTI_FAMILY = "multi_family"
    CONDO = "condo"
    TOWNHOUSE = "townhouse"
    LAND = "land"
    COMMERCIAL = "commercial"
    OTHER = "other"


class PropertyStatus(str, enum.Enum):
    """Property status enumeration."""
    ACTIVE = "active"
    PENDING = "pending"
    SOLD = "sold"
    OFF_MARKET = "off_market"
    ARCHIVED = "archived"


class Property(Base, TimestampMixin, SoftDeleteMixin):
    """Core property model."""
    __tablename__ = 'properties'

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)

    # Address
    address_line1 = Column(String(255), nullable=False)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(50), nullable=False, index=True)
    zip_code = Column(String(20), nullable=False, index=True)
    country = Column(String(50), default='USA', nullable=False)

    # Geolocation
    latitude = Column(Numeric(10, 7), nullable=True)
    longitude = Column(Numeric(10, 7), nullable=True)

    # Property details
    property_type = Column(SQLEnum(PropertyType), nullable=False, index=True)
    status = Column(SQLEnum(PropertyStatus), default=PropertyStatus.ACTIVE, nullable=False, index=True)
    bedrooms = Column(Integer, nullable=True)
    bathrooms = Column(Numeric(3, 1), nullable=True)
    square_feet = Column(Integer, nullable=True)
    lot_size = Column(Integer, nullable=True)
    year_built = Column(Integer, nullable=True)

    # Pricing
    list_price = Column(Numeric(12, 2), nullable=True, index=True)
    sale_price = Column(Numeric(12, 2), nullable=True)
    estimated_value = Column(Numeric(12, 2), nullable=True)

    # Metadata
    description = Column(Text, nullable=True)
    features = Column(JSON, default=list)  # ["pool", "garage", "renovated"]
    notes = Column(Text, nullable=True)
    external_id = Column(String(100), nullable=True, index=True)  # MLS or external system ID
    source = Column(String(100), nullable=True)  # Where property came from

    # Relationships
    images = relationship('PropertyImage', back_populates='property', cascade='all, delete-orphan', order_by='PropertyImage.display_order')
    documents = relationship('PropertyDocument', back_populates='property', cascade='all, delete-orphan')
    valuations = relationship('PropertyValuation', back_populates='property', cascade='all, delete-orphan')
    metrics = relationship('PropertyMetrics', back_populates='property', uselist=False, cascade='all, delete-orphan')
    history = relationship('PropertyHistory', back_populates='property', cascade='all, delete-orphan', order_by='PropertyHistory.event_date.desc()')
    listings = relationship('Listing', back_populates='property', cascade='all, delete-orphan')

    __table_args__ = (
        Index('idx_property_location', 'city', 'state', 'zip_code'),
        Index('idx_property_price_type', 'property_type', 'list_price'),
    )


class PropertyImage(Base, TimestampMixin):
    """Property image model."""
    __tablename__ = 'property_images'

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)

    url = Column(String(500), nullable=False)
    storage_key = Column(String(500), nullable=True)  # S3/MinIO key
    caption = Column(String(255), nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)

    # Image metadata
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    file_size = Column(Integer, nullable=True)  # bytes
    mime_type = Column(String(50), nullable=True)

    # Relationships
    property = relationship('Property', back_populates='images')


class PropertyDocument(Base, TimestampMixin, SoftDeleteMixin):
    """Property document model (contracts, disclosures, etc.)."""
    __tablename__ = 'property_documents'

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)

    name = Column(String(255), nullable=False)
    document_type = Column(String(100), nullable=False)  # contract, disclosure, inspection, etc.
    storage_key = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(50), nullable=True)
    uploaded_by_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # Relationships
    property = relationship('Property', back_populates='documents')


class PropertyValuation(Base, TimestampMixin):
    """Automated property valuation model."""
    __tablename__ = 'property_valuations'

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)

    estimated_value = Column(Numeric(12, 2), nullable=False)
    confidence_score = Column(Numeric(3, 2), nullable=True)  # 0.0 to 1.0
    valuation_date = Column(DateTime(timezone=True), nullable=False)
    source = Column(String(100), nullable=False)  # 'internal', 'zillow', 'redfin', etc.
    model_version = Column(String(50), nullable=True)

    # Valuation details
    comparables = Column(JSON, default=list)  # Comparable properties used
    adjustments = Column(JSON, default=dict)  # Value adjustments made
    metadata = Column(JSON, default=dict)

    # Relationships
    property = relationship('Property', back_populates='valuations')


class PropertyMetrics(Base, TimestampMixin):
    """Calculated metrics and analytics for a property."""
    __tablename__ = 'property_metrics'

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False, unique=True)

    # Engagement metrics
    views = Column(Integer, default=0, nullable=False)
    inquiries = Column(Integer, default=0, nullable=False)
    favorites = Column(Integer, default=0, nullable=False)

    # Performance metrics
    days_on_market = Column(Integer, default=0, nullable=False)
    price_changes = Column(Integer, default=0, nullable=False)

    # Calculated scores
    investment_score = Column(Numeric(3, 2), nullable=True)  # 0.0 to 1.0
    rental_yield = Column(Numeric(5, 2), nullable=True)  # Percentage
    cap_rate = Column(Numeric(5, 2), nullable=True)  # Percentage

    # Relationships
    property = relationship('Property', back_populates='metrics')


class PropertyHistory(Base, TimestampMixin):
    """Property ownership and transaction history."""
    __tablename__ = 'property_history'

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)

    event_type = Column(String(50), nullable=False, index=True)  # 'sale', 'listing', 'price_change', etc.
    event_date = Column(DateTime(timezone=True), nullable=False, index=True)

    # Transaction details
    sale_price = Column(Numeric(12, 2), nullable=True)
    buyer_name = Column(String(255), nullable=True)
    seller_name = Column(String(255), nullable=True)

    # Event details
    description = Column(Text, nullable=True)
    metadata = Column(JSON, default=dict)

    # Relationships
    property = relationship('Property', back_populates='history')


class Listing(Base, TimestampMixin, SoftDeleteMixin):
    """Active listing model."""
    __tablename__ = 'listings'

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey('properties.id', ondelete='CASCADE'), nullable=False)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)

    listing_agent_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    mls_number = Column(String(100), nullable=True, index=True)

    # Listing details
    list_price = Column(Numeric(12, 2), nullable=False, index=True)
    status = Column(String(50), default='active', nullable=False, index=True)
    listed_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Marketing
    public_remarks = Column(Text, nullable=True)
    private_remarks = Column(Text, nullable=True)
    showing_instructions = Column(Text, nullable=True)

    # Relationships
    property = relationship('Property', back_populates='listings')
    snapshots = relationship('ListingSnapshot', back_populates='listing', cascade='all, delete-orphan')


class ListingSnapshot(Base, TimestampMixin):
    """Historical snapshot of listing state."""
    __tablename__ = 'listing_snapshots'

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey('listings.id', ondelete='CASCADE'), nullable=False)

    snapshot_date = Column(DateTime(timezone=True), nullable=False, index=True)
    list_price = Column(Numeric(12, 2), nullable=False)
    status = Column(String(50), nullable=False)
    data = Column(JSON, default=dict)  # Full listing state at snapshot time

    # Relationships
    listing = relationship('Listing', back_populates='snapshots')
