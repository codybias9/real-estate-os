"""Lead and CRM router."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from typing import Optional, List
from datetime import datetime

from ..database import get_db
from ..dependencies import get_current_user, require_permission
from ..models import User, Lead, LeadActivity, LeadNote, LeadDocument
from ..models.lead import LeadSource, LeadStatus
from ..schemas.lead import (
    LeadCreate,
    LeadUpdate,
    LeadResponse,
    LeadListResponse,
    LeadStats,
    LeadAssignRequest,
    LeadActivityCreate,
    LeadActivityResponse,
    LeadNoteCreate,
    LeadNoteResponse,
    LeadDocumentCreate,
    LeadDocumentResponse,
)

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def create_lead(
    lead: LeadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("lead:create")),
):
    """Create a new lead."""
    # Verify assigned user if provided
    if lead.assigned_to:
        assigned_user = db.query(User).filter(
            User.id == lead.assigned_to,
            User.organization_id == current_user.organization_id,
        ).first()

        if not assigned_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned user not found",
            )

    db_lead = Lead(
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        **lead.model_dump(),
    )

    db.add(db_lead)
    db.commit()
    db.refresh(db_lead)

    return db_lead


@router.get("", response_model=LeadListResponse)
def list_leads(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    source: Optional[LeadSource] = None,
    status: Optional[LeadStatus] = None,
    assigned_to: Optional[int] = None,
    min_score: Optional[int] = None,
    max_score: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("lead:read")),
):
    """List leads with filtering and pagination."""
    query = db.query(Lead).filter(
        Lead.organization_id == current_user.organization_id,
        Lead.deleted_at.is_(None),
    )

    # Apply filters
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

    if source:
        query = query.filter(Lead.source == source)

    if status:
        query = query.filter(Lead.status == status)

    if assigned_to:
        query = query.filter(Lead.assigned_to == assigned_to)

    if min_score is not None:
        query = query.filter(Lead.score >= min_score)

    if max_score is not None:
        query = query.filter(Lead.score <= max_score)

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    leads = query.order_by(Lead.created_at.desc()).offset(offset).limit(page_size).all()

    return {
        "items": leads,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/stats", response_model=LeadStats)
def get_lead_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("lead:read")),
):
    """Get lead statistics."""
    leads = db.query(Lead).filter(
        Lead.organization_id == current_user.organization_id,
        Lead.deleted_at.is_(None),
    ).all()

    total_leads = len(leads)

    # Group by status
    by_status = {}
    for status in LeadStatus:
        count = sum(1 for lead in leads if lead.status == status)
        by_status[status.value] = count

    # Group by source
    by_source = {}
    for source in LeadSource:
        count = sum(1 for lead in leads if lead.source == source)
        by_source[source.value] = count

    # Calculate average score
    avg_score = sum(lead.score for lead in leads) / total_leads if total_leads > 0 else 0.0

    # Calculate conversion rate
    converted = sum(1 for lead in leads if lead.status == LeadStatus.CONVERTED)
    conversion_rate = (converted / total_leads * 100) if total_leads > 0 else 0.0

    return {
        "total_leads": total_leads,
        "by_status": by_status,
        "by_source": by_source,
        "avg_score": avg_score,
        "conversion_rate": conversion_rate,
    }


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("lead:read")),
):
    """Get a specific lead."""
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == current_user.organization_id,
        Lead.deleted_at.is_(None),
    ).first()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    return lead


@router.put("/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: int,
    lead_update: LeadUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("lead:update")),
):
    """Update a lead."""
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == current_user.organization_id,
        Lead.deleted_at.is_(None),
    ).first()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    # Verify assigned user if being updated
    if lead_update.assigned_to is not None:
        assigned_user = db.query(User).filter(
            User.id == lead_update.assigned_to,
            User.organization_id == current_user.organization_id,
        ).first()

        if not assigned_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned user not found",
            )

    # Update lead
    update_data = lead_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lead, field, value)

    lead.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(lead)

    return lead


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("lead:delete")),
):
    """Soft delete a lead."""
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == current_user.organization_id,
        Lead.deleted_at.is_(None),
    ).first()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    lead.deleted_at = datetime.utcnow()
    db.commit()


@router.post("/{lead_id}/assign", response_model=LeadResponse)
def assign_lead(
    lead_id: int,
    request: LeadAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("lead:update")),
):
    """Assign a lead to a user."""
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == current_user.organization_id,
        Lead.deleted_at.is_(None),
    ).first()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    # Verify assigned user
    assigned_user = db.query(User).filter(
        User.id == request.user_id,
        User.organization_id == current_user.organization_id,
    ).first()

    if not assigned_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    lead.assigned_to = request.user_id
    lead.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(lead)

    return lead


# ================== LEAD ACTIVITIES ==================

@router.post("/{lead_id}/activities", response_model=LeadActivityResponse, status_code=status.HTTP_201_CREATED)
def add_lead_activity(
    lead_id: int,
    activity: LeadActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("lead:update")),
):
    """Add an activity to a lead."""
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == current_user.organization_id,
        Lead.deleted_at.is_(None),
    ).first()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    db_activity = LeadActivity(
        lead_id=lead_id,
        created_by=current_user.id,
        **activity.model_dump(),
    )

    db.add(db_activity)

    # Update last_contacted_at
    lead.last_contacted_at = datetime.utcnow()

    db.commit()
    db.refresh(db_activity)

    return db_activity


@router.get("/{lead_id}/activities", response_model=List[LeadActivityResponse])
def list_lead_activities(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("lead:read")),
):
    """List all activities for a lead."""
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == current_user.organization_id,
        Lead.deleted_at.is_(None),
    ).first()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    activities = db.query(LeadActivity).filter(
        LeadActivity.lead_id == lead_id
    ).order_by(LeadActivity.created_at.desc()).all()

    return activities


# ================== LEAD NOTES ==================

@router.post("/{lead_id}/notes", response_model=LeadNoteResponse, status_code=status.HTTP_201_CREATED)
def add_lead_note(
    lead_id: int,
    note: LeadNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("lead:update")),
):
    """Add a note to a lead."""
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == current_user.organization_id,
        Lead.deleted_at.is_(None),
    ).first()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    db_note = LeadNote(
        lead_id=lead_id,
        created_by=current_user.id,
        **note.model_dump(),
    )

    db.add(db_note)
    db.commit()
    db.refresh(db_note)

    return db_note


@router.get("/{lead_id}/notes", response_model=List[LeadNoteResponse])
def list_lead_notes(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("lead:read")),
):
    """List all notes for a lead."""
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == current_user.organization_id,
        Lead.deleted_at.is_(None),
    ).first()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    notes = db.query(LeadNote).filter(
        LeadNote.lead_id == lead_id
    ).order_by(LeadNote.is_pinned.desc(), LeadNote.created_at.desc()).all()

    return notes


# ================== LEAD DOCUMENTS ==================

@router.post("/{lead_id}/documents", response_model=LeadDocumentResponse, status_code=status.HTTP_201_CREATED)
def add_lead_document(
    lead_id: int,
    document: LeadDocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("lead:update")),
):
    """Add a document to a lead."""
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == current_user.organization_id,
        Lead.deleted_at.is_(None),
    ).first()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    db_document = LeadDocument(
        lead_id=lead_id,
        uploaded_by=current_user.id,
        **document.model_dump(),
    )

    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    return db_document


@router.get("/{lead_id}/documents", response_model=List[LeadDocumentResponse])
def list_lead_documents(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("lead:read")),
):
    """List all documents for a lead."""
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == current_user.organization_id,
        Lead.deleted_at.is_(None),
    ).first()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead not found",
        )

    documents = db.query(LeadDocument).filter(
        LeadDocument.lead_id == lead_id
    ).order_by(LeadDocument.uploaded_at.desc()).all()

    return documents
