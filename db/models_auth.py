"""Authentication database models

Tables:
- auth_users: User accounts with email/password (separate from provenance tenants)
- auth_api_keys: Service-to-service API keys

Note: We reuse existing 'tenant' table from models_provenance.py for tenant_id references
"""

from sqlalchemy import (
    Column, String, DateTime, Boolean, ARRAY, Text,
    ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from .models import Base


# Note: Tenant model exists in models_provenance.py - we reference it via tenant_id


class User(Base):
    """User account model for authentication

    Separate from user_accounts in models.py to support new auth architecture.
    References tenant.id (UUID) from models_provenance.py
    """
    __tablename__ = "auth_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)  # bcrypt hash
    roles = Column(ARRAY(String), nullable=False, default=list)  # ['owner', 'admin', 'analyst']
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    last_login = Column(TIMESTAMP(timezone=True), nullable=True)

    # OAuth fields (for OIDC integration)
    oidc_provider = Column(String(50), nullable=True)  # 'keycloak', 'auth0', etc.
    oidc_sub = Column(String(255), nullable=True)  # Subject from OIDC provider

    __table_args__ = (
        Index("idx_auth_users_email", "email"),
        Index("idx_auth_users_tenant_id", "tenant_id"),
        Index("idx_auth_users_oidc_sub", "oidc_sub"),
    )


class APIKey(Base):
    """API key for service-to-service authentication"""
    __tablename__ = "auth_api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenant.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    key_hash = Column(String(255), nullable=False)  # bcrypt hash of full key
    key_prefix = Column(String(8), nullable=False)  # First 8 chars for identification
    roles = Column(ARRAY(String), nullable=False, default=list)  # ['service']
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(TIMESTAMP(timezone=True), nullable=True)
    last_used = Column(TIMESTAMP(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_auth_api_keys_key_prefix", "key_prefix"),
        Index("idx_auth_api_keys_tenant_id", "tenant_id"),
        Index("idx_auth_api_keys_is_active", "is_active"),
    )
