"""Email campaign and outreach models."""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr


class CampaignStatus(str, Enum):
    """Status of email campaign."""

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class OutreachStatus(str, Enum):
    """Status of individual outreach email."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    REPLIED = "replied"
    BOUNCED = "bounced"
    UNSUBSCRIBED = "unsubscribed"
    FAILED = "failed"


class CampaignBase(BaseModel):
    """Base campaign model."""

    # Campaign details
    name: str = Field(..., description="Campaign name")
    description: Optional[str] = Field(None, description="Campaign description")

    # Email content
    subject: str = Field(..., description="Email subject line")
    email_template: str = Field(..., description="Email template name or content")

    # Targeting
    property_ids: List[int] = Field(..., description="List of property IDs to include")
    min_score: Optional[int] = Field(None, ge=0, le=100, description="Minimum property score")
    max_score: Optional[int] = Field(None, ge=0, le=100, description="Maximum property score")

    # Recipients
    recipient_emails: List[EmailStr] = Field(..., description="List of recipient email addresses")

    # Scheduling
    scheduled_send_time: Optional[datetime] = Field(None, description="When to send campaign")

    # Status
    status: CampaignStatus = Field(default=CampaignStatus.DRAFT, description="Campaign status")

    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class CampaignCreate(CampaignBase):
    """Model for creating a campaign."""
    pass


class Campaign(CampaignBase):
    """Full campaign model with database fields."""

    id: int = Field(..., description="Unique campaign ID")

    # Statistics
    total_recipients: int = Field(default=0, description="Total number of recipients")
    emails_sent: int = Field(default=0, description="Number of emails sent")
    emails_delivered: int = Field(default=0, description="Number of emails delivered")
    emails_opened: int = Field(default=0, description="Number of emails opened")
    emails_clicked: int = Field(default=0, description="Number of emails with clicks")
    emails_replied: int = Field(default=0, description="Number of replies received")
    emails_bounced: int = Field(default=0, description="Number of bounced emails")
    emails_unsubscribed: int = Field(default=0, description="Number of unsubscribes")

    # Timing
    sent_at: Optional[datetime] = Field(None, description="When campaign was sent")
    completed_at: Optional[datetime] = Field(None, description="When campaign completed")

    # Database fields
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record update timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Q1 2024 High-Value Properties",
                "description": "Campaign targeting high-scoring properties for Q1",
                "subject": "Exclusive Investment Opportunity: High-Yield Property",
                "email_template": "investor_opportunity_v1",
                "property_ids": [1, 5, 12, 18],
                "min_score": 80,
                "max_score": 100,
                "recipient_emails": ["investor1@example.com", "investor2@example.com"],
                "scheduled_send_time": "2024-01-20T09:00:00",
                "status": "sent",
                "metadata": {
                    "campaign_type": "investor_outreach",
                    "priority": "high"
                },
                "total_recipients": 2,
                "emails_sent": 2,
                "emails_delivered": 2,
                "emails_opened": 1,
                "emails_clicked": 1,
                "emails_replied": 0,
                "emails_bounced": 0,
                "emails_unsubscribed": 0,
                "sent_at": "2024-01-20T09:00:00",
                "completed_at": "2024-01-20T09:05:00",
                "created_at": "2024-01-15T14:00:00",
                "updated_at": "2024-01-20T09:05:00"
            }
        }


class OutreachLogBase(BaseModel):
    """Base outreach log model."""

    campaign_id: int = Field(..., description="Foreign key to campaign")
    property_id: int = Field(..., description="Foreign key to property")
    recipient_email: EmailStr = Field(..., description="Recipient email address")

    # Email details
    subject: str = Field(..., description="Email subject")
    message_id: Optional[str] = Field(None, description="Email service message ID")

    # Status
    status: OutreachStatus = Field(default=OutreachStatus.PENDING, description="Outreach status")

    # Tracking
    sent_at: Optional[datetime] = Field(None, description="When email was sent")
    delivered_at: Optional[datetime] = Field(None, description="When email was delivered")
    opened_at: Optional[datetime] = Field(None, description="When email was first opened")
    clicked_at: Optional[datetime] = Field(None, description="When link was first clicked")
    replied_at: Optional[datetime] = Field(None, description="When reply was received")

    # Engagement metrics
    open_count: int = Field(default=0, description="Number of times opened")
    click_count: int = Field(default=0, description="Number of times links clicked")

    # Error handling
    error_message: Optional[str] = Field(None, description="Error message if failed")
    bounce_reason: Optional[str] = Field(None, description="Reason for bounce")

    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class OutreachLog(OutreachLogBase):
    """Full outreach log model with database fields."""

    id: int = Field(..., description="Unique log ID")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record update timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "campaign_id": 1,
                "property_id": 1,
                "recipient_email": "investor1@example.com",
                "subject": "Exclusive Investment Opportunity: High-Yield Property",
                "message_id": "msg_abc123xyz",
                "status": "opened",
                "sent_at": "2024-01-20T09:00:15",
                "delivered_at": "2024-01-20T09:00:18",
                "opened_at": "2024-01-20T10:30:00",
                "clicked_at": None,
                "replied_at": None,
                "open_count": 3,
                "click_count": 0,
                "error_message": None,
                "bounce_reason": None,
                "metadata": {
                    "user_agent": "Mozilla/5.0...",
                    "ip_address": "192.168.1.1"
                },
                "created_at": "2024-01-20T09:00:00",
                "updated_at": "2024-01-20T10:30:00"
            }
        }
