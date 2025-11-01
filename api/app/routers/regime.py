"""Regime Monitoring Router
Market regime detection and policy recommendations
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from enum import Enum

from ..database import get_db
from ..auth.hybrid_dependencies import get_current_user
from ..auth.models import User
import sys
sys.path.append('/home/user/real-estate-os')
from ml.regime.market_regime_detector import (
    MarketRegimeDetector,
    PolicyEngine,
    MarketSignals,
    MarketRegime
)
from ml.regime.changepoint_detection import (
    BayesianOnlineChangePointDetection,
    detect_changepoints_offline
)
import pandas as pd
import numpy as np

router = APIRouter(
    prefix="/regime",
    tags=["regime-monitoring"]
)


# ============================================================================
# Models
# ============================================================================

class RegimeEnum(str, Enum):
    """Market regime types"""
    HOT = "hot"
    WARM = "warm"
    COOL = "cool"
    COLD = "cold"


class MarketSignalsInput(BaseModel):
    """Input market signals"""
    date: str
    market: str

    # Inventory
    active_listings: int
    months_of_inventory: float
    new_listings_mom: float

    # Price
    median_list_price: float
    median_sale_price: float
    list_to_sale_ratio: float
    price_yoy_change: float

    # Velocity
    avg_days_on_market: float
    dom_yoy_change: float
    sell_through_rate: float

    # Financial
    avg_cap_rate: float
    avg_price_per_sf: float
    mortgage_rate: float

    # Volume
    sales_volume_mom: float


class RegimeDetectionResponse(BaseModel):
    """Regime detection result"""
    date: str
    market: str
    composite_index: float
    regime: RegimeEnum
    regime_confidence: float
    is_change_point: bool

    # Component scores
    inventory_score: float
    price_score: float
    velocity_score: float
    financial_score: float


class PolicyRecommendationResponse(BaseModel):
    """Policy recommendations"""
    regime: RegimeEnum

    # Offer strategy
    max_offer_to_arv: float
    earnest_money_pct: float
    due_diligence_days: int

    # Targeting
    target_cap_rate_min: float
    target_margin_min: float

    # Competition
    max_bidding_rounds: int
    offer_deadline_hours: int

    # Messaging
    followup_frequency_days: int
    max_followups: int

    # Rationale
    rationale: str


class MarketHealthResponse(BaseModel):
    """Market health summary"""
    market: str
    as_of_date: str
    current_regime: RegimeEnum
    composite_index: float
    days_in_current_regime: int
    previous_regime: Optional[RegimeEnum] = None
    last_regime_change: Optional[str] = None


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/detect", response_model=RegimeDetectionResponse)
async def detect_regime(
    signals: MarketSignalsInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Detect market regime from current signals

    Args:
        signals: Market signals
        user: Current authenticated user
        db: Database session

    Returns:
        Regime detection result with composite index and classification
    """

    # Convert to MarketSignals
    market_signals = MarketSignals(
        date=datetime.fromisoformat(signals.date),
        market=signals.market,
        active_listings=signals.active_listings,
        months_of_inventory=signals.months_of_inventory,
        new_listings_mom=signals.new_listings_mom,
        median_list_price=signals.median_list_price,
        median_sale_price=signals.median_sale_price,
        list_to_sale_ratio=signals.list_to_sale_ratio,
        price_yoy_change=signals.price_yoy_change,
        avg_days_on_market=signals.avg_days_on_market,
        dom_yoy_change=signals.dom_yoy_change,
        sell_through_rate=signals.sell_through_rate,
        avg_cap_rate=signals.avg_cap_rate,
        avg_price_per_sf=signals.avg_price_per_sf,
        mortgage_rate=signals.mortgage_rate,
        sales_volume_mom=signals.sales_volume_mom
    )

    # Detect regime
    detector = MarketRegimeDetector()

    # TODO: Load previous regime from database for hysteresis
    previous_regime = None

    result = detector.detect_regime(market_signals, previous_regime)

    # TODO: Store result in database with tenant_id

    return RegimeDetectionResponse(
        date=result.date.isoformat(),
        market=result.market,
        composite_index=result.composite_index,
        regime=RegimeEnum(result.regime.value),
        regime_confidence=result.regime_confidence,
        is_change_point=result.is_change_point,
        inventory_score=result.inventory_score,
        price_score=result.price_score,
        velocity_score=result.velocity_score,
        financial_score=result.financial_score
    )


