"""
Offers CRUD endpoints with RLS integration.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
import logging

from api.models import OfferCreate, OfferUpdate, OfferResponse, OfferListResponse
from api.orm_models import Offer, Property, Prospect
from api.auth import TokenData, get_current_user_with_db, Role, require_roles
from api.database import AsyncSession, get_db, set_tenant_context

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/offers", tags=["Offers"])


@router.get("", response_model=OfferListResponse)
async def list_offers(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    property_id: Optional[UUID] = Query(None),
    user_db: tuple[TokenData, AsyncSession] = Depends(get_current_user_with_db)
) -> OfferListResponse:
    """List offers endpoint."""
    user, db = user_db

    try:
        query = select(Offer)
        if status:
            query = query.where(Offer.status == status)
        if property_id:
            query = query.where(Offer.property_id == property_id)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar()

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size).order_by(Offer.created_at.desc())
        offers = (await db.execute(query)).scalars().all()

        return OfferListResponse(
            items=[OfferResponse.model_validate(o) for o in offers],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size
        )
    except Exception as e:
        logger.error(f"List offers error: {e}")
        raise HTTPException(status_code=500, detail="Failed to list offers")


@router.get("/{offer_id}", response_model=OfferResponse)
async def get_offer(
    offer_id: UUID,
    user_db: tuple[TokenData, AsyncSession] = Depends(get_current_user_with_db)
) -> OfferResponse:
    """Get offer by ID."""
    user, db = user_db
    offer = (await db.execute(select(Offer).where(Offer.id == offer_id))).scalar_one_or_none()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    return OfferResponse.model_validate(offer)


@router.post("", response_model=OfferResponse, status_code=201)
@require_roles([Role.ADMIN, Role.ANALYST])
async def create_offer(
    offer_data: OfferCreate,
    user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> OfferResponse:
    """Create offer."""
    await set_tenant_context(db, user.tenant_id)

    try:
        # Verify property exists
        if not (await db.execute(select(Property).where(Property.id == offer_data.property_id))).scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Property not found")

        offer = Offer(
            tenant_id=user.tenant_id,
            property_id=offer_data.property_id,
            prospect_id=offer_data.prospect_id,
            offer_price=offer_data.offer_price,
            earnest_money=offer_data.earnest_money,
            closing_days=offer_data.closing_days,
            contingencies=offer_data.contingencies,
            terms=offer_data.terms,
            notes=offer_data.notes,
            status="draft"
        )

        db.add(offer)
        await db.commit()
        await db.refresh(offer)

        logger.info(f"Created offer: id={offer.id}, tenant={user.tenant_id}")
        return OfferResponse.model_validate(offer)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Create offer error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create offer")


@router.patch("/{offer_id}", response_model=OfferResponse)
@require_roles([Role.ADMIN, Role.ANALYST])
async def update_offer(
    offer_id: UUID,
    offer_data: OfferUpdate,
    user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> OfferResponse:
    """Update offer."""
    await set_tenant_context(db, user.tenant_id)

    try:
        offer = (await db.execute(select(Offer).where(Offer.id == offer_id))).scalar_one_or_none()
        if not offer:
            raise HTTPException(status_code=404, detail="Offer not found")

        update_data = offer_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(offer, field):
                setattr(offer, field, value.value if hasattr(value, 'value') else value)

        await db.commit()
        await db.refresh(offer)

        logger.info(f"Updated offer: id={offer_id}, tenant={user.tenant_id}")
        return OfferResponse.model_validate(offer)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Update offer error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update offer")


@router.delete("/{offer_id}", status_code=204)
@require_roles([Role.ADMIN])
async def delete_offer(
    offer_id: UUID,
    user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> None:
    """Delete offer."""
    await set_tenant_context(db, user.tenant_id)

    try:
        offer = (await db.execute(select(Offer).where(Offer.id == offer_id))).scalar_one_or_none()
        if not offer:
            raise HTTPException(status_code=404, detail="Offer not found")

        await db.delete(offer)
        await db.commit()

        logger.info(f"Deleted offer: id={offer_id}, tenant={user.tenant_id}")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Delete offer error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete offer")
