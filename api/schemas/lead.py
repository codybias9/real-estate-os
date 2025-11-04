"""
Pydantic schemas for Lead/CRM endpoints
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
import uuid


# ============================================================================
# LEAD SCHEMAS
# ============================================================================

class LeadBase(BaseModel):
    """Base schema for Lead"""
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    company: Optional[str] = Field(None, max_length=255)
    status: str = Field(default="new")
    score: Optional[float] = Field(None, ge=0, le=100)
    tags: List[str] = Field(default_factory=list)
    last_contact_date: Optional[datetime] = None
    next_follow_up_date: Optional[datetime] = None


class LeadCreate(LeadBase):
    """Schema for creating a lead"""
    property_id: Optional[uuid.UUID] = None
    lead_source_id: Optional[uuid.UUID] = None
    assigned_to: Optional[uuid.UUID] = None


class LeadUpdate(BaseModel):
    """Schema for updating a lead"""
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    company: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = None
    score: Optional[float] = Field(None, ge=0, le=100)
    tags: Optional[List[str]] = None
    assigned_to: Optional[uuid.UUID] = None
    next_follow_up_date: Optional[datetime] = None


class LeadResponse(LeadBase):
    """Schema for lead response"""
    id: uuid.UUID
    organization_id: uuid.UUID
    property_id: Optional[uuid.UUID]
    lead_source_id: Optional[uuid.UUID]
    assigned_to: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LeadListResponse(BaseModel):
    """Schema for paginated lead list"""
    leads: List[LeadResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# LEAD ACTIVITY SCHEMAS
# ============================================================================

class LeadActivityCreate(BaseModel):
    """Schema for creating lead activity"""
    lead_id: uuid.UUID
    activity_type: str = Field(..., max_length=50)
    subject: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    activity_date: datetime
    duration_minutes: Optional[int] = Field(None, ge=0)


class LeadActivityResponse(LeadActivityCreate):
    """Schema for lead activity response"""
    id: uuid.UUID
    user_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# LEAD NOTE SCHEMAS
# ============================================================================

class LeadNoteCreate(BaseModel):
    """Schema for creating lead note"""
    lead_id: uuid.UUID
    content: str
    is_pinned: bool = Field(default=False)


class LeadNoteResponse(LeadNoteCreate):
    """Schema for lead note response"""
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# LEAD SOURCE SCHEMAS
# ============================================================================

class LeadSourceCreate(BaseModel):
    """Schema for creating lead source"""
    name: str = Field(..., max_length=100)
    source_type: str = Field(..., max_length=50)
    description: Optional[str] = None
    is_active: bool = Field(default=True)


class LeadSourceUpdate(BaseModel):
    """Schema for updating lead source"""
    name: Optional[str] = Field(None, max_length=100)
    source_type: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class LeadSourceResponse(LeadSourceCreate):
    """Schema for lead source response"""
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
