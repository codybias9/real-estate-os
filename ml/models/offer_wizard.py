"""
Offer Wizard - Constraint Satisfaction & Deal Optimization

Wave 4.1: Multi-criteria optimization for optimal deal structures

Features:
- Constraint satisfaction (hard requirements)
- Multi-objective optimization (price, acceptance, timeline, risk)
- Deal structure generation (contingencies, earnest money, etc.)
- Scenario comparison with trade-off analysis
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ObjectiveType(str, Enum):
    """Optimization objectives"""
    MINIMIZE_PRICE = "minimize_price"  # Get lowest price
    MAXIMIZE_ACCEPTANCE = "maximize_acceptance"  # Highest acceptance probability
    MINIMIZE_RISK = "minimize_risk"  # Lowest deal risk
    MINIMIZE_TIME = "minimize_time"  # Fastest closing
    MAXIMIZE_FLEXIBILITY = "maximize_flexibility"  # Most contingencies


class DealRisk(str, Enum):
    """Deal risk levels"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class HardConstraints:
    """Hard constraints that MUST be satisfied"""
    max_price: float  # Absolute ceiling
    max_closing_days: int  # Must close by this date
    min_inspection_days: int = 7  # Minimum inspection period
    required_contingencies: List[str] = None  # Must-have contingencies
    financing_contingency_required: bool = True
    max_earnest_money: Optional[float] = None  # Cap on earnest deposit


@dataclass
class SoftPreferences:
    """Soft preferences to optimize for"""
    target_price: float
    target_closing_days: int = 30
    preferred_contingencies: List[str] = None
    risk_tolerance: str = "moderate"  # low/moderate/high
    objectives: List[ObjectiveType] = None  # Ordered by priority


@dataclass
class MarketInputs:
    """Market and property context"""
    listing_price: float
    estimated_market_value: float
    days_on_market: int
    competing_offers_likelihood: float  # 0-1
    seller_motivation: float  # 0-1
    market_velocity: str  # hot/warm/cool/cold
    property_condition: str  # excellent/good/fair/poor


@dataclass
class DealStructure:
    """Complete deal structure"""
    # Price
    offer_price: float
    earnest_money: float
    earnest_money_percent: float

    # Timeline
    closing_days: int
    inspection_period_days: int
    financing_contingency_days: int
    appraisal_contingency_days: int

    # Contingencies
    contingencies: List[str]
    inspection_contingency: bool
    financing_contingency: bool
    appraisal_contingency: bool
    sale_of_home_contingency: bool

    # Additional terms
    escalation_clause: bool
    escalation_max: Optional[float] = None
    appraisal_gap_coverage: Optional[float] = None
    seller_concessions: Optional[float] = None

    # Metadata
    deal_risk: DealRisk = DealRisk.MODERATE
    acceptance_probability: float = 0.5
    competitive_score: float = 0.5  # How competitive vs other offers


@dataclass
class OfferScenario:
    """Complete offer scenario with scoring"""
    name: str
    deal: DealStructure

    # Objectives (0-1, higher is better)
    price_score: float  # Lower price = higher score
    acceptance_score: float  # Higher acceptance probability
    risk_score: float  # Lower risk = higher score
    time_score: float  # Faster closing = higher score
    flexibility_score: float  # More contingencies = higher score

    # Overall
    overall_score: float
    rank: int = 0

    # Explanation
    strengths: List[str] = None
    weaknesses: List[str] = None
    tradeoffs: str = ""


@dataclass
class OfferWizardResult:
    """Wizard output with multiple scenarios"""
    recommended: OfferScenario
    scenarios: List[OfferScenario]  # All scenarios ranked
    infeasible_reasons: List[str]  # Why some scenarios weren't possible
    market_summary: str
    created_at: datetime = None


