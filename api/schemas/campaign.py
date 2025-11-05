"""Campaign schemas."""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class CampaignType(str, Enum):
    """Campaign type enum."""
    EMAIL = "email"
    SMS = "sms"
    DIRECT_MAIL = "direct_mail"
    SOCIAL_MEDIA = "social_media"


class CampaignStatus(str, Enum):
    """Campaign status enum."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


# Campaign Schemas
class CampaignBase(BaseModel):
    """Base campaign schema."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    campaign_type: CampaignType
    status: CampaignStatus = CampaignStatus.DRAFT
    subject: Optional[str] = Field(None, max_length=500)
    content: str = Field(..., min_length=1)
    template_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class CampaignCreate(CampaignBase):
    """Campaign creation schema."""
    pass


class CampaignUpdate(BaseModel):
    """Campaign update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    subject: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = Field(None, min_length=1)
    status: Optional[CampaignStatus] = None
    metadata: Optional[Dict[str, Any]] = None


class CampaignResponse(CampaignBase):
    """Campaign response schema."""
    id: int
    organization_id: int
    created_by: int
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_recipients: int
    sent_count: int
    delivered_count: int
    opened_count: int
    clicked_count: int
    bounced_count: int
    unsubscribed_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CampaignListResponse(BaseModel):
    """Campaign list response."""
    items: List[CampaignResponse]
    total: int
    page: int
    page_size: int
    pages: int


class CampaignStats(BaseModel):
    """Campaign statistics."""
    total_campaigns: int
    total_sent: int
    total_delivered: int
    total_opened: int
    total_clicked: int
    delivery_rate: float
    open_rate: float
    click_rate: float
    by_status: Dict[str, int]
    by_type: Dict[str, int]


class CampaignSendRequest(BaseModel):
    """Campaign send request."""
    lead_ids: Optional[List[int]] = None
    filters: Optional[Dict[str, Any]] = None
    send_now: bool = True
    send_at: Optional[datetime] = None


# Campaign Template Schemas
class CampaignTemplateBase(BaseModel):
    """Base campaign template schema."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    campaign_type: CampaignType
    subject: Optional[str] = Field(None, max_length=500)
    content: str = Field(..., min_length=1)
    is_active: bool = True


class CampaignTemplateCreate(CampaignTemplateBase):
    """Campaign template creation schema."""
    pass


class CampaignTemplateUpdate(BaseModel):
    """Campaign template update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    subject: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = Field(None, min_length=1)
    is_active: Optional[bool] = None


class CampaignTemplateResponse(CampaignTemplateBase):
    """Campaign template response schema."""
    id: int
    organization_id: int
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
