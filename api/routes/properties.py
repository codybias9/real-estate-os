"""Properties API routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
import sys
sys.path.insert(0, '/home/user/real-estate-os')

from api.database import get_db
from api.schemas import Property, PropertyCreate, PropertyUpdate, PropertyListResponse, PropertyStatus, PropertyType
from db.models import Property as PropertyModel

router = APIRouter(prefix="/api/properties", tags=["properties"])


@router.get("", response_model=PropertyListResponse)
def list_properties(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    city: Optional[str] = Query(None, description="Filter by city"),
    state: Optional[str] = Query(None, description="Filter by state"),
    property_type: Optional[PropertyType] = Query(None, description="Filter by property type"),
    status: Optional[PropertyStatus] = Query(None, description="Filter by status"),
    min_price: Optional[int] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[int] = Query(None, ge=0, description="Maximum price"),
    min_bedrooms: Optional[int] = Query(None, ge=0, description="Minimum bedrooms"),
    max_bedrooms: Optional[int] = Query(None, ge=0, description="Maximum bedrooms"),
    search: Optional[str] = Query(None, description="Search in address, city, description"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    db: Session = Depends(get_db),
):
    """List all properties with filtering and pagination."""

    # Build query
    query = db.query(PropertyModel)

    # Apply filters
    if city:
        query = query.filter(PropertyModel.city.ilike(f"%{city}%"))
    if state:
        query = query.filter(PropertyModel.state == state.upper())
    if property_type:
        query = query.filter(PropertyModel.property_type == property_type)
    if status:
        query = query.filter(PropertyModel.status == status)
    if min_price is not None:
        query = query.filter(PropertyModel.price >= min_price)
    if max_price is not None:
        query = query.filter(PropertyModel.price <= max_price)
    if min_bedrooms is not None:
        query = query.filter(PropertyModel.bedrooms >= min_bedrooms)
    if max_bedrooms is not None:
        query = query.filter(PropertyModel.bedrooms <= max_bedrooms)
    if search:
        search_filter = or_(
            PropertyModel.address.ilike(f"%{search}%"),
            PropertyModel.city.ilike(f"%{search}%"),
            PropertyModel.description.ilike(f"%{search}%"),
        )
        query = query.filter(search_filter)

    # Get total count
    total = query.count()

    # Apply sorting
    sort_column = getattr(PropertyModel, sort_by, PropertyModel.created_at)
    if sort_order.lower() == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    offset = (page - 1) * page_size
    properties = query.offset(offset).limit(page_size).all()

    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size

    return PropertyListResponse(
        properties=[Property.model_validate(p) for p in properties],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{property_id}", response_model=Property)
def get_property(
    property_id: int,
    db: Session = Depends(get_db),
):
    """Get a single property by ID."""
    property_obj = db.query(PropertyModel).filter(PropertyModel.id == property_id).first()

    if not property_obj:
        raise HTTPException(status_code=404, detail=f"Property {property_id} not found")

    return Property.model_validate(property_obj)


@router.post("", response_model=Property, status_code=201)
def create_property(
    property_data: PropertyCreate,
    db: Session = Depends(get_db),
):
    """Create a new property."""

    # Check if source_id already exists
    existing = db.query(PropertyModel).filter(PropertyModel.source_id == property_data.source_id).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Property with source_id {property_data.source_id} already exists")

    # Create property
    property_obj = PropertyModel(**property_data.model_dump())
    db.add(property_obj)
    db.commit()
    db.refresh(property_obj)

    return Property.model_validate(property_obj)


@router.put("/{property_id}", response_model=Property)
def update_property(
    property_id: int,
    property_data: PropertyUpdate,
    db: Session = Depends(get_db),
):
    """Update a property."""
    property_obj = db.query(PropertyModel).filter(PropertyModel.id == property_id).first()

    if not property_obj:
        raise HTTPException(status_code=404, detail=f"Property {property_id} not found")

    # Update fields
    update_data = property_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(property_obj, field, value)

    db.commit()
    db.refresh(property_obj)

    return Property.model_validate(property_obj)


@router.delete("/{property_id}", status_code=204)
def delete_property(
    property_id: int,
    db: Session = Depends(get_db),
):
    """Delete a property."""
    property_obj = db.query(PropertyModel).filter(PropertyModel.id == property_id).first()

    if not property_obj:
        raise HTTPException(status_code=404, detail=f"Property {property_id} not found")

    db.delete(property_obj)
    db.commit()

    return None


@router.get("/stats/summary")
def get_properties_summary(db: Session = Depends(get_db)):
    """Get summary statistics for properties."""

    total = db.query(func.count(PropertyModel.id)).scalar()

    status_counts = db.query(
        PropertyModel.status,
        func.count(PropertyModel.id)
    ).group_by(PropertyModel.status).all()

    type_counts = db.query(
        PropertyModel.property_type,
        func.count(PropertyModel.id)
    ).group_by(PropertyModel.property_type).all()

    avg_price = db.query(func.avg(PropertyModel.price)).scalar()
    min_price = db.query(func.min(PropertyModel.price)).scalar()
    max_price = db.query(func.max(PropertyModel.price)).scalar()

    return {
        "total_properties": total,
        "by_status": {status: count for status, count in status_counts},
        "by_type": {ptype: count for ptype, count in type_counts},
        "price_stats": {
            "average": int(avg_price) if avg_price else 0,
            "min": int(min_price) if min_price else 0,
            "max": int(max_price) if max_price else 0,
        },
    }
