"""
Properties CRUD endpoints with RLS integration.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
import logging

from api.models import (
    PropertyCreate, PropertyUpdate, PropertyResponse, PropertyListResponse
)
from api.orm_models import Property
from api.auth import TokenData, get_current_user, get_current_user_with_db, Role, require_roles
from api.database import AsyncSession, get_db, set_tenant_context
from api.redis_client import redis_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/properties", tags=["Properties"])


@router.get(
    "",
    response_model=PropertyListResponse,
    summary="List properties",
    description="""
    List all properties for the authenticated tenant with pagination.

    RLS automatically filters results to the tenant's data only.

    Optional filters:
    - status: Filter by property status
    - property_type: Filter by property type
    - min_price, max_price: Price range filter

    Results are cached in Redis for 5 minutes per tenant.
    """
)
async def list_properties(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    property_type: Optional[str] = Query(None, description="Filter by type"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    user_db: tuple[TokenData, AsyncSession] = Depends(get_current_user_with_db)
) -> PropertyListResponse:
    """
    List properties endpoint with pagination and filtering.
    """
    user, db = user_db

    # Check cache first
    cache_key = f"properties:list:page={page}:size={page_size}:status={status}:type={property_type}"
    cached = await redis_client.get_tenant_cache(user.tenant_id, cache_key)
    if cached:
        logger.debug(f"Cache hit: {cache_key}")
        return PropertyListResponse(**cached)

    try:
        # Build query
        query = select(Property)

        # Apply filters
        if status:
            query = query.where(Property.status == status)
        if property_type:
            query = query.where(Property.property_type == property_type)
        if min_price is not None:
            query = query.where(Property.price >= min_price)
        if max_price is not None:
            query = query.where(Property.price <= max_price)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        query = query.order_by(Property.created_at.desc())

        # Execute query (RLS automatically filters by tenant)
        result = await db.execute(query)
        properties = result.scalars().all()

        # Build response
        response = PropertyListResponse(
            items=[PropertyResponse.model_validate(prop) for prop in properties],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size
        )

        # Cache for 5 minutes
        await redis_client.set_tenant_cache(
            user.tenant_id,
            cache_key,
            response.model_dump(),
            ttl=300
        )

        logger.info(
            f"Listed properties: tenant={user.tenant_id}, "
            f"count={len(properties)}, total={total}"
        )

        return response

    except Exception as e:
        logger.error(f"List properties error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list properties"
        )


@router.get(
    "/{property_id}",
    response_model=PropertyResponse,
    summary="Get property by ID",
    description="""
    Get a single property by ID.

    RLS ensures you can only access properties in your tenant.
    Returns 404 if property doesn't exist or belongs to another tenant.
    """
)
async def get_property(
    property_id: UUID,
    user_db: tuple[TokenData, AsyncSession] = Depends(get_current_user_with_db)
) -> PropertyResponse:
    """
    Get property by ID endpoint.
    """
    user, db = user_db

    # Check cache
    cache_key = f"properties:detail:{property_id}"
    cached = await redis_client.get_tenant_cache(user.tenant_id, cache_key)
    if cached:
        return PropertyResponse(**cached)

    try:
        # Query property (RLS filters by tenant automatically)
        query = select(Property).where(Property.id == property_id)
        result = await db.execute(query)
        property_obj = result.scalar_one_or_none()

        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found"
            )

        response = PropertyResponse.model_validate(property_obj)

        # Cache for 5 minutes
        await redis_client.set_tenant_cache(
            user.tenant_id,
            cache_key,
            response.model_dump(),
            ttl=300
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get property error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get property"
        )


@router.post(
    "",
    response_model=PropertyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create property",
    description="""
    Create a new property.

    Requires role: admin or analyst

    The tenant_id is automatically set from the JWT token.
    RLS INSERT policy ensures property is created in correct tenant.
    """
)
@require_roles([Role.ADMIN, Role.ANALYST])
async def create_property(
    property_data: PropertyCreate,
    user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> PropertyResponse:
    """
    Create property endpoint.
    """
    # Set tenant context for RLS
    await set_tenant_context(db, user.tenant_id)

    try:
        # Create property object
        property_obj = Property(
            tenant_id=user.tenant_id,
            address=property_data.address,
            property_type=property_data.property_type.value,
            bedrooms=property_data.bedrooms,
            bathrooms=property_data.bathrooms,
            sqft=property_data.sqft,
            price=property_data.price,
            latitude=property_data.latitude,
            longitude=property_data.longitude,
            description=property_data.description,
            metadata=property_data.metadata,
            status="active"
        )

        # Add to session
        db.add(property_obj)
        await db.flush()  # Flush to get ID

        # Update PostGIS geometry if lat/lon provided
        if property_data.latitude and property_data.longitude:
            await db.execute(
                text("""
                    UPDATE properties
                    SET geom = ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
                    WHERE id = :id
                """),
                {
                    "lon": float(property_data.longitude),
                    "lat": float(property_data.latitude),
                    "id": property_obj.id
                }
            )

        await db.commit()
        await db.refresh(property_obj)

        # Invalidate list cache
        await redis_client.delete_tenant_cache(user.tenant_id, "properties:list:*")

        logger.info(
            f"Created property: id={property_obj.id}, "
            f"tenant={user.tenant_id}, user={user.sub}"
        )

        return PropertyResponse.model_validate(property_obj)

    except Exception as e:
        await db.rollback()
        logger.error(f"Create property error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create property"
        )


@router.patch(
    "/{property_id}",
    response_model=PropertyResponse,
    summary="Update property",
    description="""
    Update a property (partial update).

    Requires role: admin or analyst

    Only provided fields will be updated.
    RLS ensures you can only update properties in your tenant.
    """
)
@require_roles([Role.ADMIN, Role.ANALYST])
async def update_property(
    property_id: UUID,
    property_data: PropertyUpdate,
    user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> PropertyResponse:
    """
    Update property endpoint.
    """
    # Set tenant context for RLS
    await set_tenant_context(db, user.tenant_id)

    try:
        # Get property (RLS filters by tenant)
        query = select(Property).where(Property.id == property_id)
        result = await db.execute(query)
        property_obj = result.scalar_one_or_none()

        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found"
            )

        # Update fields
        update_data = property_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(property_obj, field):
                # Convert enum to value if needed
                if hasattr(value, 'value'):
                    value = value.value
                setattr(property_obj, field, value)

        # Update PostGIS geometry if lat/lon changed
        if property_data.latitude is not None or property_data.longitude is not None:
            lat = property_data.latitude or property_obj.latitude
            lon = property_data.longitude or property_obj.longitude
            if lat and lon:
                await db.execute(
                    text("""
                        UPDATE properties
                        SET geom = ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
                        WHERE id = :id
                    """),
                    {"lon": float(lon), "lat": float(lat), "id": property_id}
                )

        await db.commit()
        await db.refresh(property_obj)

        # Invalidate caches
        await redis_client.delete_tenant_cache(user.tenant_id, f"properties:detail:{property_id}")
        await redis_client.delete_tenant_cache(user.tenant_id, "properties:list:*")

        logger.info(
            f"Updated property: id={property_id}, "
            f"tenant={user.tenant_id}, user={user.sub}"
        )

        return PropertyResponse.model_validate(property_obj)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Update property error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update property"
        )


@router.delete(
    "/{property_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete property",
    description="""
    Delete a property (soft delete by setting status to 'archived').

    Requires role: admin

    RLS ensures you can only delete properties in your tenant.
    Related records (prospects, offers) are cascade deleted via FK constraints.
    """
)
@require_roles([Role.ADMIN])
async def delete_property(
    property_id: UUID,
    hard_delete: bool = Query(False, description="Permanent deletion (use with caution)"),
    user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Delete property endpoint.
    """
    # Set tenant context for RLS
    await set_tenant_context(db, user.tenant_id)

    try:
        # Get property (RLS filters by tenant)
        query = select(Property).where(Property.id == property_id)
        result = await db.execute(query)
        property_obj = result.scalar_one_or_none()

        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found"
            )

        if hard_delete:
            # Permanent deletion
            await db.delete(property_obj)
            logger.warning(
                f"Hard deleted property: id={property_id}, "
                f"tenant={user.tenant_id}, user={user.sub}"
            )
        else:
            # Soft delete (archive)
            property_obj.status = "archived"
            logger.info(
                f"Soft deleted property: id={property_id}, "
                f"tenant={user.tenant_id}, user={user.sub}"
            )

        await db.commit()

        # Invalidate caches
        await redis_client.delete_tenant_cache(user.tenant_id, f"properties:detail:{property_id}")
        await redis_client.delete_tenant_cache(user.tenant_id, "properties:list:*")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Delete property error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete property"
        )


