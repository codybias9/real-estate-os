"""
Analytics endpoints for portfolio, market, and pipeline metrics.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from api.models import PortfolioSummary, PipelineMetrics
from api.orm_models import Property, Prospect, Offer
from api.auth import TokenData, get_current_user_with_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/portfolio",
    response_model=PortfolioSummary,
    summary="Portfolio summary",
    description="Get portfolio-wide statistics and metrics"
)
async def get_portfolio_summary(
    user_db: tuple[TokenData, AsyncSession] = Depends(get_current_user_with_db)
) -> PortfolioSummary:
    """Get portfolio summary statistics."""
    user, db = user_db

    try:
        # Total properties
        total_properties = (
            await db.execute(select(func.count(Property.id)))
        ).scalar()

        # Total value
        total_value = (
            await db.execute(
                select(func.sum(Property.price)).where(Property.price.isnot(None))
            )
        ).scalar() or 0.0

        # Properties by type
        type_counts = await db.execute(
            select(Property.property_type, func.count(Property.id))
            .group_by(Property.property_type)
        )
        properties_by_type = {row[0]: row[1] for row in type_counts}

        # Properties by status
        status_counts = await db.execute(
            select(Property.status, func.count(Property.id))
            .group_by(Property.status)
        )
        properties_by_status = {row[0]: row[1] for row in status_counts}

        return PortfolioSummary(
            total_properties=total_properties,
            total_value=total_value,
            total_equity=total_value * 0.7,  # Stub: 70% equity assumption
            average_cap_rate=0.065,  # Stub
            occupancy_rate=0.92,  # Stub
            properties_by_type=properties_by_type,
            properties_by_status=properties_by_status,
            recent_acquisitions=0  # Stub
        )

    except Exception as e:
        logger.error(f"Portfolio summary error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get portfolio summary")


@router.get(
    "/pipeline",
    response_model=PipelineMetrics,
    summary="Pipeline metrics",
    description="Get deal pipeline metrics and conversion rates"
)
async def get_pipeline_metrics(
    user_db: tuple[TokenData, AsyncSession] = Depends(get_current_user_with_db)
) -> PipelineMetrics:
    """Get pipeline metrics."""
    user, db = user_db

    try:
        # Count prospects by status
        total_prospects = (await db.execute(select(func.count(Prospect.id)))).scalar()

        qualified_prospects = (
            await db.execute(
                select(func.count(Prospect.id))
                .where(Prospect.status.in_(["qualified", "negotiating"]))
            )
        ).scalar()

        active_negotiations = (
            await db.execute(
                select(func.count(Prospect.id))
                .where(Prospect.status == "negotiating")
            )
        ).scalar()

        # Count offers
        offers_sent = (
            await db.execute(
                select(func.count(Offer.id))
                .where(Offer.status.in_(["sent", "accepted", "rejected"]))
            )
        ).scalar()

        offers_accepted = (
            await db.execute(
                select(func.count(Offer.id))
                .where(Offer.status == "accepted")
            )
        ).scalar()

        # Calculate conversion rate
        conversion_rate = (
            (offers_accepted / offers_sent) if offers_sent > 0 else 0.0
        )

        # Pipeline value (sum of offer prices for active offers)
        pipeline_value = (
            await db.execute(
                select(func.sum(Offer.offer_price))
                .where(Offer.status.in_(["draft", "sent"]))
            )
        ).scalar() or 0.0

        return PipelineMetrics(
            total_prospects=total_prospects,
            qualified_prospects=qualified_prospects,
            active_negotiations=active_negotiations,
            offers_sent=offers_sent,
            offers_accepted=offers_accepted,
            conversion_rate=conversion_rate,
            average_days_to_close=45.0,  # Stub
            pipeline_value=pipeline_value
        )

    except Exception as e:
        logger.error(f"Pipeline metrics error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get pipeline metrics")
