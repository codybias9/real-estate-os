"""Property router."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

from ..database import get_db
from ..dependencies import get_current_user, require_permission
from ..models import User, Property, PropertyImage, PropertyValuation, PropertyNote, PropertyActivity
from ..models.property import PropertyType, PropertyStatus
from ..schemas.property import (
    PropertyCreate,
    PropertyUpdate,
    PropertyResponse,
    PropertyListResponse,
    PropertyImageCreate,
    PropertyImageResponse,
    PropertyValuationCreate,
    PropertyValuationResponse,
    PropertyNoteCreate,
    PropertyNoteResponse,
    PropertyActivityCreate,
    PropertyActivityResponse,
)

router = APIRouter(prefix="/properties", tags=["properties"])


@router.post("", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
def create_property(
    property: PropertyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("property:create")),
):
    """Create a new property."""
    db_property = Property(
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        **property.model_dump(),
    )

    db.add(db_property)
    db.commit()
    db.refresh(db_property)

    return db_property


@router.get("", response_model=PropertyListResponse)
def list_properties(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    property_type: Optional[PropertyType] = None,
    status: Optional[PropertyStatus] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    min_bedrooms: Optional[int] = None,
    max_bedrooms: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("property:read")),
):
    """List properties with filtering and pagination."""
    query = db.query(Property).filter(
        Property.organization_id == current_user.organization_id,
        Property.deleted_at.is_(None),
    )

    # Apply filters
    if search:
        query = query.filter(
            or_(
                Property.address.ilike(f"%{search}%"),
                Property.city.ilike(f"%{search}%"),
                Property.state.ilike(f"%{search}%"),
                Property.description.ilike(f"%{search}%"),
            )
        )

    if city:
        query = query.filter(Property.city.ilike(f"%{city}%"))

    if state:
        query = query.filter(Property.state.ilike(f"%{state}%"))

    if property_type:
        query = query.filter(Property.property_type == property_type)

    if status:
        query = query.filter(Property.status == status)

    if min_price is not None:
        query = query.filter(Property.price >= min_price)

    if max_price is not None:
        query = query.filter(Property.price <= max_price)

    if min_bedrooms is not None:
        query = query.filter(Property.bedrooms >= min_bedrooms)

    if max_bedrooms is not None:
        query = query.filter(Property.bedrooms <= max_bedrooms)

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    properties = query.order_by(Property.created_at.desc()).offset(offset).limit(page_size).all()

    return {
        "items": properties,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/{property_id}", response_model=PropertyResponse)
def get_property(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("property:read")),
):
    """Get a specific property."""
    property = db.query(Property).filter(
        Property.id == property_id,
        Property.organization_id == current_user.organization_id,
        Property.deleted_at.is_(None),
    ).first()

    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    return property


@router.put("/{property_id}", response_model=PropertyResponse)
def update_property(
    property_id: int,
    property_update: PropertyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("property:update")),
):
    """Update a property."""
    property = db.query(Property).filter(
        Property.id == property_id,
        Property.organization_id == current_user.organization_id,
        Property.deleted_at.is_(None),
    ).first()

    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    # Update property
    update_data = property_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(property, field, value)

    property.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(property)

    return property


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_property(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("property:delete")),
):
    """Soft delete a property."""
    property = db.query(Property).filter(
        Property.id == property_id,
        Property.organization_id == current_user.organization_id,
        Property.deleted_at.is_(None),
    ).first()

    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    property.deleted_at = datetime.utcnow()
    db.commit()


# ================== PROPERTY IMAGES ==================

@router.post("/{property_id}/images", response_model=PropertyImageResponse, status_code=status.HTTP_201_CREATED)
def add_property_image(
    property_id: int,
    image: PropertyImageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("property:update")),
):
    """Add an image to a property."""
    property = db.query(Property).filter(
        Property.id == property_id,
        Property.organization_id == current_user.organization_id,
        Property.deleted_at.is_(None),
    ).first()

    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    db_image = PropertyImage(
        property_id=property_id,
        **image.model_dump(),
    )

    db.add(db_image)
    db.commit()
    db.refresh(db_image)

    return db_image


@router.get("/{property_id}/images", response_model=List[PropertyImageResponse])
def list_property_images(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("property:read")),
):
    """List all images for a property."""
    property = db.query(Property).filter(
        Property.id == property_id,
        Property.organization_id == current_user.organization_id,
        Property.deleted_at.is_(None),
    ).first()

    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    images = db.query(PropertyImage).filter(
        PropertyImage.property_id == property_id
    ).order_by(PropertyImage.order, PropertyImage.created_at).all()

    return images


@router.delete("/{property_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_property_image(
    property_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("property:update")),
):
    """Delete a property image."""
    property = db.query(Property).filter(
        Property.id == property_id,
        Property.organization_id == current_user.organization_id,
        Property.deleted_at.is_(None),
    ).first()

    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    image = db.query(PropertyImage).filter(
        PropertyImage.id == image_id,
        PropertyImage.property_id == property_id,
    ).first()

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    db.delete(image)
    db.commit()


# ================== PROPERTY VALUATIONS ==================

@router.post("/{property_id}/valuations", response_model=PropertyValuationResponse, status_code=status.HTTP_201_CREATED)
def add_property_valuation(
    property_id: int,
    valuation: PropertyValuationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("property:update")),
):
    """Add a valuation to a property."""
    property = db.query(Property).filter(
        Property.id == property_id,
        Property.organization_id == current_user.organization_id,
        Property.deleted_at.is_(None),
    ).first()

    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    db_valuation = PropertyValuation(
        property_id=property_id,
        created_by=current_user.id,
        **valuation.model_dump(),
    )

    db.add(db_valuation)
    db.commit()
    db.refresh(db_valuation)

    return db_valuation


@router.get("/{property_id}/valuations", response_model=List[PropertyValuationResponse])
def list_property_valuations(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("property:read")),
):
    """List all valuations for a property."""
    property = db.query(Property).filter(
        Property.id == property_id,
        Property.organization_id == current_user.organization_id,
        Property.deleted_at.is_(None),
    ).first()

    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    valuations = db.query(PropertyValuation).filter(
        PropertyValuation.property_id == property_id
    ).order_by(PropertyValuation.valuation_date.desc()).all()

    return valuations


# ================== PROPERTY NOTES ==================

@router.post("/{property_id}/notes", response_model=PropertyNoteResponse, status_code=status.HTTP_201_CREATED)
def add_property_note(
    property_id: int,
    note: PropertyNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("property:update")),
):
    """Add a note to a property."""
    property = db.query(Property).filter(
        Property.id == property_id,
        Property.organization_id == current_user.organization_id,
        Property.deleted_at.is_(None),
    ).first()

    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    db_note = PropertyNote(
        property_id=property_id,
        created_by=current_user.id,
        **note.model_dump(),
    )

    db.add(db_note)
    db.commit()
    db.refresh(db_note)

    return db_note


@router.get("/{property_id}/notes", response_model=List[PropertyNoteResponse])
def list_property_notes(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("property:read")),
):
    """List all notes for a property."""
    property = db.query(Property).filter(
        Property.id == property_id,
        Property.organization_id == current_user.organization_id,
        Property.deleted_at.is_(None),
    ).first()

    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    notes = db.query(PropertyNote).filter(
        PropertyNote.property_id == property_id
    ).order_by(PropertyNote.created_at.desc()).all()

    return notes


# ================== PROPERTY ACTIVITIES ==================

@router.post("/{property_id}/activities", response_model=PropertyActivityResponse, status_code=status.HTTP_201_CREATED)
def add_property_activity(
    property_id: int,
    activity: PropertyActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("property:update")),
):
    """Add an activity to a property."""
    property = db.query(Property).filter(
        Property.id == property_id,
        Property.organization_id == current_user.organization_id,
        Property.deleted_at.is_(None),
    ).first()

    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    db_activity = PropertyActivity(
        property_id=property_id,
        created_by=current_user.id,
        **activity.model_dump(),
    )

    db.add(db_activity)
    db.commit()
    db.refresh(db_activity)

    return db_activity


@router.get("/{property_id}/activities", response_model=List[PropertyActivityResponse])
def list_property_activities(
    property_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("property:read")),
):
    """List all activities for a property."""
    property = db.query(Property).filter(
        Property.id == property_id,
        Property.organization_id == current_user.organization_id,
        Property.deleted_at.is_(None),
    ).first()

    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    activities = db.query(PropertyActivity).filter(
        PropertyActivity.property_id == property_id
    ).order_by(PropertyActivity.created_at.desc()).all()

    return activities
