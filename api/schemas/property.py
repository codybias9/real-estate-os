"""
Pydantic schemas for Property endpoints
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
import uuid


# ============================================================================
# PROPERTY SCHEMAS
# ============================================================================

class PropertyBase(BaseModel):
    """Base schema for Property"""
    address_line1: str = Field(..., max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., max_length=100)
    state: str = Field(..., min_length=2, max_length=2)
    zip_code: str = Field(..., max_length=10)
    county: Optional[str] = Field(None, max_length=100)
    country: str = Field(default="US", max_length=2)

    apn: Optional[str] = Field(None, max_length=50)
    property_type: Optional[str] = Field(None, max_length=50)
    bedrooms: Optional[int] = Field(None, ge=0)
    bathrooms: Optional[float] = Field(None, ge=0)
    square_feet: Optional[int] = Field(None, ge=0)
    lot_size: Optional[int] = Field(None, ge=0)
    year_built: Optional[int] = Field(None, ge=1800, le=2100)

    purchase_price: Optional[Decimal] = None
    current_value: Optional[Decimal] = None
    estimated_rent: Optional[Decimal] = None

    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

    status: Optional[str] = Field(default="active")
    source: Optional[str] = None
    source_id: Optional[str] = None


class PropertyCreate(PropertyBase):
    """Schema for creating a property"""
    pass


class PropertyUpdate(BaseModel):
    """Schema for updating a property (all fields optional)"""
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, min_length=2, max_length=2)
    zip_code: Optional[str] = Field(None, max_length=10)
    county: Optional[str] = Field(None, max_length=100)

    property_type: Optional[str] = None
    bedrooms: Optional[int] = Field(None, ge=0)
    bathrooms: Optional[float] = Field(None, ge=0)
    square_feet: Optional[int] = Field(None, ge=0)
    lot_size: Optional[int] = Field(None, ge=0)
    year_built: Optional[int] = Field(None, ge=1800, le=2100)

    purchase_price: Optional[Decimal] = None
    current_value: Optional[Decimal] = None
    estimated_rent: Optional[Decimal] = None

    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    status: Optional[str] = None


class PropertyResponse(PropertyBase):
    """Schema for property response"""
    id: uuid.UUID
    organization_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PropertyListResponse(BaseModel):
    """Schema for paginated property list"""
    properties: List[PropertyResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# PROPERTY IMAGE SCHEMAS
# ============================================================================

class PropertyImageCreate(BaseModel):
    """Schema for creating property image"""
    property_id: uuid.UUID
    url: str = Field(..., max_length=1000)
    thumbnail_url: Optional[str] = Field(None, max_length=1000)
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    display_order: int = Field(default=0)
    is_primary: bool = Field(default=False)


class PropertyImageResponse(PropertyImageCreate):
    """Schema for property image response"""
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# PROPERTY VALUATION SCHEMAS
# ============================================================================

class PropertyValuationCreate(BaseModel):
    """Schema for creating property valuation"""
    property_id: uuid.UUID
    valuation_date: datetime
    valuation_type: str = Field(..., max_length=50)
    value: Decimal = Field(..., gt=0)
    confidence_score: Optional[float] = Field(None, ge=0, le=1)
    source: Optional[str] = Field(None, max_length=100)


class PropertyValuationResponse(PropertyValuationCreate):
    """Schema for property valuation response"""
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
