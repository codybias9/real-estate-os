"""System models for idempotency, webhooks, and audit logging."""
from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey,
    DateTime, JSON, Index
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from .base import TimestampMixin


class IdempotencyKey(Base, TimestampMixin):
    """Idempotency key storage for request deduplication."""
    __tablename__ = 'idempotency_keys'

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, nullable=False, index=True)

    # Request details
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # Response caching
    response_status = Column(Integer, nullable=False)
    response_body = Column(Text, nullable=True)
    response_headers = Column(JSON, default=dict)

    # Metadata
    request_hash = Column(String(64), nullable=True, index=True)  # SHA256 of request body
    created_at_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # TTL - keys are valid for 24 hours
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    __table_args__ = (
        Index('idx_idempotency_key_expires', 'key', 'expires_at'),
    )


class WebhookLog(Base, TimestampMixin):
    """Webhook delivery tracking and logging."""
    __tablename__ = 'webhook_logs'

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)

    # Webhook details
    event_type = Column(String(100), nullable=False, index=True)
    target_url = Column(String(500), nullable=False)
    payload = Column(JSON, nullable=False)

    # Delivery tracking
    attempts = Column(Integer, default=0, nullable=False)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    next_retry_at = Column(DateTime(timezone=True), nullable=True, index=True)

    # Response details
    status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    response_headers = Column(JSON, default=dict)

    # Status
    delivered = Column(String(50), default='pending', nullable=False, index=True)  # pending, delivered, failed
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(String(500), nullable=True)

    # Security
    signature = Column(String(255), nullable=True)  # HMAC signature
    signature_algorithm = Column(String(50), default='sha256', nullable=False)

    # Metadata
    source_event_id = Column(String(255), nullable=True, index=True)  # ID of event that triggered webhook
    metadata = Column(JSON, default=dict)

    __table_args__ = (
        Index('idx_webhook_status_retry', 'delivered', 'next_retry_at'),
    )


class AuditLog(Base, TimestampMixin):
    """System audit trail for security and compliance."""
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # Event details
    event_type = Column(String(100), nullable=False, index=True)  # login, create, update, delete, etc.
    resource_type = Column(String(100), nullable=True, index=True)  # property, lead, campaign, etc.
    resource_id = Column(Integer, nullable=True, index=True)

    # Action details
    action = Column(String(50), nullable=False, index=True)  # create, read, update, delete, auth
    description = Column(String(500), nullable=True)

    # Request context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    request_method = Column(String(10), nullable=True)
    request_path = Column(String(500), nullable=True)

    # Changes
    old_values = Column(JSON, default=dict)  # Previous state
    new_values = Column(JSON, default=dict)  # New state

    # Result
    status = Column(String(50), nullable=False, index=True)  # success, failure, error
    error_message = Column(Text, nullable=True)

    # Metadata
    metadata = Column(JSON, default=dict)
    created_at_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # Relationships
    user = relationship('User', back_populates='audit_logs')

    __table_args__ = (
        Index('idx_audit_log_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_log_user_event', 'user_id', 'event_type', 'created_at_timestamp'),
    )
