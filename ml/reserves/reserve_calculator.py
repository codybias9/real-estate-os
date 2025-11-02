"""
Reserve Calculation Engine.

Calculates required cash reserves for investment properties including:
- Operating reserves (rent loss, repairs, vacancy)
- Capital reserves (major systems replacement)
- Lender reserve requirements
- Recommended reserve levels by property type
- Reserve depletion scenarios

Critical for:
- Portfolio risk management
- Lender qualification
- Cash flow planning
- Emergency preparedness
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PropertyType(Enum):
    """Property types for reserve calculation."""
    SINGLE_FAMILY = "Single Family"
    SMALL_MULTIFAMILY = "Small Multifamily (2-4 units)"
    LARGE_MULTIFAMILY = "Large Multifamily (5+ units)"
    COMMERCIAL = "Commercial"


@dataclass
class CapitalItem:
    """Major capital expenditure item."""
    category: str  # Roof, HVAC, etc.
    replacement_cost: float
    useful_life_years: int
    current_age_years: int

    @property
    def remaining_life_years(self) -> int:
        """Years remaining before replacement."""
        return max(0, self.useful_life_years - self.current_age_years)

    @property
    def annual_reserve(self) -> float:
        """Annual reserve amount (straight-line)."""
        return self.replacement_cost / self.useful_life_years


@dataclass
class ReserveAnalysis:
    """Complete reserve analysis results."""
    # Operating reserves
    operating_reserve_months: float
    operating_reserve_amount: float

    # Capital reserves
    capital_reserve_annual: float
    capital_reserve_amount: float  # For first year

    # Total reserves
    total_recommended_reserves: float

    # Lender requirements
    lender_required_reserves: float
    lender_months: float

    # Breakdown
    monthly_piti: float
    vacancy_reserve: float
    repair_reserve: float
    capital_items: List[CapitalItem]

    # Adequacy
    reserves_adequate: bool
    shortfall: float


class ReserveCalculator:
    """
    Calculates required cash reserves for investment properties.
    """

    # Standard reserve recommendations by property type (months of PITI)
    RESERVE_MONTHS = {
        PropertyType.SINGLE_FAMILY: 6.0,
        PropertyType.SMALL_MULTIFAMILY: 9.0,
        PropertyType.LARGE_MULTIFAMILY: 12.0,
        PropertyType.COMMERCIAL: 12.0
    }

    # Standard useful life for major systems (years)
    USEFUL_LIFE = {
        "Roof": 25,
        "HVAC": 15,
        "Water Heater": 12,
        "Appliances": 10,
        "Flooring": 10,
        "Paint (Interior)": 5,
        "Paint (Exterior)": 7,
        "Windows": 25,
        "Plumbing": 40,
        "Electrical": 40,
        "Foundation": 100
    }

    def calculate_reserves(
        self,
        property_type: PropertyType,
        monthly_piti: float,
        property_value: float,
        num_units: int = 1,
        capital_items: Optional[List[CapitalItem]] = None,
        lender_required_months: Optional[float] = None
    ) -> ReserveAnalysis:
        """
        Calculate required reserves.

        Args:
            property_type: Type of property
            monthly_piti: Monthly principal, interest, taxes, insurance
            property_value: Property value
            num_units: Number of units
            capital_items: List of major capital items
            lender_required_months: Lender's reserve requirement (months of PITI)

        Returns:
            ReserveAnalysis with complete breakdown
        """
        logger.info(f"Calculating reserves for {property_type.value}, ${property_value:,.0f}")

        # Operating reserves (months of PITI)
        recommended_months = self.RESERVE_MONTHS[property_type]
        operating_reserve = monthly_piti * recommended_months

        # Capital reserves
        if capital_items:
            annual_capital = sum(item.annual_reserve for item in capital_items)
        else:
            # Estimate 1-2% of property value annually for capital reserves
            capital_rate = 0.015 if property_type == PropertyType.SINGLE_FAMILY else 0.020
            annual_capital = property_value * capital_rate

        capital_reserve_amount = annual_capital  # First year

        # Total recommended
        total_recommended = operating_reserve + capital_reserve_amount

        # Lender requirements
        if lender_required_months:
            lender_required = monthly_piti * lender_required_months
        else:
            lender_required = 0

        # Adequacy check
        shortfall = max(0, lender_required - total_recommended)
        adequate = shortfall == 0

        # Breakdown components
        vacancy_months = 1.0  # 1 month rent loss reserve
        repair_months = 1.0   # 1 month repair reserve

        vacancy_reserve = monthly_piti * vacancy_months
        repair_reserve = monthly_piti * repair_months

        logger.info(
            f"Total reserves: ${total_recommended:,.0f} "
            f"({recommended_months:.1f} months PITI + capital)"
        )

        return ReserveAnalysis(
            operating_reserve_months=recommended_months,
            operating_reserve_amount=operating_reserve,
            capital_reserve_annual=annual_capital,
            capital_reserve_amount=capital_reserve_amount,
            total_recommended_reserves=total_recommended,
            lender_required_reserves=lender_required,
            lender_months=lender_required_months or 0,
            monthly_piti=monthly_piti,
            vacancy_reserve=vacancy_reserve,
            repair_reserve=repair_reserve,
            capital_items=capital_items or [],
            reserves_adequate=adequate,
            shortfall=shortfall
        )

    def estimate_capital_items(
        self,
        property_value: float,
        building_sqft: int,
        year_built: int,
        num_units: int = 1
    ) -> List[CapitalItem]:
        """
        Estimate major capital items based on property characteristics.

        Returns list of CapitalItem objects with estimated costs and ages.
        """
        current_year = 2024
        property_age = current_year - year_built

        items = []

        # Roof
        roof_cost = building_sqft * 8  # $8/sqft average
        items.append(CapitalItem(
            category="Roof",
            replacement_cost=roof_cost,
            useful_life_years=25,
            current_age_years=min(property_age, 20)  # Assume replaced at some point
        ))

        # HVAC
        hvac_cost = num_units * 5000  # $5k per unit
        items.append(CapitalItem(
            category="HVAC",
            replacement_cost=hvac_cost,
            useful_life_years=15,
            current_age_years=min(property_age, 12)
        ))

        # Water Heater
        wh_cost = num_units * 1200
        items.append(CapitalItem(
            category="Water Heater",
            replacement_cost=wh_cost,
            useful_life_years=12,
            current_age_years=min(property_age, 10)
        ))

        # Appliances
        if num_units <= 4:
            app_cost = num_units * 2500
            items.append(CapitalItem(
                category="Appliances",
                replacement_cost=app_cost,
                useful_life_years=10,
                current_age_years=min(property_age, 8)
            ))

        # Flooring
        flooring_cost = building_sqft * 4  # $4/sqft
        items.append(CapitalItem(
            category="Flooring",
            replacement_cost=flooring_cost,
            useful_life_years=10,
            current_age_years=min(property_age, 8)
        ))

        # Exterior Paint
        paint_cost = building_sqft * 2  # $2/sqft for exterior
        items.append(CapitalItem(
            category="Paint (Exterior)",
            replacement_cost=paint_cost,
            useful_life_years=7,
            current_age_years=min(property_age, 5)
        ))

        logger.info(f"Estimated {len(items)} capital items, total annual reserve: ${sum(i.annual_reserve for i in items):,.0f}")

        return items


def calculate_simple_reserves(
    monthly_payment: float,
    property_type: str = "single_family",
    lender_months: float = 6.0
) -> Dict[str, float]:
    """
    Quick reserve calculator.

    Args:
        monthly_payment: Monthly PITI payment
        property_type: Property type string
        lender_months: Lender requirement in months

    Returns:
        Dictionary with reserve amounts
    """
    # Map string to enum
    type_map = {
        "single_family": PropertyType.SINGLE_FAMILY,
        "small_multifamily": PropertyType.SMALL_MULTIFAMILY,
        "large_multifamily": PropertyType.LARGE_MULTIFAMILY,
        "commercial": PropertyType.COMMERCIAL
    }

    prop_type = type_map.get(property_type, PropertyType.SINGLE_FAMILY)

    # Operating reserves
    recommended_months = ReserveCalculator.RESERVE_MONTHS[prop_type]
    operating_reserve = monthly_payment * recommended_months

    # Lender requirement
    lender_required = monthly_payment * lender_months

    # Total with capital buffer (add 20%)
    total_recommended = operating_reserve * 1.20

    return {
        "monthly_payment": monthly_payment,
        "recommended_months": recommended_months,
        "operating_reserve": operating_reserve,
        "lender_required": lender_required,
        "total_recommended": total_recommended,
        "shortfall": max(0, lender_required - total_recommended)
    }
