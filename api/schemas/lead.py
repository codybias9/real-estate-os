"""Lead and CRM schemas."""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum


class LeadSource(str, Enum):
    """Lead source enum."""
    WEBSITE = "website"
    REFERRAL = "referral"
    SOCIAL_MEDIA = "social_media"
    EMAIL = "email"
    PHONE = "phone"
    WALK_IN = "walk_in"
    EVENT = "event"
    ADVERTISEMENT = "advertisement"
    OTHER = "other"


class LeadStatus(str, Enum):
    """Lead status enum."""
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    UNQUALIFIED = "unqualified"
    NURTURING = "nurturing"
    CONVERTED = "converted"
    LOST = "lost"


class ActivityType(str, Enum):
    """Activity type enum."""
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    SMS = "sms"
    NOTE = "note"


# Lead Schemas
class LeadBase(BaseModel):
    """Base lead schema."""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    company: Optional[str] = Field(None, max_length=200)
    source: LeadSource
    status: LeadStatus = LeadStatus.NEW
    score: int = Field(default=0, ge=0, le=100)
    budget: Optional[Decimal] = Field(None, ge=0)
    timeline: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    assigned_to: Optional[int] = None


class LeadCreate(LeadBase):
    """Lead creation schema."""
    pass


class LeadUpdate(BaseModel):
    """Lead update schema."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    company: Optional[str] = Field(None, max_length=200)
    source: Optional[LeadSource] = None
    status: Optional[LeadStatus] = None
    score: Optional[int] = Field(None, ge=0, le=100)
    budget: Optional[Decimal] = Field(None, ge=0)
    timeline: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    assigned_to: Optional[int] = None


class LeadResponse(LeadBase):
    """Lead response schema."""
    id: int
    organization_id: int
    created_by: int
    created_at: datetime
    updated_at: datetime
    last_contacted_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LeadListResponse(BaseModel):
    """Lead list response."""
    items: List[LeadResponse]
    total: int
    page: int
    page_size: int
    pages: int


class LeadStats(BaseModel):
    """Lead statistics."""
    total_leads: int
    by_status: Dict[str, int]
    by_source: Dict[str, int]
    avg_score: float
    conversion_rate: float


class LeadAssignRequest(BaseModel):
    """Lead assignment request."""
    user_id: int


# Lead Activity Schemas
class LeadActivityCreate(BaseModel):
    """Lead activity creation schema."""
    activity_type: ActivityType
    subject: Optional[str] = Field(None, max_length=200)
    description: str = Field(..., min_length=1)
    outcome: Optional[str] = Field(None, max_length=100)
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class LeadActivityResponse(BaseModel):
    """Lead activity response schema."""
    id: int
    lead_id: int
    activity_type: str
    subject: Optional[str]
    description: str
    outcome: Optional[str]
    scheduled_at: Optional[datetime]
    completed_at: Optional[datetime]
    metadata: Optional[Dict[str, Any]]
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True


# Lead Note Schemas
class LeadNoteCreate(BaseModel):
    """Lead note creation schema."""
    content: str = Field(..., min_length=1)
    is_pinned: bool = False


class LeadNoteResponse(BaseModel):
    """Lead note response schema."""
    id: int
    lead_id: int
    content: str
    is_pinned: bool
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Lead Document Schemas
class LeadDocumentCreate(BaseModel):
    """Lead document creation schema."""
    title: str = Field(..., min_length=1, max_length=200)
    file_path: str = Field(..., min_length=1, max_length=1000)
    file_type: Optional[str] = Field(None, max_length=100)
    file_size: Optional[int] = Field(None, ge=0)


class LeadDocumentResponse(BaseModel):
    """Lead document response schema."""
    id: int
    lead_id: int
    title: str
    file_path: str
    file_type: Optional[str]
    file_size: Optional[int]
    uploaded_by: int
    uploaded_at: datetime

    class Config:
        from_attributes = True
