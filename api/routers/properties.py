"""Properties router for real estate listings management."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

router = APIRouter(prefix="/properties", tags=["properties"])


class PropertyCreate(BaseModel):
    """Schema for creating a property."""
    address: str
    city: str
    state: str
    zip: str
    price: float
    bedrooms: int
    bathrooms: float
    square_feet: int
    property_type: str
    status: str = "active"


class PropertyUpdate(BaseModel):
    """Schema for updating a property."""
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    price: Optional[float] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    square_feet: Optional[int] = None
    property_type: Optional[str] = None
    status: Optional[str] = None


class PropertyResponse(BaseModel):
    """Schema for property response."""
    id: str
    address: str
    city: str
    state: str
    zip: str
    price: float
    bedrooms: int
    bathrooms: float
    square_feet: int
    property_type: str
    status: str
    created_at: str


# Mock data storage (in-memory for demo)
MOCK_PROPERTIES = [
    PropertyResponse(
        id=str(uuid.uuid4()),
        address="123 Main Street",
        city="San Francisco",
        state="CA",
        zip="94102",
        price=1500000,
        bedrooms=3,
        bathrooms=2.5,
        square_feet=2200,
        property_type="single_family",
        status="active",
        created_at=datetime.now().isoformat()
    ),
    PropertyResponse(
        id=str(uuid.uuid4()),
        address="456 Oak Avenue",
        city="San Francisco",
        state="CA",
        zip="94103",
        price=2100000,
        bedrooms=4,
        bathrooms=3.0,
        square_feet=2800,
        property_type="single_family",
        status="active",
        created_at=datetime.now().isoformat()
    ),
    PropertyResponse(
        id=str(uuid.uuid4()),
        address="789 Pine Boulevard",
        city="Oakland",
        state="CA",
        zip="94601",
        price=950000,
        bedrooms=2,
        bathrooms=2.0,
        square_feet=1500,
        property_type="condo",
        status="active",
        created_at=datetime.now().isoformat()
    ),
]


@router.get("", response_model=List[PropertyResponse])
def list_properties(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    city: Optional[str] = None,
    status: Optional[str] = None
):
    """
    List properties with optional filtering.
    Returns mock data for demonstration purposes.
    """
    filtered = MOCK_PROPERTIES

    if city:
        filtered = [p for p in filtered if p.city.lower() == city.lower()]

    if status:
        filtered = [p for p in filtered if p.status == status]

    return filtered[skip : skip + limit]


@router.get("/{property_id}", response_model=PropertyResponse)
def get_property(property_id: str):
    """
    Get property details by ID.
    Returns mock data for demonstration purposes.
    """
    # Find property in mock data
    for prop in MOCK_PROPERTIES:
        if prop.id == property_id:
            return prop

    raise HTTPException(status_code=404, detail="Property not found")


@router.post("", response_model=PropertyResponse, status_code=201)
def create_property(property_data: PropertyCreate):
    """
    Create a new property.
    Returns mock data for demonstration purposes.
    """
    new_property = PropertyResponse(
        id=str(uuid.uuid4()),
        **property_data.dict(),
        created_at=datetime.now().isoformat()
    )

    MOCK_PROPERTIES.append(new_property)
    return new_property


@router.patch("/{property_id}", response_model=PropertyResponse)
def update_property(property_id: str, property_data: PropertyUpdate):
    """
    Update property details.
    Returns mock data for demonstration purposes.
    """
    for prop in MOCK_PROPERTIES:
        if prop.id == property_id:
            # Update fields that were provided
            update_data = property_data.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(prop, key, value)
            return prop

    raise HTTPException(status_code=404, detail="Property not found")


@router.delete("/{property_id}", status_code=204)
def delete_property(property_id: str):
    """
    Delete a property.
    Returns mock data for demonstration purposes.
    """
    for i, prop in enumerate(MOCK_PROPERTIES):
        if prop.id == property_id:
            MOCK_PROPERTIES.pop(i)
            return

    raise HTTPException(status_code=404, detail="Property not found")


class PipelineStats(BaseModel):
    """Schema for pipeline statistics."""
    total_properties: int
    stage_counts: dict
    properties_needing_contact: int


@router.get("/stats/pipeline", response_model=PipelineStats)
def get_pipeline_stats(team_id: Optional[str] = Query(None)):
    """
    Get pipeline statistics for dashboard.
    Returns mock data for demonstration purposes.
    """
    return PipelineStats(
        total_properties=len(MOCK_PROPERTIES),
        stage_counts={
            "new": 5,
            "outreach": 8,
            "qualified": 6,
            "negotiation": 3,
            "under_contract": 2,
            "closed_won": 1,
        },
        properties_needing_contact=12
    )
