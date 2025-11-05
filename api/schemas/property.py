"""Property schemas."""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from enum import Enum


class PropertyType(str, Enum):
    """Property type enum."""
    SINGLE_FAMILY = "single_family"
    MULTI_FAMILY = "multi_family"
    CONDO = "condo"
    TOWNHOUSE = "townhouse"
    LAND = "land"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    MIXED_USE = "mixed_use"


class PropertyStatus(str, Enum):
    """Property status enum."""
    AVAILABLE = "available"
    UNDER_CONTRACT = "under_contract"
    SOLD = "sold"
    RENTED = "rented"
    OFF_MARKET = "off_market"


# Property Schemas
class PropertyBase(BaseModel):
    """Base property schema."""
    address: str = Field(..., min_length=1, max_length=500)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=1, max_length=50)
    zip_code: str = Field(..., min_length=1, max_length=20)
    country: str = Field(default="USA", max_length=50)
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    property_type: PropertyType
    status: PropertyStatus = PropertyStatus.AVAILABLE
    price: Optional[Decimal] = Field(None, ge=0)
    bedrooms: Optional[int] = Field(None, ge=0)
    bathrooms: Optional[Decimal] = Field(None, ge=0)
    square_feet: Optional[int] = Field(None, ge=0)
    lot_size: Optional[int] = Field(None, ge=0)
    year_built: Optional[int] = Field(None, ge=1800, le=2100)
    description: Optional[str] = None
    features: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class PropertyCreate(PropertyBase):
    """Property creation schema."""
    pass


class PropertyUpdate(BaseModel):
    """Property update schema."""
    address: Optional[str] = Field(None, min_length=1, max_length=500)
    city: Optional[str] = Field(None, min_length=1, max_length=100)
    state: Optional[str] = Field(None, min_length=1, max_length=50)
    zip_code: Optional[str] = Field(None, min_length=1, max_length=20)
    country: Optional[str] = Field(None, max_length=50)
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    property_type: Optional[PropertyType] = None
    status: Optional[PropertyStatus] = None
    price: Optional[Decimal] = Field(None, ge=0)
    bedrooms: Optional[int] = Field(None, ge=0)
    bathrooms: Optional[Decimal] = Field(None, ge=0)
    square_feet: Optional[int] = Field(None, ge=0)
    lot_size: Optional[int] = Field(None, ge=0)
    year_built: Optional[int] = Field(None, ge=1800, le=2100)
    description: Optional[str] = None
    features: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class PropertyResponse(PropertyBase):
    """Property response schema."""
    id: int
    organization_id: int
    created_by: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PropertyListResponse(BaseModel):
    """Property list response."""
    items: List[PropertyResponse]
    total: int
    page: int
    page_size: int
    pages: int


# Property Image Schemas
class PropertyImageCreate(BaseModel):
    """Property image creation schema."""
    url: str = Field(..., min_length=1, max_length=1000)
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    order: int = Field(default=0, ge=0)
    is_primary: bool = False


class PropertyImageResponse(BaseModel):
    """Property image response schema."""
    id: int
    property_id: int
    url: str
    title: Optional[str]
    description: Optional[str]
    order: int
    is_primary: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Property Valuation Schemas
class PropertyValuationCreate(BaseModel):
    """Property valuation creation schema."""
    value: Decimal = Field(..., ge=0)
    valuation_date: datetime
    source: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class PropertyValuationResponse(BaseModel):
    """Property valuation response schema."""
    id: int
    property_id: int
    value: Decimal
    valuation_date: datetime
    source: Optional[str]
    notes: Optional[str]
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True


# Property Note Schemas
class PropertyNoteCreate(BaseModel):
    """Property note creation schema."""
    content: str = Field(..., min_length=1)


class PropertyNoteResponse(BaseModel):
    """Property note response schema."""
    id: int
    property_id: int
    content: str
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Property Activity Schemas
class PropertyActivityCreate(BaseModel):
    """Property activity creation schema."""
    activity_type: str = Field(..., min_length=1, max_length=50)
    description: str = Field(..., min_length=1)
    metadata: Optional[Dict[str, Any]] = None


class PropertyActivityResponse(BaseModel):
    """Property activity response schema."""
    id: int
    property_id: int
    activity_type: str
    description: str
    metadata: Optional[Dict[str, Any]]
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True
