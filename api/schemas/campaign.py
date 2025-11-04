"""
Pydantic schemas for Campaign endpoints
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


# ============================================================================
# CAMPAIGN SCHEMAS
# ============================================================================

class CampaignBase(BaseModel):
    """Base schema for Campaign"""
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    campaign_type: str = Field(..., max_length=50)
    status: str = Field(default="draft")
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None


class CampaignCreate(CampaignBase):
    """Schema for creating a campaign"""
    pass


class CampaignUpdate(BaseModel):
    """Schema for updating a campaign"""
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None


class CampaignResponse(CampaignBase):
    """Schema for campaign response"""
    id: uuid.UUID
    organization_id: uuid.UUID
    created_by: uuid.UUID
    actual_start: Optional[datetime]
    actual_end: Optional[datetime]
    target_count: int
    sent_count: int
    delivered_count: int
    opened_count: int
    clicked_count: int
    replied_count: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CampaignListResponse(BaseModel):
    """Schema for paginated campaign list"""
    campaigns: List[CampaignResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# EMAIL TEMPLATE SCHEMAS
# ============================================================================

class EmailTemplateCreate(BaseModel):
    """Schema for creating email template"""
    name: str = Field(..., max_length=255)
    subject: str = Field(..., max_length=500)
    html_body: Optional[str] = None
    text_body: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    variables: List[str] = Field(default_factory=list)


class EmailTemplateUpdate(BaseModel):
    """Schema for updating email template"""
    name: Optional[str] = Field(None, max_length=255)
    subject: Optional[str] = Field(None, max_length=500)
    html_body: Optional[str] = None
    text_body: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class EmailTemplateResponse(EmailTemplateCreate):
    """Schema for email template response"""
    id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================================
# OUTREACH ATTEMPT SCHEMAS
# ============================================================================

class OutreachAttemptCreate(BaseModel):
    """Schema for creating outreach attempt"""
    campaign_id: Optional[uuid.UUID] = None
    lead_id: Optional[uuid.UUID] = None
    outreach_type: str = Field(..., max_length=50)
    recipient_email: Optional[EmailStr] = None
    recipient_phone: Optional[str] = Field(None, max_length=50)
    subject: Optional[str] = Field(None, max_length=500)
    body: Optional[str] = None


class OutreachAttemptResponse(OutreachAttemptCreate):
    """Schema for outreach attempt response"""
    id: uuid.UUID
    status: str
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    opened_at: Optional[datetime]
    clicked_at: Optional[datetime]
    replied_at: Optional[datetime]
    provider: Optional[str]
    provider_message_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# CAMPAIGN TARGET SCHEMAS
# ============================================================================

class CampaignTargetCreate(BaseModel):
    """Schema for creating campaign target"""
    campaign_id: uuid.UUID
    lead_id: Optional[uuid.UUID] = None
    contact_id: Optional[uuid.UUID] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    personalization_data: Dict[str, Any] = Field(default_factory=dict)


class CampaignTargetResponse(CampaignTargetCreate):
    """Schema for campaign target response"""
    id: uuid.UUID
    is_sent: bool
    sent_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
