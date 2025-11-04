"""Database models for Real Estate OS."""
from .base import TimestampMixin, SoftDeleteMixin
from .user import User, Organization, Team, Role, Permission
from .property import (
    Property, PropertyImage, PropertyDocument, PropertyValuation,
    PropertyMetrics, PropertyHistory, Listing, ListingSnapshot
)
from .lead import (
    Lead, LeadSource, LeadScore, Contact, LeadActivity, LeadNote
)
from .campaign import (
    Campaign, CampaignTarget, EmailTemplate, SMSTemplate,
    OutreachAttempt, DeliverabilityEvent, UnsubscribeList
)
from .deal import Deal, DealStage, Transaction
from .portfolio import Portfolio, PortfolioHolding, Reconciliation
from .system import IdempotencyKey, WebhookLog, AuditLog

__all__ = [
    # Base
    "TimestampMixin",
    "SoftDeleteMixin",
    # User & Auth
    "User",
    "Organization",
    "Team",
    "Role",
    "Permission",
    # Property
    "Property",
    "PropertyImage",
    "PropertyDocument",
    "PropertyValuation",
    "PropertyMetrics",
    "PropertyHistory",
    "Listing",
    "ListingSnapshot",
    # Lead & CRM
    "Lead",
    "LeadSource",
    "LeadScore",
    "Contact",
    "LeadActivity",
    "LeadNote",
    # Campaign
    "Campaign",
    "CampaignTarget",
    "EmailTemplate",
    "SMSTemplate",
    "OutreachAttempt",
    "DeliverabilityEvent",
    "UnsubscribeList",
    # Deal
    "Deal",
    "DealStage",
    "Transaction",
    # Portfolio
    "Portfolio",
    "PortfolioHolding",
    "Reconciliation",
    # System
    "IdempotencyKey",
    "WebhookLog",
    "AuditLog",
]
