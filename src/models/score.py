"""Property scoring models."""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ScoreFeatures(BaseModel):
    """Features used for scoring calculation."""

    # Price analysis
    price_below_market_pct: Optional[float] = Field(None, description="Percentage below market value")
    price_reduction_amount: Optional[int] = Field(None, description="Amount of price reduction")
    price_reduction_pct: Optional[float] = Field(None, description="Percentage of price reduction")

    # Time on market
    days_on_market: Optional[int] = Field(None, description="Days property has been listed")

    # Investment metrics
    estimated_rental_yield: Optional[float] = Field(None, description="Estimated rental yield percentage")
    cap_rate: Optional[float] = Field(None, description="Capitalization rate")
    cash_on_cash_return: Optional[float] = Field(None, description="Cash on cash return percentage")

    # Equity opportunity
    equity_opportunity_pct: Optional[float] = Field(None, description="Immediate equity percentage")
    arv_after_repair_value: Optional[int] = Field(None, description="After Repair Value estimate")
    estimated_repair_cost: Optional[int] = Field(None, description="Estimated repair costs")

    # Market trends
    neighborhood_appreciation_1yr: Optional[float] = Field(None, description="1-year neighborhood appreciation")
    neighborhood_appreciation_5yr: Optional[float] = Field(None, description="5-year neighborhood appreciation")

    # Property condition indicators
    year_built_score: Optional[float] = Field(None, description="Score based on age of property")
    condition_score: Optional[float] = Field(None, description="Overall condition score")

    # Location quality
    location_score: Optional[float] = Field(None, description="Location quality score")
    school_quality_score: Optional[float] = Field(None, description="School quality score")
    walkability_score: Optional[int] = Field(None, description="Walkability score")

    # Investment potential
    flip_potential_score: Optional[float] = Field(None, description="Score for flip potential")
    rental_potential_score: Optional[float] = Field(None, description="Score for rental potential")
    hold_potential_score: Optional[float] = Field(None, description="Score for long-term hold")


class ScoreBreakdown(BaseModel):
    """Breakdown of score components."""

    price_score: float = Field(..., ge=0, le=100, description="Price analysis score (0-100)")
    market_timing_score: float = Field(..., ge=0, le=100, description="Market timing score (0-100)")
    investment_metrics_score: float = Field(..., ge=0, le=100, description="Investment metrics score (0-100)")
    location_quality_score: float = Field(..., ge=0, le=100, description="Location quality score (0-100)")
    property_condition_score: float = Field(..., ge=0, le=100, description="Property condition score (0-100)")

    # Weights for each component
    price_weight: float = Field(default=0.25, description="Weight for price component")
    market_timing_weight: float = Field(default=0.20, description="Weight for market timing")
    investment_metrics_weight: float = Field(default=0.25, description="Weight for investment metrics")
    location_quality_weight: float = Field(default=0.15, description="Weight for location")
    property_condition_weight: float = Field(default=0.15, description="Weight for condition")


class ScoreBase(BaseModel):
    """Base score model."""

    property_id: int = Field(..., description="Foreign key to property")

    # Overall score
    total_score: int = Field(..., ge=0, le=100, description="Total investment score (0-100)")

    # Score breakdown
    score_breakdown: ScoreBreakdown = Field(..., description="Detailed score breakdown")

    # Features used
    features: ScoreFeatures = Field(..., description="Features used in scoring")

    # Recommendation
    recommendation: str = Field(..., description="Investment recommendation (strong_buy, buy, hold, pass)")
    recommendation_reason: str = Field(..., description="Reason for recommendation")

    # Risk assessment
    risk_level: str = Field(..., description="Risk level (low, medium, high)")
    risk_factors: list[str] = Field(default_factory=list, description="Identified risk factors")

    # Model information
    model_version: str = Field(..., description="Version of scoring model used")
    scoring_method: str = Field(..., description="Method used (ml, rule_based, hybrid)")

    # Confidence
    confidence_score: float = Field(..., ge=0, le=1, description="Confidence in the score (0-1)")

    # Metadata
    scoring_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class ScoreCreate(ScoreBase):
    """Model for creating a score."""
    pass


class PropertyScore(ScoreBase):
    """Full score model with database fields."""

    id: int = Field(..., description="Unique score ID")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record update timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "property_id": 1,
                "total_score": 87,
                "score_breakdown": {
                    "price_score": 90,
                    "market_timing_score": 75,
                    "investment_metrics_score": 92,
                    "location_quality_score": 85,
                    "property_condition_score": 80,
                    "price_weight": 0.25,
                    "market_timing_weight": 0.20,
                    "investment_metrics_weight": 0.25,
                    "location_quality_weight": 0.15,
                    "property_condition_weight": 0.15
                },
                "features": {
                    "price_below_market_pct": 8.5,
                    "days_on_market": 45,
                    "estimated_rental_yield": 7.2,
                    "equity_opportunity_pct": 12.0,
                    "neighborhood_appreciation_5yr": 28.5
                },
                "recommendation": "strong_buy",
                "recommendation_reason": "Excellent investment opportunity with strong rental yield and immediate equity",
                "risk_level": "low",
                "risk_factors": ["Market volatility"],
                "model_version": "1.0.0",
                "scoring_method": "ml",
                "confidence_score": 0.92,
                "scoring_metadata": {},
                "created_at": "2024-01-15T12:00:00",
                "updated_at": "2024-01-15T12:00:00"
            }
        }
