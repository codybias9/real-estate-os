"""
ML valuation endpoints (Comp-Critic, DCF, etc.).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import logging
from datetime import datetime

from api.models import ValuationRequest, ValuationResponse, CompDetail
from api.orm_models import Property
from api.auth import TokenData, get_current_user_with_db
from api.rate_limit import check_burst_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ml", tags=["ML Valuation"])


@router.post(
    "/valuation",
    response_model=ValuationResponse,
    summary="Get property valuation",
    description="""
    Get ML-based property valuation using Comp-Critic, DCF, or ensemble models.

    Models:
    - comp-critic: Comparable sales analysis with AI adjustments
    - dcf: Discounted cash flow for income properties
    - ensemble: Combined prediction from multiple models

    Rate limit: 50 requests per minute per tenant
    Burst limit: 10 requests in 5 seconds
    """
)
async def get_valuation(
    request: ValuationRequest,
    user_db: tuple[TokenData, AsyncSession] = Depends(get_current_user_with_db)
) -> ValuationResponse:
    """
    Get property valuation endpoint.

    This is a stub implementation that demonstrates the API structure.
    In P0.4, this will be connected to real ML models.
    """
    user, db = user_db

    # Apply burst protection
    await check_burst_limit(user.tenant_id, user.sub, limit=10)

    try:
        # Get property
        query = select(Property).where(Property.id == request.property_id)
        result = await db.execute(query)
        property_obj = result.scalar_one_or_none()

        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found"
            )

        # STUB: In P0.4, this will call real ML models
        # For now, return mock valuation
        base_value = float(property_obj.price) if property_obj.price else 500000.0
        estimated_value = base_value * 1.05  # Mock 5% adjustment

        # Mock comparables (in P0.4, will come from Qdrant similarity search)
        comparables = [
            CompDetail(
                property_id=UUID("00000000-0000-0000-0000-000000000001"),
                address="123 Comparable St",
                distance_miles=0.8,
                similarity_score=0.92,
                sale_price=480000,
                sale_date=datetime(2024, 10, 15),
                adjustments={
                    "sqft": 5000,
                    "bedrooms": 10000,
                    "condition": -5000
                },
                adjusted_price=490000
            ),
            CompDetail(
                property_id=UUID("00000000-0000-0000-0000-000000000002"),
                address="456 Similar Ave",
                distance_miles=1.2,
                similarity_score=0.88,
                sale_price=510000,
                sale_date=datetime(2024, 10, 20),
                adjustments={
                    "sqft": -8000,
                    "bathrooms": 5000,
                    "location": 3000
                },
                adjusted_price=510000
            ),
            CompDetail(
                property_id=UUID("00000000-0000-0000-0000-000000000003"),
                address="789 Close Rd",
                distance_miles=0.5,
                similarity_score=0.95,
                sale_price=495000,
                sale_date=datetime(2024, 11, 1),
                adjustments={
                    "sqft": 2000,
                    "age": -3000,
                    "updates": 8000
                },
                adjusted_price=502000
            )
        ]

        response = ValuationResponse(
            property_id=request.property_id,
            model=request.model,
            estimated_value=estimated_value,
            confidence_score=0.85,
            value_range_low=estimated_value * 0.95,
            value_range_high=estimated_value * 1.05,
            comparables=comparables if request.model == "comp-critic" else None,
            methodology=f"{request.model} model analysis",
            generated_at=datetime.utcnow(),
            metadata={
                "model_version": "v1.0.0-stub",
                "note": "This is a stub implementation. Real ML integration in P0.4."
            }
        )

        logger.info(
            f"Generated valuation: property={request.property_id}, "
            f"model={request.model}, value={estimated_value}, tenant={user.tenant_id}"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Valuation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate valuation"
        )


@router.post(
    "/comp-critic/{property_id}",
    response_model=ValuationResponse,
    summary="Comp-Critic valuation (shortcut)",
    description="Shortcut endpoint for Comp-Critic valuation"
)
async def comp_critic_valuation(
    property_id: UUID,
    user_db: tuple[TokenData, AsyncSession] = Depends(get_current_user_with_db)
) -> ValuationResponse:
    """Comp-Critic valuation shortcut."""
    request = ValuationRequest(property_id=property_id, model="comp-critic")
    return await get_valuation(request, user_db)


@router.post(
    "/dcf/{property_id}",
    response_model=ValuationResponse,
    summary="DCF valuation (shortcut)",
    description="Shortcut endpoint for DCF valuation"
)
async def dcf_valuation(
    property_id: UUID,
    user_db: tuple[TokenData, AsyncSession] = Depends(get_current_user_with_db)
) -> ValuationResponse:
    """DCF valuation shortcut."""
    request = ValuationRequest(property_id=property_id, model="dcf")
    return await get_valuation(request, user_db)
