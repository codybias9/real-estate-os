"""Properties router for real estate listings management."""
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import uuid
import sys
import os

# Add parent directory to path to import event emitter
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from api.event_emitter import emit_property_updated
from api.auth_utils import get_current_user
from db.models import User

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
    """Schema for property response (frontend-compatible)."""
    id: str
    team_id: int = 1  # Default team for demo
    address: str
    city: str
    state: str
    zip_code: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    apn: Optional[str] = None
    owner_name: Optional[str] = None
    bird_dog_score: float = 0.5
    current_stage: str = "new"  # PropertyStage enum value
    previous_stage: Optional[str] = None
    stage_changed_at: str
    assigned_user_id: Optional[int] = None
    tags: List[str] = []
    notes: Optional[str] = None
    last_contact_at: Optional[str] = None
    memo_generated_at: Optional[str] = None
    memo_content: Optional[str] = None
    custom_fields: Dict[str, Any] = {}
    created_at: str
    updated_at: str
    archived_at: Optional[str] = None
    # Legacy fields for backward compatibility
    price: Optional[float] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    square_feet: Optional[int] = None
    property_type: Optional[str] = None
    status: Optional[str] = "active"


# Mock data storage (in-memory for demo)
# Enhanced seed data with 15 properties across all pipeline stages
now = datetime.now()

