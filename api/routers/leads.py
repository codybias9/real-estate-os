"""Lead router."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional, List
from datetime import datetime
from ..database import get_db
from ..dependencies import get_current_user
from ..models import User, Lead, LeadActivity, LeadNote, Property
from ..models.lead import LeadStatus, LeadSource, LeadType
from ..schemas.lead import (
    LeadCreate,
    LeadUpdate,
    LeadResponse,
    LeadListResponse,
    LeadActivityCreate,
    LeadActivityResponse,
    LeadNoteCreate,
    LeadNoteResponse,
    LeadAssignRequest,
)
import math

router = APIRouter(prefix="/leads", tags=["Leads"])


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def create_lead(
    lead_data: LeadCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new lead."""
    # Verify property belongs to organization if provided
    if lead_data.property_id:
        property = db.query(Property).filter(
            Property.id == lead_data.property_id,
            Property.organization_id == current_user.organization_id,
        ).first()
        if not property:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Property not found",
            )

    # Verify assigned user belongs to organization if provided
    if lead_data.assigned_to_id:
        assigned_user = db.query(User).filter(
            User.id == lead_data.assigned_to_id,
            User.organization_id == current_user.organization_id,
        ).first()
        if not assigned_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned user not found",
            )

    lead = Lead(
        organization_id=current_user.organization_id,
        created_by_id=current_user.id,
        **lead_data.model_dump()
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    return lead


@router.get("", response_model=LeadListResponse)
def list_leads(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[LeadStatus] = None,
    lead_type: Optional[LeadType] = None,
    source: Optional[LeadSource] = None,
    assigned_to_id: Optional[int] = None,
    property_id: Optional[int] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List leads with filtering and pagination."""
    query = db.query(Lead).filter(
        Lead.organization_id == current_user.organization_id,
        Lead.deleted_at.is_(None),
    )

    # Apply filters
    if status:
        query = query.filter(Lead.status == status)
    if lead_type:
        query = query.filter(Lead.lead_type == lead_type)
    if source:
        query = query.filter(Lead.source == source)
    if assigned_to_id:
        query = query.filter(Lead.assigned_to_id == assigned_to_id)
    if property_id:
        query = query.filter(Lead.property_id == property_id)
    if search:
        query = query.filter(
            or_(
                Lead.first_name.ilike(f"%{search}%"),
                Lead.last_name.ilike(f"%{search}%"),
                Lead.email.ilike(f"%{search}%"),
                Lead.phone.ilike(f"%{search}%"),
                Lead.company.ilike(f"%{search}%"),
            )
        )

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    leads = query.order_by(Lead.created_at.desc()).offset(offset).limit(page_size).all()

    return LeadListResponse(
        items=leads,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get lead by ID."""
    lead = (
        db.query(Lead)
        .filter(
            Lead.id == lead_id,
            Lead.organization_id == current_user.organization_id,
            Lead.deleted_at.is_(None),
        )
        .first()
    )

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    return lead


@router.patch("/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: int,
    lead_data: LeadUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update lead."""
    lead = (
        db.query(Lead)
        .filter(
            Lead.id == lead_id,
            Lead.organization_id == current_user.organization_id,
            Lead.deleted_at.is_(None),
        )
        .first()
    )

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    # Update fields
    update_data = lead_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lead, field, value)

    db.commit()
    db.refresh(lead)

    return lead


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft delete lead."""
    lead = (
        db.query(Lead)
        .filter(
            Lead.id == lead_id,
            Lead.organization_id == current_user.organization_id,
            Lead.deleted_at.is_(None),
        )
        .first()
    )

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    lead.deleted_at = datetime.utcnow()
    lead.deleted_by = current_user.id
    db.commit()


@router.post("/{lead_id}/assign", response_model=LeadResponse)
def assign_lead(
    lead_id: int,
    assignment: LeadAssignRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Assign lead to a user."""
    lead = (
        db.query(Lead)
        .filter(
            Lead.id == lead_id,
            Lead.organization_id == current_user.organization_id,
            Lead.deleted_at.is_(None),
        )
        .first()
    )

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    # Verify user belongs to organization
    assigned_user = db.query(User).filter(
        User.id == assignment.user_id,
        User.organization_id == current_user.organization_id,
    ).first()

    if not assigned_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found",
        )

    lead.assigned_to_id = assignment.user_id
    db.commit()
    db.refresh(lead)

    # Log activity
    activity = LeadActivity(
        lead_id=lead.id,
        user_id=current_user.id,
        activity_type="assigned",
        description=f"Lead assigned to {assigned_user.first_name} {assigned_user.last_name}",
    )
    db.add(activity)
    db.commit()

    return lead


# Lead Activities


@router.post("/{lead_id}/activities", response_model=LeadActivityResponse, status_code=status.HTTP_201_CREATED)
def add_lead_activity(
    lead_id: int,
    activity_data: LeadActivityCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add activity to lead."""
    lead = (
        db.query(Lead)
        .filter(
            Lead.id == lead_id,
            Lead.organization_id == current_user.organization_id,
            Lead.deleted_at.is_(None),
        )
        .first()
    )

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    activity = LeadActivity(
        lead_id=lead_id,
        user_id=current_user.id,
        **activity_data.model_dump()
    )
    db.add(activity)

    # Update last_contacted_at if applicable
    if activity_data.activity_type in ["call", "email", "meeting", "sms"]:
        lead.last_contacted_at = datetime.utcnow()

    db.commit()
    db.refresh(activity)

    return activity


@router.get("/{lead_id}/activities", response_model=List[LeadActivityResponse])
def list_lead_activities(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List lead activities."""
    lead = (
        db.query(Lead)
        .filter(
            Lead.id == lead_id,
            Lead.organization_id == current_user.organization_id,
            Lead.deleted_at.is_(None),
        )
        .first()
    )

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    activities = (
        db.query(LeadActivity)
        .filter(LeadActivity.lead_id == lead_id)
        .order_by(LeadActivity.created_at.desc())
        .limit(100)
        .all()
    )

    return activities


# Lead Notes


@router.post("/{lead_id}/notes", response_model=LeadNoteResponse, status_code=status.HTTP_201_CREATED)
def add_lead_note(
    lead_id: int,
    note_data: LeadNoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add note to lead."""
    lead = (
        db.query(Lead)
        .filter(
            Lead.id == lead_id,
            Lead.organization_id == current_user.organization_id,
            Lead.deleted_at.is_(None),
        )
        .first()
    )

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    note = LeadNote(
        lead_id=lead_id,
        created_by_id=current_user.id,
        **note_data.model_dump()
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    return note


@router.get("/{lead_id}/notes", response_model=List[LeadNoteResponse])
def list_lead_notes(
    lead_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List lead notes."""
    lead = (
        db.query(Lead)
        .filter(
            Lead.id == lead_id,
            Lead.organization_id == current_user.organization_id,
            Lead.deleted_at.is_(None),
        )
        .first()
    )

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    notes = (
        db.query(LeadNote)
        .filter(
            LeadNote.lead_id == lead_id,
            LeadNote.deleted_at.is_(None),
        )
        .order_by(LeadNote.is_pinned.desc(), LeadNote.created_at.desc())
        .all()
    )

    return notes


# Lead Statistics


@router.get("/stats/overview", response_model=dict)
def get_lead_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get lead statistics."""
    base_query = db.query(Lead).filter(
        Lead.organization_id == current_user.organization_id,
        Lead.deleted_at.is_(None),
    )

    total_leads = base_query.count()
    new_leads = base_query.filter(Lead.status == LeadStatus.NEW).count()
    qualified_leads = base_query.filter(Lead.status == LeadStatus.QUALIFIED).count()
    converted_leads = base_query.filter(Lead.status == LeadStatus.CONVERTED).count()

    # Leads by source
    leads_by_source = (
        db.query(Lead.source, func.count(Lead.id))
        .filter(
            Lead.organization_id == current_user.organization_id,
            Lead.deleted_at.is_(None),
        )
        .group_by(Lead.source)
        .all()
    )

    # Leads by type
    leads_by_type = (
        db.query(Lead.lead_type, func.count(Lead.id))
        .filter(
            Lead.organization_id == current_user.organization_id,
            Lead.deleted_at.is_(None),
        )
        .group_by(Lead.lead_type)
        .all()
    )

    return {
        "total_leads": total_leads,
        "new_leads": new_leads,
        "qualified_leads": qualified_leads,
        "converted_leads": converted_leads,
        "conversion_rate": round((converted_leads / total_leads * 100) if total_leads > 0 else 0, 2),
        "by_source": dict(leads_by_source),
        "by_type": dict(leads_by_type),
    }