class ConstraintSolver:
    """Check if deal structure satisfies hard constraints"""

    @staticmethod
    def check(deal: DealStructure, constraints: HardConstraints) -> Tuple[bool, List[str]]:
        """
        Check if deal satisfies constraints

        Returns: (is_feasible, violations)
        """
        violations = []

        # Price constraint
        if deal.offer_price > constraints.max_price:
            violations.append(f"Offer price ${deal.offer_price:,.0f} exceeds max ${constraints.max_price:,.0f}")

        # Closing timeline
        if deal.closing_days > constraints.max_closing_days:
            violations.append(f"Closing {deal.closing_days} days exceeds max {constraints.max_closing_days} days")

        # Inspection period
        if deal.inspection_contingency and deal.inspection_period_days < constraints.min_inspection_days:
            violations.append(f"Inspection period {deal.inspection_period_days} days below minimum {constraints.min_inspection_days} days")

        # Required contingencies
        if constraints.required_contingencies:
            for req in constraints.required_contingencies:
                if req not in deal.contingencies:
                    violations.append(f"Required contingency '{req}' missing")

        # Financing contingency
        if constraints.financing_contingency_required and not deal.financing_contingency:
            violations.append("Financing contingency required but not included")

        # Earnest money cap
        if constraints.max_earnest_money and deal.earnest_money > constraints.max_earnest_money:
            violations.append(f"Earnest money ${deal.earnest_money:,.0f} exceeds max ${constraints.max_earnest_money:,.0f}")

        return (len(violations) == 0, violations)


