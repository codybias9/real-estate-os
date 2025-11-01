"""Structured logging and audit trail

Provides:
- Structured JSON logging
- Audit logs for security events
- Request/response logging
- Error logging with context
"""

import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from loguru import logger
import sys


def setup_logging(log_level: str = "INFO"):
    """Setup structured logging with Loguru

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Remove default handler
    logger.remove()

    # Add JSON formatter for production
    logger.add(
        sys.stdout,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {message}",
        level=log_level,
        serialize=False  # Set to True for JSON output in production
    )

    # Add file handler for persistence
    logger.add(
        "logs/app.log",
        rotation="500 MB",
        retention="10 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {message}",
        level=log_level
    )

    print(f"✅ Logging enabled (level: {log_level})")


def audit_log(
    event_type: str,
    user_id: Optional[UUID] = None,
    tenant_id: Optional[UUID] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[UUID] = None,
    action: Optional[str] = None,
    result: str = "success",
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
):
    """Log an audit event

    Creates a structured audit log entry for security and compliance.

    Args:
        event_type: Type of event (auth, property_access, campaign_send, etc.)
        user_id: User who performed the action
        tenant_id: Tenant context
        resource_type: Type of resource (property, campaign, template)
        resource_id: ID of the resource
        action: Action performed (create, update, delete, view)
        result: Result of the action (success, failure, denied)
        details: Additional context
        ip_address: IP address of the request

    Example:
        audit_log(
            event_type="property_access",
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            resource_type="property",
            resource_id=property_id,
            action="view",
            result="success",
            ip_address=request.client.host
        )
    """
    audit_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "user_id": str(user_id) if user_id else None,
        "tenant_id": str(tenant_id) if tenant_id else None,
        "resource_type": resource_type,
        "resource_id": str(resource_id) if resource_id else None,
        "action": action,
        "result": result,
        "details": details or {},
        "ip_address": ip_address
    }

    # Log to structured logger
    logger.info(f"AUDIT: {json.dumps(audit_entry)}")

    # TODO: Also store in database audit_log table for compliance
    # db.add(AuditLog(**audit_entry))
    # db.commit()


class RequestLoggingMiddleware:
    """Middleware to log all HTTP requests"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request_id = scope.get("request_id", "unknown")
            method = scope["method"]
            path = scope["path"]

            logger.info(f"Request {request_id}: {method} {path}")

        await self.app(scope, receive, send)
