"""
ARV (After Repair Value) API Router.

Endpoints for calculating ARV and fix-and-flip ROI analysis.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from api.auth import get_current_user, TokenData
from api.rate_limit import rate_limit
from ml.arv.arv_calculator import (
    ARVCalculator,
    PropertyCondition,
    RenovationItem,
    RenovationPlan,
    calculate_fix_and_flip_roi
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/arv",
    tags=["ARV & Fix-and-Flip"]
)

# Initialize calculator
arv_calculator = ARVCalculator()


# ============================================================================
# Request/Response Models
# ============================================================================

class PropertyConditionRequest(BaseModel):
    """Property condition assessment."""
    overall_condition: str = Field(..., description="Poor, Fair, Average, Good, Excellent")
    condition_score: float = Field(..., ge=1, le=10, description="Condition score 1-10")

    # Component conditions
    roof_condition: Optional[float] = Field(None, ge=1, le=10)
    hvac_condition: Optional[float] = Field(None, ge=1, le=10)
    plumbing_condition: Optional[float] = Field(None, ge=1, le=10)
    electrical_condition: Optional[float] = Field(None, ge=1, le=10)
    kitchen_condition: Optional[float] = Field(None, ge=1, le=10)
    bathroom_condition: Optional[float] = Field(None, ge=1, le=10)
    flooring_condition: Optional[float] = Field(None, ge=1, le=10)
    paint_condition: Optional[float] = Field(None, ge=1, le=10)
    foundation_condition: Optional[float] = Field(None, ge=1, le=10)

    deferred_maintenance_cost: Optional[float] = Field(None, description="Deferred maintenance cost estimate")
    year_built: int = Field(..., description="Year property was built")
    last_renovation_year: Optional[int] = Field(None, description="Last renovation year")


class RenovationItemRequest(BaseModel):
    """Single renovation item."""
    category: str = Field(..., description="Kitchen, Bathroom, Roof, etc.")
    description: str = Field(..., description="Item description")
    cost: float = Field(..., gt=0, description="Item cost")
    value_add_factor: Optional[float] = Field(None, ge=0, le=2, description="Value add factor (0.5 = 50% recovery)")
    duration_days: int = Field(30, ge=1, description="Duration in days")
    priority: str = Field("Medium", description="Low, Medium, High, Critical")


class ARVCalculationRequest(BaseModel):
    """ARV calculation request."""
    # Property details
    current_value: float = Field(..., gt=0, description="Current as-is value")
    purchase_price: float = Field(..., gt=0, description="Purchase price")
    property_sqft: int = Field(..., gt=0, description="Square footage")

    # Condition
    condition: PropertyConditionRequest

    # Renovation plan
    renovation_items: List[RenovationItemRequest]
    contingency_percent: float = Field(0.10, ge=0, le=0.30, description="Contingency percentage")

    # Optional comps for validation
    comp_properties: Optional[List[Dict[str, Any]]] = Field(None, description="Comparable properties")


class ARVAnalysisResponse(BaseModel):
    """ARV analysis results."""
    # Input
    current_value: float
    purchase_price: float

    # Renovation
    renovation_cost: float
    expected_value_add: float

    # ARV
    arv: float
    arv_method: str
    confidence_score: float

    # ROI metrics
    total_investment: float
    gross_profit: float
    roi_percent: float
    renovation_roi_percent: float

    # Costs
    holding_months: int
    holding_costs: float
    selling_costs_percent: float
    selling_costs: float

    # Net profit
    net_profit: float
    net_roi_percent: float

    # Comp validation
    comp_arv_low: Optional[float]
    comp_arv_high: Optional[float]
    comp_arv_median: Optional[float]

    # Risk
    risk_level: str
    risk_factors: List[str]

    # Metadata
    calculated_at: datetime


class QuickFlipROIRequest(BaseModel):
    """Quick fix-and-flip ROI request."""
    purchase_price: float = Field(..., gt=0)
    current_value: float = Field(..., gt=0)
    renovation_cost: float = Field(..., gt=0)
    expected_arv: float = Field(..., gt=0)
    holding_months: int = Field(6, ge=1, le=24)


class QuickFlipROIResponse(BaseModel):
    """Quick fix-and-flip ROI response."""
    purchase_price: float
    renovation_cost: float
    total_investment: float
    arv: float
    holding_costs: float
    selling_costs: float
    gross_profit: float
    net_profit: float
    roi_percent: float


class RenovationBudgetResponse(BaseModel):
    """Renovation budget summary."""
    items: List[Dict[str, Any]]
    subtotal: float
    contingency_percent: float
    contingency_amount: float
    total_cost: float
    expected_value_add: float
    total_duration_days: int
    roi_estimate: float


# ============================================================================
# Endpoints
# ============================================================================

@router.post(
    "/calculate",
    response_model=ARVAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate ARV",
    description="Calculate After Repair Value with complete ROI analysis"
)
@rate_limit(requests_per_minute=30)
async def calculate_arv(
    request: ARVCalculationRequest,
    user: TokenData = Depends(get_current_user)
):
    """
    Calculate After Repair Value (ARV) for a property.

    **Process:**
    1. Assess current property condition
    2. Define renovation scope and costs
    3. Calculate expected value increase
    4. Validate against comparable properties
    5. Calculate ROI metrics (gross and net)

    **Methods:**
    - Cost-Based: Current value + expected value add
    - Comp-Based: Price/sqft from high-condition comps
    - Hybrid: Weighted average of both methods

    **ROI Metrics:**
    - Gross profit: ARV - total investment
    - Net profit: Gross profit - holding costs - selling costs
    - ROI %: Net profit / total investment
    - Renovation ROI %: Value add / renovation cost

    **Use Cases:**
    - Fix-and-flip analysis
    - BRRRR strategy (Buy, Rehab, Rent, Refinance, Repeat)
    - Value-add investment evaluation
    - Renovation ROI justification
    """
    logger.info(f"ARV calculation request from user {user.user_id}")

    try:
        # Convert condition
        condition = PropertyCondition(
            overall_condition=request.condition.overall_condition,
            condition_score=request.condition.condition_score,
            roof_condition=request.condition.roof_condition,
            hvac_condition=request.condition.hvac_condition,
            plumbing_condition=request.condition.plumbing_condition,
            electrical_condition=request.condition.electrical_condition,
            kitchen_condition=request.condition.kitchen_condition,
            bathroom_condition=request.condition.bathroom_condition,
            flooring_condition=request.condition.flooring_condition,
            paint_condition=request.condition.paint_condition,
            foundation_condition=request.condition.foundation_condition,
            deferred_maintenance_cost=request.condition.deferred_maintenance_cost,
            year_built=request.condition.year_built,
            last_renovation_year=request.condition.last_renovation_year
        )

        # Convert renovation items
        items_list = []
        for item in request.renovation_items:
            items_list.append({
                "category": item.category,
                "description": item.description,
                "cost": item.cost,
                "value_add_factor": item.value_add_factor,
                "duration_days": item.duration_days,
                "priority": item.priority
            })

        # Create renovation plan
        renovation_plan = arv_calculator.create_renovation_plan(
            items_list,
            contingency_percent=request.contingency_percent
        )

        # Calculate ARV
        analysis = arv_calculator.calculate_arv(
            current_value=request.current_value,
            purchase_price=request.purchase_price,
            condition=condition,
            renovation_plan=renovation_plan,
            property_sqft=request.property_sqft,
            comp_properties=request.comp_properties
        )

        logger.info(
            f"ARV calculated: ${analysis.arv:,.0f}, "
            f"Net ROI: {analysis.net_roi_percent:.1f}%"
        )

        return ARVAnalysisResponse(
            current_value=analysis.current_value,
            purchase_price=analysis.purchase_price,
            renovation_cost=analysis.renovation_cost,
            expected_value_add=analysis.expected_value_add,
            arv=analysis.arv,
            arv_method=analysis.arv_method,
            confidence_score=analysis.confidence_score,
            total_investment=analysis.total_investment,
            gross_profit=analysis.gross_profit,
            roi_percent=analysis.roi_percent,
            renovation_roi_percent=analysis.renovation_roi_percent,
            holding_months=analysis.holding_months,
            holding_costs=analysis.holding_costs,
            selling_costs_percent=analysis.selling_costs_percent,
            selling_costs=analysis.selling_costs,
            net_profit=analysis.net_profit,
            net_roi_percent=analysis.net_roi_percent,
            comp_arv_low=analysis.comp_arv_low,
            comp_arv_high=analysis.comp_arv_high,
            comp_arv_median=analysis.comp_arv_median,
            risk_level=analysis.risk_level,
            risk_factors=analysis.risk_factors,
            calculated_at=datetime.utcnow()
        )

    except Exception as e:
        logger.error(f"ARV calculation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ARV calculation failed: {str(e)}"
        )


@router.post(
    "/quick-flip-roi",
    response_model=QuickFlipROIResponse,
    status_code=status.HTTP_200_OK,
    summary="Quick fix-and-flip ROI",
    description="Quick ROI calculator for fix-and-flip analysis"
)
@rate_limit(requests_per_minute=60)
async def quick_flip_roi(
    request: QuickFlipROIRequest,
    user: TokenData = Depends(get_current_user)
):
    """
    Quick fix-and-flip ROI calculator.

    Simplified calculator for rapid deal analysis. Calculates net profit
    and ROI including holding costs and selling costs.

    **Assumptions:**
    - 8% hard money loan interest
    - 1.2% annual property tax
    - $1,500/year insurance
    - $300/month utilities
    - 8% selling costs (6% commission + 2% closing)
    """
    logger.info(f"Quick flip ROI request from user {user.user_id}")

    try:
        metrics = calculate_fix_and_flip_roi(
            purchase_price=request.purchase_price,
            current_value=request.current_value,
            renovation_cost=request.renovation_cost,
            expected_arv=request.expected_arv,
            holding_months=request.holding_months
        )

        logger.info(f"Quick flip ROI: {metrics['roi_percent']:.1f}%")

        return QuickFlipROIResponse(
            purchase_price=metrics["purchase_price"],
            renovation_cost=metrics["renovation_cost"],
            total_investment=metrics["total_investment"],
            arv=metrics["arv"],
            holding_costs=metrics["holding_costs"],
            selling_costs=metrics["selling_costs"],
            gross_profit=metrics["gross_profit"],
            net_profit=metrics["net_profit"],
            roi_percent=metrics["roi_percent"]
        )

    except Exception as e:
        logger.error(f"Quick flip ROI calculation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Calculation failed: {str(e)}"
        )


@router.post(
    "/renovation-budget",
    response_model=RenovationBudgetResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate renovation budget",
    description="Calculate total renovation budget with contingency and ROI"
)
@rate_limit(requests_per_minute=60)
async def calculate_renovation_budget(
    items: List[RenovationItemRequest],
    contingency_percent: float = 0.10,
    user: TokenData = Depends(get_current_user)
):
    """
    Calculate renovation budget summary.

    Totals all renovation items, adds contingency, calculates expected
    value add, and estimates ROI.
    """
    logger.info(f"Renovation budget request from user {user.user_id}")

    try:
        # Convert items
        items_list = []
        for item in items:
            items_list.append({
                "category": item.category,
                "description": item.description,
                "cost": item.cost,
                "value_add_factor": item.value_add_factor,
                "duration_days": item.duration_days,
                "priority": item.priority
            })

        # Create renovation plan
        plan = arv_calculator.create_renovation_plan(
            items_list,
            contingency_percent=contingency_percent
        )

        # Calculate totals
        subtotal = sum(item.cost for item in plan.items)
        contingency_amount = subtotal * contingency_percent
        total_cost = plan.total_cost
        expected_value_add = plan.expected_value_add
        roi_estimate = (expected_value_add / total_cost) * 100 if total_cost > 0 else 0

        # Format items for response
        items_formatted = []
        for item in plan.items:
            items_formatted.append({
                "category": item.category,
                "description": item.description,
                "cost": item.cost,
                "value_add_factor": item.value_add_factor,
                "expected_value_add": item.cost * item.value_add_factor,
                "duration_days": item.duration_days,
                "priority": item.priority
            })

        logger.info(f"Renovation budget: ${total_cost:,.0f}, Expected value add: ${expected_value_add:,.0f}")

        return RenovationBudgetResponse(
            items=items_formatted,
            subtotal=subtotal,
            contingency_percent=contingency_percent,
            contingency_amount=contingency_amount,
            total_cost=total_cost,
            expected_value_add=expected_value_add,
            total_duration_days=plan.total_duration_days,
            roi_estimate=roi_estimate
        )

    except Exception as e:
        logger.error(f"Budget calculation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Budget calculation failed: {str(e)}"
        )


@router.get(
    "/value-add-factors",
    summary="Get standard value add factors",
    description="Get industry-standard value add factors by renovation category"
)
@rate_limit(requests_per_minute=60)
async def get_value_add_factors(
    user: TokenData = Depends(get_current_user)
):
    """
    Get standard value add factors.

    Returns industry-standard ROI percentages for common renovation
    categories based on Remodeling Magazine Cost vs Value Report.

    **Example:**
    - Kitchen Remodel (Minor): 72% cost recovery
    - Garage Door Replacement: 94% cost recovery
    - Paint (Interior): 100% cost recovery
    """
    return {
        "value_add_factors": arv_calculator.value_add_factors,
        "source": "Based on Remodeling Magazine Cost vs Value Report",
        "note": "Actual ROI varies by market, property type, and quality of work"
    }
