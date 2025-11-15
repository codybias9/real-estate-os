"""Property scoring service - evaluates investment potential of properties."""

import sys
sys.path.insert(0, '/home/user/real-estate-os')

from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from db.models import Property, PropertyEnrichment, PropertyScore
from src.models.score import ScoreBreakdown, ScoreFeatures


class PropertyScorer:
    """Service for scoring properties based on investment potential."""

    MODEL_VERSION = "1.0.0"
    METHOD = "rule_based"  # Can be changed to "ml" when actual model is trained

    def __init__(self, db_session: Session):
        """Initialize scorer with database session."""
        self.db = db_session

    def score_property(self, property_id: int) -> PropertyScore:
        """
        Score a property based on investment criteria.

        Args:
            property_id: ID of the property to score

        Returns:
            PropertyScore object with scores and recommendation
        """
        # Get property and enrichment
        prop = self.db.query(Property).filter(Property.id == property_id).first()
        if not prop:
            raise ValueError(f"Property {property_id} not found")

        enrichment = self.db.query(PropertyEnrichment).filter(
            PropertyEnrichment.property_id == property_id
        ).first()

        if not enrichment:
            raise ValueError(f"Property {property_id} must be enriched before scoring")

        # Calculate features
        features = self._calculate_features(prop, enrichment)

        # Calculate component scores
        price_score = self._score_price_analysis(prop, enrichment, features)
        market_timing_score = self._score_market_timing(prop, enrichment, features)
        investment_metrics_score = self._score_investment_metrics(prop, enrichment, features)
        location_quality_score = self._score_location_quality(prop, enrichment, features)
        property_condition_score = self._score_property_condition(prop, enrichment, features)

        # Create score breakdown
        score_breakdown = ScoreBreakdown(
            price_score=price_score,
            market_timing_score=market_timing_score,
            investment_metrics_score=investment_metrics_score,
            location_quality_score=location_quality_score,
            property_condition_score=property_condition_score,
            price_weight=0.25,
            market_timing_weight=0.20,
            investment_metrics_weight=0.25,
            location_quality_weight=0.15,
            property_condition_weight=0.15,
        )

        # Calculate weighted total score
        total_score = int(
            price_score * 0.25 +
            market_timing_score * 0.20 +
            investment_metrics_score * 0.25 +
            location_quality_score * 0.15 +
            property_condition_score * 0.15
        )

        # Determine recommendation and risk
        recommendation, recommendation_reason = self._determine_recommendation(total_score, features)
        risk_level, risk_factors = self._assess_risk(prop, enrichment, features)

        # Calculate confidence based on data completeness
        confidence_score = self._calculate_confidence(prop, enrichment)

        # Check if score already exists
        existing = self.db.query(PropertyScore).filter(
            PropertyScore.property_id == property_id
        ).first()

        score_data = {
            "property_id": property_id,
            "total_score": total_score,
            "score_breakdown": score_breakdown.model_dump(),
            "features": features.model_dump(),
            "recommendation": recommendation,
            "recommendation_reason": recommendation_reason,
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "model_version": self.MODEL_VERSION,
            "scoring_method": self.METHOD,
            "confidence_score": confidence_score,
        }

        if existing:
            # Update existing score
            for field, value in score_data.items():
                if field != "property_id":  # Don't update FK
                    setattr(existing, field, value)
            score = existing
        else:
            # Create new score
            score = PropertyScore(**score_data)
            self.db.add(score)

        # Update property status
        if prop.status in ['new', 'enriched']:
            prop.status = 'scored'

        self.db.commit()
        self.db.refresh(score)

        return score

    def _calculate_features(self, prop: Property, enrichment: PropertyEnrichment) -> ScoreFeatures:
        """Calculate all features used for scoring."""

        # Price analysis
        median_value = enrichment.median_home_value or prop.price
        price_below_market_pct = ((median_value - prop.price) / median_value * 100) if median_value > 0 else 0

        # Days on market (estimate from listing date)
        days_on_market = 30  # Placeholder - would calculate from listing_date

        # Investment metrics
        monthly_rent = (enrichment.median_rent or 0)
        annual_rent = monthly_rent * 12
        rental_yield = (annual_rent / prop.price * 100) if prop.price > 0 else 0
        cap_rate = rental_yield - 2.0  # Rough estimate (rental yield - operating expenses %)

        # Equity opportunity
        last_sale = enrichment.last_sale_price or prop.price
        equity_opportunity_pct = ((prop.price - last_sale) / last_sale * 100) if last_sale > 0 else 0

        # Property condition (based on age)
        current_year = 2025
        age = current_year - (prop.year_built or 2000)
        condition_score = max(0, 100 - (age * 1.5))  # Newer = better condition

        return ScoreFeatures(
            price_below_market_pct=round(price_below_market_pct, 2),
            days_on_market=days_on_market,
            estimated_rental_yield=round(rental_yield, 2),
            cap_rate=round(cap_rate, 2),
            equity_opportunity_pct=round(equity_opportunity_pct, 2),
            neighborhood_appreciation_1yr=enrichment.appreciation_1yr,
            neighborhood_appreciation_5yr=enrichment.appreciation_5yr,
            year_built_score=round(condition_score, 1),
            condition_score=round(condition_score, 1),
            location_score=float(enrichment.walkability_score or 50),
            school_quality_score=float((enrichment.school_rating or 5) * 10),
            walkability_score=enrichment.walkability_score,
        )

    def _score_price_analysis(self, prop: Property, enrichment: PropertyEnrichment, features: ScoreFeatures) -> float:
        """Score based on price competitiveness."""
        score = 50.0  # Base score

        # Below market value is good
        if features.price_below_market_pct and features.price_below_market_pct > 0:
            score += min(features.price_below_market_pct * 2, 40)  # Up to +40 points
        elif features.price_below_market_pct and features.price_below_market_pct < 0:
            score += max(features.price_below_market_pct * 1.5, -30)  # Up to -30 points

        return min(100, max(0, score))

    def _score_market_timing(self, prop: Property, enrichment: PropertyEnrichment, features: ScoreFeatures) -> float:
        """Score based on market timing and trends."""
        score = 50.0

        # Strong appreciation is good
        if features.neighborhood_appreciation_1yr:
            if features.neighborhood_appreciation_1yr > 5:
                score += 20
            elif features.neighborhood_appreciation_1yr > 3:
                score += 10
            else:
                score += 5

        # Days on market (longer = more negotiable)
        if features.days_on_market:
            if features.days_on_market > 90:
                score += 20
            elif features.days_on_market > 60:
                score += 10

        return min(100, max(0, score))

    def _score_investment_metrics(self, prop: Property, enrichment: PropertyEnrichment, features: ScoreFeatures) -> float:
        """Score based on investment return potential."""
        score = 30.0

        # Rental yield
        if features.estimated_rental_yield:
            if features.estimated_rental_yield > 8:
                score += 35
            elif features.estimated_rental_yield > 6:
                score += 25
            elif features.estimated_rental_yield > 4:
                score += 15
            else:
                score += 5

        # Cap rate
        if features.cap_rate:
            if features.cap_rate > 6:
                score += 20
            elif features.cap_rate > 4:
                score += 10

        # Equity opportunity
        if features.equity_opportunity_pct and features.equity_opportunity_pct > 10:
            score += 15

        return min(100, max(0, score))

    def _score_location_quality(self, prop: Property, enrichment: PropertyEnrichment, features: ScoreFeatures) -> float:
        """Score based on location desirability."""
        score = 0.0

        # Walkability
        score += (features.walkability_score or 0) * 0.4

        # School quality
        score += (features.school_quality_score or 0) * 0.4

        # Crime (lower is better)
        crime_score = 100 - (enrichment.crime_index or 50)
        score += crime_score * 0.2

        return min(100, max(0, score))

    def _score_property_condition(self, prop: Property, enrichment: PropertyEnrichment, features: ScoreFeatures) -> float:
        """Score based on property condition and quality."""
        score = features.condition_score or 50

        # Adjust for property type
        if prop.property_type == "single_family":
            score += 5  # SFH tend to appreciate better
        elif prop.property_type == "condo":
            score -= 5  # Condos have HOA concerns

        # Adjust for size
        if prop.sqft:
            if prop.sqft > 2500:
                score += 5
            elif prop.sqft < 1000:
                score -= 5

        return min(100, max(0, score))

    def _determine_recommendation(self, total_score: int, features: ScoreFeatures) -> Tuple[str, str]:
        """Determine investment recommendation based on score."""

        if total_score >= 85:
            return "strong_buy", (
                f"Excellent investment opportunity with strong fundamentals. "
                f"Property scores {total_score}/100 with {features.estimated_rental_yield:.1f}% rental yield "
                f"and {features.price_below_market_pct:.1f}% below market value."
            )
        elif total_score >= 70:
            return "buy", (
                f"Good investment opportunity. Property scores {total_score}/100 with solid fundamentals. "
                f"Rental yield of {features.estimated_rental_yield:.1f}% and good location quality."
            )
        elif total_score >= 55:
            return "hold", (
                f"Moderate investment potential. Property scores {total_score}/100. "
                f"Consider for portfolio diversification but not a priority deal."
            )
        else:
            return "pass", (
                f"Limited investment potential. Property scores {total_score}/100. "
                f"Better opportunities likely available in the market."
            )

    def _assess_risk(self, prop: Property, enrichment: PropertyEnrichment, features: ScoreFeatures) -> Tuple[str, List[str]]:
        """Assess investment risk level and factors."""

        risk_factors = []
        risk_score = 0

        # Market risks
        if features.price_below_market_pct and features.price_below_market_pct < -10:
            risk_factors.append("Property priced above market")
            risk_score += 2

        if features.neighborhood_appreciation_1yr and features.neighborhood_appreciation_1yr < 2:
            risk_factors.append("Slow market appreciation")
            risk_score += 1

        # Location risks
        if enrichment.crime_index and enrichment.crime_index > 60:
            risk_factors.append("Higher crime area")
            risk_score += 2

        if enrichment.school_rating and enrichment.school_rating < 6:
            risk_factors.append("Below average schools")
            risk_score += 1

        # Environmental risks
        if enrichment.flood_zone and enrichment.flood_zone in ["A", "AE", "VE"]:
            risk_factors.append("Flood risk zone")
            risk_score += 2

        if enrichment.earthquake_zone and enrichment.earthquake_zone == "high":
            risk_factors.append("High earthquake risk")
            risk_score += 1

        # Property risks
        age = 2025 - (prop.year_built or 2000)
        if age > 40:
            risk_factors.append("Older property may need repairs")
            risk_score += 1

        # Financial risks
        if features.estimated_rental_yield and features.estimated_rental_yield < 4:
            risk_factors.append("Low rental yield")
            risk_score += 1

        # Determine risk level
        if risk_score >= 5:
            risk_level = "high"
        elif risk_score >= 3:
            risk_level = "medium"
        else:
            risk_level = "low"

        if not risk_factors:
            risk_factors = ["Standard market risks apply"]

        return risk_level, risk_factors

    def _calculate_confidence(self, prop: Property, enrichment: PropertyEnrichment) -> float:
        """Calculate confidence score based on data completeness."""

        completeness_score = 0.5  # Base confidence

        # Check property data completeness
        if prop.sqft:
            completeness_score += 0.05
        if prop.year_built:
            completeness_score += 0.05
        if prop.bedrooms and prop.bathrooms:
            completeness_score += 0.05

        # Check enrichment data completeness
        if enrichment.median_home_value:
            completeness_score += 0.10
        if enrichment.median_rent:
            completeness_score += 0.10
        if enrichment.school_rating:
            completeness_score += 0.05
        if enrichment.walkability_score:
            completeness_score += 0.05
        if enrichment.appreciation_1yr:
            completeness_score += 0.05

        return min(1.0, completeness_score)


def score_property_by_id(property_id: int, db_session: Session) -> PropertyScore:
    """
    Convenience function to score a property by ID.

    Args:
        property_id: ID of property to score
        db_session: SQLAlchemy session

    Returns:
        PropertyScore object
    """
    scorer = PropertyScorer(db_session)
    return scorer.score_property(property_id)
