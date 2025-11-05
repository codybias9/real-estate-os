"""System models for infrastructure features."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from ..database import Base


class IdempotencyKey(Base):
    """Idempotency key model for preventing duplicate requests."""

    __tablename__ = "idempotency_keys"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    request_path = Column(String(500), nullable=False)
    request_method = Column(String(10), nullable=False)
    request_body = Column(Text, nullable=True)
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Relationships
    organization = relationship("Organization")


class WebhookLog(Base):
    """Webhook log model for tracking outgoing webhooks."""

    __tablename__ = "webhook_logs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    url = Column(String(1000), nullable=False)
    payload = Column(Text, nullable=False)
    status_code = Column(Integer, nullable=True)
    response = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    success = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization")


class AuditLog(Base):
    """Audit log model for tracking all system changes."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)  # create, update, delete, login, etc.
    resource_type = Column(String(100), nullable=False, index=True)  # property, lead, user, etc.
    resource_id = Column(Integer, nullable=True, index=True)
    changes = Column(Text, nullable=True)  # JSON object with before/after values
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    additional_data = Column(Text, nullable=True)  # JSON object (renamed from metadata)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization")
