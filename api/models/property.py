"""Property-related models."""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime, Numeric, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from .base import BaseModel, SoftDeleteMixin
import enum


class PropertyStatus(str, enum.Enum):
    """Property status enum."""
    ACTIVE = "active"
    PENDING = "pending"
    SOLD = "sold"
    OFF_MARKET = "off_market"
    ARCHIVED = "archived"


class PropertyType(str, enum.Enum):
    """Property type enum."""
    SINGLE_FAMILY = "single_family"
    MULTI_FAMILY = "multi_family"
    CONDO = "condo"
    TOWNHOUSE = "townhouse"
    LAND = "land"
    COMMERCIAL = "commercial"
    MIXED_USE = "mixed_use"
    OTHER = "other"


class Property(BaseModel, SoftDeleteMixin):
    """Property model."""

    __tablename__ = "properties"

    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)

    # Basic Info
    address = Column(String(500), nullable=False)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(100), nullable=False, index=True)
    zip_code = Column(String(20), nullable=False, index=True)
    country = Column(String(100), nullable=False, default="USA")
    latitude = Column(Numeric(10, 7), nullable=True)
    longitude = Column(Numeric(10, 7), nullable=True)

    # Property Details
    property_type = Column(SQLEnum(PropertyType), nullable=False, index=True)
    status = Column(SQLEnum(PropertyStatus), nullable=False, default=PropertyStatus.ACTIVE, index=True)
    bedrooms = Column(Integer, nullable=True)
    bathrooms = Column(Numeric(3, 1), nullable=True)
    square_feet = Column(Integer, nullable=True)
    lot_size = Column(Numeric(10, 2), nullable=True)
    year_built = Column(Integer, nullable=True)

    # Financial
    list_price = Column(Numeric(12, 2), nullable=True)
    sale_price = Column(Numeric(12, 2), nullable=True)
    estimated_value = Column(Numeric(12, 2), nullable=True)
    tax_assessed_value = Column(Numeric(12, 2), nullable=True)
    annual_taxes = Column(Numeric(10, 2), nullable=True)
    hoa_fees = Column(Numeric(10, 2), nullable=True)

    # Listing Info
    mls_number = Column(String(100), nullable=True, index=True)
    listing_agent = Column(String(255), nullable=True)
    listing_date = Column(DateTime(timezone=True), nullable=True)
    days_on_market = Column(Integer, nullable=True)

    # Description
    description = Column(Text, nullable=True)
    features = Column(JSON, nullable=True)  # amenities, parking, etc.

    # Owner Info
    owner_name = Column(String(255), nullable=True)
    owner_phone = Column(String(50), nullable=True)
    owner_email = Column(String(255), nullable=True)

    # Custom fields
    custom_fields = Column(JSON, nullable=True, default=dict)

    # Relationships
    organization = relationship("Organization", back_populates="properties")
    images = relationship("PropertyImage", back_populates="property", cascade="all, delete-orphan")
    valuations = relationship("PropertyValuation", back_populates="property", cascade="all, delete-orphan")
    notes = relationship("PropertyNote", back_populates="property", cascade="all, delete-orphan")
    activities = relationship("PropertyActivity", back_populates="property", cascade="all, delete-orphan")
    leads = relationship("Lead", back_populates="property")


class PropertyImage(BaseModel):
    """Property image model."""

    __tablename__ = "property_images"

    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(String(1000), nullable=False)
    thumbnail_url = Column(String(1000), nullable=True)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    is_primary = Column(Boolean, default=False, nullable=False)

    # Relationships
    property = relationship("Property", back_populates="images")


class PropertyValuation(BaseModel):
    """Property valuation history."""

    __tablename__ = "property_valuations"

    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    value = Column(Numeric(12, 2), nullable=False)
    source = Column(String(100), nullable=False)  # Zillow, Redfin, Manual, etc.
    confidence_score = Column(Numeric(3, 2), nullable=True)  # 0.00 to 1.00
    valuation_date = Column(DateTime(timezone=True), nullable=False)
    metadata = Column(JSON, nullable=True)

    # Relationships
    property = relationship("Property", back_populates="valuations")


class PropertyNote(BaseModel, SoftDeleteMixin):
    """Notes on properties."""

    __tablename__ = "property_notes"

    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    content = Column(Text, nullable=False)
    is_pinned = Column(Boolean, default=False, nullable=False)

    # Relationships
    property = relationship("Property", back_populates="notes")
    created_by = relationship("User")


class PropertyActivity(BaseModel):
    """Activity log for properties."""

    __tablename__ = "property_activities"

    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    activity_type = Column(String(100), nullable=False, index=True)  # viewed, updated, contacted, etc.
    description = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)

    # Relationships
    property = relationship("Property", back_populates="activities")
    user = relationship("User")
