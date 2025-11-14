"""Leads router for customer relationship management."""
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
import uuid
import sys
import os

# Add parent directory to path to import event emitter and auth utils
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from api.event_emitter import emit_lead_created
from api.auth_utils import require_demo_write_permission

router = APIRouter(prefix="/leads", tags=["leads"])


class LeadCreate(BaseModel):
    """Schema for creating a lead."""
    name: str
    email: EmailStr
    phone: Optional[str] = None
    source: str
    status: str = "new"
    notes: Optional[str] = None


class LeadActivity(BaseModel):
    """Schema for lead activity."""
    type: str
    note: str
    outcome: Optional[str] = None


class LeadActivityResponse(BaseModel):
    """Schema for lead activity response."""
    id: str
    lead_id: str
    type: str
    note: str
    outcome: Optional[str] = None
    created_at: str


class LeadResponse(BaseModel):
    """Schema for lead response."""
    id: str
    name: str
    email: str
    phone: Optional[str] = None
    source: str
    status: str
    notes: Optional[str] = None
    created_at: str


# Mock data storage (in-memory for demo)
MOCK_LEADS = [
    LeadResponse(
        id=str(uuid.uuid4()),
        name="Jane Smith",
        email="jane.smith@example.com",
        phone="415-555-0100",
        source="website",
        status="new",
        notes="Interested in 3BR homes in SF",
        created_at=datetime.now().isoformat()
    ),
    LeadResponse(
        id=str(uuid.uuid4()),
        name="John Doe",
        email="john.doe@example.com",
        phone="415-555-0200",
        source="referral",
        status="contacted",
        notes="Looking for investment properties",
        created_at=datetime.now().isoformat()
    ),
    LeadResponse(
        id=str(uuid.uuid4()),
        name="Alice Johnson",
        email="alice.j@example.com",
        phone="510-555-0300",
        source="zillow",
        status="qualified",
        notes="Pre-approved for $1.5M",
        created_at=datetime.now().isoformat()
    ),
]

MOCK_ACTIVITIES = []


@router.get("", response_model=List[LeadResponse])
def list_leads(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = None
):
    """
    List leads with optional filtering.
    Returns mock data for demonstration purposes.
    """
    filtered = MOCK_LEADS

    if status:
        filtered = [lead for lead in filtered if lead.status == status]

    return filtered[skip : skip + limit]


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: str):
    """
    Get lead details by ID.
    Returns mock data for demonstration purposes.
    """
    for lead in MOCK_LEADS:
        if lead.id == lead_id:
            return lead

    raise HTTPException(status_code=404, detail="Lead not found")


@router.post("", response_model=LeadResponse, status_code=201)
def create_lead(
    lead_data: LeadCreate,
    _write_check: None = Depends(require_demo_write_permission)
):
    """
    Create a new lead.
    Returns mock data for demonstration purposes.

    Requires: Demo write permission (Bearer token or DEMO_ALLOW_WRITES=true)
    """
    new_lead = LeadResponse(
        id=str(uuid.uuid4()),
        **lead_data.dict(),
        created_at=datetime.now().isoformat()
    )

    MOCK_LEADS.append(new_lead)

    # Emit lead_created event
    emit_lead_created(
        lead_id=new_lead.id,
        contact_name=new_lead.name,
        source=new_lead.source,
        property_id=None  # Could be linked to a property if available
    )

    return new_lead


@router.post("/{lead_id}/activities", response_model=LeadActivityResponse, status_code=201)
def add_lead_activity(lead_id: str, activity: LeadActivity):
    """
    Add activity to a lead.
    Returns mock data for demonstration purposes.
    """
    # Check if lead exists
    lead_exists = any(lead.id == lead_id for lead in MOCK_LEADS)
    if not lead_exists:
        raise HTTPException(status_code=404, detail="Lead not found")

    new_activity = LeadActivityResponse(
        id=str(uuid.uuid4()),
        lead_id=lead_id,
        **activity.dict(),
        created_at=datetime.now().isoformat()
    )

    MOCK_ACTIVITIES.append(new_activity)
    return new_activity


@router.get("/{lead_id}/activities", response_model=List[LeadActivityResponse])
def get_lead_activities(lead_id: str):
    """
    Get activities for a lead.
    Returns mock data for demonstration purposes.
    """
    # Check if lead exists
    lead_exists = any(lead.id == lead_id for lead in MOCK_LEADS)
    if not lead_exists:
        raise HTTPException(status_code=404, detail="Lead not found")

    return [activity for activity in MOCK_ACTIVITIES if activity.lead_id == lead_id]
