"""
OutreachStatus - Normalized outreach events across all channels
SendGrid, Mailgun, Lob, Twilio → single status model
"""

from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class OutreachChannel(str, Enum):
    """Communication channel"""
    EMAIL = "email"
    SMS = "sms"
    POSTAL = "postal"
    VOICE = "voice"


class OutreachStatusType(str, Enum):
    """
    Normalized status across all providers.

    Lifecycle: QUEUED → SENT → DELIVERED → [OPENED → CLICKED → REPLIED]
    Failures: BOUNCED, SPAM, FAILED
    """
    QUEUED = "QUEUED"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    OPENED = "OPENED"
    CLICKED = "CLICKED"
    REPLIED = "REPLIED"
    BOUNCED = "BOUNCED"
    SPAM = "SPAM"
    FAILED = "FAILED"
    UNSUBSCRIBED = "UNSUBSCRIBED"


class OutreachStatus(BaseModel):
    """
    Unified outreach status event.

    Emitted by: Outreach.Orchestrator
    Consumed by: Collab.Timeline (append), Obs.Metrics (funnel tracking)
    """

    message_id: str = Field(..., description="Provider message ID")
    channel: OutreachChannel = Field(..., description="Communication channel")
    status: OutreachStatusType = Field(..., description="Normalized status")

    # Provider metadata (preserved for debugging)
    meta: dict[str, Any] = Field(
        default_factory=dict,
        description="Provider-specific metadata (provider, ts, raw event)"
    )

    # Optional: engagement tracking
    opened_at: datetime | None = Field(None, description="First open timestamp")
    clicked_at: datetime | None = Field(None, description="First click timestamp")
    replied_at: datetime | None = Field(None, description="Reply timestamp")

    # Failure details
    bounce_type: str | None = Field(None, description="Bounce type (hard|soft|complaint)")
    error_message: str | None = Field(None, description="Error message if failed")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
