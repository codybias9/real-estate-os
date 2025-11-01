"""
Negotiation Brain - Strategic Negotiation Recommendation Engine

Wave 3.2 Part 1: Intelligent negotiation strategy modeling

This module provides strategic negotiation recommendations by analyzing:
- Comparative market analysis (from Comp-Critic)
- Market conditions and trends
- Property-specific factors (DOM, condition, motivation signals)
- Buyer constraints and preferences

The Negotiation Brain outputs:
1. Recommended negotiation strategy (aggressive/moderate/cautious)
2. Optimal offer range with justification
3. Talking points and leverage indicators
4. Counter-offer response strategies
5. Deal structure suggestions (contingencies, timeline, etc.)
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from datetime import datetime, timedelta


class NegotiationStrategy(str, Enum):
    """Negotiation strategy types"""
    AGGRESSIVE = "aggressive"      # Push hard for discounts, use strong leverage
    MODERATE = "moderate"          # Balanced approach, fair value focus
    CAUTIOUS = "cautious"          # Conservative, minimize risk of rejection
    WALK_AWAY = "walk_away"        # Strong recommendation to pass on property


class MarketCondition(str, Enum):
    """Market condition classifications"""
    STRONG_BUYER = "strong_buyer_market"     # High leverage for buyers
    MODERATE_BUYER = "moderate_buyer_market" # Some buyer leverage
    BALANCED = "balanced_market"             # Neutral conditions
    MODERATE_SELLER = "moderate_seller_market" # Some seller leverage
    STRONG_SELLER = "strong_seller_market"   # High leverage for sellers


class MotivationSignal(str, Enum):
    """Seller motivation indicators"""
    HIGHLY_MOTIVATED = "highly_motivated"   # Multiple strong signals
    SOMEWHAT_MOTIVATED = "somewhat_motivated" # Some signals
    NEUTRAL = "neutral"                     # No clear signals
    NOT_MOTIVATED = "not_motivated"         # Seller has leverage


@dataclass
class PropertyContext:
    """Contextual information about the subject property"""
    property_id: str
    listing_price: float
    price_per_sqft: float
    days_on_market: int

    # Market analysis results (from Comp-Critic)
    market_position: str  # overvalued/fairly_valued/undervalued
    price_deviation_percent: float
    negotiation_leverage: float  # 0-1 score
    avg_comp_price: float
    num_comps: int

    # Property attributes
    property_type: str
    bedrooms: int
    bathrooms: float
    square_footage: int
    condition: Optional[str] = None  # excellent/good/fair/poor

    # Seller signals
    price_reductions: int = 0
    price_reduction_amount: float = 0.0
    listing_history_days: int = 0  # Total days on market including relists

    # Market conditions
    inventory_months: Optional[float] = None  # Months of inventory
    recent_sales_trend: Optional[str] = None  # increasing/stable/decreasing


@dataclass
class BuyerConstraints:
    """Buyer's constraints and preferences"""
    max_budget: float
    preferred_budget: float
    min_acceptable_price: Optional[float] = None
    must_close_by: Optional[datetime] = None

    # Financing
    financing_type: str = "conventional"  # conventional/fha/cash
    down_payment_percent: float = 20.0
    preapproval_amount: float = 0.0

    # Preferences
    contingencies_required: List[str] = None  # inspection, appraisal, financing, sale
    desired_closing_timeline_days: int = 45
    flexibility: str = "moderate"  # flexible/moderate/inflexible


@dataclass
class TalkingPoint:
    """Strategic talking point for negotiation"""
    category: str  # leverage_point/risk_factor/market_comparison/value_justification
    point: str
    evidence: str
    weight: float  # 0-1, importance of this point


@dataclass
class CounterOfferStrategy:
    """Strategy for responding to counter-offers"""
    initial_counter_max_increase: float  # Max amount to increase from initial offer
    walk_away_price: float
    concession_strategy: str  # gradual/meet_halfway/minimal
    alternative_concessions: List[str]  # Non-price items to negotiate


@dataclass
class DealStructure:
    """Recommended deal structure"""
    contingencies: List[str]
    inspection_period_days: int
    closing_timeline_days: int
    earnest_money_percent: float
    escalation_clause: bool
    appraisal_gap_coverage: Optional[float] = None
    seller_concessions_target: Optional[float] = None


