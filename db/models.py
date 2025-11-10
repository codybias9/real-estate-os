"""Database models for Real Estate OS."""
from sqlalchemy import Column, Integer, String, TIMESTAMP, Boolean, DECIMAL, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import func
import uuid

Base = declarative_base()


class Tenant(Base):
    """Tenant model for multi-tenancy isolation."""
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    name = Column(String(255), nullable=False)
    subscription_tier = Column(String(50), default='trial')
    settings = Column(JSONB, default={})
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Relationships
    teams = relationship("Team", back_populates="tenant")
    users = relationship("User", back_populates="tenant")


class Team(Base):
    """Team model for organizing users within a tenant."""
    __tablename__ = "teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    name = Column(String(255), nullable=False)
    subscription_tier = Column(String(50), default='trial')
    monthly_budget_cap = Column(DECIMAL(10, 2), default=500.00)
    settings = Column(JSONB, default={})
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="teams")
    users = relationship("User", back_populates="team")


class User(Base):
    """User model with authentication and tenant/team relationships."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    team_id = Column(UUID(as_uuid=True), ForeignKey('teams.id'), nullable=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default='agent')
    is_active = Column(Boolean, default=True)
    settings = Column(JSONB, default={})
    last_login_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    team = relationship("Team", back_populates="users")


class Property(Base):
    """Property model for real estate listings."""
    __tablename__ = "properties"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False)
    address = Column(String(500), nullable=False)
    city = Column(String(100))
    state = Column(String(50))
    zip_code = Column(String(20))
    price = Column(DECIMAL(12, 2))
    bedrooms = Column(Integer)
    bathrooms = Column(DECIMAL(3, 1))
    square_feet = Column(Integer)
    property_type = Column(String(50))
    listing_url = Column(Text)
    description = Column(Text)
    metadata = Column(JSONB, default={})
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)


class Ping(Base):
    """Simple ping model for health checks."""
    __tablename__ = "ping"

    id = Column(Integer, primary_key=True)
    ts = Column(TIMESTAMP(timezone=True), server_default=func.now())
