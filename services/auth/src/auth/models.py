"""
Authentication domain models
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


class UserRole(str, Enum):
    """User roles for RBAC"""

    ADMIN = "admin"  # Full system access
    ANALYST = "analyst"  # Property discovery and analysis
    UNDERWRITER = "underwriter"  # Scoring and memo review
    OPS = "ops"  # Outreach and pipeline management
    VIEWER = "viewer"  # Read-only access


@dataclass
class User:
    """User model"""

    id: str
    tenant_id: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def has_permission(self, permission: str) -> bool:
        """Check if user has permission based on role"""
        role_permissions = {
            UserRole.ADMIN: {"*"},  # All permissions
            UserRole.ANALYST: {
                "properties:read",
                "properties:create",
                "properties:update",
                "timeline:read",
                "timeline:write",
            },
            UserRole.UNDERWRITER: {
                "properties:read",
                "scores:read",
                "memos:read",
                "timeline:read",
                "timeline:write",
            },
            UserRole.OPS: {
                "properties:read",
                "properties:update",
                "outreach:read",
                "outreach:write",
                "timeline:read",
                "timeline:write",
            },
            UserRole.VIEWER: {
                "properties:read",
                "scores:read",
                "memos:read",
                "timeline:read",
            },
        }

        permissions = role_permissions.get(self.role, set())
        return "*" in permissions or permission in permissions


@dataclass
class Tenant:
    """Tenant model"""

    id: str
    name: str
    slug: str
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