@router.get("/policy/{regime}", response_model=PolicyRecommendationResponse)
async def get_policy_for_regime(
    regime: RegimeEnum,
    user: User = Depends(get_current_user)
):
    """Get policy recommendations for a given regime

    Args:
        regime: Market regime
        user: Current authenticated user

    Returns:
        Policy recommendations
    """

    policy_engine = PolicyEngine()
    regime_obj = MarketRegime(regime.value)
    policy = policy_engine.get_policy_for_regime(regime_obj)

    return PolicyRecommendationResponse(
        regime=RegimeEnum(policy.regime.value),
        max_offer_to_arv=policy.max_offer_to_arv,
        earnest_money_pct=policy.earnest_money_pct,
        due_diligence_days=policy.due_diligence_days,
        target_cap_rate_min=policy.target_cap_rate_min,
        target_margin_min=policy.target_margin_min,
        max_bidding_rounds=policy.max_bidding_rounds,
        offer_deadline_hours=policy.offer_deadline_hours,
        followup_frequency_days=policy.followup_frequency_days,
        max_followups=policy.max_followups,
        rationale=policy.rationale
    )


@router.get("/current/{market}", response_model=MarketHealthResponse)
async def get_current_regime(
    market: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current market regime for a market

    Args:
        market: Market identifier (e.g., ZIP code)
        user: Current authenticated user
        db: Database session

    Returns:
        Current market health summary
    """

    # TODO: Load from database
    # For now, return mock response

    raise HTTPException(
        status_code=501,
        detail="Current regime retrieval requires database integration"
    )


@router.get("/history/{market}")
async def get_regime_history(
    market: str,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get historical regime classifications for a market

    Args:
        market: Market identifier
        start_date: Start date (ISO format)
        end_date: End date (ISO format)
        user: Current authenticated user
        db: Database session

    Returns:
        Time series of regime classifications
    """

    # TODO: Load from database

    raise HTTPException(
        status_code=501,
        detail="Regime history requires database integration"
    )


@router.post("/detect-changepoints/{market}")
async def detect_changepoints(
    market: str,
    lookback_days: int = Query(default=365, ge=90, le=1825),
    method: str = Query(default="bocpd", regex="^(bocpd|cusum|ruptures)$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Detect regime change points in historical data

    Args:
        market: Market identifier
        lookback_days: Days to look back
        method: Detection method (bocpd, cusum, ruptures)
        user: Current authenticated user
        db: Database session

    Returns:
        List of change point dates with probabilities
    """

    # TODO: Load historical composite index from database
    # For now, generate synthetic data for demo

    # Synthetic data: 365 days with a regime shift at day 200
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=lookback_days, freq="D")

    # Generate time series with a change point
    before_shift = np.random.normal(60, 5, 200)  # Warm regime
    after_shift = np.random.normal(80, 5, lookback_days - 200)  # Hot regime
    composite_index = np.concatenate([before_shift, after_shift])

    # Detect change points
    change_point_indices = detect_changepoints_offline(
        composite_index,
        method=method
    )

    # Convert to dates
    change_points = [
        {
            "date": dates[idx].isoformat(),
            "index": int(idx),
            "composite_index_before": float(composite_index[max(0, idx - 10):idx].mean()),
            "composite_index_after": float(composite_index[idx:min(len(composite_index), idx + 10)].mean())
        }
        for idx in change_point_indices
    ]

    return {
        "market": market,
        "method": method,
        "lookback_days": lookback_days,
        "change_points_detected": len(change_points),
        "change_points": change_points
    }


@router.get("/markets")
async def list_monitored_markets(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List markets currently being monitored

    Args:
        user: Current authenticated user
        db: Database session

    Returns:
        List of monitored markets with current regimes
    """

    # TODO: Load from database filtered by tenant_id

    raise HTTPException(
        status_code=501,
        detail="Market listing requires database integration"
    )


@router.post("/policy/apply")
async def apply_policy_to_properties(
    market: str,
    regime: RegimeEnum,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Apply regime-based policy to all active properties in market

    This endpoint updates offer parameters for all properties in the specified market
    based on the current regime.

    Args:
        market: Market identifier
        regime: Market regime to apply
        user: Current authenticated user
        db: Database session

    Returns:
        Summary of properties updated
    """

    # Get policy for regime
    policy_engine = PolicyEngine()
    regime_obj = MarketRegime(regime.value)
    policy = policy_engine.get_policy_for_regime(regime_obj)

    # TODO: Update property offer parameters in database
    # UPDATE property SET
    #   max_offer_pct = policy.max_offer_to_arv,
    #   earnest_money_pct = policy.earnest_money_pct,
    #   dd_days = policy.due_diligence_days
    # WHERE market = ? AND tenant_id = ? AND status = 'active'

    return {
        "market": market,
        "regime": regime.value,
        "policy_applied": {
            "max_offer_to_arv": policy.max_offer_to_arv,
            "earnest_money_pct": policy.earnest_money_pct,
            "due_diligence_days": policy.due_diligence_days
        },
        "properties_updated": 0  # TODO: Actual count
    }
