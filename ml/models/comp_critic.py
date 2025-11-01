"""
Comp-Critic: Adversarial Comparative Market Analysis

Analyzes properties against comparable properties to identify:
- Over/undervalued properties
- Negotiation leverage
- Market anomalies

Part of Wave 3.1 - Comp-Critic adversarial comp analysis.
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MarketPosition(str, Enum):
    """Market position classification"""
    OVERVALUED = "overvalued"
    FAIRLY_VALUED = "fairly_valued"
    UNDERVALUED = "undervalued"


class NegotiationStrategy(str, Enum):
    """Recommended negotiation approach"""
    AGGRESSIVE = "aggressive"  # High leverage, push for discount
    MODERATE = "moderate"      # Balanced approach
    CAUTIOUS = "cautious"      # Low leverage, be careful


@dataclass
class ComparableProperty:
    """Comparable property with analysis"""
    property_id: str
    similarity_score: float
    listing_price: float
    price_per_sqft: float
    bedrooms: int
    bathrooms: float
    square_footage: int
    days_on_market: int
    property_type: str


@dataclass
class CompAnalysis:
    """Result of comparative market analysis"""
    property_id: str
    subject_price: float
    subject_price_per_sqft: float

    # Comps statistics
    num_comps: int
    avg_comp_price: float
    avg_comp_price_per_sqft: float
    median_comp_price: float
    median_comp_price_per_sqft: float

    # Market position
    market_position: MarketPosition
    price_deviation_percent: float  # Positive = overvalued, Negative = undervalued
    price_deviation_std_dev: float  # How many std devs from mean

    # Negotiation leverage
    negotiation_leverage: float  # 0-1 scale (higher = more leverage for buyer)
    negotiation_strategy: NegotiationStrategy
    recommended_offer_range: Tuple[float, float]  # (min, max)

    # Supporting data
    comps: List[ComparableProperty]
    outlier_comps: List[ComparableProperty]  # Excluded as outliers

    # Recommendations
    recommendations: List[str]
    risk_factors: List[str]
    opportunities: List[str]


class CompCriticAnalyzer:
    """
    Adversarial Comparative Market Analysis Engine

    Uses similar properties to identify pricing anomalies and
    calculate negotiation leverage.
    """

    def __init__(
        self,
        min_comps: int = 5,
        max_comps: int = 20,
        min_similarity: float = 0.6,
        outlier_threshold: float = 2.5  # Std devs
    ):
        """
        Initialize Comp-Critic analyzer

        Args:
            min_comps: Minimum number of comps required for analysis
            max_comps: Maximum number of comps to consider
            min_similarity: Minimum similarity score to include comp
            outlier_threshold: Std dev threshold for outlier detection
        """
        self.min_comps = min_comps
        self.max_comps = max_comps
        self.min_similarity = min_similarity
        self.outlier_threshold = outlier_threshold

    def analyze(
        self,
        subject_property: ComparableProperty,
        comparable_properties: List[ComparableProperty]
    ) -> CompAnalysis:
        """
        Perform comprehensive comp analysis

        Args:
            subject_property: Property being analyzed
            comparable_properties: List of similar properties

        Returns:
            CompAnalysis with market position and recommendations
        """
        # Filter comps by similarity threshold
        valid_comps = [
            comp for comp in comparable_properties
            if comp.similarity_score >= self.min_similarity
        ]

        if len(valid_comps) < self.min_comps:
            logger.warning(
                f"Only {len(valid_comps)} valid comps found "
                f"(min required: {self.min_comps})"
            )

        # Limit to max_comps
        valid_comps = sorted(
            valid_comps,
            key=lambda x: x.similarity_score,
            reverse=True
        )[:self.max_comps]

        # Remove outliers
        comps, outliers = self._remove_outliers(valid_comps)

        # Calculate comp statistics
        comp_prices = [comp.price_per_sqft for comp in comps]
        avg_price_per_sqft = np.mean(comp_prices)
        median_price_per_sqft = np.median(comp_prices)
        std_price_per_sqft = np.std(comp_prices)

        avg_comp_price = np.mean([comp.listing_price for comp in comps])
        median_comp_price = np.median([comp.listing_price for comp in comps])

        # Calculate price deviation
        price_deviation_percent = (
            (subject_property.price_per_sqft - avg_price_per_sqft)
            / avg_price_per_sqft * 100
        )

        price_deviation_std_dev = (
            (subject_property.price_per_sqft - avg_price_per_sqft)
            / std_price_per_sqft
        ) if std_price_per_sqft > 0 else 0

        # Determine market position
        market_position = self._determine_market_position(
            price_deviation_percent,
            price_deviation_std_dev
        )

        # Calculate negotiation leverage
        negotiation_leverage = self._calculate_negotiation_leverage(
            subject_property,
            comps,
            market_position,
            price_deviation_percent
        )

        # Determine negotiation strategy
        negotiation_strategy = self._determine_negotiation_strategy(
            negotiation_leverage,
            market_position,
            price_deviation_percent
        )

        # Calculate recommended offer range
        offer_range = self._calculate_offer_range(
            subject_property.listing_price,
            market_position,
            price_deviation_percent,
            negotiation_leverage
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            subject_property,
            comps,
            market_position,
            price_deviation_percent,
            negotiation_leverage
        )

        # Identify risk factors
        risk_factors = self._identify_risk_factors(
            subject_property,
            comps,
            market_position
        )

        # Identify opportunities
        opportunities = self._identify_opportunities(
            subject_property,
            comps,
            market_position,
            price_deviation_percent
        )

        return CompAnalysis(
            property_id=subject_property.property_id,
            subject_price=subject_property.listing_price,
            subject_price_per_sqft=subject_property.price_per_sqft,
            num_comps=len(comps),
            avg_comp_price=float(avg_comp_price),
            avg_comp_price_per_sqft=float(avg_price_per_sqft),
            median_comp_price=float(median_comp_price),
            median_comp_price_per_sqft=float(median_price_per_sqft),
            market_position=market_position,
            price_deviation_percent=float(price_deviation_percent),
            price_deviation_std_dev=float(price_deviation_std_dev),
            negotiation_leverage=float(negotiation_leverage),
            negotiation_strategy=negotiation_strategy,
            recommended_offer_range=offer_range,
            comps=comps,
            outlier_comps=outliers,
            recommendations=recommendations,
            risk_factors=risk_factors,
            opportunities=opportunities
        )

    def _remove_outliers(
        self,
        comps: List[ComparableProperty]
    ) -> Tuple[List[ComparableProperty], List[ComparableProperty]]:
        """Remove price outliers from comp set"""
        if len(comps) < 3:
            return comps, []

        prices = np.array([comp.price_per_sqft for comp in comps])
        mean_price = np.mean(prices)
        std_price = np.std(prices)

        valid_comps = []
        outliers = []

        for comp in comps:
            z_score = abs((comp.price_per_sqft - mean_price) / std_price) if std_price > 0 else 0
            if z_score <= self.outlier_threshold:
                valid_comps.append(comp)
            else:
                outliers.append(comp)

        return valid_comps, outliers

    def _determine_market_position(
        self,
        price_deviation_percent: float,
        price_deviation_std_dev: float
    ) -> MarketPosition:
        """Determine if property is over/under/fairly valued"""
        # Thresholds
        OVERVALUED_THRESHOLD = 10.0  # 10% above comps
        UNDERVALUED_THRESHOLD = -10.0  # 10% below comps

        if price_deviation_percent > OVERVALUED_THRESHOLD:
            return MarketPosition.OVERVALUED
        elif price_deviation_percent < UNDERVALUED_THRESHOLD:
            return MarketPosition.UNDERVALUED
        else:
            return MarketPosition.FAIRLY_VALUED

    def _calculate_negotiation_leverage(
        self,
        subject: ComparableProperty,
        comps: List[ComparableProperty],
        market_position: MarketPosition,
        price_deviation_percent: float
    ) -> float:
        """
        Calculate negotiation leverage score (0-1)

        Higher score = more leverage for buyer
        """
        leverage = 0.5  # Baseline

        # Factor 1: Price deviation (30% weight)
        if market_position == MarketPosition.OVERVALUED:
            leverage += 0.3 * min(abs(price_deviation_percent) / 30.0, 1.0)
        elif market_position == MarketPosition.UNDERVALUED:
            leverage -= 0.2 * min(abs(price_deviation_percent) / 30.0, 1.0)

        # Factor 2: Days on market (25% weight)
        avg_dom = np.mean([comp.days_on_market for comp in comps if comp.days_on_market > 0])
        if subject.days_on_market > avg_dom * 1.5:
            leverage += 0.25
        elif subject.days_on_market < avg_dom * 0.5:
            leverage -= 0.15

        # Factor 3: Number of quality comps (15% weight)
        high_similarity_comps = sum(1 for comp in comps if comp.similarity_score >= 0.85)
        if high_similarity_comps >= 5:
            leverage += 0.15

        # Factor 4: Price consistency (10% weight)
        price_std = np.std([comp.price_per_sqft for comp in comps])
        price_mean = np.mean([comp.price_per_sqft for comp in comps])
        cv = price_std / price_mean if price_mean > 0 else 1.0  # Coefficient of variation
        if cv < 0.1:  # Low variance = strong comp evidence
            leverage += 0.1

        # Clamp to [0, 1]
        return max(0.0, min(1.0, leverage))

    def _determine_negotiation_strategy(
        self,
        leverage: float,
        market_position: MarketPosition,
        price_deviation: float
    ) -> NegotiationStrategy:
        """Recommend negotiation strategy based on leverage"""
        if leverage >= 0.7 and market_position == MarketPosition.OVERVALUED:
            return NegotiationStrategy.AGGRESSIVE
        elif leverage <= 0.3 or market_position == MarketPosition.UNDERVALUED:
            return NegotiationStrategy.CAUTIOUS
        else:
            return NegotiationStrategy.MODERATE

    def _calculate_offer_range(
        self,
        listing_price: float,
        market_position: MarketPosition,
        price_deviation: float,
        leverage: float
    ) -> Tuple[float, float]:
        """Calculate recommended offer range"""
        # Base discount/premium
        if market_position == MarketPosition.OVERVALUED:
            # Aim to bring to market value
            base_discount = min(abs(price_deviation), 20.0)  # Cap at 20%
        elif market_position == MarketPosition.UNDERVALUED:
            # Less room to negotiate
            base_discount = 2.0
        else:
            # Standard negotiation room
            base_discount = 5.0

        # Adjust based on leverage
        leverage_adjustment = (leverage - 0.5) * 10.0  # ±5% based on leverage
        total_discount = base_discount + leverage_adjustment

        # Calculate range (±2% around target discount)
        min_offer = listing_price * (1 - (total_discount + 2.0) / 100)
        max_offer = listing_price * (1 - (total_discount - 2.0) / 100)

        # Ensure sensible bounds
        min_offer = max(min_offer, listing_price * 0.70)  # Don't go below 30% discount
        max_offer = min(max_offer, listing_price * 0.98)  # Don't offer more than 2% below ask

        return (float(min_offer), float(max_offer))

    def _generate_recommendations(
        self,
        subject: ComparableProperty,
        comps: List[ComparableProperty],
        market_position: MarketPosition,
        price_deviation: float,
        leverage: float
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        if market_position == MarketPosition.OVERVALUED:
            recommendations.append(
                f"Property is {abs(price_deviation):.1f}% overvalued "
                f"based on {len(comps)} comparable properties"
            )
            recommendations.append(
                f"Strong negotiation position - aim for "
                f"{abs(price_deviation):.0f}% price reduction"
            )
        elif market_position == MarketPosition.UNDERVALUED:
            recommendations.append(
                f"Property is {abs(price_deviation):.1f}% undervalued "
                f"- good investment opportunity"
            )
            recommendations.append("Act quickly - limited negotiation room expected")
        else:
            recommendations.append("Property is fairly priced relative to market")
            recommendations.append("Standard negotiation approach recommended")

        if leverage >= 0.7:
            recommendations.append(
                "High buyer leverage - seller may be motivated"
            )
        elif leverage <= 0.3:
            recommendations.append(
                "Limited buyer leverage - expect competitive bidding"
            )

        if subject.days_on_market > 60:
            recommendations.append(
                f"Property has been on market {subject.days_on_market} days "
                "- seller may be more motivated"
            )

        return recommendations

    def _identify_risk_factors(
        self,
        subject: ComparableProperty,
        comps: List[ComparableProperty],
        market_position: MarketPosition
    ) -> List[str]:
        """Identify potential risks"""
        risks = []

        if len(comps) < self.min_comps:
            risks.append(
                f"Limited comp data - only {len(comps)} comparable properties found"
            )

        if market_position == MarketPosition.UNDERVALUED:
            risks.append(
                "Undervalued properties may have hidden issues or undesirable features"
            )

        if subject.days_on_market < 7:
            risks.append(
                "New listing - may attract multiple offers"
            )

        # Check for wide price variance in comps
        price_std = np.std([comp.price_per_sqft for comp in comps])
        price_mean = np.mean([comp.price_per_sqft for comp in comps])
        if price_std / price_mean > 0.2:
            risks.append(
                "High price variance in comps - market may be unstable"
            )

        return risks

    def _identify_opportunities(
        self,
        subject: ComparableProperty,
        comps: List[ComparableProperty],
        market_position: MarketPosition,
        price_deviation: float
    ) -> List[str]:
        """Identify opportunities"""
        opportunities = []

        if market_position == MarketPosition.OVERVALUED and abs(price_deviation) > 15:
            opportunities.append(
                "Significant room for negotiation - could secure 15%+ discount"
            )

        if subject.days_on_market > 90:
            opportunities.append(
                "Stale listing - seller likely highly motivated"
            )

        # Check if subject has better features than comps
        avg_sqft = np.mean([comp.square_footage for comp in comps])
        if subject.square_footage > avg_sqft * 1.1:
            opportunities.append(
                "Property is 10%+ larger than comps - good value per sqft"
            )

        return opportunities
