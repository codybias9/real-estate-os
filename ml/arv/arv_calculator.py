"""
ARV (After Repair Value) Calculator.

Calculates expected property value after repairs/improvements for:
- Fix-and-flip analysis
- BRRRR (Buy, Rehab, Rent, Refinance, Repeat) strategy
- Value-add investments
- Renovation ROI analysis

Process:
1. Assess current property condition
2. Define renovation scope and costs
3. Calculate expected value increase from improvements
4. Validate ARV using comparable properties
5. Calculate renovation ROI metrics
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import date
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class PropertyCondition:
    """Current property condition assessment."""
    overall_condition: str  # Poor, Fair, Average, Good, Excellent
    condition_score: float  # 1-10 scale

    # Component conditions (1-10 scale)
    roof_condition: Optional[float] = None
    hvac_condition: Optional[float] = None
    plumbing_condition: Optional[float] = None
    electrical_condition: Optional[float] = None
    kitchen_condition: Optional[float] = None
    bathroom_condition: Optional[float] = None
    flooring_condition: Optional[float] = None
    paint_condition: Optional[float] = None
    foundation_condition: Optional[float] = None

    # Deferred maintenance estimate
    deferred_maintenance_cost: Optional[float] = None

    # Property details
    year_built: int = 1980
    last_renovation_year: Optional[int] = None


@dataclass
class RenovationItem:
    """Single renovation/improvement item."""
    category: str  # Kitchen, Bathroom, Roof, HVAC, etc.
    description: str
    cost: float
    value_add_factor: float  # Expected value increase factor (0.5 = 50% of cost, 1.2 = 120% of cost)
    duration_days: int = 30
    priority: str = "Medium"  # Low, Medium, High, Critical


@dataclass
class RenovationPlan:
    """Complete renovation plan."""
    items: List[RenovationItem]
    contingency_percent: float = 0.10  # 10% contingency buffer

    @property
    def total_cost(self) -> float:
        """Total renovation cost including contingency."""
        base_cost = sum(item.cost for item in self.items)
        return base_cost * (1 + self.contingency_percent)

    @property
    def total_duration_days(self) -> int:
        """Total project duration (assuming sequential work)."""
        # In reality, some work can be parallel, but we use sequential for conservative estimate
        return sum(item.duration_days for item in self.items)

    @property
    def expected_value_add(self) -> float:
        """Expected value increase from renovations."""
        return sum(item.cost * item.value_add_factor for item in self.items)


@dataclass
class ARVAnalysis:
    """ARV analysis results."""
    # Input values
    current_value: float  # As-is property value
    purchase_price: float  # Actual or intended purchase price

    # Renovation
    renovation_cost: float  # Total renovation budget
    expected_value_add: float  # Expected value increase

    # ARV calculation
    arv: float  # After Repair Value
    arv_method: str  # Method used (Cost-Based, Comp-Based, Hybrid)
    confidence_score: float  # 0-1 confidence in ARV estimate

    # ROI metrics
    total_investment: float  # Purchase + renovation
    gross_profit: float  # ARV - total investment
    roi_percent: float  # Profit / total investment
    renovation_roi_percent: float  # Value add / renovation cost

    # Holding costs (for fix-and-flip)
    holding_months: int = 6
    holding_costs: float = 0.0  # Interest, taxes, insurance, utilities

    # Exit costs
    selling_costs_percent: float = 0.08  # 6% commission + 2% closing
    selling_costs: float = 0.0

    # Net profit
    net_profit: float = 0.0
    net_roi_percent: float = 0.0

    # Comparable properties validation
    comp_arv_low: Optional[float] = None
    comp_arv_high: Optional[float] = None
    comp_arv_median: Optional[float] = None

    # Risk factors
    risk_level: str = "Medium"  # Low, Medium, High
    risk_factors: List[str] = None


# ============================================================================
# ARV Calculator
# ============================================================================

class ARVCalculator:
    """
    After Repair Value (ARV) Calculator.

    Calculates expected property value after renovations using multiple methods
    and validates results against comparable properties.
    """

    def __init__(self):
        # Value add factors by renovation category (typical ROI)
        # Based on industry averages from Remodeling Magazine Cost vs Value Report
        self.value_add_factors = {
            "Kitchen Remodel (Minor)": 0.72,      # 72% cost recovery
            "Kitchen Remodel (Major)": 0.59,      # 59% cost recovery
            "Bathroom Remodel (Minor)": 0.67,     # 67% cost recovery
            "Bathroom Remodel (Major)": 0.56,     # 56% cost recovery
            "Bathroom Addition": 0.52,             # 52% cost recovery
            "Master Suite Addition": 0.51,         # 51% cost recovery
            "Roof Replacement": 0.60,              # 60% cost recovery
            "Siding Replacement": 0.68,            # 68% cost recovery
            "Window Replacement": 0.68,            # 68% cost recovery
            "HVAC Replacement": 0.60,              # 60% cost recovery
            "Flooring": 0.70,                      # 70% cost recovery
            "Paint (Interior)": 1.00,              # 100% cost recovery (high ROI)
            "Paint (Exterior)": 0.75,              # 75% cost recovery
            "Deck Addition": 0.66,                 # 66% cost recovery
            "Landscaping": 0.80,                   # 80% cost recovery
            "Garage Door Replacement": 0.94,       # 94% cost recovery (very high ROI)
            "Entry Door Replacement": 0.75,        # 75% cost recovery
            "Foundation Repair": 0.50,             # 50% cost recovery
            "Plumbing": 0.65,                      # 65% cost recovery
            "Electrical": 0.65,                    # 65% cost recovery
            "Basement Finish": 0.70,               # 70% cost recovery
            "Attic Conversion": 0.65,              # 65% cost recovery
        }

    def calculate_arv(
        self,
        current_value: float,
        purchase_price: float,
        condition: PropertyCondition,
        renovation_plan: RenovationPlan,
        property_sqft: int,
        comp_properties: Optional[List[Dict[str, Any]]] = None
    ) -> ARVAnalysis:
        """
        Calculate After Repair Value (ARV) for a property.

        Args:
            current_value: Current as-is property value
            purchase_price: Actual or intended purchase price
            condition: Current property condition assessment
            renovation_plan: Planned renovations
            property_sqft: Property square footage
            comp_properties: Optional list of comparable properties for validation

        Returns:
            ARVAnalysis with complete ROI metrics
        """
        logger.info(f"Calculating ARV for ${current_value:,.0f} property with ${renovation_plan.total_cost:,.0f} renovation budget")

        # Calculate ARV using multiple methods
        arv_cost_based = self._calculate_arv_cost_based(current_value, renovation_plan)
        arv_comp_based = self._calculate_arv_comp_based(
            property_sqft, condition, renovation_plan, comp_properties
        ) if comp_properties else None

        # Use hybrid approach if comps available, otherwise use cost-based
        if arv_comp_based:
            # Weight cost-based 40%, comp-based 60%
            arv = arv_cost_based * 0.4 + arv_comp_based * 0.6
            method = "Hybrid (Cost + Comps)"
            confidence = 0.85
        else:
            arv = arv_cost_based
            method = "Cost-Based"
            confidence = 0.70

        # Calculate total investment
        total_investment = purchase_price + renovation_plan.total_cost

        # Calculate gross profit
        gross_profit = arv - total_investment

        # Calculate ROI
        roi_percent = (gross_profit / total_investment) * 100 if total_investment > 0 else 0

        # Calculate renovation ROI (value add vs renovation cost)
        renovation_roi = (renovation_plan.expected_value_add / renovation_plan.total_cost) * 100

        # Estimate holding costs (6 months typical for flip)
        holding_months = 6
        holding_costs = self._calculate_holding_costs(
            purchase_price,
            renovation_plan.total_cost,
            holding_months
        )

        # Calculate selling costs (6% commission + 2% closing costs)
        selling_costs_percent = 0.08
        selling_costs = arv * selling_costs_percent

        # Calculate net profit and ROI
        net_profit = gross_profit - holding_costs - selling_costs
        net_roi_percent = (net_profit / total_investment) * 100 if total_investment > 0 else 0

        # Get comp validation if available
        comp_arv_low = None
        comp_arv_high = None
        comp_arv_median = None
        if comp_properties:
            comp_values = [comp.get("value", 0) for comp in comp_properties if comp.get("value")]
            if comp_values:
                comp_arv_low = min(comp_values)
                comp_arv_high = max(comp_values)
                comp_arv_median = sorted(comp_values)[len(comp_values) // 2]

        # Assess risk
        risk_level, risk_factors = self._assess_risk(
            roi_percent,
            renovation_roi,
            condition,
            renovation_plan.total_duration_days,
            arv,
            comp_arv_low,
            comp_arv_high
        )

        analysis = ARVAnalysis(
            current_value=current_value,
            purchase_price=purchase_price,
            renovation_cost=renovation_plan.total_cost,
            expected_value_add=renovation_plan.expected_value_add,
            arv=arv,
            arv_method=method,
            confidence_score=confidence,
            total_investment=total_investment,
            gross_profit=gross_profit,
            roi_percent=roi_percent,
            renovation_roi_percent=renovation_roi,
            holding_months=holding_months,
            holding_costs=holding_costs,
            selling_costs_percent=selling_costs_percent,
            selling_costs=selling_costs,
            net_profit=net_profit,
            net_roi_percent=net_roi_percent,
            comp_arv_low=comp_arv_low,
            comp_arv_high=comp_arv_high,
            comp_arv_median=comp_arv_median,
            risk_level=risk_level,
            risk_factors=risk_factors
        )

        logger.info(f"ARV calculated: ${arv:,.0f} (method: {method})")
        logger.info(f"Net profit: ${net_profit:,.0f} ({net_roi_percent:.1f}% ROI)")

        return analysis

    def _calculate_arv_cost_based(
        self,
        current_value: float,
        renovation_plan: RenovationPlan
    ) -> float:
        """
        Calculate ARV using cost-based method.

        ARV = Current Value + Expected Value Add from Renovations
        """
        return current_value + renovation_plan.expected_value_add

    def _calculate_arv_comp_based(
        self,
        property_sqft: int,
        condition: PropertyCondition,
        renovation_plan: RenovationPlan,
        comp_properties: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate ARV using comparable properties.

        Finds comps in excellent condition and uses their price/sqft
        to estimate ARV.
        """
        if not comp_properties:
            return None

        # Filter for high-condition comps (similar to post-renovation condition)
        high_condition_comps = [
            comp for comp in comp_properties
            if comp.get("condition_score", 0) >= 8.0  # Excellent condition
        ]

        if not high_condition_comps:
            # Use all comps if no high-condition comps available
            high_condition_comps = comp_properties

        # Calculate average price per sqft from comps
        price_per_sqft_values = []
        for comp in high_condition_comps:
            comp_value = comp.get("value", 0)
            comp_sqft = comp.get("sqft", 0)
            if comp_value and comp_sqft:
                price_per_sqft_values.append(comp_value / comp_sqft)

        if not price_per_sqft_values:
            return None

        avg_price_per_sqft = sum(price_per_sqft_values) / len(price_per_sqft_values)

        # Calculate ARV
        arv = property_sqft * avg_price_per_sqft

        logger.info(f"Comp-based ARV: ${arv:,.0f} (${avg_price_per_sqft:.0f}/sqft from {len(high_condition_comps)} comps)")

        return arv

    def _calculate_holding_costs(
        self,
        purchase_price: float,
        renovation_cost: float,
        holding_months: int
    ) -> float:
        """
        Calculate holding costs during renovation and sale period.

        Includes:
        - Interest on purchase and renovation loans
        - Property taxes
        - Insurance
        - Utilities
        """
        # Loan interest (assume 8% hard money loan)
        interest_rate_annual = 0.08
        interest_monthly = (purchase_price + renovation_cost) * (interest_rate_annual / 12)
        total_interest = interest_monthly * holding_months

        # Property taxes (assume 1.2% annual)
        tax_rate_annual = 0.012
        tax_monthly = purchase_price * (tax_rate_annual / 12)
        total_taxes = tax_monthly * holding_months

        # Insurance (assume $1,500/year)
        insurance_monthly = 1500 / 12
        total_insurance = insurance_monthly * holding_months

        # Utilities (assume $300/month)
        utilities_monthly = 300
        total_utilities = utilities_monthly * holding_months

        total_holding_costs = total_interest + total_taxes + total_insurance + total_utilities

        logger.info(f"Holding costs for {holding_months} months: ${total_holding_costs:,.0f}")

        return total_holding_costs

    def _assess_risk(
        self,
        roi_percent: float,
        renovation_roi: float,
        condition: PropertyCondition,
        project_duration: int,
        arv: float,
        comp_arv_low: Optional[float],
        comp_arv_high: Optional[float]
    ) -> tuple[str, List[str]]:
        """
        Assess investment risk level and identify risk factors.

        Returns:
            (risk_level, list of risk factors)
        """
        risk_factors = []
        risk_score = 0  # Higher = more risk

        # ROI risk
        if roi_percent < 10:
            risk_factors.append("Low ROI (<10%)")
            risk_score += 2
        elif roi_percent < 20:
            risk_factors.append("Moderate ROI (10-20%)")
            risk_score += 1

        # Renovation ROI risk
        if renovation_roi < 50:
            risk_factors.append("Low renovation value recovery (<50%)")
            risk_score += 2
        elif renovation_roi < 70:
            risk_factors.append("Moderate renovation value recovery (50-70%)")
            risk_score += 1

        # Property condition risk
        if condition.overall_condition == "Poor":
            risk_factors.append("Poor property condition requires extensive work")
            risk_score += 2
        elif condition.overall_condition == "Fair":
            risk_factors.append("Fair property condition")
            risk_score += 1

        # Project timeline risk
        if project_duration > 180:  # > 6 months
            risk_factors.append(f"Long project timeline ({project_duration} days)")
            risk_score += 2
        elif project_duration > 120:  # > 4 months
            risk_factors.append(f"Extended project timeline ({project_duration} days)")
            risk_score += 1

        # Comp validation risk
        if comp_arv_low and comp_arv_high:
            if arv > comp_arv_high:
                risk_factors.append("ARV above comparable properties range")
                risk_score += 2
            elif arv < comp_arv_low:
                risk_factors.append("ARV below comparable properties range")
                risk_score += 1

        # Determine risk level
        if risk_score >= 6:
            risk_level = "High"
        elif risk_score >= 3:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        if not risk_factors:
            risk_factors.append("No significant risk factors identified")

        return risk_level, risk_factors

    def create_renovation_plan(
        self,
        items: List[Dict[str, Any]],
        contingency_percent: float = 0.10
    ) -> RenovationPlan:
        """
        Create a renovation plan from a list of items.

        Args:
            items: List of renovation items with keys: category, description, cost, etc.
            contingency_percent: Contingency buffer percentage

        Returns:
            RenovationPlan object
        """
        renovation_items = []
        for item in items:
            # Get value add factor from category or use provided
            category = item.get("category", "Other")
            value_add_factor = item.get(
                "value_add_factor",
                self.value_add_factors.get(category, 0.65)  # Default 65%
            )

            renovation_items.append(RenovationItem(
                category=category,
                description=item.get("description", ""),
                cost=item.get("cost", 0),
                value_add_factor=value_add_factor,
                duration_days=item.get("duration_days", 30),
                priority=item.get("priority", "Medium")
            ))

        return RenovationPlan(
            items=renovation_items,
            contingency_percent=contingency_percent
        )


