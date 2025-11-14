"""Portfolio router for deal scenarios, investor readiness, and portfolio analytics."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import random

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


# ============================================================================
# Enums
# ============================================================================

class ScenarioType(str, Enum):
    """Type of financial scenario."""
    base_case = "base_case"
    best_case = "best_case"
    worst_case = "worst_case"
    custom = "custom"


class InvestorReadinessLevel(str, Enum):
    """Investor readiness badge level."""
    excellent = "excellent"  # 90-100%
    good = "good"           # 70-89%
    fair = "fair"           # 50-69%
    poor = "poor"           # Below 50%


class HoldPeriod(str, Enum):
    """Hold period for investment analysis."""
    short_term = "short_term"      # < 1 year
    medium_term = "medium_term"    # 1-5 years
    long_term = "long_term"        # 5+ years


# ============================================================================
# Schemas
# ============================================================================

class FinancialMetrics(BaseModel):
    """Financial metrics for a deal scenario."""
    purchase_price: float
    closing_costs: float
    renovation_budget: float
    total_investment: float
    annual_rental_income: float
    annual_operating_expenses: float
    annual_debt_service: float
    net_operating_income: float
    cash_flow_year_1: float
    cap_rate: float
    cash_on_cash_return: float
    irr: float  # Internal Rate of Return
    equity_multiple: float
    break_even_occupancy: float


class DealScenario(BaseModel):
    """Financial scenario for a deal."""
    id: str
    deal_id: str
    scenario_type: ScenarioType
    name: str
    description: Optional[str]
    assumptions: Dict[str, Any] = Field(description="Scenario assumptions (rent growth, appreciation, etc.)")
    metrics: FinancialMetrics
    probability: Optional[float] = Field(None, description="Probability of this scenario (0-1)")
    created_at: str
    created_by: str


class ScenarioCreate(BaseModel):
    """Request to create a custom scenario."""
    deal_id: str
    name: str
    description: Optional[str] = None
    assumptions: Dict[str, Any]


class ReadinessCriteria(BaseModel):
    """Individual readiness criterion."""
    name: str
    score: float = Field(..., ge=0, le=100, description="Score 0-100")
    weight: float = Field(..., ge=0, le=1, description="Weight in overall score")
    status: str = Field(description="complete, incomplete, or missing")
    details: Optional[str] = None


class InvestorReadiness(BaseModel):
    """Investor readiness assessment for a property."""
    property_id: str
    overall_score: float = Field(..., ge=0, le=100)
    level: InvestorReadinessLevel
    criteria: List[ReadinessCriteria]
    recommendations: List[str] = Field(description="Actions to improve readiness")
    strengths: List[str] = Field(description="What's strong about this deal")
    weaknesses: List[str] = Field(description="What needs improvement")
    last_updated: str


class PortfolioSummary(BaseModel):
    """Summary of entire portfolio."""
    total_properties: int
    total_value: float
    total_equity: float
    total_debt: float
    average_cap_rate: float
    average_cash_on_cash: float
    total_annual_income: float
    total_annual_expenses: float
    portfolio_irr: float
    properties_by_type: Dict[str, int]
    properties_by_stage: Dict[str, int]


class PerformanceMetrics(BaseModel):
    """Performance metrics for portfolio or property."""
    period: str  # "month", "quarter", "year", "all_time"
    revenue: float
    expenses: float
    net_income: float
    occupancy_rate: float
    appreciation: float
    total_return: float


# ============================================================================
# Mock Data Store
# ============================================================================

DEAL_SCENARIOS: Dict[str, List[Dict]] = {
    "deal_001": [
        {
            "id": "scenario_001",
            "deal_id": "deal_001",
            "scenario_type": "base_case",
            "name": "Base Case - Moderate Growth",
            "description": "Conservative projections with 3% annual rent growth and 4% appreciation",
            "assumptions": {
                "rent_growth_rate": 0.03,
                "appreciation_rate": 0.04,
                "vacancy_rate": 0.05,
                "exit_year": 5,
                "exit_cap_rate": 0.055
            },
            "metrics": {
                "purchase_price": 875000,
                "closing_costs": 26250,
                "renovation_budget": 50000,
                "total_investment": 951250,
                "annual_rental_income": 78000,
                "annual_operating_expenses": 23400,
                "annual_debt_service": 35100,
                "net_operating_income": 54600,
                "cash_flow_year_1": 19500,
                "cap_rate": 0.0624,
                "cash_on_cash_return": 0.0820,
                "irr": 0.1450,
                "equity_multiple": 1.85,
                "break_even_occupancy": 0.72
            },
            "probability": 0.60,
            "created_at": "2025-11-10T10:00:00",
            "created_by": "demo@realestateos.com"
        },
        {
            "id": "scenario_002",
            "deal_id": "deal_001",
            "scenario_type": "best_case",
            "name": "Best Case - Strong Market",
            "description": "Optimistic projections with 5% rent growth and 6% appreciation",
            "assumptions": {
                "rent_growth_rate": 0.05,
                "appreciation_rate": 0.06,
                "vacancy_rate": 0.03,
                "exit_year": 5,
                "exit_cap_rate": 0.050
            },
            "metrics": {
                "purchase_price": 875000,
                "closing_costs": 26250,
                "renovation_budget": 50000,
                "total_investment": 951250,
                "annual_rental_income": 82000,
                "annual_operating_expenses": 22140,
                "annual_debt_service": 35100,
                "net_operating_income": 59860,
                "cash_flow_year_1": 24760,
                "cap_rate": 0.0684,
                "cash_on_cash_return": 0.1040,
                "irr": 0.1920,
                "equity_multiple": 2.25,
                "break_even_occupancy": 0.68
            },
            "probability": 0.20,
            "created_at": "2025-11-10T10:00:00",
            "created_by": "demo@realestateos.com"
        },
        {
            "id": "scenario_003",
            "deal_id": "deal_001",
            "scenario_type": "worst_case",
            "name": "Worst Case - Market Downturn",
            "description": "Conservative projections with 1% rent growth and 2% appreciation",
            "assumptions": {
                "rent_growth_rate": 0.01,
                "appreciation_rate": 0.02,
                "vacancy_rate": 0.10,
                "exit_year": 5,
                "exit_cap_rate": 0.065
            },
            "metrics": {
                "purchase_price": 875000,
                "closing_costs": 26250,
                "renovation_budget": 50000,
                "total_investment": 951250,
                "annual_rental_income": 74000,
                "annual_operating_expenses": 25900,
                "annual_debt_service": 35100,
                "net_operating_income": 48100,
                "cash_flow_year_1": 13000,
                "cap_rate": 0.0550,
                "cash_on_cash_return": 0.0546,
                "irr": 0.0980,
                "equity_multiple": 1.52,
                "break_even_occupancy": 0.78
            },
            "probability": 0.20,
            "created_at": "2025-11-10T10:00:00",
            "created_by": "demo@realestateos.com"
        }
    ]
}


# ============================================================================
# Deal Scenario Endpoints
# ============================================================================

@router.get("/deals/{deal_id}/scenarios", response_model=List[DealScenario])
def get_deal_scenarios(deal_id: str):
    """
    Get financial scenarios for a deal.

    Returns base case, best case, worst case, and any custom scenarios.
    Each scenario includes assumptions and projected financial metrics.
    """
    if deal_id not in DEAL_SCENARIOS:
        # Return mock scenarios if deal exists but has no custom scenarios
        return [
            DealScenario(**scenario)
            for scenario in DEAL_SCENARIOS.get("deal_001", [])
        ]

    scenarios = DEAL_SCENARIOS[deal_id]
    return [DealScenario(**scenario) for scenario in scenarios]


@router.post("/deals/{deal_id}/scenarios", response_model=DealScenario, status_code=201)
def create_deal_scenario(deal_id: str, scenario: ScenarioCreate):
    """
    Create a custom financial scenario for a deal.

    Allows creating "what-if" scenarios with custom assumptions
    to model different outcomes.
    """
    # Generate new ID
    if deal_id not in DEAL_SCENARIOS:
        DEAL_SCENARIOS[deal_id] = []

    scenario_id = f"scenario_{str(len(DEAL_SCENARIOS[deal_id]) + 1).zfill(3)}"

    # Mock financial calculation based on assumptions
    # In real system, would run actual financial model
    new_scenario = {
        "id": scenario_id,
        "deal_id": deal_id,
        "scenario_type": "custom",
        "name": scenario.name,
        "description": scenario.description,
        "assumptions": scenario.assumptions,
        "metrics": {
            "purchase_price": 875000,
            "closing_costs": 26250,
            "renovation_budget": 50000,
            "total_investment": 951250,
            "annual_rental_income": 78000 * (1 + scenario.assumptions.get("rent_growth_rate", 0.03)),
            "annual_operating_expenses": 23400,
            "annual_debt_service": 35100,
            "net_operating_income": 54600,
            "cash_flow_year_1": 19500,
            "cap_rate": 0.0624,
            "cash_on_cash_return": 0.0820,
            "irr": 0.1450,
            "equity_multiple": 1.85,
            "break_even_occupancy": 0.72
        },
        "probability": None,
        "created_at": datetime.now().isoformat(),
        "created_by": "demo@realestateos.com"
    }

    DEAL_SCENARIOS[deal_id].append(new_scenario)

    return DealScenario(**new_scenario)


@router.get("/deals/{deal_id}/scenarios/{scenario_id}", response_model=DealScenario)
def get_deal_scenario(deal_id: str, scenario_id: str):
    """
    Get details of a specific scenario.
    """
    if deal_id not in DEAL_SCENARIOS:
        raise HTTPException(status_code=404, detail="Deal not found")

    scenarios = DEAL_SCENARIOS[deal_id]
    scenario = next((s for s in scenarios if s["id"] == scenario_id), None)

    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    return DealScenario(**scenario)


@router.delete("/deals/{deal_id}/scenarios/{scenario_id}", status_code=204)
def delete_deal_scenario(deal_id: str, scenario_id: str):
    """
    Delete a custom scenario.

    Cannot delete built-in scenarios (base_case, best_case, worst_case).
    """
    if deal_id not in DEAL_SCENARIOS:
        raise HTTPException(status_code=404, detail="Deal not found")

    scenarios = DEAL_SCENARIOS[deal_id]
    scenario = next((s for s in scenarios if s["id"] == scenario_id), None)

    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    if scenario["scenario_type"] != "custom":
        raise HTTPException(
            status_code=403,
            detail="Cannot delete built-in scenarios"
        )

    DEAL_SCENARIOS[deal_id] = [s for s in scenarios if s["id"] != scenario_id]
    return None


@router.get("/deals/{deal_id}/scenarios/comparison")
def compare_scenarios(deal_id: str):
    """
    Compare all scenarios for a deal side-by-side.

    Returns a comparison matrix of key metrics across scenarios.
    """
    if deal_id not in DEAL_SCENARIOS:
        # Return mock comparison
        scenarios = DEAL_SCENARIOS.get("deal_001", [])
    else:
        scenarios = DEAL_SCENARIOS[deal_id]

    comparison = {
        "deal_id": deal_id,
        "scenarios": []
    }

    for scenario in scenarios:
        metrics = scenario["metrics"]
        comparison["scenarios"].append({
            "scenario_id": scenario["id"],
            "name": scenario["name"],
            "type": scenario["scenario_type"],
            "probability": scenario.get("probability"),
            "key_metrics": {
                "total_investment": metrics["total_investment"],
                "cash_flow_year_1": metrics["cash_flow_year_1"],
                "cap_rate": metrics["cap_rate"],
                "cash_on_cash_return": metrics["cash_on_cash_return"],
                "irr": metrics["irr"],
                "equity_multiple": metrics["equity_multiple"]
            }
        })

    # Calculate expected value weighted by probability
    weighted_irr = sum(
        s["metrics"]["irr"] * s.get("probability", 0)
        for s in scenarios
        if s.get("probability")
    )

    comparison["expected_irr"] = weighted_irr

    return comparison


# ============================================================================
# Investor Readiness Endpoints
# ============================================================================

@router.get("/properties/{property_id}/investor-readiness", response_model=InvestorReadiness)
def get_investor_readiness(property_id: str):
    """
    Get investor readiness assessment for a property.

    Evaluates how ready a property is to present to investors.
    Scores multiple criteria and provides recommendations.
    """
    # Mock readiness assessment
    criteria = [
        ReadinessCriteria(
            name="Property Information Completeness",
            score=85,
            weight=0.15,
            status="complete",
            details="All basic property details present. Missing property tax history."
        ),
        ReadinessCriteria(
            name="Financial Analysis",
            score=90,
            weight=0.25,
            status="complete",
            details="Pro forma, comps analysis, and multiple scenarios completed."
        ),
        ReadinessCriteria(
            name="Market Data",
            score=75,
            weight=0.15,
            status="complete",
            details="Market trends and demographics included. Could add more neighborhood data."
        ),
        ReadinessCriteria(
            name="Property Condition Assessment",
            score=95,
            weight=0.20,
            status="complete",
            details="Full inspection report with photos. Recent appraisal on file."
        ),
        ReadinessCriteria(
            name="Legal Documentation",
            score=60,
            weight=0.15,
            status="incomplete",
            details="Title search pending. Need environmental reports."
        ),
        ReadinessCriteria(
            name="Investment Presentation",
            score=70,
            weight=0.10,
            status="incomplete",
            details="Executive summary drafted. Need to finalize investor deck."
        )
    ]

    # Calculate weighted overall score
    overall_score = sum(c.score * c.weight for c in criteria)

    # Determine level
    if overall_score >= 90:
        level = InvestorReadinessLevel.excellent
    elif overall_score >= 70:
        level = InvestorReadinessLevel.good
    elif overall_score >= 50:
        level = InvestorReadinessLevel.fair
    else:
        level = InvestorReadinessLevel.poor

    recommendations = [
        "Complete title search and obtain title insurance",
        "Order Phase I environmental assessment",
        "Finalize investor presentation deck with renderings",
        "Add 5-year cash flow projection to financial analysis",
        "Include property tax appeal opportunity analysis"
    ]

    strengths = [
        "Comprehensive financial analysis with multiple scenarios",
        "Recent professional inspection with detailed photo documentation",
        "Strong market fundamentals in growing neighborhood",
        "Below-market acquisition price with 15% built-in equity"
    ]

    weaknesses = [
        "Legal due diligence not yet complete",
        "Investment presentation needs refinement",
        "Limited historical operating data (property was vacant)",
        "Environmental assessment not yet ordered"
    ]

    return InvestorReadiness(
        property_id=property_id,
        overall_score=round(overall_score, 1),
        level=level,
        criteria=criteria,
        recommendations=recommendations,
        strengths=strengths,
        weaknesses=weaknesses,
        last_updated=datetime.now().isoformat()
    )


@router.get("/portfolio/summary", response_model=PortfolioSummary)
def get_portfolio_summary():
    """
    Get summary of entire portfolio.

    Returns aggregate metrics across all properties and deals.
    """
    return PortfolioSummary(
        total_properties=25,
        total_value=18750000,
        total_equity=7500000,
        total_debt=11250000,
        average_cap_rate=0.0625,
        average_cash_on_cash=0.0890,
        total_annual_income=1875000,
        total_annual_expenses=937500,
        portfolio_irr=0.1420,
        properties_by_type={
            "single_family": 8,
            "multi_family": 12,
            "commercial": 3,
            "land": 2
        },
        properties_by_stage={
            "prospect": 5,
            "under_contract": 3,
            "owned": 15,
            "sold": 2
        }
    )


@router.get("/portfolio/performance", response_model=List[PerformanceMetrics])
def get_portfolio_performance(period: str = "year"):
    """
    Get performance metrics for portfolio over time.

    Shows revenue, expenses, occupancy, and returns by period.
    """
    # Mock performance data
    if period == "month":
        periods = ["2025-11", "2025-10", "2025-09", "2025-08", "2025-07", "2025-06"]
    elif period == "quarter":
        periods = ["2025-Q4", "2025-Q3", "2025-Q2", "2025-Q1"]
    else:  # year
        periods = ["2025", "2024", "2023", "2022", "2021"]

    performance = []
    for p in periods:
        performance.append(PerformanceMetrics(
            period=p,
            revenue=random.uniform(140000, 180000),
            expenses=random.uniform(60000, 80000),
            net_income=random.uniform(70000, 100000),
            occupancy_rate=random.uniform(0.88, 0.97),
            appreciation=random.uniform(0.03, 0.07),
            total_return=random.uniform(0.12, 0.18)
        ))

    return performance


@router.get("/properties/{property_id}/performance", response_model=List[PerformanceMetrics])
def get_property_performance(property_id: str, period: str = "month"):
    """
    Get performance metrics for a specific property over time.
    """
    # Mock property performance data
    if period == "month":
        periods = ["2025-11", "2025-10", "2025-09", "2025-08", "2025-07", "2025-06"]
    else:
        periods = ["2025", "2024", "2023"]

    performance = []
    for p in periods:
        performance.append(PerformanceMetrics(
            period=p,
            revenue=random.uniform(6000, 7500),
            expenses=random.uniform(2000, 3000),
            net_income=random.uniform(3500, 5000),
            occupancy_rate=random.uniform(0.90, 1.0),
            appreciation=random.uniform(0.03, 0.06),
            total_return=random.uniform(0.10, 0.16)
        ))

    return performance
