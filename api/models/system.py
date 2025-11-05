"""System models for operational features."""
from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, JSON, Boolean
from sqlalchemy.orm import relationship
from .base import BaseModel
import enum


class IdempotencyKey(BaseModel):
    """Idempotency key for preventing duplicate operations."""

    __tablename__ = "idempotency_keys"

    key = Column(String(255), unique=True, nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    endpoint = Column(String(500), nullable=False)
    method = Column(String(10), nullable=False)
    request_data = Column(JSON, nullable=True)
    response_data = Column(JSON, nullable=True)
    status_code = Column(Integer, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Relationships
    organization = relationship("Organization")
    user = relationship("User")


class WebhookLog(BaseModel):
    """Log of webhook deliveries."""

    __tablename__ = "webhook_logs"

    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    event_id = Column(String(255), nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    target_url = Column(String(1000), nullable=False)
    http_method = Column(String(10), nullable=False, default="POST")
    headers = Column(JSON, nullable=True)

    # Delivery tracking
    attempt_count = Column(Integer, default=0, nullable=False)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)

    # Response
    status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # Status
    is_delivered = Column(Boolean, default=False, nullable=False)
    is_failed = Column(Boolean, default=False, nullable=False)

    # Relationships
    organization = relationship("Organization")


class AuditLog(BaseModel):
    """Audit log for tracking changes."""

    __tablename__ = "audit_logs"

    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Action details
    action = Column(String(100), nullable=False, index=True)  # create, update, delete, login, etc.
    resource_type = Column(String(100), nullable=False, index=True)  # user, property, lead, etc.
    resource_id = Column(Integer, nullable=True, index=True)
    description = Column(Text, nullable=True)

    # Changes
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)

    # Request context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    request_id = Column(String(255), nullable=True, index=True)

    # Relationships
    organization = relationship("Organization")
    user = relationship("User")
