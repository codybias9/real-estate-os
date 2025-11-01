"""Data models for enrichment agent

Pydantic models for API responses and enriched data.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from pydantic import BaseModel, Field, validator
from decimal import Decimal


class PropertyEnrichmentData(BaseModel):
    """Complete enrichment data for a property"""

    # Identifiers
    prospect_id: int
    apn: Optional[str] = None  # Assessor Parcel Number

    # Property characteristics
    square_footage: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[Decimal] = None
    year_built: Optional[int] = None

    # Financial data
    assessed_value: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    last_sale_date: Optional[date] = None
    last_sale_price: Optional[Decimal] = None
    tax_amount_annual: Optional[Decimal] = None

    # Property details
    zoning: Optional[str] = None
    lot_size_sqft: Optional[int] = None
    property_type: Optional[str] = None

    # Owner information
    owner_name: Optional[str] = None
    owner_mailing_address: Optional[str] = None

    # Metadata
    source_api: str = Field(..., description="Which API provided this data")
    raw_response: Optional[Dict[str, Any]] = None

    @validator('bathrooms', pre=True)
    def parse_bathrooms(cls, v):
        """Convert bathrooms to Decimal"""
        if v is None:
            return None
        return Decimal(str(v))

    @validator('assessed_value', 'market_value', 'last_sale_price', 'tax_amount_annual', pre=True)
    def parse_decimal(cls, v):
        """Convert currency values to Decimal"""
        if v is None:
            return None
        if isinstance(v, str):
            # Remove currency symbols and commas
            v = v.replace('$', '').replace(',', '').strip()
        return Decimal(str(v))

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v) if v else None,
            date: lambda v: v.isoformat() if v else None
        }


class AssessorResponse(BaseModel):
    """Response from county assessor API"""

    apn: Optional[str] = None
    owner_name: Optional[str] = None
    owner_address: Optional[str] = None
    property_address: Optional[str] = None
    assessed_value: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    square_footage: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[Decimal] = None
    year_built: Optional[int] = None
    lot_size: Optional[int] = None
    property_type: Optional[str] = None
    zoning: Optional[str] = None
    last_sale_date: Optional[date] = None
    last_sale_price: Optional[Decimal] = None
    annual_tax: Optional[Decimal] = None

    # Raw response for debugging
    raw_data: Optional[Dict[str, Any]] = None


class CensusResponse(BaseModel):
    """Response from US Census Bureau API"""

    zip_code: str
    population: Optional[int] = None
    median_household_income: Optional[Decimal] = None
    median_age: Optional[Decimal] = None
    owner_occupied_rate: Optional[Decimal] = None
    renter_occupied_rate: Optional[Decimal] = None
    median_home_value: Optional[Decimal] = None
    unemployment_rate: Optional[Decimal] = None

    raw_data: Optional[Dict[str, Any]] = None


class MarketDataResponse(BaseModel):
    """Response from market data API (Zillow, Redfin, etc.)"""

    address: str
    estimated_value: Optional[Decimal] = None
    value_range_low: Optional[Decimal] = None
    value_range_high: Optional[Decimal] = None
    rental_estimate: Optional[Decimal] = None
    rental_range_low: Optional[Decimal] = None
    rental_range_high: Optional[Decimal] = None
    comp_properties: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    market_trend: Optional[str] = None  # "increasing", "decreasing", "stable"
    days_on_market_avg: Optional[int] = None

    raw_data: Optional[Dict[str, Any]] = None


class EnrichmentStatus(BaseModel):
    """Status of enrichment process for a property"""

    prospect_id: int
    status: str  # "pending", "enriching", "completed", "failed"
    data_sources_completed: List[str] = Field(default_factory=list)
    data_sources_failed: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    enrichment_data: Optional[PropertyEnrichmentData] = None


class EnrichmentBatch(BaseModel):
    """Batch of properties to enrich"""

    batch_id: str
    prospect_ids: List[int]
    county: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    total_count: int
    completed_count: int = 0
    failed_count: int = 0