# ============================================================================
# Convenience Functions
# ============================================================================

def calculate_fix_and_flip_roi(
    purchase_price: float,
    current_value: float,
    renovation_cost: float,
    expected_arv: float,
    holding_months: int = 6
) -> Dict[str, float]:
    """
    Quick fix-and-flip ROI calculator.

    Returns dictionary with key metrics.
    """
    calculator = ARVCalculator()

    # Create simple renovation plan
    renovation_plan = RenovationPlan(
        items=[RenovationItem(
            category="Total Renovation",
            description="Complete renovation",
            cost=renovation_cost / 1.1,  # Remove contingency since we add it back
            value_add_factor=(expected_arv - current_value) / renovation_cost
        )],
        contingency_percent=0.10
    )

    # Calculate holding costs
    holding_costs = calculator._calculate_holding_costs(
        purchase_price, renovation_cost, holding_months
    )

    # Calculate selling costs
    selling_costs = expected_arv * 0.08

    # Calculate metrics
    total_investment = purchase_price + renovation_cost
    gross_profit = expected_arv - total_investment
    net_profit = gross_profit - holding_costs - selling_costs
    roi_percent = (net_profit / total_investment) * 100

    return {
        "purchase_price": purchase_price,
        "renovation_cost": renovation_cost,
        "total_investment": total_investment,
        "arv": expected_arv,
        "holding_costs": holding_costs,
        "selling_costs": selling_costs,
        "gross_profit": gross_profit,
        "net_profit": net_profit,
        "roi_percent": roi_percent
    }
