"""
Offer Recommendation Engine

Wave 3.2 Part 2: Optimal offer calculation with multi-objective optimization

This module calculates optimal offer amounts by balancing multiple objectives:
- Maximize value (minimize price)
- Maximize acceptance probability
- Respect buyer constraints (budget, financing, timeline)
- Account for market dynamics

Uses constraint satisfaction and scoring to recommend offers that optimize
the buyer's position while maintaining realistic acceptance chances.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import numpy as np
from datetime import datetime


@dataclass
class OfferConstraints:
    """Hard constraints that must be satisfied"""
    min_offer: float  # Absolute minimum (can't go below)
    max_offer: float  # Absolute maximum (budget ceiling)
    must_close_by: Optional[datetime] = None
    max_appraisal_gap: float = 0.0  # Max amount willing to cover if appraisal comes in low
    required_contingencies: List[str] = None  # Must-have contingencies


@dataclass
class OfferPreferences:
    """Soft preferences for optimization"""
    target_price: float  # Preferred price
    target_closing_days: int = 45
    preferred_contingencies: List[str] = None
    risk_tolerance: str = "moderate"  # conservative/moderate/aggressive
    speed_priority: float = 0.5  # 0-1, how important is quick closing


@dataclass
class MarketContext:
    """Market and property context for offer calculation"""
    listing_price: float
    market_value_estimate: float  # From comp analysis
    market_value_confidence: float  # 0-1
    days_on_market: int
    price_reductions: int
    competing_offers_likelihood: float  # 0-1 estimate
    seller_motivation_score: float  # 0-1
    market_velocity: str  # hot/warm/cool/cold


@dataclass
class OfferScenario:
    """Single offer scenario with scoring"""
    offer_amount: float
    acceptance_probability: float
    value_score: float  # How good a deal (0-1)
    constraint_score: float  # How well it fits constraints (0-1)
    overall_score: float  # Combined weighted score
    recommended_contingencies: List[str]
    recommended_closing_days: int
    escalation_clause_amount: Optional[float] = None
    rationale: str = ""


@dataclass
class OfferRecommendation:
    """Complete offer recommendation with multiple scenarios"""
    property_id: str

    # Primary recommendation
    recommended_offer: OfferScenario

    # Alternative scenarios
    conservative_offer: OfferScenario  # Lower risk, higher acceptance
    aggressive_offer: OfferScenario    # Maximum value, lower acceptance
    balanced_offer: OfferScenario      # Middle ground

    # Context
    market_context: MarketContext
    constraints: OfferConstraints

    # Insights
    key_factors: List[str]
    warnings: List[str]

    created_at: datetime


class OfferRecommendationEngine:
    """
    Optimal offer calculation engine using multi-objective optimization
    """

    def __init__(
        self,
        acceptance_weight: float = 0.4,
        value_weight: float = 0.35,
        constraint_weight: float = 0.25
    ):
        """
        Initialize engine with scoring weights

        Args:
            acceptance_weight: Weight for acceptance probability (0-1)
            value_weight: Weight for value/deal quality (0-1)
            constraint_weight: Weight for constraint satisfaction (0-1)

        Note: Weights should sum to 1.0
        """
        total_weight = acceptance_weight + value_weight + constraint_weight
        self.acceptance_weight = acceptance_weight / total_weight
        self.value_weight = value_weight / total_weight
        self.constraint_weight = constraint_weight / total_weight

    def recommend(
        self,
        property_id: str,
        constraints: OfferConstraints,
        preferences: OfferPreferences,
        market_context: MarketContext
    ) -> OfferRecommendation:
        """
        Generate optimal offer recommendation with multiple scenarios

        Args:
            property_id: Property identifier
            constraints: Hard constraints (must satisfy)
            preferences: Soft preferences (optimize for)
            market_context: Market and property data

        Returns:
            Complete offer recommendation with scenarios
        """

        # Generate candidate offers across the feasible range
        candidates = self._generate_candidates(constraints, preferences, market_context)

        # Score each candidate
        scored_scenarios = []
        for candidate in candidates:
            scenario = self._score_offer(
                candidate, constraints, preferences, market_context
            )
            scored_scenarios.append(scenario)

        # Select scenarios
        balanced = self._select_best_overall(scored_scenarios)
        conservative = self._select_most_conservative(scored_scenarios, balanced)
        aggressive = self._select_most_aggressive(scored_scenarios, balanced)

        # Determine primary recommendation based on risk tolerance
        if preferences.risk_tolerance == "conservative":
            recommended = conservative
        elif preferences.risk_tolerance == "aggressive":
            recommended = aggressive
        else:
            recommended = balanced

        # Generate insights
        key_factors = self._identify_key_factors(market_context, constraints, preferences)
        warnings = self._generate_warnings(market_context, constraints, recommended)

        return OfferRecommendation(
            property_id=property_id,
            recommended_offer=recommended,
            conservative_offer=conservative,
            aggressive_offer=aggressive,
            balanced_offer=balanced,
            market_context=market_context,
            constraints=constraints,
            key_factors=key_factors,
            warnings=warnings,
            created_at=datetime.utcnow()
        )

    def _generate_candidates(
        self,
        constraints: OfferConstraints,
        preferences: OfferPreferences,
        market: MarketContext
    ) -> List[Dict]:
        """Generate candidate offers to evaluate"""

        min_offer = constraints.min_offer
        max_offer = min(constraints.max_offer, market.listing_price * 1.05)  # Cap at 5% over asking

        # Generate offers at different discount levels
        candidates = []

        # Listing price (no discount)
        candidates.append({'amount': market.listing_price, 'type': 'at_ask'})

        # Market value
        candidates.append({'amount': market.market_value_estimate, 'type': 'market_value'})

        # Discount levels: 3%, 5%, 7%, 10%, 12%, 15%
        for discount_pct in [0.03, 0.05, 0.07, 0.10, 0.12, 0.15]:
            offer = market.listing_price * (1 - discount_pct)
            if min_offer <= offer <= max_offer:
                candidates.append({'amount': offer, 'type': f'{int(discount_pct*100)}pct_below'})

        # Target price
        if min_offer <= preferences.target_price <= max_offer:
            candidates.append({'amount': preferences.target_price, 'type': 'target'})

        # Ensure min and max are included
        candidates.append({'amount': min_offer, 'type': 'min_budget'})
        candidates.append({'amount': max_offer, 'type': 'max_budget'})

        # Remove duplicates and sort
        unique_candidates = []
        seen_amounts = set()
        for c in candidates:
            amount_rounded = round(c['amount'], -2)  # Round to nearest $100
            if amount_rounded not in seen_amounts and min_offer <= amount_rounded <= max_offer:
                seen_amounts.add(amount_rounded)
                unique_candidates.append({'amount': amount_rounded, 'type': c['type']})

        return sorted(unique_candidates, key=lambda x: x['amount'])

    def _score_offer(
        self,
        candidate: Dict,
        constraints: OfferConstraints,
        preferences: OfferPreferences,
        market: MarketContext
    ) -> OfferScenario:
        """Score a single offer candidate"""

        amount = candidate['amount']

        # Calculate acceptance probability
        acceptance_prob = self._calculate_acceptance_probability(amount, market)

        # Calculate value score (how good a deal)
        value_score = self._calculate_value_score(amount, market)

        # Calculate constraint satisfaction score
        constraint_score = self._calculate_constraint_score(amount, constraints, preferences)

        # Combined score
        overall_score = (
            self.acceptance_weight * acceptance_prob +
            self.value_weight * value_score +
            self.constraint_weight * constraint_score
        )

        # Determine deal structure for this offer
        contingencies = self._recommend_contingencies(amount, market, preferences)
        closing_days = self._recommend_closing_timeline(amount, market, preferences)
        escalation = self._recommend_escalation_clause(amount, market, preferences)

        # Build rationale
        rationale = self._build_scenario_rationale(
            amount, market, acceptance_prob, value_score, candidate['type']
        )

        return OfferScenario(
            offer_amount=round(amount, 2),
            acceptance_probability=round(acceptance_prob, 3),
            value_score=round(value_score, 3),
            constraint_score=round(constraint_score, 3),
            overall_score=round(overall_score, 3),
            recommended_contingencies=contingencies,
            recommended_closing_days=closing_days,
            escalation_clause_amount=escalation,
            rationale=rationale
        )

    def _calculate_acceptance_probability(
        self,
        offer_amount: float,
        market: MarketContext
    ) -> float:
        """
        Estimate probability of seller accepting offer

        Factors:
        - Distance from listing price
        - Market velocity
        - Days on market
        - Seller motivation
        - Competing offers likelihood
        """

        # Base probability from price distance
        price_ratio = offer_amount / market.listing_price

        if price_ratio >= 1.0:
            base_prob = 0.95  # At or above asking
        elif price_ratio >= 0.97:
            base_prob = 0.85  # Within 3%
        elif price_ratio >= 0.93:
            base_prob = 0.65  # 3-7% below
        elif price_ratio >= 0.90:
            base_prob = 0.45  # 7-10% below
        elif price_ratio >= 0.85:
            base_prob = 0.25  # 10-15% below
        else:
            base_prob = 0.10  # >15% below

        # Adjust for market velocity
        velocity_adjustment = {
            'hot': -0.15,    # Harder to negotiate in hot market
            'warm': -0.05,
            'cool': 0.05,
            'cold': 0.15     # Easier in cold market
        }
        base_prob += velocity_adjustment.get(market.market_velocity, 0.0)

        # Adjust for days on market
        if market.days_on_market > 90:
            base_prob += 0.15
        elif market.days_on_market > 60:
            base_prob += 0.10
        elif market.days_on_market > 30:
            base_prob += 0.05
        elif market.days_on_market < 7:
            base_prob -= 0.10

        # Adjust for seller motivation
        base_prob += market.seller_motivation_score * 0.2

        # Adjust for competing offers
        base_prob -= market.competing_offers_likelihood * 0.25

        # Adjust for price reductions (seller has already shown flexibility)
        if market.price_reductions >= 2:
            base_prob += 0.10
        elif market.price_reductions == 1:
            base_prob += 0.05

        return max(0.0, min(1.0, base_prob))

    def _calculate_value_score(
        self,
        offer_amount: float,
        market: MarketContext
    ) -> float:
        """
        Calculate value score (higher = better deal for buyer)

        Compares offer to market value and listing price
        """

        # Distance from market value (best score at significant discount)
        if market.market_value_estimate > 0:
            value_ratio = offer_amount / market.market_value_estimate
        else:
            value_ratio = offer_amount / market.listing_price

        if value_ratio <= 0.85:
            value_score = 1.0  # Excellent deal
        elif value_ratio <= 0.90:
            value_score = 0.85
        elif value_ratio <= 0.95:
            value_score = 0.70
        elif value_ratio <= 1.0:
            value_score = 0.50
        elif value_ratio <= 1.05:
            value_score = 0.25
        else:
            value_score = 0.0  # Overpaying

        # Weight by market value confidence
        confidence = market.market_value_confidence
        value_score = value_score * confidence + 0.5 * (1 - confidence)

        return value_score

    def _calculate_constraint_score(
        self,
        offer_amount: float,
        constraints: OfferConstraints,
        preferences: OfferPreferences
    ) -> float:
        """
        Calculate constraint satisfaction score

        Higher score = better fit to buyer's preferences
        """

        score = 1.0

        # Distance from target price
        if preferences.target_price > 0:
            target_distance = abs(offer_amount - preferences.target_price) / preferences.target_price
            score -= min(0.3, target_distance * 0.5)

        # Budget utilization (prefer not to max out budget)
        budget_range = constraints.max_offer - constraints.min_offer
        if budget_range > 0:
            position = (offer_amount - constraints.min_offer) / budget_range
            # Penalize being at extremes
            if position > 0.95 or position < 0.05:
                score -= 0.15
            elif position > 0.85 or position < 0.15:
                score -= 0.05

        return max(0.0, score)

    def _recommend_contingencies(
        self,
        offer_amount: float,
        market: MarketContext,
        preferences: OfferPreferences
    ) -> List[str]:
        """Recommend contingencies for this offer level"""

        contingencies = preferences.preferred_contingencies or []

        # In competitive markets with strong offers, may need to limit contingencies
        if market.competing_offers_likelihood > 0.7 and offer_amount >= market.listing_price * 0.98:
            # Remove financing contingency if buyer can (has high down payment)
            if "financing" in contingencies and preferences.risk_tolerance == "aggressive":
                contingencies.remove("financing")

        # Always recommend inspection unless extremely aggressive
        if "inspection" not in contingencies and preferences.risk_tolerance != "aggressive":
            contingencies.append("inspection")

        return contingencies

    def _recommend_closing_timeline(
        self,
        offer_amount: float,
        market: MarketContext,
        preferences: OfferPreferences
    ) -> int:
        """Recommend closing timeline for this offer"""

        # Start with preference
        timeline = preferences.target_closing_days

        # Faster closing can strengthen offer in competitive markets
        if market.competing_offers_likelihood > 0.6:
            timeline = min(timeline, 30)  # Offer quick close

        # In buyer's market, can be more flexible
        if market.market_velocity == 'cold':
            timeline = max(timeline, 45)  # Take time for due diligence

        return timeline

    def _recommend_escalation_clause(
        self,
        offer_amount: float,
        market: MarketContext,
        preferences: OfferPreferences
    ) -> Optional[float]:
        """Recommend escalation clause amount if applicable"""

        # Only use escalation in competitive situations
        if market.competing_offers_likelihood < 0.5:
            return None

        # Only if we have room to escalate
        max_escalation = market.listing_price * 1.05
        if offer_amount >= max_escalation:
            return None

        # Escalate up to listing price or slightly above
        if preferences.risk_tolerance == "aggressive":
            return max_escalation
        else:
            return market.listing_price

    def _select_best_overall(self, scenarios: List[OfferScenario]) -> OfferScenario:
        """Select scenario with highest overall score"""
        return max(scenarios, key=lambda s: s.overall_score)

    def _select_most_conservative(
        self,
        scenarios: List[OfferScenario],
        balanced: OfferScenario
    ) -> OfferScenario:
        """Select most conservative scenario (highest acceptance probability)"""
        # Filter to scenarios with acceptance >= balanced scenario
        conservative_candidates = [
            s for s in scenarios
            if s.acceptance_probability >= balanced.acceptance_probability
        ]

        if not conservative_candidates:
            conservative_candidates = scenarios

        # Pick highest acceptance probability
        return max(conservative_candidates, key=lambda s: s.acceptance_probability)

    def _select_most_aggressive(
        self,
        scenarios: List[OfferScenario],
        balanced: OfferScenario
    ) -> OfferScenario:
        """Select most aggressive scenario (highest value score)"""
        # Filter to scenarios with value >= balanced scenario
        aggressive_candidates = [
            s for s in scenarios
            if s.value_score >= balanced.value_score
        ]

        if not aggressive_candidates:
            aggressive_candidates = scenarios

        # Pick highest value score (best deal)
        return max(aggressive_candidates, key=lambda s: s.value_score)

    def _identify_key_factors(
        self,
        market: MarketContext,
        constraints: OfferConstraints,
        preferences: OfferPreferences
    ) -> List[str]:
        """Identify key factors influencing recommendation"""
        factors = []

        if market.days_on_market > 60:
            factors.append(f"Property has been on market {market.days_on_market} days")

        if market.price_reductions > 0:
            factors.append(f"Seller has reduced price {market.price_reductions} time(s)")

        if market.competing_offers_likelihood > 0.6:
            factors.append("High likelihood of competing offers")

        if market.seller_motivation_score > 0.7:
            factors.append("Strong seller motivation signals detected")

        price_vs_value = market.listing_price - market.market_value_estimate
        if abs(price_vs_value) > market.listing_price * 0.05:
            if price_vs_value > 0:
                factors.append(f"Listing appears overpriced by ${price_vs_value:,.0f}")
            else:
                factors.append(f"Listing appears underpriced by ${abs(price_vs_value):,.0f}")

        return factors

    def _generate_warnings(
        self,
        market: MarketContext,
        constraints: OfferConstraints,
        recommended: OfferScenario
    ) -> List[str]:
        """Generate warnings about recommended offer"""
        warnings = []

        if recommended.acceptance_probability < 0.3:
            warnings.append("Low acceptance probability - offer may be rejected")

        if recommended.offer_amount > constraints.max_offer * 0.95:
            warnings.append("Offer near budget ceiling - limited negotiation room")

        if market.competing_offers_likelihood > 0.7:
            warnings.append("Expect competition - consider escalation clause or stronger terms")

        if market.market_velocity == 'hot' and recommended.offer_amount < market.listing_price * 0.95:
            warnings.append("Hot market conditions may reduce effectiveness of low offers")

        return warnings

    def _build_scenario_rationale(
        self,
        amount: float,
        market: MarketContext,
        acceptance_prob: float,
        value_score: float,
        offer_type: str
    ) -> str:
        """Build explanation for scenario"""

        discount_pct = ((market.listing_price - amount) / market.listing_price) * 100

        if amount >= market.listing_price:
            price_desc = "at or above asking price"
        else:
            price_desc = f"{discount_pct:.1f}% below asking"

        acceptance_desc = "high" if acceptance_prob >= 0.7 else "moderate" if acceptance_prob >= 0.4 else "low"
        value_desc = "excellent" if value_score >= 0.7 else "good" if value_score >= 0.5 else "fair"

        return f"Offer {price_desc} with {acceptance_desc} acceptance probability and {value_desc} value positioning"