class DealOptimizer:
    """Generate and score deal scenarios"""

    def __init__(self):
        pass

    def generate_scenarios(
        self,
        constraints: HardConstraints,
        preferences: SoftPreferences,
        market: MarketInputs
    ) -> List[DealStructure]:
        """Generate candidate deal structures"""

        scenarios = []

        # Scenario 1: Maximum Competitiveness
        # - Strong price, few contingencies, quick close
        scenarios.append(self._generate_competitive_deal(
            constraints, preferences, market
        ))

        # Scenario 2: Balanced
        # - Fair price, standard contingencies, reasonable timeline
        scenarios.append(self._generate_balanced_deal(
            constraints, preferences, market
        ))

        # Scenario 3: Maximum Protection
        # - More contingencies, longer timelines, lower risk
        scenarios.append(self._generate_protected_deal(
            constraints, preferences, market
        ))

        # Scenario 4: Budget-Focused
        # - Lowest possible price, accept higher risk
        scenarios.append(self._generate_budget_deal(
            constraints, preferences, market
        ))

        # Scenario 5: Speed-Focused
        # - Fast closing, streamlined contingencies
        scenarios.append(self._generate_speed_deal(
            constraints, preferences, market
        ))

        return scenarios

    def _generate_competitive_deal(
        self,
        constraints: HardConstraints,
        preferences: SoftPreferences,
        market: MarketInputs
    ) -> DealStructure:
        """Generate highly competitive offer"""

        # Aggressive price (95-100% of listing)
        offer_price = min(market.listing_price * 0.98, constraints.max_price)

        # Minimal contingencies
        contingencies = ["inspection"]  # Keep only inspection
        if constraints.financing_contingency_required:
            contingencies.append("financing")

        return DealStructure(
            offer_price=offer_price,
            earnest_money=offer_price * 0.03,  # 3% earnest
            earnest_money_percent=3.0,
            closing_days=21,  # Fast close
            inspection_period_days=constraints.min_inspection_days,
            financing_contingency_days=17 if constraints.financing_contingency_required else 0,
            appraisal_contingency_days=0,  # Waive appraisal
            contingencies=contingencies,
            inspection_contingency=True,
            financing_contingency=constraints.financing_contingency_required,
            appraisal_contingency=False,  # Waived for competitiveness
            sale_of_home_contingency=False,
            escalation_clause=True,
            escalation_max=min(market.listing_price * 1.02, constraints.max_price),
            appraisal_gap_coverage=10000,  # Cover gap
            seller_concessions=None,
            deal_risk=DealRisk.MODERATE,
            acceptance_probability=0.85,
            competitive_score=0.9
        )

    def _generate_balanced_deal(
        self,
        constraints: HardConstraints,
        preferences: SoftPreferences,
        market: MarketInputs
    ) -> DealStructure:
        """Generate balanced offer"""

        # Fair price (92-96% of listing)
        offer_price = min(market.listing_price * 0.95, preferences.target_price)

        # Standard contingencies
        contingencies = ["inspection", "financing", "appraisal"]

        return DealStructure(
            offer_price=offer_price,
            earnest_money=offer_price * 0.02,
            earnest_money_percent=2.0,
            closing_days=min(30, preferences.target_closing_days),
            inspection_period_days=10,
            financing_contingency_days=21,
            appraisal_contingency_days=21,
            contingencies=contingencies,
            inspection_contingency=True,
            financing_contingency=True,
            appraisal_contingency=True,
            sale_of_home_contingency=False,
            escalation_clause=False,
            escalation_max=None,
            appraisal_gap_coverage=5000,
            seller_concessions=None,
            deal_risk=DealRisk.LOW,
            acceptance_probability=0.65,
            competitive_score=0.6
        )

    def _generate_protected_deal(
        self,
        constraints: HardConstraints,
        preferences: SoftPreferences,
        market: MarketInputs
    ) -> DealStructure:
        """Generate maximum protection offer"""

        # Conservative price (88-93% of listing)
        offer_price = min(market.listing_price * 0.92, preferences.target_price * 0.98)

        # All contingencies
        contingencies = ["inspection", "financing", "appraisal"]

        return DealStructure(
            offer_price=offer_price,
            earnest_money=offer_price * 0.01,  # Lower earnest
            earnest_money_percent=1.0,
            closing_days=min(45, constraints.max_closing_days),
            inspection_period_days=14,  # Extended inspection
            financing_contingency_days=30,
            appraisal_contingency_days=30,
            contingencies=contingencies,
            inspection_contingency=True,
            financing_contingency=True,
            appraisal_contingency=True,
            sale_of_home_contingency=False,
            escalation_clause=False,
            escalation_max=None,
            appraisal_gap_coverage=None,  # No gap coverage
            seller_concessions=3000,  # Request concessions
            deal_risk=DealRisk.LOW,
            acceptance_probability=0.45,
            competitive_score=0.3
        )

    def _generate_budget_deal(
        self,
        constraints: HardConstraints,
        preferences: SoftPreferences,
        market: MarketInputs
    ) -> DealStructure:
        """Generate budget-focused offer"""

        # Low price (85-90% of listing)
        target_discount = 0.10 if market.days_on_market > 60 else 0.08
        offer_price = market.listing_price * (1 - target_discount)

        contingencies = ["inspection", "financing"]

        return DealStructure(
            offer_price=offer_price,
            earnest_money=offer_price * 0.015,
            earnest_money_percent=1.5,
            closing_days=40,
            inspection_period_days=12,
            financing_contingency_days=25,
            appraisal_contingency_days=0,
            contingencies=contingencies,
            inspection_contingency=True,
            financing_contingency=True,
            appraisal_contingency=False,
            sale_of_home_contingency=False,
            escalation_clause=False,
            escalation_max=None,
            appraisal_gap_coverage=None,
            seller_concessions=5000,  # Request max concessions
            deal_risk=DealRisk.MODERATE,
            acceptance_probability=0.35,
            competitive_score=0.25
        )

    def _generate_speed_deal(
        self,
        constraints: HardConstraints,
        preferences: SoftPreferences,
        market: MarketInputs
    ) -> DealStructure:
        """Generate speed-focused offer"""

        # Near asking price for speed
        offer_price = min(market.listing_price * 0.99, constraints.max_price)

        contingencies = ["inspection"]
        if constraints.financing_contingency_required:
            contingencies.append("financing")

        return DealStructure(
            offer_price=offer_price,
            earnest_money=offer_price * 0.02,
            earnest_money_percent=2.0,
            closing_days=14,  # Very fast
            inspection_period_days=constraints.min_inspection_days,
            financing_contingency_days=10 if constraints.financing_contingency_required else 0,
            appraisal_contingency_days=0,
            contingencies=contingencies,
            inspection_contingency=True,
            financing_contingency=constraints.financing_contingency_required,
            appraisal_contingency=False,
            sale_of_home_contingency=False,
            escalation_clause=False,
            escalation_max=None,
            appraisal_gap_coverage=8000,
            seller_concessions=None,
            deal_risk=DealRisk.MODERATE,
            acceptance_probability=0.80,
            competitive_score=0.85
        )

    def score_deal(
        self,
        deal: DealStructure,
        preferences: SoftPreferences,
        market: MarketInputs
    ) -> Dict[str, float]:
        """Score deal on multiple objectives"""

        # Price score (lower price = higher score)
        price_diff = market.listing_price - deal.offer_price
        max_discount = market.listing_price * 0.15
        price_score = min(1.0, price_diff / max_discount) if max_discount > 0 else 0.5

        # Acceptance score (use deal's estimated probability)
        acceptance_score = deal.acceptance_probability

        # Risk score (lower risk = higher score)
        risk_map = {
            DealRisk.LOW: 1.0,
            DealRisk.MODERATE: 0.7,
            DealRisk.HIGH: 0.4,
            DealRisk.VERY_HIGH: 0.2
        }
        risk_score = risk_map.get(deal.deal_risk, 0.5)

        # Time score (faster = higher score)
        max_time = 60
        time_score = 1.0 - (deal.closing_days / max_time)

        # Flexibility score (more contingencies = higher score)
        max_contingencies = 5
        flexibility_score = len(deal.contingencies) / max_contingencies

        return {
            'price': price_score,
            'acceptance': acceptance_score,
            'risk': risk_score,
            'time': time_score,
            'flexibility': flexibility_score
        }


