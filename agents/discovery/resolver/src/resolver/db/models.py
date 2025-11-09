"""
SQLAlchemy models for Discovery.Resolver database persistence
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Tenant(Base):
    """Tenant model for multi-tenancy"""

    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    properties = relationship("Property", back_populates="tenant", cascade="all, delete-orphan")


class User(Base):
    """User model with tenant association"""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")


class Property(Base):
    """Property model with full metadata and scoring"""

    __tablename__ = "properties"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Property identifiers
    apn = Column(String(50), nullable=True, index=True)
    apn_hash = Column(String(64), nullable=True, index=True)

    # Address fields
    street = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True, index=True)
    state = Column(String(2), nullable=True, index=True)
    zip_code = Column(String(10), nullable=True, index=True)

    # Geographic coordinates
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Owner information
    owner_name = Column(String(255), nullable=True)
    owner_type = Column(String(50), nullable=True)

    # Property attributes
    bedrooms = Column(Integer, nullable=True)
    bathrooms = Column(Float, nullable=True)
    square_feet = Column(Integer, nullable=True)
    year_built = Column(Integer, nullable=True)
    lot_size = Column(Float, nullable=True)

    # Scoring data
    score = Column(Integer, nullable=True)
    score_reasons = Column(JSON, nullable=True)  # Array of score reason objects

    # Status and extra metadata
    status = Column(String(50), nullable=False, default="discovered", index=True)
    extra_metadata = Column(JSON, nullable=True)  # Flexible key-value storage

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="properties")

    def __repr__(self):
        return f"<Property(id={self.id}, apn={self.apn}, address={self.street}, {self.city})>"
