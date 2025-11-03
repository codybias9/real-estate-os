"""
Property API endpoints with caching
"""

import sys
import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from datetime import datetime

# Add cache service to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/cache/src"))

from cache import (
    get_cache_client,
    cached_property_list,
    cached_property_detail,
    cached_property_score,
    cache_aside,
    invalidate_property,
    invalidate_property_list,
    handle_cache_event,
)

# Import auth middleware
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/auth/src"))
from auth import get_current_user, User, require_role, UserRole

# Import observability
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/observability/src"))
from observability import get_logger, record_property_operation

router = APIRouter(prefix="/properties", tags=["Properties"])
logger = get_logger(__name__)


# Pydantic models
class PropertyCreate(BaseModel):
    """Property creation request"""

    apn: str = Field(..., description="Assessor's Parcel Number")
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    county: Optional[str] = None


class PropertyUpdate(BaseModel):
    """Property update request"""

    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    beds: Optional[int] = None
    baths: Optional[float] = None
    sqft: Optional[int] = None


class PropertyResponse(BaseModel):
    """Property response"""

    id: str
    tenant_id: str
    apn: str
    apn_hash: str
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    county: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    beds: Optional[int] = None
    baths: Optional[float] = None
    sqft: Optional[int] = None
    lot_sqft: Optional[int] = None
    year_built: Optional[int] = None
    state_field: str = Field(..., alias="state")
    score: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class PropertyListResponse(BaseModel):
    """Property list response"""

    properties: List[PropertyResponse]
    total: int
    page: int
    page_size: int


class ScoreResponse(BaseModel):
    """Property score response"""

    property_id: str
    score: float
    reasons: List[dict]
    calculated_at: datetime


# Mock data store (in production, this would be a database)
_properties_store = {}


def get_property_from_db(property_id: str, tenant_id: str) -> Optional[dict]:
    """Fetch property from database (mock)"""
    key = f"{tenant_id}:{property_id}"
    return _properties_store.get(key)


def get_properties_from_db(tenant_id: str, filters: dict) -> List[dict]:
    """Fetch properties from database (mock)"""
    # In production, this would query the database with filters
    results = []
    for key, prop in _properties_store.items():
        if key.startswith(f"{tenant_id}:"):
            # Apply filters
            if filters.get("state") and prop.get("state_field") != filters["state"]:
                continue
            results.append(prop)
    return results


def save_property_to_db(property_data: dict) -> dict:
    """Save property to database (mock)"""
    key = f"{property_data['tenant_id']}:{property_data['id']}"
    _properties_store[key] = property_data
    return property_data


@router.get("", response_model=PropertyListResponse)
def list_properties(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    state: Optional[str] = Query(None, description="Filter by property state"),
    current_user: User = Depends(get_current_user),
):
    """
    List properties with caching.

    Cached for 5 minutes per tenant/filter combination.
    """
    logger.info(
        "list_properties",
        tenant_id=current_user.tenant_id,
        page=page,
        state=state,
    )

    # Build filters
    filters = {"page": page, "page_size": page_size}
    if state:
        filters["state"] = state

    # Use cache-aside pattern
    cache_key = cached_property_list(current_user.tenant_id, filters)

    def fetch_properties():
        properties = get_properties_from_db(current_user.tenant_id, filters)
        return {
            "properties": properties,
            "total": len(properties),
            "page": page,
            "page_size": page_size,
        }

    result = cache_aside(cache_key, fetch_properties, ttl=300)

    record_property_operation(operation="list", status="success")

    return result


