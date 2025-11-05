"""Database models."""
from .base import BaseModel, TimestampMixin, SoftDeleteMixin
from .organization import Organization, Team, TeamMember
from .user import User, Role, Permission, UserRole, RolePermission
from .property import (
    Property,
    PropertyImage,
    PropertyValuation,
    PropertyNote,
    PropertyActivity,
    PropertyStatus,
    PropertyType,
)
from .lead import (
    Lead,
    LeadActivity,
    LeadNote,
    LeadDocument,
    LeadStatus,
    LeadSource,
    LeadType,
)
from .campaign import (
    Campaign,
    CampaignTemplate,
    CampaignRecipient,
    CampaignType,
    CampaignStatus,
)
from .deal import (
    Deal,
    Transaction,
    Portfolio,
    DealStatus,
    TransactionType,
)
from .system import (
    IdempotencyKey,
    WebhookLog,
    AuditLog,
)

__all__ = [
    # Base
    "BaseModel",
    "TimestampMixin",
    "SoftDeleteMixin",
    # Organization
    "Organization",
    "Team",
    "TeamMember",
    # User & Auth
    "User",
    "Role",
    "Permission",
    "UserRole",
    "RolePermission",
    # Property
    "Property",
    "PropertyImage",
    "PropertyValuation",
    "PropertyNote",
    "PropertyActivity",
    "PropertyStatus",
    "PropertyType",
    # Lead & CRM
    "Lead",
    "LeadActivity",
    "LeadNote",
    "LeadDocument",
    "LeadStatus",
    "LeadSource",
    "LeadType",
    # Campaign
    "Campaign",
    "CampaignTemplate",
    "CampaignRecipient",
    "CampaignType",
    "CampaignStatus",
    # Deal & Portfolio
    "Deal",
    "Transaction",
    "Portfolio",
    "DealStatus",
    "TransactionType",
    # System
    "IdempotencyKey",
    "WebhookLog",
    "AuditLog",
]
