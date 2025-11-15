"""Property data models."""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


class PropertyType(str, Enum):
    """Type of property."""

    SINGLE_FAMILY = "single_family"
    CONDO = "condo"
    TOWNHOUSE = "townhouse"
    MULTIFAMILY = "multifamily"
    COMMERCIAL = "commercial"
    LAND = "land"
    MIXED_USE = "mixed_use"
    OTHER = "other"


class PropertyStatus(str, Enum):
    """Processing status of property."""

    NEW = "new"
    ENRICHED = "enriched"
    SCORED = "scored"
    DOCUMENTED = "documented"
    CAMPAIGNED = "campaigned"
    ARCHIVED = "archived"


class PropertyBase(BaseModel):
    """Base property model with common fields."""

    # Source information
    source: str = Field(..., description="Data source identifier (e.g., 'zillow', 'redfin')")
    source_id: str = Field(..., description="Unique ID from the source")
    url: Optional[HttpUrl] = Field(None, description="URL to property listing")

    # Location
    address: str = Field(..., description="Street address")
    city: str = Field(..., description="City")
    state: str = Field(..., max_length=2, description="State abbreviation (e.g., 'NV')")
    zip_code: str = Field(..., description="ZIP code")
    county: Optional[str] = Field(None, description="County name")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude coordinate")

    # Property details
    property_type: PropertyType = Field(..., description="Type of property")
    price: int = Field(..., gt=0, description="Listing price in dollars")
    bedrooms: Optional[int] = Field(None, ge=0, description="Number of bedrooms")
    bathrooms: Optional[float] = Field(None, ge=0, description="Number of bathrooms")
    sqft: Optional[int] = Field(None, gt=0, description="Square footage")
    lot_size: Optional[int] = Field(None, gt=0, description="Lot size in square feet")
    year_built: Optional[int] = Field(None, ge=1800, le=2030, description="Year built")

    # Listing information
    listing_date: Optional[datetime] = Field(None, description="Date property was listed")
    description: Optional[str] = Field(None, description="Property description")
    features: Optional[List[str]] = Field(default_factory=list, description="Property features/amenities")
    images: Optional[List[HttpUrl]] = Field(default_factory=list, description="Property image URLs")

    # Status
    status: PropertyStatus = Field(default=PropertyStatus.NEW, description="Processing status")

    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class PropertyCreate(PropertyBase):
    """Model for creating a new property."""
    pass


class PropertyUpdate(BaseModel):
    """Model for updating a property (all fields optional)."""

    source: Optional[str] = None
    url: Optional[HttpUrl] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    county: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    property_type: Optional[PropertyType] = None
    price: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    sqft: Optional[int] = None
    lot_size: Optional[int] = None
    year_built: Optional[int] = None
    listing_date: Optional[datetime] = None
    description: Optional[str] = None
    features: Optional[List[str]] = None
    images: Optional[List[HttpUrl]] = None
    status: Optional[PropertyStatus] = None
    metadata: Optional[Dict[str, Any]] = None


class Property(PropertyBase):
    """Full property model with database fields."""

    id: int = Field(..., description="Unique property ID")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record update timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "source": "zillow",
                "source_id": "123456789",
                "url": "https://www.zillow.com/homedetails/123-Main-St/123456789_zpid/",
                "address": "123 Main Street",
                "city": "Las Vegas",
                "state": "NV",
                "zip_code": "89101",
                "county": "Clark",
                "latitude": 36.1699,
                "longitude": -115.1398,
                "property_type": "single_family",
                "price": 350000,
                "bedrooms": 3,
                "bathrooms": 2.0,
                "sqft": 1800,
                "lot_size": 7200,
                "year_built": 2005,
                "listing_date": "2024-01-15T10:00:00",
                "description": "Beautiful single-family home in desirable neighborhood",
                "features": ["granite countertops", "hardwood floors", "2-car garage"],
                "images": ["https://example.com/image1.jpg"],
                "status": "new",
                "metadata": {},
                "created_at": "2024-01-15T10:00:00",
                "updated_at": "2024-01-15T10:00:00"
            }
        }


class PropertyListResponse(BaseModel):
    """Response model for property list endpoint."""

    properties: List[Property]
    total: int
    page: int
    page_size: int
    total_pages: int
