"""Lead schemas."""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from ..models.lead import LeadStatus, LeadSource, LeadType


class LeadBase(BaseModel):
    """Base lead schema."""

    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = None
    company: Optional[str] = None
    lead_type: LeadType
    status: LeadStatus = LeadStatus.NEW
    source: LeadSource
    score: Optional[int] = Field(None, ge=0, le=100)
    budget_min: Optional[Decimal] = None
    budget_max: Optional[Decimal] = None
    timeline: Optional[str] = None
    preferred_locations: Optional[List[str]] = None
    requirements: Optional[str] = None
    preferred_contact_method: Optional[str] = None
    contact_time_preference: Optional[str] = None
    do_not_contact: bool = False
    next_follow_up_at: Optional[datetime] = None
    custom_fields: Optional[dict] = None
    tags: Optional[List[str]] = None


class LeadCreate(LeadBase):
    """Create lead schema."""
    property_id: Optional[int] = None
    assigned_to_id: Optional[int] = None


class LeadUpdate(BaseModel):
    """Update lead schema."""

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    property_id: Optional[int] = None
    assigned_to_id: Optional[int] = None
    lead_type: Optional[LeadType] = None
    status: Optional[LeadStatus] = None
    source: Optional[LeadSource] = None
    score: Optional[int] = None
    budget_min: Optional[Decimal] = None
    budget_max: Optional[Decimal] = None
    timeline: Optional[str] = None
    preferred_locations: Optional[List[str]] = None
    requirements: Optional[str] = None
    preferred_contact_method: Optional[str] = None
    contact_time_preference: Optional[str] = None
    do_not_contact: Optional[bool] = None
    next_follow_up_at: Optional[datetime] = None
    custom_fields: Optional[dict] = None
    tags: Optional[List[str]] = None


class LeadResponse(LeadBase):
    """Lead response schema."""

    id: int
    organization_id: int
    property_id: Optional[int]
    assigned_to_id: Optional[int]
    created_by_id: Optional[int]
    last_contacted_at: Optional[datetime]
    converted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
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


class LeadActivityBase(BaseModel):
    """Base lead activity schema."""

    activity_type: str
    subject: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Optional[dict] = None


class LeadActivityCreate(LeadActivityBase):
    """Create lead activity schema."""
    pass


class LeadActivityResponse(LeadActivityBase):
    """Lead activity response schema."""

    id: int
    lead_id: int
    user_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class LeadNoteBase(BaseModel):
    """Base lead note schema."""

    content: str
    is_pinned: bool = False


class LeadNoteCreate(LeadNoteBase):
    """Create lead note schema."""
    pass


class LeadNoteResponse(LeadNoteBase):
    """Lead note response schema."""

    id: int
    lead_id: int
    created_by_id: Optional[int]
    created_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LeadAssignRequest(BaseModel):
    """Lead assignment request."""

    user_id: int