MOCK_PROPERTIES = [
    # NEW STAGE (3)
    PropertyResponse(
        id=str(uuid.uuid4()),
        address="2847 Sacramento St",
        city="San Francisco",
        state="CA",
        zip_code="94115",
        owner_name="Margaret Chen",
        bird_dog_score=0.82,
        current_stage="new",
        tags=["high-equity", "motivated"],
        price=2100000,
        bedrooms=4,
        bathrooms=3.0,
        square_feet=2200,
        property_type="single_family",
        status="active",
        created_at=(now - timedelta(days=1)).isoformat(),
        updated_at=(now - timedelta(days=1)).isoformat(),
        stage_changed_at=(now - timedelta(days=1)).isoformat()
    ),
    PropertyResponse(
        id=str(uuid.uuid4()),
        address="1456 Potrero Ave",
        city="San Francisco",
        state="CA",
        zip_code="94110",
        owner_name="David Rodriguez",
        bird_dog_score=0.67,
        current_stage="new",
        tags=["out-of-state", "rental"],
        price=1650000,
        bedrooms=3,
        bathrooms=2.0,
        square_feet=1800,
        property_type="single_family",
        status="active",
        created_at=(now - timedelta(days=2)).isoformat(),
        updated_at=(now - timedelta(days=2)).isoformat(),
        stage_changed_at=(now - timedelta(days=2)).isoformat()
    ),
    PropertyResponse(
        id=str(uuid.uuid4()),
        address="3421 19th Ave",
        city="San Francisco",
        state="CA",
        zip_code="94132",
        owner_name="Linda Wong",
        bird_dog_score=0.75,
        current_stage="new",
        tags=["vacant", "needs-repair"],
        price=1450000,
        bedrooms=2,
        bathrooms=1.5,
        square_feet=1400,
        property_type="single_family",
        status="active",
        created_at=(now - timedelta(days=3)).isoformat(),
        updated_at=(now - timedelta(days=3)).isoformat(),
        stage_changed_at=(now - timedelta(days=3)).isoformat()
    ),
    # OUTREACH STAGE (4)
    PropertyResponse(
        id=str(uuid.uuid4()),
        address="742 Divisadero St",
        city="San Francisco",
        state="CA",
        zip_code="94117",
        owner_name="Lisa Thompson",
        bird_dog_score=0.85,
        current_stage="outreach",
        previous_stage="new",
        tags=["high-equity", "pre-foreclosure"],
        last_contact_at=(now - timedelta(days=1)).isoformat(),
        memo_generated_at=(now - timedelta(days=2)).isoformat(),
        price=2350000,
        bedrooms=4,
        bathrooms=3.5,
        square_feet=2600,
        property_type="single_family",
        status="active",
        created_at=(now - timedelta(days=7)).isoformat(),
        updated_at=(now - timedelta(days=1)).isoformat(),
        stage_changed_at=(now - timedelta(days=5)).isoformat()
    ),
    PropertyResponse(
        id=str(uuid.uuid4()),
        address="456 Oak Avenue",
        city="San Francisco",
        state="CA",
        zip_code="94103",
        owner_name="Sarah Johnson",
        bird_dog_score=0.73,
        current_stage="outreach",
        previous_stage="new",
        tags=["investment", "rental"],
        last_contact_at=(now - timedelta(days=3)).isoformat(),
        price=2100000,
        bedrooms=4,
        bathrooms=3.0,
        square_feet=2800,
        property_type="single_family",
        status="active",
        created_at=(now - timedelta(days=10)).isoformat(),
        updated_at=(now - timedelta(days=3)).isoformat(),
        stage_changed_at=(now - timedelta(days=8)).isoformat()
    ),
    PropertyResponse(
        id=str(uuid.uuid4()),
        address="2134 Fulton St",
        city="San Francisco",
        state="CA",
        zip_code="94117",
        owner_name="Michael Brown",
        bird_dog_score=0.68,
        current_stage="outreach",
        previous_stage="new",
        tags=["renovation", "good-bones"],
        last_contact_at=(now - timedelta(days=4)).isoformat(),
        price=1750000,
        bedrooms=3,
        bathrooms=2.5,
        square_feet=2000,
        property_type="single_family",
        status="active",
        created_at=(now - timedelta(days=12)).isoformat(),
        updated_at=(now - timedelta(days=4)).isoformat(),
        stage_changed_at=(now - timedelta(days=10)).isoformat()
    ),
    PropertyResponse(
        id=str(uuid.uuid4()),
        address="789 Pine Blvd",
        city="Oakland",
        state="CA",
        zip_code="94601",
        owner_name="Thomas Wilson",
        bird_dog_score=0.64,
        current_stage="outreach",
        previous_stage="new",
        tags=["first-time-investor"],
        last_contact_at=(now - timedelta(days=7)).isoformat(),
        price=950000,
        bedrooms=2,
        bathrooms=2.0,
        square_feet=1500,
        property_type="condo",
        status="active",
        created_at=(now - timedelta(days=16)).isoformat(),
        updated_at=(now - timedelta(days=7)).isoformat(),
        stage_changed_at=(now - timedelta(days=14)).isoformat()
    ),
    # QUALIFIED STAGE (3)
    PropertyResponse(
        id=str(uuid.uuid4()),
        address="5621 Geary Blvd",
        city="San Francisco",
        state="CA",
        zip_code="94121",
        owner_name="Barbara Lee",
        bird_dog_score=0.88,
        current_stage="qualified",
        previous_stage="outreach",
        tags=["hot-lead", "motivated"],
        last_contact_at=(now - timedelta(days=1)).isoformat(),
        notes="Owner interested in cash offer, willing to sell before holidays",
        price=2450000,
        bedrooms=4,
        bathrooms=3.0,
        square_feet=2400,
        property_type="single_family",
        status="active",
        created_at=(now - timedelta(days=20)).isoformat(),
        updated_at=(now - timedelta(days=1)).isoformat(),
        stage_changed_at=(now - timedelta(days=5)).isoformat()
    ),
    PropertyResponse(
        id=str(uuid.uuid4()),
        address="3142 Scott St",
        city="San Francisco",
        state="CA",
        zip_code="94123",
        owner_name="Richard Martinez",
        bird_dog_score=0.91,
        current_stage="qualified",
        previous_stage="outreach",
        tags=["duplex", "income"],
        last_contact_at=(now - timedelta(hours=18)).isoformat(),
        notes="Seller relocating, needs quick close",
        price=3100000,
        bedrooms=6,
        bathrooms=4.0,
        square_feet=3500,
        property_type="multi_family",
        status="active",
        created_at=(now - timedelta(days=25)).isoformat(),
        updated_at=(now - timedelta(hours=18)).isoformat(),
        stage_changed_at=(now - timedelta(days=10)).isoformat()
    ),
    PropertyResponse(
        id=str(uuid.uuid4()),
        address="4523 Judah St",
        city="San Francisco",
        state="CA",
        zip_code="94122",
        owner_name="Christopher Clark",
        bird_dog_score=0.87,
        current_stage="qualified",
        previous_stage="outreach",
        tags=["beach-adjacent", "strong-rental"],
        last_contact_at=(now - timedelta(days=3)).isoformat(),
        notes="Owner interested in 1031 exchange",
        price=2200000,
        bedrooms=4,
        bathrooms=3.0,
        square_feet=2300,
        property_type="single_family",
        status="active",
        created_at=(now - timedelta(days=30)).isoformat(),
        updated_at=(now - timedelta(days=3)).isoformat(),
        stage_changed_at=(now - timedelta(days=15)).isoformat()
    ),
    # NEGOTIATION STAGE (2)
    PropertyResponse(
        id=str(uuid.uuid4()),
        address="2789 Broadway",
        city="San Francisco",
        state="CA",
        zip_code="94115",
        owner_name="Susan Taylor",
        bird_dog_score=0.93,
        current_stage="negotiation",
        previous_stage="qualified",
        tags=["premium", "pacific-heights"],
        last_contact_at=(now - timedelta(hours=12)).isoformat(),
        notes="Negotiating price - seller at $3.5M, we're at $3.2M",
        price=3350000,
        bedrooms=5,
        bathrooms=4.5,
        square_feet=4000,
        property_type="single_family",
        status="active",
        created_at=(now - timedelta(days=35)).isoformat(),
        updated_at=(now - timedelta(hours=12)).isoformat(),
        stage_changed_at=(now - timedelta(days=8)).isoformat()
    ),
    PropertyResponse(
        id=str(uuid.uuid4()),
        address="1534 Page St",
        city="San Francisco",
        state="CA",
        zip_code="94117",
        owner_name="Daniel White",
        bird_dog_score=0.89,
        current_stage="negotiation",
        previous_stage="qualified",
        tags=["victorian", "historic"],
        last_contact_at=(now - timedelta(hours=6)).isoformat(),
        notes="Agreed on price, negotiating inspection contingencies",
        price=2750000,
        bedrooms=4,
        bathrooms=3.5,
        square_feet=2900,
        property_type="single_family",
        status="active",
        created_at=(now - timedelta(days=38)).isoformat(),
        updated_at=(now - timedelta(hours=6)).isoformat(),
        stage_changed_at=(now - timedelta(days=12)).isoformat()
    ),
    # UNDER CONTRACT (1)
    PropertyResponse(
        id=str(uuid.uuid4()),
        address="1245 Union St",
        city="San Francisco",
        state="CA",
        zip_code="94109",
        owner_name="Jason Young",
        bird_dog_score=0.94,
        current_stage="under_contract",
        previous_stage="negotiation",
        tags=["marina", "turnkey"],
        last_contact_at=(now - timedelta(hours=24)).isoformat(),
        notes="Pending final walkthrough, closing in 5 days",
        price=2850000,
        bedrooms=3,
        bathrooms=2.5,
        square_feet=2100,
        property_type="single_family",
        status="active",
        created_at=(now - timedelta(days=45)).isoformat(),
        updated_at=(now - timedelta(hours=24)).isoformat(),
        stage_changed_at=(now - timedelta(days=3)).isoformat()
    ),
    # CLOSED WON (2)
    PropertyResponse(
        id=str(uuid.uuid4()),
        address="2456 Lombard St",
        city="San Francisco",
        state="CA",
        zip_code="94123",
        owner_name="Mark Wright",
        bird_dog_score=0.95,
        current_stage="closed_won",
        previous_stage="under_contract",
        tags=["successful", "quick-close"],
        last_contact_at=(now - timedelta(days=32)).isoformat(),
        notes="Closed successfully, 15% below market value",
        price=1950000,
        bedrooms=3,
        bathrooms=2.0,
        square_feet=1900,
        property_type="single_family",
        status="sold",
        created_at=(now - timedelta(days=55)).isoformat(),
        updated_at=(now - timedelta(days=32)).isoformat(),
        stage_changed_at=(now - timedelta(days=32)).isoformat()
    ),
    PropertyResponse(
        id=str(uuid.uuid4()),
        address="3789 Clay St",
        city="San Francisco",
        state="CA",
        zip_code="94118",
        owner_name="Laura Scott",
        bird_dog_score=0.96,
        current_stage="closed_won",
        previous_stage="under_contract",
        tags=["portfolio", "strong-roi"],
        last_contact_at=(now - timedelta(days=35)).isoformat(),
        notes="Excellent acquisition, rental income $8k/month",
        price=2650000,
        bedrooms=4,
        bathrooms=3.0,
        square_feet=2700,
        property_type="single_family",
        status="sold",
        created_at=(now - timedelta(days=60)).isoformat(),
        updated_at=(now - timedelta(days=35)).isoformat(),
        stage_changed_at=(now - timedelta(days=35)).isoformat()
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
def create_property(
    property_data: PropertyCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new property.
    Returns mock data for demonstration purposes.

    **Requires authentication**: Bearer token in Authorization header
    """
    new_property = PropertyResponse(
        id=str(uuid.uuid4()),
        **property_data.dict(),
        created_at=datetime.now().isoformat()
    )

    MOCK_PROPERTIES.append(new_property)
    return new_property


@router.patch("/{property_id}", response_model=PropertyResponse)
def update_property(
    property_id: str,
    property_data: PropertyUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Update property details.
    Returns mock data for demonstration purposes.

    **Requires authentication**: Bearer token in Authorization header
    """
    for prop in MOCK_PROPERTIES:
        if prop.id == property_id:
            # Track changes for event emission
            update_data = property_data.dict(exclude_unset=True)

            # Update fields and emit events for each change
            for key, value in update_data.items():
                old_value = getattr(prop, key, None)
                setattr(prop, key, value)

                # Emit property_updated event for significant field changes
                if old_value != value:
                    emit_property_updated(
                        property_id=property_id,
                        field_updated=key,
                        old_value=str(old_value) if old_value is not None else None,
                        new_value=str(value) if value is not None else None,
                        updated_by="demo@realestateos.com"
                    )

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
    Returns counts based on enhanced seed data.
    """
    # Count properties by stage
    stage_counts = {}
    for prop in MOCK_PROPERTIES:
        stage = prop.current_stage
        stage_counts[stage] = stage_counts.get(stage, 0) + 1

    # Calculate properties needing contact (new + outreach stages with no recent contact)
    needing_contact = sum(
        1 for prop in MOCK_PROPERTIES
        if prop.current_stage in ["new", "outreach"] and (
            not prop.last_contact_at or
            (datetime.fromisoformat(prop.last_contact_at) < datetime.now() - timedelta(days=7))
        )
    )

    return PipelineStats(
        total_properties=len(MOCK_PROPERTIES),
        stage_counts=stage_counts,
        properties_needing_contact=needing_contact
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
            # Track old stage for event emission
            old_stage = getattr(prop, 'current_stage', 'unknown')

            # In a real system, would update the stage field
            # For demo, we'll emit the event even though we're not persisting
            if hasattr(prop, 'current_stage'):
                prop.current_stage = stage_update.stage.value

            # Emit property_updated event for stage change
            emit_property_updated(
                property_id=property_id,
                field_updated="current_stage",
                old_value=str(old_stage),
                new_value=stage_update.stage.value,
                updated_by="demo@realestateos.com"
            )

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