@dataclass
class NegotiationRecommendation:
    """Complete negotiation recommendation output"""
    property_id: str

    # Strategy
    strategy: NegotiationStrategy
    strategy_confidence: float  # 0-1
    strategy_rationale: str

    # Offers
    recommended_initial_offer: float
    recommended_max_offer: float
    walk_away_price: float
    offer_justification: str

    # Market context
    market_condition: MarketCondition
    seller_motivation: MotivationSignal

    # Tactical guidance
    talking_points: List[TalkingPoint]
    counter_offer_strategy: CounterOfferStrategy
    deal_structure: DealStructure

    # Risks and opportunities
    key_risks: List[str]
    key_opportunities: List[str]

    # Timeline
    recommended_response_time: str  # e.g., "24 hours", "same day", "1 week"

    # Metadata
    created_at: datetime


class NegotiationBrain:
    """
    Strategic negotiation recommendation engine

    Analyzes market data, property context, and buyer constraints to provide
    actionable negotiation strategies and tactics.
    """

    def __init__(
        self,
        aggressive_leverage_threshold: float = 0.65,
        cautious_leverage_threshold: float = 0.35,
        high_dom_threshold_days: int = 60,
        overpriced_threshold_percent: float = 10.0
    ):
        """
        Initialize Negotiation Brain

        Args:
            aggressive_leverage_threshold: Min leverage score for aggressive strategy
            cautious_leverage_threshold: Max leverage score for cautious strategy
            high_dom_threshold_days: DOM threshold for "stale" listings
            overpriced_threshold_percent: Price deviation for "overpriced" classification
        """
        self.aggressive_leverage_threshold = aggressive_leverage_threshold
        self.cautious_leverage_threshold = cautious_leverage_threshold
        self.high_dom_threshold_days = high_dom_threshold_days
        self.overpriced_threshold_percent = overpriced_threshold_percent

    def recommend(
        self,
        property_context: PropertyContext,
        buyer_constraints: BuyerConstraints
    ) -> NegotiationRecommendation:
        """
        Generate comprehensive negotiation recommendation

        Args:
            property_context: Property and market data
            buyer_constraints: Buyer's constraints and preferences

        Returns:
            Complete negotiation recommendation
        """
        # Step 1: Assess market conditions
        market_condition = self._assess_market_condition(property_context)

        # Step 2: Detect seller motivation signals
        seller_motivation = self._detect_seller_motivation(property_context)

        # Step 3: Determine negotiation strategy
        strategy, confidence, rationale = self._determine_strategy(
            property_context, market_condition, seller_motivation, buyer_constraints
        )

        # Step 4: Calculate offer range
        initial_offer, max_offer, walk_away = self._calculate_offer_range(
            property_context, strategy, buyer_constraints
        )

        # Step 5: Generate talking points
        talking_points = self._generate_talking_points(
            property_context, market_condition, seller_motivation
        )

        # Step 6: Create counter-offer strategy
        counter_strategy = self._create_counter_strategy(
            initial_offer, max_offer, walk_away, strategy
        )

        # Step 7: Design deal structure
        deal_structure = self._design_deal_structure(
            property_context, buyer_constraints, strategy
        )

        # Step 8: Identify risks and opportunities
        risks = self._identify_risks(property_context, market_condition)
        opportunities = self._identify_opportunities(property_context, seller_motivation)

        # Step 9: Determine response timing
        response_time = self._recommend_response_time(strategy, market_condition)

        # Build offer justification
        offer_justification = self._build_offer_justification(
            property_context, initial_offer, talking_points
        )

        return NegotiationRecommendation(
            property_id=property_context.property_id,
            strategy=strategy,
            strategy_confidence=confidence,
            strategy_rationale=rationale,
            recommended_initial_offer=initial_offer,
            recommended_max_offer=max_offer,
            walk_away_price=walk_away,
            offer_justification=offer_justification,
            market_condition=market_condition,
            seller_motivation=seller_motivation,
            talking_points=talking_points,
            counter_offer_strategy=counter_strategy,
            deal_structure=deal_structure,
            key_risks=risks,
            key_opportunities=opportunities,
            recommended_response_time=response_time,
            created_at=datetime.utcnow()
        )

    def _assess_market_condition(self, ctx: PropertyContext) -> MarketCondition:
        """Assess overall market conditions"""
        # Use inventory months as primary signal if available
        if ctx.inventory_months is not None:
            if ctx.inventory_months >= 8:
                return MarketCondition.STRONG_BUYER
            elif ctx.inventory_months >= 6:
                return MarketCondition.MODERATE_BUYER
            elif ctx.inventory_months <= 3:
                return MarketCondition.STRONG_SELLER
            elif ctx.inventory_months <= 4:
                return MarketCondition.MODERATE_SELLER
            else:
                return MarketCondition.BALANCED

        # Fallback: use DOM and market position
        avg_dom_threshold = 45
        if ctx.days_on_market > avg_dom_threshold and ctx.market_position == 'overvalued':
            return MarketCondition.MODERATE_BUYER
        elif ctx.days_on_market < 15 and ctx.market_position != 'overvalued':
            return MarketCondition.MODERATE_SELLER
        else:
            return MarketCondition.BALANCED

    def _detect_seller_motivation(self, ctx: PropertyContext) -> MotivationSignal:
        """Detect seller motivation from signals"""
        motivation_score = 0.0

        # Price reductions (strong signal)
        if ctx.price_reductions >= 2:
            motivation_score += 0.3
        elif ctx.price_reductions == 1:
            motivation_score += 0.15

        # Days on market (moderate signal)
        if ctx.days_on_market > self.high_dom_threshold_days:
            motivation_score += 0.25
        elif ctx.days_on_market > 45:
            motivation_score += 0.15

        # Listing history (moderate signal)
        if ctx.listing_history_days > ctx.days_on_market * 1.5:
            motivation_score += 0.2  # Relisted property

        # Price deviation (weak signal)
        if ctx.price_deviation_percent > 15:
            motivation_score += 0.1

        # Classify motivation
        if motivation_score >= 0.6:
            return MotivationSignal.HIGHLY_MOTIVATED
        elif motivation_score >= 0.3:
            return MotivationSignal.SOMEWHAT_MOTIVATED
        elif motivation_score <= 0.1:
            return MotivationSignal.NOT_MOTIVATED
        else:
            return MotivationSignal.NEUTRAL

    def _determine_strategy(
        self,
        ctx: PropertyContext,
        market: MarketCondition,
        motivation: MotivationSignal,
        constraints: BuyerConstraints
    ) -> Tuple[NegotiationStrategy, float, str]:
        """Determine optimal negotiation strategy"""

        # Check for walk-away conditions
        if ctx.listing_price > constraints.max_budget * 1.15:
            return (
                NegotiationStrategy.WALK_AWAY,
                0.95,
                "Property is significantly beyond maximum budget, even with aggressive negotiation"
            )

        # Calculate strategy score (higher = more aggressive)
        strategy_score = 0.5  # Baseline

        # Factor 1: Negotiation leverage (40% weight)
        strategy_score += (ctx.negotiation_leverage - 0.5) * 0.8

        # Factor 2: Market condition (25% weight)
        market_adjustment = {
            MarketCondition.STRONG_BUYER: 0.25,
            MarketCondition.MODERATE_BUYER: 0.15,
            MarketCondition.BALANCED: 0.0,
            MarketCondition.MODERATE_SELLER: -0.15,
            MarketCondition.STRONG_SELLER: -0.25
        }
        strategy_score += market_adjustment.get(market, 0.0)

        # Factor 3: Seller motivation (25% weight)
        motivation_adjustment = {
            MotivationSignal.HIGHLY_MOTIVATED: 0.25,
            MotivationSignal.SOMEWHAT_MOTIVATED: 0.15,
            MotivationSignal.NEUTRAL: 0.0,
            MotivationSignal.NOT_MOTIVATED: -0.2
        }
        strategy_score += motivation_adjustment.get(motivation, 0.0)

        # Factor 4: Buyer flexibility (10% weight)
        if constraints.flexibility == "flexible":
            strategy_score += 0.1
        elif constraints.flexibility == "inflexible":
            strategy_score -= 0.1

        # Determine strategy from score
        if strategy_score >= 0.7:
            strategy = NegotiationStrategy.AGGRESSIVE
            confidence = min(0.95, strategy_score)
            rationale = "Strong buyer leverage with motivated seller signals"
        elif strategy_score >= 0.45:
            strategy = NegotiationStrategy.MODERATE
            confidence = 0.75
            rationale = "Balanced market conditions with moderate leverage"
        else:
            strategy = NegotiationStrategy.CAUTIOUS
            confidence = 0.65
            rationale = "Limited leverage or strong seller position"

        return strategy, confidence, rationale

    def _calculate_offer_range(
        self,
        ctx: PropertyContext,
        strategy: NegotiationStrategy,
        constraints: BuyerConstraints
    ) -> Tuple[float, float, float]:
        """Calculate initial offer, max offer, and walk-away price"""

        listing_price = ctx.listing_price

        # Determine discount ranges based on strategy
        if strategy == NegotiationStrategy.AGGRESSIVE:
            initial_discount = 0.12  # 12% below asking
            max_discount = 0.05      # 5% below asking
        elif strategy == NegotiationStrategy.MODERATE:
            initial_discount = 0.07  # 7% below asking
            max_discount = 0.02      # 2% below asking
        else:  # CAUTIOUS
            initial_discount = 0.03  # 3% below asking
            max_discount = 0.01      # 1% below asking

        # Adjust for market position
        if ctx.market_position == 'overvalued':
            initial_discount += 0.05
            max_discount += 0.03
        elif ctx.market_position == 'undervalued':
            initial_discount -= 0.03
            max_discount -= 0.02

        # Calculate offers
        initial_offer = listing_price * (1 - initial_discount)
        max_offer = listing_price * (1 - max_discount)

        # Apply buyer budget constraints
        initial_offer = min(initial_offer, constraints.preferred_budget)
        max_offer = min(max_offer, constraints.max_budget)

        # Walk-away price (absolute ceiling)
        walk_away = min(constraints.max_budget, listing_price * 1.02)

        # Ensure logical ordering
        if initial_offer > max_offer:
            initial_offer = max_offer * 0.95
        if max_offer > walk_away:
            max_offer = walk_away * 0.98

        return (
            round(initial_offer, 2),
            round(max_offer, 2),
            round(walk_away, 2)
        )

    def _generate_talking_points(
        self,
        ctx: PropertyContext,
        market: MarketCondition,
        motivation: MotivationSignal
    ) -> List[TalkingPoint]:
        """Generate strategic talking points for negotiation"""
        points = []

        # Leverage point: Days on market
        if ctx.days_on_market > self.high_dom_threshold_days:
            points.append(TalkingPoint(
                category="leverage_point",
                point=f"Property has been on market for {ctx.days_on_market} days",
                evidence=f"Significantly above market average, indicating pricing concerns",
                weight=0.8
            ))

        # Leverage point: Price vs comps
        if ctx.price_deviation_percent > self.overpriced_threshold_percent:
            points.append(TalkingPoint(
                category="leverage_point",
                point=f"Listing price is {ctx.price_deviation_percent:.1f}% above comparable properties",
                evidence=f"Analysis of {ctx.num_comps} similar properties shows market value at ${ctx.avg_comp_price:,.0f}",
                weight=0.9
            ))

        # Market comparison
        if market in [MarketCondition.STRONG_BUYER, MarketCondition.MODERATE_BUYER]:
            points.append(TalkingPoint(
                category="market_comparison",
                point="Current market favors buyers",
                evidence="Inventory levels and sales trends indicate buyer leverage",
                weight=0.6
            ))

        # Value justification
        points.append(TalkingPoint(
            category="value_justification",
            point=f"Offer reflects fair market value at ${ctx.price_per_sqft:.0f}/sqft",
            evidence=f"Comparable properties average ${ctx.avg_comp_price / ctx.square_footage:.0f}/sqft",
            weight=0.7
        ))

        # Risk factor (if applicable)
        if ctx.condition == "fair" or ctx.condition == "poor":
            points.append(TalkingPoint(
                category="risk_factor",
                point=f"Property condition ({ctx.condition}) requires renovation budget",
                evidence="Inspection and repair costs should be factored into valuation",
                weight=0.75
            ))

        # Sort by weight
        points.sort(key=lambda p: p.weight, reverse=True)
        return points

    def _create_counter_strategy(
        self,
        initial_offer: float,
        max_offer: float,
        walk_away: float,
        strategy: NegotiationStrategy
    ) -> CounterOfferStrategy:
        """Create counter-offer response strategy"""

        negotiation_range = max_offer - initial_offer

        if strategy == NegotiationStrategy.AGGRESSIVE:
            return CounterOfferStrategy(
                initial_counter_max_increase=negotiation_range * 0.3,
                walk_away_price=walk_away,
                concession_strategy="minimal",
                alternative_concessions=[
                    "Request seller to cover closing costs",
                    "Request home warranty",
                    "Request repairs from inspection"
                ]
            )
        elif strategy == NegotiationStrategy.MODERATE:
            return CounterOfferStrategy(
                initial_counter_max_increase=negotiation_range * 0.5,
                walk_away_price=walk_away,
                concession_strategy="gradual",
                alternative_concessions=[
                    "Request seller concessions for closing costs",
                    "Negotiate repair credits from inspection",
                    "Flexible closing timeline"
                ]
            )
        else:  # CAUTIOUS
            return CounterOfferStrategy(
                initial_counter_max_increase=negotiation_range * 0.7,
                walk_away_price=walk_away,
                concession_strategy="meet_halfway",
                alternative_concessions=[
                    "Flexible closing date",
                    "Waive minor inspection items",
                    "Quick response times"
                ]
            )

    def _design_deal_structure(
        self,
        ctx: PropertyContext,
        constraints: BuyerConstraints,
        strategy: NegotiationStrategy
    ) -> DealStructure:
        """Design recommended deal structure"""

        # Base contingencies
        contingencies = constraints.contingencies_required or ["inspection", "financing"]

        # Appraisal contingency
        if constraints.financing_type != "cash":
            contingencies.append("appraisal")

        # Escalation clause (for competitive markets)
        use_escalation = strategy == NegotiationStrategy.CAUTIOUS

        # Earnest money (stronger in cautious strategy)
        earnest_money_pct = 2.0 if strategy == NegotiationStrategy.CAUTIOUS else 1.0

        # Inspection period
        inspection_days = 10 if strategy == NegotiationStrategy.AGGRESSIVE else 7

        # Closing timeline
        closing_days = constraints.desired_closing_timeline_days

        # Appraisal gap coverage (for competitive markets)
        appraisal_gap = None
        if use_escalation:
            appraisal_gap = 5000  # Cover up to $5k gap

        return DealStructure(
            contingencies=contingencies,
            inspection_period_days=inspection_days,
            closing_timeline_days=closing_days,
            earnest_money_percent=earnest_money_pct,
            escalation_clause=use_escalation,
            appraisal_gap_coverage=appraisal_gap,
            seller_concessions_target=3000 if strategy == NegotiationStrategy.AGGRESSIVE else None
        )

    def _identify_risks(
        self,
        ctx: PropertyContext,
        market: MarketCondition
    ) -> List[str]:
        """Identify key negotiation risks"""
        risks = []

        if ctx.market_position == 'undervalued':
            risks.append("Property may have competing offers due to below-market pricing")

        if market in [MarketCondition.MODERATE_SELLER, MarketCondition.STRONG_SELLER]:
            risks.append("Seller's market reduces negotiation leverage")

        if ctx.days_on_market < 7:
            risks.append("Fresh listing may limit seller's willingness to negotiate")

        if ctx.num_comps < 5:
            risks.append("Limited comparable properties weaken negotiation evidence")

        return risks

    def _identify_opportunities(
        self,
        ctx: PropertyContext,
        motivation: MotivationSignal
    ) -> List[str]:
        """Identify key negotiation opportunities"""
        opportunities = []

        if motivation in [MotivationSignal.HIGHLY_MOTIVATED, MotivationSignal.SOMEWHAT_MOTIVATED]:
            opportunities.append("Seller motivation signals suggest room for negotiation")

        if ctx.price_reductions > 0:
            opportunities.append(f"Property has {ctx.price_reductions} price reduction(s), indicating flexibility")

        if ctx.days_on_market > self.high_dom_threshold_days:
            opportunities.append("Extended days on market increase seller urgency")

        if ctx.market_position == 'overvalued':
            opportunities.append("Overpriced listing provides strong negotiation leverage")

        return opportunities

    def _recommend_response_time(
        self,
        strategy: NegotiationStrategy,
        market: MarketCondition
    ) -> str:
        """Recommend how quickly to respond to listing/counter"""

        if market == MarketCondition.STRONG_SELLER:
            return "Same day or within 12 hours"
        elif strategy == NegotiationStrategy.AGGRESSIVE:
            return "24-48 hours (don't appear too eager)"
        elif strategy == NegotiationStrategy.CAUTIOUS:
            return "Same day or next business day"
        else:
            return "Within 24 hours"

    def _build_offer_justification(
        self,
        ctx: PropertyContext,
        initial_offer: float,
        talking_points: List[TalkingPoint]
    ) -> str:
        """Build written justification for offer amount"""

        discount_pct = ((ctx.listing_price - initial_offer) / ctx.listing_price) * 100

        justification = f"Our offer of ${initial_offer:,.0f} ({discount_pct:.1f}% below asking) is based on:\n\n"

        # Add top 3 talking points
        for i, point in enumerate(talking_points[:3], 1):
            justification += f"{i}. {point.point}\n   {point.evidence}\n\n"

        justification += f"This reflects fair market value at ${initial_offer / ctx.square_footage:.0f}/sqft."

        return justification
