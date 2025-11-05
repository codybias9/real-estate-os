"""Property models."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Numeric, Enum as SQLEnum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum
from ..database import Base


class PropertyType(str, Enum):
    """Property type enum."""
    SINGLE_FAMILY = "single_family"
    MULTI_FAMILY = "multi_family"
    CONDO = "condo"
    TOWNHOUSE = "townhouse"
    LAND = "land"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    MIXED_USE = "mixed_use"


class PropertyStatus(str, Enum):
    """Property status enum."""
    AVAILABLE = "available"
    UNDER_CONTRACT = "under_contract"
    SOLD = "sold"
    RENTED = "rented"
    OFF_MARKET = "off_market"


class Property(Base):
    """Property model."""

    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Address
    address = Column(String(500), nullable=False)
    city = Column(String(100), nullable=False, index=True)
    state = Column(String(50), nullable=False, index=True)
    zip_code = Column(String(20), nullable=False, index=True)
    country = Column(String(50), default="USA", nullable=False)
    latitude = Column(Numeric(10, 7), nullable=True)
    longitude = Column(Numeric(10, 7), nullable=True)

    # Property Details
    property_type = Column(SQLEnum(PropertyType), nullable=False, index=True)
    status = Column(SQLEnum(PropertyStatus), default=PropertyStatus.AVAILABLE, nullable=False, index=True)
    price = Column(Numeric(12, 2), nullable=True)
    bedrooms = Column(Integer, nullable=True)
    bathrooms = Column(Numeric(3, 1), nullable=True)
    square_feet = Column(Integer, nullable=True)
    lot_size = Column(Integer, nullable=True)
    year_built = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    features = Column(Text, nullable=True)  # JSON array
    metadata = Column(Text, nullable=True)  # JSON object

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="properties")
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_properties")
    images = relationship("PropertyImage", back_populates="property", cascade="all, delete-orphan")
    valuations = relationship("PropertyValuation", back_populates="property", cascade="all, delete-orphan")
    notes = relationship("PropertyNote", back_populates="property", cascade="all, delete-orphan")
    activities = relationship("PropertyActivity", back_populates="property", cascade="all, delete-orphan")
    deals = relationship("Deal", back_populates="property")
    portfolios = relationship("Portfolio", secondary="portfolio_properties", back_populates="properties")


class PropertyImage(Base):
    """Property image model."""

    __tablename__ = "property_images"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    url = Column(String(1000), nullable=False)
    title = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    order = Column(Integer, default=0, nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    property = relationship("Property", back_populates="images")


class PropertyValuation(Base):
    """Property valuation model for tracking historical values."""

    __tablename__ = "property_valuations"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    value = Column(Numeric(12, 2), nullable=False)
    valuation_date = Column(DateTime(timezone=True), nullable=False, index=True)
    source = Column(String(100), nullable=True)  # e.g., 'manual', 'zillow', 'appraisal'
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    property = relationship("Property", back_populates="valuations")


class PropertyNote(Base):
    """Property note model for collaboration."""

    __tablename__ = "property_notes"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    property = relationship("Property", back_populates="notes")


class PropertyActivity(Base):
    """Property activity model for tracking actions."""

    __tablename__ = "property_activities"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    activity_type = Column(String(50), nullable=False, index=True)  # e.g., 'viewing', 'offer', 'inspection'
    description = Column(Text, nullable=False)
    metadata = Column(Text, nullable=True)  # JSON object
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    property = relationship("Property", back_populates="activities")