class OfferWizard:
    """Main Offer Wizard orchestrator"""

    def __init__(self):
        self.solver = ConstraintSolver()
        self.optimizer = DealOptimizer()

    def create_offer_scenarios(
        self,
        constraints: HardConstraints,
        preferences: SoftPreferences,
        market: MarketInputs
    ) -> OfferWizardResult:
        """
        Generate optimal offer scenarios

        Returns ranked scenarios optimized for buyer's objectives
        """

        # Generate candidate deals
        candidate_deals = self.optimizer.generate_scenarios(
            constraints, preferences, market
        )

        # Filter by constraints
        feasible_deals = []
        infeasible = []

        for deal in candidate_deals:
            is_feasible, violations = self.solver.check(deal, constraints)
            if is_feasible:
                feasible_deals.append(deal)
            else:
                infeasible.extend(violations)

        if not feasible_deals:
            logger.warning("No feasible deal structures found")
            # Return empty result
            return OfferWizardResult(
                recommended=None,
                scenarios=[],
                infeasible_reasons=infeasible,
                market_summary=self._summarize_market(market),
                created_at=datetime.utcnow()
            )

        # Score and rank scenarios
        scenarios = []
        for i, deal in enumerate(feasible_deals):
            scores = self.optimizer.score_deal(deal, preferences, market)

            # Calculate overall score based on objectives priority
            overall = self._calculate_overall_score(scores, preferences.objectives)

            # Generate scenario
            scenario = OfferScenario(
                name=self._name_scenario(i, deal),
                deal=deal,
                price_score=scores['price'],
                acceptance_score=scores['acceptance'],
                risk_score=scores['risk'],
                time_score=scores['time'],
                flexibility_score=scores['flexibility'],
                overall_score=overall,
                strengths=self._identify_strengths(deal, scores),
                weaknesses=self._identify_weaknesses(deal, scores),
                tradeoffs=self._describe_tradeoffs(deal, scores)
            )
            scenarios.append(scenario)

        # Rank by overall score
        scenarios.sort(key=lambda s: s.overall_score, reverse=True)
        for i, scenario in enumerate(scenarios, 1):
            scenario.rank = i

        # Select recommended (top-ranked)
        recommended = scenarios[0]

        return OfferWizardResult(
            recommended=recommended,
            scenarios=scenarios,
            infeasible_reasons=list(set(infeasible)),
            market_summary=self._summarize_market(market),
            created_at=datetime.utcnow()
        )

    def _calculate_overall_score(
        self,
        scores: Dict[str, float],
        objectives: Optional[List[ObjectiveType]]
    ) -> float:
        """Calculate weighted overall score"""

        if not objectives:
            # Default equal weighting
            return sum(scores.values()) / len(scores)

        # Weight by priority order
        weights = {
            0: 0.4,  # Highest priority
            1: 0.3,
            2: 0.2,
            3: 0.1,
        }

        total = 0.0
        total_weight = 0.0

        for i, obj in enumerate(objectives[:4]):  # Top 4 objectives
            weight = weights.get(i, 0.05)
            if obj == ObjectiveType.MINIMIZE_PRICE:
                total += scores['price'] * weight
            elif obj == ObjectiveType.MAXIMIZE_ACCEPTANCE:
                total += scores['acceptance'] * weight
            elif obj == ObjectiveType.MINIMIZE_RISK:
                total += scores['risk'] * weight
            elif obj == ObjectiveType.MINIMIZE_TIME:
                total += scores['time'] * weight
            elif obj == ObjectiveType.MAXIMIZE_FLEXIBILITY:
                total += scores['flexibility'] * weight
            total_weight += weight

        return total / total_weight if total_weight > 0 else 0.5

    def _name_scenario(self, index: int, deal: DealStructure) -> str:
        """Generate scenario name"""
        names = [
            "Maximum Competitiveness",
            "Balanced Approach",
            "Maximum Protection",
            "Budget-Focused",
            "Speed-Focused"
        ]
        return names[index] if index < len(names) else f"Scenario {index + 1}"

    def _identify_strengths(self, deal: DealStructure, scores: Dict[str, float]) -> List[str]:
        """Identify deal strengths"""
        strengths = []

        if scores['acceptance'] >= 0.7:
            strengths.append(f"High acceptance probability ({deal.acceptance_probability:.0%})")

        if scores['price'] >= 0.7:
            strengths.append(f"Strong value at ${deal.offer_price:,.0f}")

        if scores['risk'] >= 0.8:
            strengths.append("Low risk with protective contingencies")

        if scores['time'] >= 0.7:
            strengths.append(f"Fast closing ({deal.closing_days} days)")

        if deal.competitive_score >= 0.8:
            strengths.append("Highly competitive against other offers")

        return strengths

    def _identify_weaknesses(self, deal: DealStructure, scores: Dict[str, float]) -> List[str]:
        """Identify deal weaknesses"""
        weaknesses = []

        if scores['acceptance'] < 0.5:
            weaknesses.append(f"Lower acceptance probability ({deal.acceptance_probability:.0%})")

        if scores['risk'] < 0.6:
            weaknesses.append(f"{deal.deal_risk.value.replace('_', ' ').title()} risk level")

        if not deal.appraisal_contingency:
            weaknesses.append("No appraisal contingency (buyer assumes risk)")

        if deal.closing_days < 21:
            weaknesses.append("Very tight closing timeline")

        return weaknesses

    def _describe_tradeoffs(self, deal: DealStructure, scores: Dict[str, float]) -> str:
        """Describe key tradeoffs"""
        if scores['acceptance'] > 0.7 and scores['risk'] < 0.6:
            return "Maximizes acceptance probability at cost of buyer protection"
        elif scores['risk'] > 0.8 and scores['acceptance'] < 0.6:
            return "Prioritizes buyer protection over competitiveness"
        elif scores['price'] > 0.7 and scores['acceptance'] < 0.6:
            return "Focuses on price savings with lower acceptance chance"
        elif scores['time'] > 0.7:
            return "Optimizes for speed with streamlined contingencies"
        else:
            return "Balanced trade-offs across objectives"

    def _summarize_market(self, market: MarketInputs) -> str:
        """Summarize market conditions"""
        return (
            f"{market.market_velocity.title()} market with "
            f"{market.competing_offers_likelihood:.0%} likelihood of competing offers. "
            f"Property listed at ${market.listing_price:,.0f}, "
            f"{market.days_on_market} days on market."
        )
