"""
Property router - CRUD operations for properties
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
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
from api.core.exceptions import ResourceNotFoundError, PermissionDeniedError
from api.schemas.property import (
    PropertyCreate,
    PropertyUpdate,
    PropertyResponse,
    PropertyListResponse,
    PropertyImageCreate,
    PropertyImageResponse,
    PropertyValuationCreate,
    PropertyValuationResponse,
)
from db.models import (
    User,
    Organization,
    Property,
    PropertyImage,
    PropertyValuation,
    PropertyStatus
)


router = APIRouter(prefix="/properties", tags=["Properties"])


# ============================================================================
# PROPERTY CRUD OPERATIONS
# ============================================================================

@router.post(
    "",
    response_model=PropertyResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(["property:create"]))]
)
async def create_property(
    property_data: PropertyCreate,
    current_user: User = Depends(get_current_active_user),
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """
    Create a new property.
    Requires 'property:create' permission.
    """
    property_dict = property_data.model_dump()

    # Create property
    property_obj = Property(
        id=uuid.uuid4(),
        organization_id=organization.id,
        **property_dict
    )

    db.add(property_obj)
    db.commit()
    db.refresh(property_obj)

    return PropertyResponse.from_orm(property_obj)


@router.get(
    "",
    response_model=PropertyListResponse,
    dependencies=[Depends(PermissionChecker(["property:read"]))]
)
async def list_properties(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    city: Optional[str] = Query(None, description="Filter by city"),
    state: Optional[str] = Query(None, description="Filter by state"),
    property_type: Optional[str] = Query(None, description="Filter by property type"),
    min_price: Optional[float] = Query(None, description="Minimum price"),
    max_price: Optional[float] = Query(None, description="Maximum price"),
    bedrooms: Optional[int] = Query(None, description="Filter by bedrooms"),
    search: Optional[str] = Query(None, description="Search in address"),
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """
    List properties with pagination and filtering.
    Requires 'property:read' permission.
    """
    # Base query - only properties in user's organization
    query = db.query(Property).filter(
        Property.organization_id == organization.id,
        Property.deleted_at.is_(None)
    )

    # Apply filters
    if status:
        query = query.filter(Property.status == status)

    if city:
        query = query.filter(Property.city.ilike(f"%{city}%"))

    if state:
        query = query.filter(Property.state == state)

    if property_type:
        query = query.filter(Property.property_type == property_type)

    if min_price is not None:
        query = query.filter(Property.current_value >= min_price)

    if max_price is not None:
        query = query.filter(Property.current_value <= max_price)

    if bedrooms is not None:
        query = query.filter(Property.bedrooms == bedrooms)

    if search:
        query = query.filter(
            or_(
                Property.address_line1.ilike(f"%{search}%"),
                Property.address_line2.ilike(f"%{search}%"),
                Property.city.ilike(f"%{search}%"),
                Property.zip_code.ilike(f"%{search}%")
            )
        )

    # Get total count
    total = query.count()

    # Apply pagination
    skip = (page - 1) * page_size
    properties = query.offset(skip).limit(page_size).all()

    # Calculate total pages
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PropertyListResponse(
        properties=[PropertyResponse.from_orm(p) for p in properties],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get(
    "/{property_id}",
    response_model=PropertyResponse,
    dependencies=[Depends(PermissionChecker(["property:read"]))]
)
async def get_property(
    property_id: uuid.UUID,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """
    Get a single property by ID.
    Requires 'property:read' permission.
    """
    property_obj = db.query(Property).filter(
        Property.id == property_id,
        Property.organization_id == organization.id,
        Property.deleted_at.is_(None)
    ).first()

    if not property_obj:
        raise ResourceNotFoundError("Property", str(property_id))

    return PropertyResponse.from_orm(property_obj)


@router.put(
    "/{property_id}",
    response_model=PropertyResponse,
    dependencies=[Depends(PermissionChecker(["property:update"]))]
)
async def update_property(
    property_id: uuid.UUID,
    property_data: PropertyUpdate,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """
    Update a property.
    Requires 'property:update' permission.
    """
    property_obj = db.query(Property).filter(
        Property.id == property_id,
        Property.organization_id == organization.id,
        Property.deleted_at.is_(None)
    ).first()

    if not property_obj:
        raise ResourceNotFoundError("Property", str(property_id))

    # Update only provided fields
    update_data = property_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(property_obj, field, value)

    db.commit()
    db.refresh(property_obj)

    return PropertyResponse.from_orm(property_obj)


@router.delete(
    "/{property_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(PermissionChecker(["property:delete"]))]
)
async def delete_property(
    property_id: uuid.UUID,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """
    Soft delete a property.
    Requires 'property:delete' permission.
    """
    property_obj = db.query(Property).filter(
        Property.id == property_id,
        Property.organization_id == organization.id,
        Property.deleted_at.is_(None)
    ).first()

    if not property_obj:
        raise ResourceNotFoundError("Property", str(property_id))

    # Soft delete
    property_obj.deleted_at = datetime.utcnow()
    db.commit()

    return None


# ============================================================================
# PROPERTY IMAGES
# ============================================================================

@router.post(
    "/{property_id}/images",
    response_model=PropertyImageResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(["property:update"]))]
)
async def add_property_image(
    property_id: uuid.UUID,
    image_data: PropertyImageCreate,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """
    Add an image to a property.
    Requires 'property:update' permission.
    """
    # Verify property exists and belongs to organization
    property_obj = db.query(Property).filter(
        Property.id == property_id,
        Property.organization_id == organization.id
    ).first()

    if not property_obj:
        raise ResourceNotFoundError("Property", str(property_id))

    # Create image
    image = PropertyImage(
        id=uuid.uuid4(),
        **image_data.model_dump()
    )

    db.add(image)
    db.commit()
    db.refresh(image)

    return PropertyImageResponse.from_orm(image)


@router.get(
    "/{property_id}/images",
    response_model=List[PropertyImageResponse],
    dependencies=[Depends(PermissionChecker(["property:read"]))]
)
async def get_property_images(
    property_id: uuid.UUID,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """
    Get all images for a property.
    Requires 'property:read' permission.
    """
    # Verify property exists and belongs to organization
    property_obj = db.query(Property).filter(
        Property.id == property_id,
        Property.organization_id == organization.id
    ).first()

    if not property_obj:
        raise ResourceNotFoundError("Property", str(property_id))

    images = db.query(PropertyImage).filter(
        PropertyImage.property_id == property_id
    ).order_by(PropertyImage.display_order).all()

    return [PropertyImageResponse.from_orm(img) for img in images]


# ============================================================================
# PROPERTY VALUATIONS
# ============================================================================

@router.post(
    "/{property_id}/valuations",
    response_model=PropertyValuationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(PermissionChecker(["property:update"]))]
)
async def add_property_valuation(
    property_id: uuid.UUID,
    valuation_data: PropertyValuationCreate,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """
    Add a valuation to a property.
    Requires 'property:update' permission.
    """
    # Verify property exists and belongs to organization
    property_obj = db.query(Property).filter(
        Property.id == property_id,
        Property.organization_id == organization.id
    ).first()

    if not property_obj:
        raise ResourceNotFoundError("Property", str(property_id))

    # Create valuation
    valuation = PropertyValuation(
        id=uuid.uuid4(),
        **valuation_data.model_dump()
    )

    db.add(valuation)
    db.commit()
    db.refresh(valuation)

    return PropertyValuationResponse.from_orm(valuation)


@router.get(
    "/{property_id}/valuations",
    response_model=List[PropertyValuationResponse],
    dependencies=[Depends(PermissionChecker(["property:read"]))]
)
async def get_property_valuations(
    property_id: uuid.UUID,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db)
):
    """
    Get all valuations for a property.
    Requires 'property:read' permission.
    """
    # Verify property exists and belongs to organization
    property_obj = db.query(Property).filter(
        Property.id == property_id,
        Property.organization_id == organization.id
    ).first()

    if not property_obj:
        raise ResourceNotFoundError("Property", str(property_id))

    valuations = db.query(PropertyValuation).filter(
        PropertyValuation.property_id == property_id
    ).order_by(PropertyValuation.valuation_date.desc()).all()

    return [PropertyValuationResponse.from_orm(val) for val in valuations]
