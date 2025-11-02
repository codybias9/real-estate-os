"""
Prospects (deal pipeline) CRUD endpoints with RLS integration.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
import logging

from api.models import (
    ProspectCreate, ProspectUpdate, ProspectResponse, ProspectListResponse
)
from api.orm_models import Prospect, Property
from api.auth import TokenData, get_current_user, get_current_user_with_db, Role, require_roles
from api.database import AsyncSession, get_db, set_tenant_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prospects", tags=["Prospects"])


@router.get(
    "",
    response_model=ProspectListResponse,
    summary="List prospects",
    description="""
    List all prospects in the deal pipeline with pagination.

    Optional filters:
    - status: Filter by prospect status (new, contacted, qualified, etc.)
    - property_id: Filter by property
    - min_motivation: Filter by minimum motivation score
    """
)
async def list_prospects(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    property_id: Optional[UUID] = Query(None),
    min_motivation: Optional[float] = Query(None, ge=0, le=1),
    user_db: tuple[TokenData, AsyncSession] = Depends(get_current_user_with_db)
) -> ProspectListResponse:
    """List prospects endpoint."""
    user, db = user_db

    try:
        # Build query
        query = select(Prospect)

        if status:
            query = query.where(Prospect.status == status)
        if property_id:
            query = query.where(Prospect.property_id == property_id)
        if min_motivation is not None:
            query = query.where(Prospect.motivation_score >= min_motivation)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        query = query.order_by(Prospect.created_at.desc())

        # Execute
        result = await db.execute(query)
        prospects = result.scalars().all()

        return ProspectListResponse(
            items=[ProspectResponse.model_validate(p) for p in prospects],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size
        )

    except Exception as e:
        logger.error(f"List prospects error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list prospects"
        )


@router.get(
    "/{prospect_id}",
    response_model=ProspectResponse,
    summary="Get prospect by ID"
)
async def get_prospect(
    prospect_id: UUID,
    user_db: tuple[TokenData, AsyncSession] = Depends(get_current_user_with_db)
) -> ProspectResponse:
    """Get prospect by ID endpoint."""
    user, db = user_db

    try:
        query = select(Prospect).where(Prospect.id == prospect_id)
        result = await db.execute(query)
        prospect = result.scalar_one_or_none()

        if not prospect:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prospect not found"
            )

        return ProspectResponse.model_validate(prospect)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get prospect error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get prospect"
        )


@router.post(
    "",
    response_model=ProspectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create prospect"
)
@require_roles([Role.ADMIN, Role.ANALYST, Role.OPERATOR])
async def create_prospect(
    prospect_data: ProspectCreate,
    user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ProspectResponse:
    """Create prospect endpoint."""
    await set_tenant_context(db, user.tenant_id)

    try:
        # Verify property exists and belongs to tenant
        prop_query = select(Property).where(Property.id == prospect_data.property_id)
        prop_result = await db.execute(prop_query)
        if not prop_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found"
            )

        # Create prospect
        prospect = Prospect(
            tenant_id=user.tenant_id,
            property_id=prospect_data.property_id,
            source=prospect_data.source,
            owner_name=prospect_data.owner_name,
            owner_email=prospect_data.owner_email,
            owner_phone=prospect_data.owner_phone,
            motivation_score=prospect_data.motivation_score,
            notes=prospect_data.notes,
            metadata=prospect_data.metadata,
            status="new"
        )

        db.add(prospect)
        await db.commit()
        await db.refresh(prospect)

        logger.info(f"Created prospect: id={prospect.id}, tenant={user.tenant_id}")

        return ProspectResponse.model_validate(prospect)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Create prospect error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create prospect"
        )


@router.patch(
    "/{prospect_id}",
    response_model=ProspectResponse,
    summary="Update prospect"
)
@require_roles([Role.ADMIN, Role.ANALYST, Role.OPERATOR])
async def update_prospect(
    prospect_id: UUID,
    prospect_data: ProspectUpdate,
    user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ProspectResponse:
    """Update prospect endpoint."""
    await set_tenant_context(db, user.tenant_id)

    try:
        # Get prospect
        query = select(Prospect).where(Prospect.id == prospect_id)
        result = await db.execute(query)
        prospect = result.scalar_one_or_none()

        if not prospect:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prospect not found"
            )

        # Update fields
        update_data = prospect_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(prospect, field):
                if hasattr(value, 'value'):  # Enum
                    value = value.value
                setattr(prospect, field, value)

        await db.commit()
        await db.refresh(prospect)

        logger.info(f"Updated prospect: id={prospect_id}, tenant={user.tenant_id}")

        return ProspectResponse.model_validate(prospect)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Update prospect error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update prospect"
        )


@router.delete(
    "/{prospect_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete prospect"
)
@require_roles([Role.ADMIN])
async def delete_prospect(
    prospect_id: UUID,
    user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """Delete prospect endpoint."""
    await set_tenant_context(db, user.tenant_id)

    try:
        query = select(Prospect).where(Prospect.id == prospect_id)
        result = await db.execute(query)
        prospect = result.scalar_one_or_none()

        if not prospect:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prospect not found"
            )

        await db.delete(prospect)
        await db.commit()

        logger.info(f"Deleted prospect: id={prospect_id}, tenant={user.tenant_id}")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Delete prospect error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete prospect"
        )
