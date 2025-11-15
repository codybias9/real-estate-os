"""Property enrichment data models."""

from datetime import datetime, date
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class EnrichmentBase(BaseModel):
    """Base enrichment model."""

    property_id: int = Field(..., description="Foreign key to property")

    # Assessor data
    apn: Optional[str] = Field(None, description="Assessor Parcel Number")
    tax_assessment_value: Optional[int] = Field(None, description="Tax assessed value")
    tax_assessment_year: Optional[int] = Field(None, description="Year of tax assessment")
    annual_tax_amount: Optional[int] = Field(None, description="Annual property tax")

    # Ownership and sales history
    owner_name: Optional[str] = Field(None, description="Current owner name")
    owner_type: Optional[str] = Field(None, description="Owner type (individual, corporation, trust)")
    last_sale_date: Optional[date] = Field(None, description="Date of last sale")
    last_sale_price: Optional[int] = Field(None, description="Last sale price")

    # Property characteristics (from assessor)
    legal_description: Optional[str] = Field(None, description="Legal property description")
    zoning: Optional[str] = Field(None, description="Zoning classification")
    land_use: Optional[str] = Field(None, description="Current land use")

    # Building details
    building_sqft: Optional[int] = Field(None, description="Building square footage from assessor")
    stories: Optional[int] = Field(None, description="Number of stories")
    units: Optional[int] = Field(None, description="Number of units (for multifamily)")
    parking_spaces: Optional[int] = Field(None, description="Number of parking spaces")

    # Neighborhood data
    school_district: Optional[str] = Field(None, description="School district")
    elementary_school: Optional[str] = Field(None, description="Elementary school")
    middle_school: Optional[str] = Field(None, description="Middle school")
    high_school: Optional[str] = Field(None, description="High school")
    school_rating: Optional[float] = Field(None, ge=0, le=10, description="Average school rating")

    # Location metrics
    walkability_score: Optional[int] = Field(None, ge=0, le=100, description="Walk Score")
    transit_score: Optional[int] = Field(None, ge=0, le=100, description="Transit Score")
    bike_score: Optional[int] = Field(None, ge=0, le=100, description="Bike Score")

    # Crime and safety
    crime_rate: Optional[str] = Field(None, description="Crime rate category (low, medium, high)")
    crime_index: Optional[int] = Field(None, ge=0, le=100, description="Crime index (0=safest, 100=most dangerous)")

    # Market data
    median_home_value: Optional[int] = Field(None, description="Median home value in area")
    appreciation_1yr: Optional[float] = Field(None, description="1-year appreciation percentage")
    appreciation_5yr: Optional[float] = Field(None, description="5-year appreciation percentage")
    median_rent: Optional[int] = Field(None, description="Median rent in area")

    # Nearby amenities
    nearby_parks: Optional[List[str]] = Field(default_factory=list, description="Nearby parks")
    nearby_shopping: Optional[List[str]] = Field(default_factory=list, description="Nearby shopping centers")
    nearby_restaurants: Optional[List[str]] = Field(default_factory=list, description="Nearby restaurants")
    distance_to_downtown: Optional[float] = Field(None, description="Distance to downtown in miles")

    # Additional data
    flood_zone: Optional[str] = Field(None, description="FEMA flood zone designation")
    earthquake_zone: Optional[str] = Field(None, description="Earthquake risk zone")
    hoa_fees: Optional[int] = Field(None, description="Monthly HOA fees if applicable")

    # Metadata
    enrichment_source: Optional[str] = Field(None, description="Source of enrichment data")
    enrichment_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class EnrichmentCreate(EnrichmentBase):
    """Model for creating enrichment data."""
    pass


class PropertyEnrichment(EnrichmentBase):
    """Full enrichment model with database fields."""

    id: int = Field(..., description="Unique enrichment ID")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record update timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "property_id": 1,
                "apn": "123-45-678-901",
                "tax_assessment_value": 325000,
                "tax_assessment_year": 2024,
                "annual_tax_amount": 3900,
                "owner_name": "Smith Family Trust",
                "owner_type": "trust",
                "last_sale_date": "2018-05-15",
                "last_sale_price": 280000,
                "legal_description": "Lot 42, Block 7, Desert Springs Subdivision",
                "zoning": "R-1",
                "land_use": "Single Family Residential",
                "building_sqft": 1800,
                "stories": 1,
                "units": 1,
                "parking_spaces": 2,
                "school_district": "Clark County School District",
                "elementary_school": "Desert Pines Elementary",
                "middle_school": "Vegas Verdes Middle School",
                "high_school": "Las Vegas High School",
                "school_rating": 7.5,
                "walkability_score": 65,
                "transit_score": 45,
                "bike_score": 58,
                "crime_rate": "low",
                "crime_index": 25,
                "median_home_value": 340000,
                "appreciation_1yr": 5.2,
                "appreciation_5yr": 28.5,
                "median_rent": 1850,
                "nearby_parks": ["Desert Breeze Park", "Sunset Park"],
                "nearby_shopping": ["Town Square Las Vegas"],
                "nearby_restaurants": ["Local favorites"],
                "distance_to_downtown": 5.2,
                "flood_zone": "X",
                "earthquake_zone": "low",
                "hoa_fees": 0,
                "enrichment_source": "clark_county_assessor",
                "enrichment_metadata": {},
                "created_at": "2024-01-15T11:00:00",
                "updated_at": "2024-01-15T11:00:00"
            }
        }