@router.get(
    "/nearby/{property_id}",
    response_model=List[PropertyResponse],
    summary="Find nearby properties",
    description="""
    Find properties within a radius of the specified property.

    Uses PostGIS ST_DWithin for efficient spatial queries.
    Results are filtered by tenant via RLS.

    Parameters:
    - radius_miles: Search radius in miles (default: 5)
    - limit: Maximum results (default: 10)
    """
)
async def find_nearby_properties(
    property_id: UUID,
    radius_miles: float = Query(5.0, ge=0.1, le=50, description="Radius in miles"),
    limit: int = Query(10, ge=1, le=100, description="Max results"),
    user_db: tuple[TokenData, AsyncSession] = Depends(get_current_user_with_db)
) -> List[PropertyResponse]:
    """
    Find nearby properties using PostGIS spatial query.
    """
    user, db = user_db

    try:
        # Get source property
        query = select(Property).where(Property.id == property_id)
        result = await db.execute(query)
        source_property = result.scalar_one_or_none()

        if not source_property:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found"
            )

        if not source_property.geom:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Property has no geolocation"
            )

        # Convert miles to meters (PostGIS uses meters for SRID 4326)
        radius_meters = radius_miles * 1609.34

        # Spatial query with RLS
        query = text("""
            SELECT *
            FROM properties
            WHERE id != :source_id
              AND geom IS NOT NULL
              AND ST_DWithin(
                  geom::geography,
                  (SELECT geom::geography FROM properties WHERE id = :source_id),
                  :radius
              )
            ORDER BY ST_Distance(
                geom::geography,
                (SELECT geom::geography FROM properties WHERE id = :source_id)
            )
            LIMIT :limit
        """)

        result = await db.execute(
            query,
            {
                "source_id": property_id,
                "radius": radius_meters,
                "limit": limit
            }
        )

        # RLS automatically filters results to tenant
        properties = result.fetchall()

        logger.info(
            f"Found {len(properties)} nearby properties within {radius_miles} miles "
            f"of {property_id}"
        )

        return [
            PropertyResponse.model_validate(dict(row._mapping))
            for row in properties
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Nearby properties error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to find nearby properties"
        )
