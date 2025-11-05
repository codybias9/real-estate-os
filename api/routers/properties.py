"""Property router."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional, List
from datetime import datetime
from ..database import get_db
from ..dependencies import get_current_user, require_permission
from ..models import (
    User,
    Property,
    PropertyImage,
    PropertyValuation,
    PropertyNote,
    PropertyActivity,
)
from ..models.property import PropertyStatus, PropertyType
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
    PropertyActivityResponse,
)
import math

router = APIRouter(prefix="/properties", tags=["Properties"])


@router.post("", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
def create_property(
    property_data: PropertyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new property."""
    property = Property(
        organization_id=current_user.organization_id,
        **property_data.model_dump()
    )
    db.add(property)
    db.commit()
    db.refresh(property)

    # Log activity
    activity = PropertyActivity(
        property_id=property.id,
        user_id=current_user.id,
        activity_type="created",
        description="Property created",
    )
    db.add(activity)
    db.commit()

    return property


@router.get("", response_model=PropertyListResponse)
def list_properties(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[PropertyStatus] = None,
    property_type: Optional[PropertyType] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    zip_code: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_bedrooms: Optional[int] = None,
    max_bedrooms: Optional[int] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List properties with filtering and pagination."""
    query = db.query(Property).filter(
        Property.organization_id == current_user.organization_id,
        Property.deleted_at.is_(None),
    )

    # Apply filters
    if status:
        query = query.filter(Property.status == status)
    if property_type:
        query = query.filter(Property.property_type == property_type)
    if city:
        query = query.filter(Property.city.ilike(f"%{city}%"))
    if state:
        query = query.filter(Property.state.ilike(f"%{state}%"))
    if zip_code:
        query = query.filter(Property.zip_code == zip_code)
    if min_price is not None:
        query = query.filter(Property.list_price >= min_price)
    if max_price is not None:
        query = query.filter(Property.list_price <= max_price)
    if min_bedrooms is not None:
        query = query.filter(Property.bedrooms >= min_bedrooms)
    if max_bedrooms is not None:
        query = query.filter(Property.bedrooms <= max_bedrooms)
    if search:
        query = query.filter(
            or_(
                Property.address.ilike(f"%{search}%"),
                Property.description.ilike(f"%{search}%"),
                Property.owner_name.ilike(f"%{search}%"),
            )
        )

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    properties = query.order_by(Property.created_at.desc()).offset(offset).limit(page_size).all()

    return PropertyListResponse(
        items=properties,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/{property_id}", response_model=PropertyResponse)
def get_property(
    property_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get property by ID."""
    property = (
        db.query(Property)
        .filter(
            Property.id == property_id,
            Property.organization_id == current_user.organization_id,
            Property.deleted_at.is_(None),
        )
        .first()
    )

    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    # Log activity
    activity = PropertyActivity(
        property_id=property.id,
        user_id=current_user.id,
        activity_type="viewed",
        description="Property viewed",
    )
    db.add(activity)
    db.commit()

    return property


@router.patch("/{property_id}", response_model=PropertyResponse)
def update_property(
    property_id: int,
    property_data: PropertyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update property."""
    property = (
        db.query(Property)
        .filter(
            Property.id == property_id,
            Property.organization_id == current_user.organization_id,
            Property.deleted_at.is_(None),
        )
        .first()
    )

    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    # Update fields
    update_data = property_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(property, field, value)

    db.commit()
    db.refresh(property)

    # Log activity
    activity = PropertyActivity(
        property_id=property.id,
        user_id=current_user.id,
        activity_type="updated",
        description="Property updated",
    )
    db.add(activity)
    db.commit()

    return property


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_property(
    property_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft delete property."""
    property = (
        db.query(Property)
        .filter(
            Property.id == property_id,
            Property.organization_id == current_user.organization_id,
            Property.deleted_at.is_(None),
        )
        .first()
    )

    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    property.deleted_at = datetime.utcnow()
    property.deleted_by = current_user.id
    db.commit()


# Property Images


@router.post("/{property_id}/images", response_model=PropertyImageResponse, status_code=status.HTTP_201_CREATED)
def add_property_image(
    property_id: int,
    image_data: PropertyImageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add image to property."""
    property = (
        db.query(Property)
        .filter(
            Property.id == property_id,
            Property.organization_id == current_user.organization_id,
            Property.deleted_at.is_(None),
        )
        .first()
    )

    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    image = PropertyImage(
        property_id=property_id,
        **image_data.model_dump()
    )
    db.add(image)
    db.commit()
    db.refresh(image)

    return image


@router.get("/{property_id}/images", response_model=List[PropertyImageResponse])
def list_property_images(
    property_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List property images."""
    property = (
        db.query(Property)
        .filter(
            Property.id == property_id,
            Property.organization_id == current_user.organization_id,
            Property.deleted_at.is_(None),
        )
        .first()
    )

    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    images = (
        db.query(PropertyImage)
        .filter(PropertyImage.property_id == property_id)
        .order_by(PropertyImage.display_order, PropertyImage.created_at)
        .all()
    )

    return images


@router.delete("/{property_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_property_image(
    property_id: int,
    image_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete property image."""
    property = (
        db.query(Property)
        .filter(
            Property.id == property_id,
            Property.organization_id == current_user.organization_id,
            Property.deleted_at.is_(None),
        )
        .first()
    )

    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    image = (
        db.query(PropertyImage)
        .filter(
            PropertyImage.id == image_id,
            PropertyImage.property_id == property_id,
        )
        .first()
    )

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    db.delete(image)
    db.commit()


# Property Valuations


@router.post("/{property_id}/valuations", response_model=PropertyValuationResponse, status_code=status.HTTP_201_CREATED)
def add_property_valuation(
    property_id: int,
    valuation_data: PropertyValuationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add valuation to property."""
    property = (
        db.query(Property)
        .filter(
            Property.id == property_id,
            Property.organization_id == current_user.organization_id,
            Property.deleted_at.is_(None),
        )
        .first()
    )

    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    valuation = PropertyValuation(
        property_id=property_id,
        **valuation_data.model_dump()
    )
    db.add(valuation)
    db.commit()
    db.refresh(valuation)

    return valuation


@router.get("/{property_id}/valuations", response_model=List[PropertyValuationResponse])
def list_property_valuations(
    property_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List property valuations."""
    property = (
        db.query(Property)
        .filter(
            Property.id == property_id,
            Property.organization_id == current_user.organization_id,
            Property.deleted_at.is_(None),
        )
        .first()
    )

    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    valuations = (
        db.query(PropertyValuation)
        .filter(PropertyValuation.property_id == property_id)
        .order_by(PropertyValuation.valuation_date.desc())
        .all()
    )

    return valuations


# Property Notes


@router.post("/{property_id}/notes", response_model=PropertyNoteResponse, status_code=status.HTTP_201_CREATED)
def add_property_note(
    property_id: int,
    note_data: PropertyNoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add note to property."""
    property = (
        db.query(Property)
        .filter(
            Property.id == property_id,
            Property.organization_id == current_user.organization_id,
            Property.deleted_at.is_(None),
        )
        .first()
    )

    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    note = PropertyNote(
        property_id=property_id,
        created_by_id=current_user.id,
        **note_data.model_dump()
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    return note


@router.get("/{property_id}/notes", response_model=List[PropertyNoteResponse])
def list_property_notes(
    property_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List property notes."""
    property = (
        db.query(Property)
        .filter(
            Property.id == property_id,
            Property.organization_id == current_user.organization_id,
            Property.deleted_at.is_(None),
        )
        .first()
    )

    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    notes = (
        db.query(PropertyNote)
        .filter(
            PropertyNote.property_id == property_id,
            PropertyNote.deleted_at.is_(None),
        )
        .order_by(PropertyNote.is_pinned.desc(), PropertyNote.created_at.desc())
        .all()
    )

    return notes


# Property Activities


@router.get("/{property_id}/activities", response_model=List[PropertyActivityResponse])
def list_property_activities(
    property_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List property activities."""
    property = (
        db.query(Property)
        .filter(
            Property.id == property_id,
            Property.organization_id == current_user.organization_id,
            Property.deleted_at.is_(None),
        )
        .first()
    )

    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    activities = (
        db.query(PropertyActivity)
        .filter(PropertyActivity.property_id == property_id)
        .order_by(PropertyActivity.created_at.desc())
        .limit(100)
        .all()
    )

    return activities
