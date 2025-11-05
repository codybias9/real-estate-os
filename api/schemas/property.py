"""Property schemas."""
from pydantic import BaseModel, Field, condecimal
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from ..models.property import PropertyStatus, PropertyType


class PropertyBase(BaseModel):
    """Base property schema."""

    address: str = Field(..., min_length=1, max_length=500)
    city: str = Field(..., min_length=1, max_length=100)
    state: str = Field(..., min_length=1, max_length=100)
    zip_code: str = Field(..., min_length=1, max_length=20)
    country: str = Field(default="USA", max_length=100)
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    property_type: PropertyType
    status: PropertyStatus = PropertyStatus.ACTIVE
    bedrooms: Optional[int] = None
    bathrooms: Optional[Decimal] = None
    square_feet: Optional[int] = None
    lot_size: Optional[Decimal] = None
    year_built: Optional[int] = None
    list_price: Optional[Decimal] = None
    sale_price: Optional[Decimal] = None
    estimated_value: Optional[Decimal] = None
    tax_assessed_value: Optional[Decimal] = None
    annual_taxes: Optional[Decimal] = None
    hoa_fees: Optional[Decimal] = None
    mls_number: Optional[str] = None
    listing_agent: Optional[str] = None
    listing_date: Optional[datetime] = None
    days_on_market: Optional[int] = None
    description: Optional[str] = None
    features: Optional[dict] = None
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    owner_email: Optional[str] = None
    custom_fields: Optional[dict] = None


class PropertyCreate(PropertyBase):
    """Create property schema."""
    pass


class PropertyUpdate(BaseModel):
    """Update property schema."""

    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    property_type: Optional[PropertyType] = None
    status: Optional[PropertyStatus] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[Decimal] = None
    square_feet: Optional[int] = None
    lot_size: Optional[Decimal] = None
    year_built: Optional[int] = None
    list_price: Optional[Decimal] = None
    sale_price: Optional[Decimal] = None
    estimated_value: Optional[Decimal] = None
    tax_assessed_value: Optional[Decimal] = None
    annual_taxes: Optional[Decimal] = None
    hoa_fees: Optional[Decimal] = None
    mls_number: Optional[str] = None
    listing_agent: Optional[str] = None
    listing_date: Optional[datetime] = None
    days_on_market: Optional[int] = None
    description: Optional[str] = None
    features: Optional[dict] = None
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    owner_email: Optional[str] = None
    custom_fields: Optional[dict] = None


class PropertyResponse(PropertyBase):
    """Property response schema."""

    id: int
    organization_id: int
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


class PropertyImageBase(BaseModel):
    """Base property image schema."""

    url: str
    thumbnail_url: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    display_order: int = 0
    is_primary: bool = False


class PropertyImageCreate(PropertyImageBase):
    """Create property image schema."""
    pass


class PropertyImageResponse(PropertyImageBase):
    """Property image response schema."""

    id: int
    property_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class PropertyValuationBase(BaseModel):
    """Base property valuation schema."""

    value: Decimal
    source: str
    confidence_score: Optional[Decimal] = None
    valuation_date: datetime
    metadata: Optional[dict] = None


class PropertyValuationCreate(PropertyValuationBase):
    """Create property valuation schema."""
    pass


class PropertyValuationResponse(PropertyValuationBase):
    """Property valuation response schema."""

    id: int
    property_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class PropertyNoteBase(BaseModel):
    """Base property note schema."""

    content: str
    is_pinned: bool = False


class PropertyNoteCreate(PropertyNoteBase):
    """Create property note schema."""
    pass


class PropertyNoteResponse(PropertyNoteBase):
    """Property note response schema."""

    id: int
    property_id: int
    created_by_id: Optional[int]
    created_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PropertyActivityResponse(BaseModel):
    """Property activity response schema."""

    id: int
    property_id: int
    user_id: Optional[int]
    activity_type: str
    description: Optional[str]
    metadata: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True
