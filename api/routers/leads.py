"""
Lead router - CRM operations for leads
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from datetime import datetime
import uuid
import math

from api.core.database import get_db
from api.dependencies.auth import (
    get_current_active_user,
    get_current_organization,
    PermissionChecker
)
from api.core.exceptions import ResourceNotFoundError
from api.schemas.lead import (
    LeadCreate,
    LeadUpdate,
    LeadResponse,
    LeadListResponse,
    LeadActivityCreate,
    LeadActivityResponse,
    LeadNoteCreate,
    LeadNoteResponse,
)
from api.schemas.auth import MessageResponse
from db.models import (
    User,
    Organization,
    Lead,
    LeadActivity,
    LeadNote,
    LeadStatus
)


router = APIRouter(prefix="/leads", tags=["Leads"])


# ============================================================================
# LEAD CRUD OPERATIONS
# ============================================================================

@router.post(
    "",
    response_model=LeadResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(["lead:create"]))]
)
async def create_lead(
    lead_data: LeadCreate,
    current_user: User = Depends(get_current_active_user),
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """
    Create a new lead.
    Requires 'lead:create' permission.
    """
    lead_dict = lead_data.model_dump()

    # Create lead
    lead = Lead(
        id=uuid.uuid4(),
        organization_id=organization.id,
        **lead_dict
    )

    db.add(lead)
    db.commit()
    db.refresh(lead)

    return LeadResponse.from_orm(lead)


@router.get(
    "",
    response_model=LeadListResponse,
    dependencies=[Depends(PermissionChecker(["lead:read"]))]
)
async def list_leads(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    assigned_to: Optional[uuid.UUID] = Query(None, description="Filter by assigned user"),
    search: Optional[str] = Query(None, description="Search in name, email, phone"),
    min_score: Optional[float] = Query(None, ge=0, le=100, description="Minimum lead score"),
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """
    List leads with pagination and filtering.
    Requires 'lead:read' permission.
    """
    # Base query
    query = db.query(Lead).filter(
        Lead.organization_id == organization.id,
        Lead.deleted_at.is_(None)
    )

    # Apply filters
    if status:
        query = query.filter(Lead.status == status)

    if assigned_to:
        query = query.filter(Lead.assigned_to == assigned_to)

    if min_score is not None:
        query = query.filter(Lead.score >= min_score)

    if search:
        query = query.filter(
            or_(
                Lead.first_name.ilike(f"%{search}%"),
                Lead.last_name.ilike(f"%{search}%"),
                Lead.email.ilike(f"%{search}%"),
                Lead.phone.ilike(f"%{search}%"),
                Lead.company.ilike(f"%{search}%")
            )
        )

    # Get total count
    total = query.count()

    # Apply pagination
    skip = (page - 1) * page_size
    leads = query.order_by(Lead.created_at.desc()).offset(skip).limit(page_size).all()

    # Calculate total pages
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return LeadListResponse(
        leads=[LeadResponse.from_orm(lead) for lead in leads],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get(
    "/{lead_id}",
    response_model=LeadResponse,
    dependencies=[Depends(PermissionChecker(["lead:read"]))]
)
async def get_lead(
    lead_id: uuid.UUID,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """
    Get a single lead by ID.
    Requires 'lead:read' permission.
    """
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == organization.id,
        Lead.deleted_at.is_(None)
    ).first()

    if not lead:
        raise ResourceNotFoundError("Lead", str(lead_id))

    return LeadResponse.from_orm(lead)


@router.put(
    "/{lead_id}",
    response_model=LeadResponse,
    dependencies=[Depends(PermissionChecker(["lead:update"]))]
)
async def update_lead(
    lead_id: uuid.UUID,
    lead_data: LeadUpdate,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """
    Update a lead.
    Requires 'lead:update' permission.
    """
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == organization.id,
        Lead.deleted_at.is_(None)
    ).first()

    if not lead:
        raise ResourceNotFoundError("Lead", str(lead_id))

    # Update only provided fields
    update_data = lead_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lead, field, value)

    db.commit()
    db.refresh(lead)

    return LeadResponse.from_orm(lead)


@router.delete(
    "/{lead_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(PermissionChecker(["lead:delete"]))]
)
async def delete_lead(
    lead_id: uuid.UUID,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """
    Soft delete a lead.
    Requires 'lead:delete' permission.
    """
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == organization.id,
        Lead.deleted_at.is_(None)
    ).first()

    if not lead:
        raise ResourceNotFoundError("Lead", str(lead_id))

    # Soft delete
    lead.deleted_at = datetime.utcnow()
    db.commit()

    return None


# ============================================================================
# LEAD ACTIVITIES
# ============================================================================

@router.post(
    "/{lead_id}/activities",
    response_model=LeadActivityResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(["lead:update"]))]
)
async def create_lead_activity(
    lead_id: uuid.UUID,
    activity_data: LeadActivityCreate,
    current_user: User = Depends(get_current_active_user),
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """
    Create a new activity for a lead.
    Requires 'lead:update' permission.
    """
    # Verify lead exists and belongs to organization
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == organization.id
    ).first()

    if not lead:
        raise ResourceNotFoundError("Lead", str(lead_id))

    # Create activity
    activity = LeadActivity(
        id=uuid.uuid4(),
        user_id=current_user.id,
        **activity_data.model_dump()
    )

    db.add(activity)

    # Update lead's last contact date
    lead.last_contact_date = datetime.utcnow()

    db.commit()
    db.refresh(activity)

    return LeadActivityResponse.from_orm(activity)


@router.get(
    "/{lead_id}/activities",
    response_model=List[LeadActivityResponse],
    dependencies=[Depends(PermissionChecker(["lead:read"]))]
)
async def get_lead_activities(
    lead_id: uuid.UUID,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """
    Get all activities for a lead.
    Requires 'lead:read' permission.
    """
    # Verify lead exists and belongs to organization
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == organization.id
    ).first()

    if not lead:
        raise ResourceNotFoundError("Lead", str(lead_id))

    activities = db.query(LeadActivity).filter(
        LeadActivity.lead_id == lead_id
    ).order_by(LeadActivity.activity_date.desc()).all()

    return [LeadActivityResponse.from_orm(activity) for activity in activities]


# ============================================================================
# LEAD NOTES
# ============================================================================

@router.post(
    "/{lead_id}/notes",
    response_model=LeadNoteResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(["lead:update"]))]
)
async def create_lead_note(
    lead_id: uuid.UUID,
    note_data: LeadNoteCreate,
    current_user: User = Depends(get_current_active_user),
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """
    Create a new note for a lead.
    Requires 'lead:update' permission.
    """
    # Verify lead exists and belongs to organization
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == organization.id
    ).first()

    if not lead:
        raise ResourceNotFoundError("Lead", str(lead_id))

    # Create note
    note = LeadNote(
        id=uuid.uuid4(),
        user_id=current_user.id,
        **note_data.model_dump()
    )

    db.add(note)
    db.commit()
    db.refresh(note)

    return LeadNoteResponse.from_orm(note)


@router.get(
    "/{lead_id}/notes",
    response_model=List[LeadNoteResponse],
    dependencies=[Depends(PermissionChecker(["lead:read"]))]
)
async def get_lead_notes(
    lead_id: uuid.UUID,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """
    Get all notes for a lead.
    Requires 'lead:read' permission.
    """
    # Verify lead exists and belongs to organization
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == organization.id
    ).first()

    if not lead:
        raise ResourceNotFoundError("Lead", str(lead_id))

    notes = db.query(LeadNote).filter(
        LeadNote.lead_id == lead_id
    ).order_by(
        LeadNote.is_pinned.desc(),
        LeadNote.created_at.desc()
    ).all()

    return [LeadNoteResponse.from_orm(note) for note in notes]


# ============================================================================
# LEAD ASSIGNMENT
# ============================================================================

@router.put(
    "/{lead_id}/assign",
    response_model=LeadResponse,
    dependencies=[Depends(PermissionChecker(["lead:update"]))]
)
async def assign_lead(
    lead_id: uuid.UUID,
    user_id: uuid.UUID,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """
    Assign a lead to a user.
    Requires 'lead:update' permission.
    """
    # Verify lead exists
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == organization.id,
        Lead.deleted_at.is_(None)
    ).first()

    if not lead:
        raise ResourceNotFoundError("Lead", str(lead_id))

    # Verify user exists and belongs to same organization
    user = db.query(User).filter(
        User.id == user_id,
        User.organization_id == organization.id
    ).first()

    if not user:
        raise ResourceNotFoundError("User", str(user_id))

    # Assign lead
    lead.assigned_to = user_id

    db.commit()
    db.refresh(lead)

    return LeadResponse.from_orm(lead)