@router.get("/{property_id}", response_model=PropertyResponse)
def get_property(
    property_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get property by ID with caching.

    Cached for 10 minutes.
    """
    logger.info(
        "get_property",
        property_id=property_id,
        tenant_id=current_user.tenant_id,
    )

    # Use cache-aside pattern
    cache_key = cached_property_detail(property_id)

    def fetch_property():
        prop = get_property_from_db(property_id, current_user.tenant_id)
        if not prop:
            raise HTTPException(status_code=404, detail="Property not found")
        return prop

    try:
        result = cache_aside(cache_key, fetch_property, ttl=600)
        record_property_operation(operation="get", status="success")
        return result
    except HTTPException:
        record_property_operation(operation="get", status="not_found")
        raise


@router.post("", response_model=PropertyResponse, status_code=201)
def create_property(
    property_data: PropertyCreate,
    current_user: User = Depends(require_role(UserRole.ANALYST, UserRole.ADMIN)),
):
    """
    Create new property.

    Requires ANALYST or ADMIN role.
    Invalidates property list cache for tenant.
    """
    import uuid
    import hashlib

    logger.info(
        "create_property",
        apn=property_data.apn,
        tenant_id=current_user.tenant_id,
    )

    # Create property
    property_dict = {
        "id": str(uuid.uuid4()),
        "tenant_id": current_user.tenant_id,
        "apn": property_data.apn,
        "apn_hash": hashlib.sha256(property_data.apn.encode()).hexdigest(),
        "street": property_data.street,
        "city": property_data.city,
        "state": property_data.state,
        "zip": property_data.zip,
        "county": property_data.county,
        "state_field": "discovered",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    # Save to database
    result = save_property_to_db(property_dict)

    # Invalidate list cache
    invalidate_property_list(current_user.tenant_id)

    # Emit cache invalidation event
    handle_cache_event({
        "type": "property.created",
        "property_id": property_dict["id"],
        "tenant_id": current_user.tenant_id,
    })

    record_property_operation(operation="create", status="success")

    return result


@router.put("/{property_id}", response_model=PropertyResponse)
def update_property(
    property_id: str,
    property_data: PropertyUpdate,
    current_user: User = Depends(require_role(UserRole.ANALYST, UserRole.ADMIN, UserRole.OPS)),
):
    """
    Update property.

    Requires ANALYST, ADMIN, or OPS role.
    Invalidates property cache.
    """
    logger.info(
        "update_property",
        property_id=property_id,
        tenant_id=current_user.tenant_id,
    )

    # Fetch existing property
    existing = get_property_from_db(property_id, current_user.tenant_id)
    if not existing:
        record_property_operation(operation="update", status="not_found")
        raise HTTPException(status_code=404, detail="Property not found")

    # Update fields
    update_dict = property_data.model_dump(exclude_unset=True)
    existing.update(update_dict)
    existing["updated_at"] = datetime.utcnow()

    # Save to database
    result = save_property_to_db(existing)

    # Invalidate property cache
    invalidate_property(property_id)

    # Emit cache invalidation event
    handle_cache_event({
        "type": "property.updated",
        "property_id": property_id,
        "tenant_id": current_user.tenant_id,
    })

    record_property_operation(operation="update", status="success")

    return result


@router.delete("/{property_id}", status_code=204)
def delete_property(
    property_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    Delete property.

    Requires ADMIN role.
    Invalidates property cache.
    """
    logger.info(
        "delete_property",
        property_id=property_id,
        tenant_id=current_user.tenant_id,
    )

    # Check if property exists
    key = f"{current_user.tenant_id}:{property_id}"
    if key not in _properties_store:
        record_property_operation(operation="delete", status="not_found")
        raise HTTPException(status_code=404, detail="Property not found")

    # Delete from database
    del _properties_store[key]

    # Invalidate property cache
    invalidate_property(property_id)

    # Emit cache invalidation event
    handle_cache_event({
        "type": "property.deleted",
        "property_id": property_id,
        "tenant_id": current_user.tenant_id,
    })

    record_property_operation(operation="delete", status="success")


@router.get("/{property_id}/score", response_model=ScoreResponse)
def get_property_score(
    property_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get property score with caching.

    Cached for 30 minutes.
    """
    logger.info(
        "get_property_score",
        property_id=property_id,
        tenant_id=current_user.tenant_id,
    )

    # Use cache-aside pattern
    cache_key = cached_property_score(property_id)

    def fetch_score():
        # Check if property exists
        prop = get_property_from_db(property_id, current_user.tenant_id)
        if not prop:
            raise HTTPException(status_code=404, detail="Property not found")

        # Mock score (in production, fetch from scoring service)
        return {
            "property_id": property_id,
            "score": prop.get("score", 0.0),
            "reasons": prop.get("score_reasons", []),
            "calculated_at": datetime.utcnow(),
        }

    try:
        result = cache_aside(cache_key, fetch_score, ttl=1800)
        return result
    except HTTPException:
        raise


@router.post("/{property_id}/cache/invalidate", status_code=204)
def invalidate_property_cache(
    property_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """
    Manually invalidate property cache.

    Requires ADMIN role.
    Useful for troubleshooting or forcing cache refresh.
    """
    logger.info(
        "invalidate_property_cache",
        property_id=property_id,
        tenant_id=current_user.tenant_id,
    )

    deleted = invalidate_property(property_id)

    logger.info(
        "cache_invalidated",
        property_id=property_id,
        keys_deleted=deleted,
    )
