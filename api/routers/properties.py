"""Properties router for real estate listings management."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timedelta
from enum import Enum
import uuid

router = APIRouter(prefix="/properties", tags=["properties"])


# ============================================================================
# Additional Enums for Extended Features
# ============================================================================

class PropertyStage(str, Enum):
    """Pipeline stages for property workflow."""
    new = "new"
    outreach = "outreach"
    contacted = "contacted"
    qualified = "qualified"
    negotiation = "negotiation"
    under_contract = "under_contract"
    closed_won = "closed_won"
    closed_lost = "closed_lost"


class ActivityType(str, Enum):
    """Types of activities in property timeline."""
    created = "created"
    stage_changed = "stage_changed"
    email_sent = "email_sent"
    email_received = "email_received"
    note_added = "note_added"
    call_made = "call_made"
    document_uploaded = "document_uploaded"
    offer_made = "offer_made"
    offer_accepted = "offer_accepted"
    inspection_scheduled = "inspection_scheduled"


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


# ============================================================================
# Additional Schemas for Extended Features
# ============================================================================

class StageUpdate(BaseModel):
    """Request to update property stage."""
    stage: PropertyStage
    note: Optional[str] = Field(None, description="Optional note about stage change")


class TimelineActivity(BaseModel):
    """Activity in property timeline."""
    id: str
    property_id: str
    activity_type: ActivityType
    title: str
    description: Optional[str]
    created_by: str
    created_at: str
    metadata: Optional[dict] = Field(default=None, description="Additional activity data")


class CommunicationSummary(BaseModel):
    """Summary of communication with property owner."""
    thread_id: str
    subject: str
    last_message_at: str
    message_count: int
    replied: bool
    opened: bool


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


# ============================================================================
# Extended Endpoints for Sales Ops Features
# ============================================================================

@router.patch("/{property_id}/stage", response_model=PropertyResponse)
def update_property_stage(property_id: str, stage_update: StageUpdate):
    """
    Update the pipeline stage of a property.

    Used for Kanban board drag-and-drop functionality.
    Creates a timeline activity when stage changes.
    """
    # Find property
    for prop in MOCK_PROPERTIES:
        if prop.id == property_id:
            # In a real system, would update the stage field
            # For now, just return the property
            # The actual stage would be stored in a 'stage' field

            # Mock: Create timeline activity for stage change
            activity_id = str(uuid.uuid4())
            # In real system, would store this activity

            return prop

    raise HTTPException(status_code=404, detail="Property not found")


@router.get("/{property_id}/timeline", response_model=List[TimelineActivity])
def get_property_timeline(property_id: str):
    """
    Get activity timeline for a property.

    Returns chronological history of all activities related to the property:
    - Stage changes
    - Communications
    - Notes
    - Documents
    - Offers
    - Inspections
    """
    # Find property to ensure it exists
    property_exists = any(prop.id == property_id for prop in MOCK_PROPERTIES)
    if not property_exists:
        raise HTTPException(status_code=404, detail="Property not found")

    # Mock timeline activities
    base_time = datetime.now()

    mock_activities = [
        TimelineActivity(
            id=str(uuid.uuid4()),
            property_id=property_id,
            activity_type=ActivityType.created,
            title="Property added to pipeline",
            description="Property imported from CSV",
            created_by="demo@realestateos.com",
            created_at=(base_time - timedelta(days=14)).isoformat(),
            metadata={"source": "csv_import", "batch_id": "batch_001"}
        ),
        TimelineActivity(
            id=str(uuid.uuid4()),
            property_id=property_id,
            activity_type=ActivityType.stage_changed,
            title="Stage changed: New → Outreach",
            description="Property moved to outreach stage",
            created_by="demo@realestateos.com",
            created_at=(base_time - timedelta(days=13)).isoformat(),
            metadata={"from_stage": "new", "to_stage": "outreach"}
        ),
        TimelineActivity(
            id=str(uuid.uuid4()),
            property_id=property_id,
            activity_type=ActivityType.email_sent,
            title="Initial outreach email sent",
            description="Sent: Interest in your property at {{address}}",
            created_by="demo@realestateos.com",
            created_at=(base_time - timedelta(days=12)).isoformat(),
            metadata={"thread_id": "thread_001", "template_id": "tpl_001"}
        ),
        TimelineActivity(
            id=str(uuid.uuid4()),
            property_id=property_id,
            activity_type=ActivityType.email_received,
            title="Owner replied",
            description="Owner expressed interest in discussing further",
            created_by="john.smith@example.com",
            created_at=(base_time - timedelta(days=10)).isoformat(),
            metadata={"thread_id": "thread_001", "sentiment": "positive"}
        ),
        TimelineActivity(
            id=str(uuid.uuid4()),
            property_id=property_id,
            activity_type=ActivityType.call_made,
            title="Phone call with owner",
            description="30-minute call discussing property condition and timeline",
            created_by="demo@realestateos.com",
            created_at=(base_time - timedelta(days=9)).isoformat(),
            metadata={"duration_minutes": 30, "outcome": "positive"}
        ),
        TimelineActivity(
            id=str(uuid.uuid4()),
            property_id=property_id,
            activity_type=ActivityType.stage_changed,
            title="Stage changed: Outreach → Qualified",
            description="Owner confirmed interest and property details",
            created_by="demo@realestateos.com",
            created_at=(base_time - timedelta(days=8)).isoformat(),
            metadata={"from_stage": "outreach", "to_stage": "qualified"}
        ),
        TimelineActivity(
            id=str(uuid.uuid4()),
            property_id=property_id,
            activity_type=ActivityType.note_added,
            title="Note: Property needs minor repairs",
            description="Owner mentioned roof is 15 years old, HVAC replaced 2 years ago",
            created_by="demo@realestateos.com",
            created_at=(base_time - timedelta(days=7)).isoformat(),
            metadata={"note_type": "property_condition"}
        ),
        TimelineActivity(
            id=str(uuid.uuid4()),
            property_id=property_id,
            activity_type=ActivityType.offer_made,
            title="Offer presented: $875,000",
            description="Presented all-cash offer with 30-day close",
            created_by="demo@realestateos.com",
            created_at=(base_time - timedelta(days=5)).isoformat(),
            metadata={"offer_amount": 875000, "close_days": 30, "financing": "cash"}
        ),
        TimelineActivity(
            id=str(uuid.uuid4()),
            property_id=property_id,
            activity_type=ActivityType.stage_changed,
            title="Stage changed: Qualified → Negotiation",
            description="Owner is considering offer",
            created_by="demo@realestateos.com",
            created_at=(base_time - timedelta(days=4)).isoformat(),
            metadata={"from_stage": "qualified", "to_stage": "negotiation"}
        ),
        TimelineActivity(
            id=str(uuid.uuid4()),
            property_id=property_id,
            activity_type=ActivityType.document_uploaded,
            title="Purchase agreement uploaded",
            description="Draft purchase agreement shared with owner",
            created_by="demo@realestateos.com",
            created_at=(base_time - timedelta(days=2)).isoformat(),
            metadata={"document_type": "purchase_agreement", "file_name": "PA_Draft_v1.pdf"}
        ),
    ]

    # Sort by created_at (most recent first)
    mock_activities.sort(key=lambda a: a.created_at, reverse=True)

    return mock_activities


@router.get("/{property_id}/communications", response_model=List[CommunicationSummary])
def get_property_communications(property_id: str):
    """
    Get all communications for a property.

    Returns summary of all email threads and communications
    related to this property.
    """
    # Find property to ensure it exists
    property_exists = any(prop.id == property_id for prop in MOCK_PROPERTIES)
    if not property_exists:
        raise HTTPException(status_code=404, detail="Property not found")

    # Mock communication threads
    mock_communications = [
        CommunicationSummary(
            thread_id="thread_001",
            subject="Interest in your property at 1234 Market St",
            last_message_at=(datetime.now() - timedelta(days=2)).isoformat(),
            message_count=5,
            replied=True,
            opened=True
        ),
        CommunicationSummary(
            thread_id="thread_005",
            subject="Following up on our conversation",
            last_message_at=(datetime.now() - timedelta(days=5)).isoformat(),
            message_count=2,
            replied=False,
            opened=True
        ),
        CommunicationSummary(
            thread_id="thread_012",
            subject="Purchase agreement for review",
            last_message_at=(datetime.now() - timedelta(days=1)).isoformat(),
            message_count=3,
            replied=True,
            opened=True
        ),
    ]

    return mock_communications
