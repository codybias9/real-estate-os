"""Deals router for transaction management."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid
import sys
import os

# Add parent directory to path to import event emitter
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from api.event_emitter import emit_deal_stage_changed

router = APIRouter(prefix="/deals", tags=["deals"])


class DealCreate(BaseModel):
    """Schema for creating a deal."""
    lead_id: str
    property_id: str
    status: str = "negotiation"
    value: float
    notes: Optional[str] = None


class DealUpdate(BaseModel):
    """Schema for updating a deal."""
    status: Optional[str] = None
    value: Optional[float] = None
    notes: Optional[str] = None


class DealResponse(BaseModel):
    """Schema for deal response."""
    id: str
    lead_id: str
    property_id: str
    status: str
    value: float
    notes: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None


# Mock data storage (in-memory for demo)
MOCK_DEALS = [
    DealResponse(
        id=str(uuid.uuid4()),
        lead_id="lead-12345",
        property_id="prop-67890",
        status="negotiation",
        value=1450000,
        notes="Buyer very interested, submitted offer",
        created_at=datetime.now().isoformat(),
        updated_at=None
    ),
    DealResponse(
        id=str(uuid.uuid4()),
        lead_id="lead-23456",
        property_id="prop-78901",
        status="under_contract",
        value=2050000,
        notes="Pending inspection",
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    ),
    DealResponse(
        id=str(uuid.uuid4()),
        lead_id="lead-34567",
        property_id="prop-89012",
        status="closed",
        value=920000,
        notes="Deal closed successfully",
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    ),
]


@router.get("", response_model=List[DealResponse])
def list_deals(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = None
):
    """
    List deals with optional filtering.
    Returns mock data for demonstration purposes.
    """
    filtered = MOCK_DEALS

    if status:
        filtered = [deal for deal in filtered if deal.status == status]

    return filtered[skip : skip + limit]


@router.get("/{deal_id}", response_model=DealResponse)
def get_deal(deal_id: str):
    """
    Get deal details by ID.
    Returns mock data for demonstration purposes.
    """
    for deal in MOCK_DEALS:
        if deal.id == deal_id:
            return deal

    raise HTTPException(status_code=404, detail="Deal not found")


@router.post("", response_model=DealResponse, status_code=201)
def create_deal(deal_data: DealCreate):
    """
    Create a new deal.
    Returns mock data for demonstration purposes.
    """
    new_deal = DealResponse(
        id=str(uuid.uuid4()),
        **deal_data.dict(),
        created_at=datetime.now().isoformat(),
        updated_at=None
    )

    MOCK_DEALS.append(new_deal)
    return new_deal


@router.patch("/{deal_id}", response_model=DealResponse)
def update_deal(deal_id: str, deal_data: DealUpdate):
    """
    Update deal details.
    Returns mock data for demonstration purposes.
    """
    for deal in MOCK_DEALS:
        if deal.id == deal_id:
            # Track status change for event emission
            old_status = deal.status

            # Update fields that were provided
            update_data = deal_data.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(deal, key, value)
            deal.updated_at = datetime.now().isoformat()

            # Emit deal_stage_changed event if status changed
            if 'status' in update_data and old_status != update_data['status']:
                emit_deal_stage_changed(
                    deal_id=deal_id,
                    property_id=deal.property_id,
                    old_stage=old_status,
                    new_stage=update_data['status'],
                    changed_by="demo@realestateos.com"
                )

            return deal

    raise HTTPException(status_code=404, detail="Deal not found")
