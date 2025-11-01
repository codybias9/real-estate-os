"""Multi-Family Valuation
Income approach for multi-family properties using unit-level analysis

Features:
- Unit mix modeling (studio, 1BR, 2BR, 3BR)
- Rent roll analysis with lease expiration
- Economic vs. physical vacancy
- Utility reimbursement income
- Amenity income (parking, storage, pet fees)
- Credit loss reserves
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import logging

from .dcf_engine import DCFEngine, DCFAssumptions, DCFResult

logger = logging.getLogger(__name__)


@dataclass
class UnitMix:
    """Unit mix by bedroom count"""
    unit_type: str  # "studio", "1BR", "2BR", "3BR", "4BR"
    unit_count: int
    avg_sf_per_unit: float
    market_rent: float  # Monthly market rent per unit
    current_avg_rent: float  # Current in-place rent
    occupied_count: int  # Currently occupied units


@dataclass
class MFProperty:
    """Multi-family property profile"""
    property_id: str
    property_name: str
    address: str

    # Physical
    total_units: int
    total_sf: int
    year_built: int
    year_renovated: Optional[int] = None

    # Unit mix
    unit_mix: List[UnitMix] = field(default_factory=list)

    # Financials
    current_monthly_rent_roll: float = 0.0  # Total in-place rent
    annual_other_income: float = 0.0  # Parking, laundry, pet fees

    # Operating
    current_physical_vacancy_rate: float = 0.05
    economic_vacancy_rate: float = 0.03  # Bad debt, concessions
    annual_opex: float = 0.0
    annual_property_tax: float = 0.0
    annual_insurance: float = 0.0

    # Market
    market: str = "unknown"
    submarket: str = "unknown"
    market_rent_growth: float = 0.03


class MFValuationEngine:
    """Multi-family valuation engine"""

    def __init__(self):
        self.dcf_engine = DCFEngine()

    def value_mf_property(
        self,
        property: MFProperty,
        holding_period_years: int = 10,
        exit_cap_rate: float = 0.055,
        discount_rate: float = 0.12,
        loan_to_value: float = 0.70,
        interest_rate: float = 0.055,
        amortization_years: int = 30
    ) -> DCFResult:
        """Value multi-family property using DCF

        Args:
            property: MF property data
            holding_period_years: Investment horizon
            exit_cap_rate: Cap rate at sale
            discount_rate: Required return on equity
            loan_to_value: LTV ratio
            interest_rate: Loan rate
            amortization_years: Loan term

        Returns:
            DCFResult with valuation and cash flows
        """

        # Step 1: Calculate stabilized GPR from unit mix
        stabilized_gpr = self._calculate_stabilized_gpr(property)

        # Step 2: Calculate vacancy and concession rates
        physical_vacancy_rate = property.current_physical_vacancy_rate
        economic_vacancy_rate = property.economic_vacancy_rate
        total_vacancy_rate = physical_vacancy_rate + economic_vacancy_rate

        # Step 3: Other income
        annual_other_income = property.annual_other_income

        # Step 4: Operating expenses
        # Calculate as % of EGI if not provided
        if property.annual_opex > 0:
            opex_per_sf = property.annual_opex / property.total_sf
        else:
            opex_per_sf = 0.0  # Will use opex_pct_egi

        # Step 5: Reserves (typical for MF is $250/unit/year)
        replacement_reserve_per_unit = 250.0

        # Step 6: Build DCF assumptions
        assumptions = DCFAssumptions(
            property_id=property.property_id,
            valuation_date=datetime.now(),
            holding_period_years=holding_period_years,

            # Revenue
            gross_potential_rent=stabilized_gpr,
            vacancy_rate=total_vacancy_rate,
            concessions_rate=0.0,  # Already included in economic vacancy
            other_income=annual_other_income,

            # Expenses
            opex_per_sf_annual=opex_per_sf,
            opex_pct_egi=0.35 if opex_per_sf == 0 else 0.0,
            property_tax_rate=property.annual_property_tax / (stabilized_gpr / 0.05) if property.annual_property_tax > 0 else 0.012,
            insurance_annual=property.annual_insurance,
            utilities_annual=0.0,  # Typically tenant-paid in MF
            management_fee_pct=0.03,

            # Reserves
            replacement_reserve_per_unit=replacement_reserve_per_unit,
            ti_reserve_per_sf=0.0,  # Not applicable for MF
            lc_reserve_per_sf=0.0,  # Not applicable for MF

            # Growth
            rent_growth_annual=property.market_rent_growth,
            expense_growth_annual=0.025,

            # Debt
            loan_to_value=loan_to_value,
            interest_rate=interest_rate,
            amortization_years=amortization_years,
            interest_only_years=0,

            # Exit
            exit_cap_rate=exit_cap_rate,
            selling_costs_pct=0.02,

            # Discount rate
            discount_rate=discount_rate,

            # Physical
            rentable_sf=float(property.total_sf),
            unit_count=property.total_units,

            # Market
            market_cap_rate=0.05  # Will be overridden with stabilized NOI / value
        )

        # Step 7: Run DCF
        result = self.dcf_engine.calculate_dcf(assumptions)

        logger.info(f"MF Valuation complete for {property.property_name}: Value=${result.direct_cap_value:,.0f}")

        return result

    def _calculate_stabilized_gpr(self, property: MFProperty) -> float:
        """Calculate stabilized gross potential rent

        Uses market rents for all units at full occupancy

        Args:
            property: MF property

        Returns:
            Annual GPR at market rents
        """

        total_annual_rent = 0.0

        for unit_type in property.unit_mix:
            # Use market rent, not current rent, for stabilized GPR
            annual_rent_per_unit = unit_type.market_rent * 12
            total_annual_rent += annual_rent_per_unit * unit_type.unit_count

        logger.info(f"Stabilized GPR: ${total_annual_rent:,.0f} for {property.total_units} units")

        return total_annual_rent

    def analyze_rent_roll(self, property: MFProperty) -> Dict:
        """Analyze current rent roll

        Args:
            property: MF property

        Returns:
            Dict with rent roll analysis
        """

        # Calculate weighted average rent per unit
        total_in_place_rent = 0.0
        total_market_rent = 0.0
        total_occupied = 0

        for unit_type in property.unit_mix:
            total_in_place_rent += unit_type.current_avg_rent * unit_type.occupied_count
            total_market_rent += unit_type.market_rent * unit_type.unit_count
            total_occupied += unit_type.occupied_count

        avg_in_place_rent = total_in_place_rent / total_occupied if total_occupied > 0 else 0.0
        avg_market_rent = total_market_rent / property.total_units if property.total_units > 0 else 0.0

        # Loss to lease (potential rent increase at renewal)
        loss_to_lease_monthly = total_market_rent - total_in_place_rent
        loss_to_lease_annual = loss_to_lease_monthly * 12
        loss_to_lease_pct = (avg_market_rent - avg_in_place_rent) / avg_market_rent if avg_market_rent > 0 else 0.0

        # Occupancy
        physical_occupancy = total_occupied / property.total_units if property.total_units > 0 else 0.0

        analysis = {
            "total_units": property.total_units,
            "occupied_units": total_occupied,
            "vacant_units": property.total_units - total_occupied,
            "physical_occupancy_pct": physical_occupancy,
            "avg_in_place_rent": avg_in_place_rent,
            "avg_market_rent": avg_market_rent,
            "loss_to_lease_monthly": loss_to_lease_monthly,
            "loss_to_lease_annual": loss_to_lease_annual,
            "loss_to_lease_pct": loss_to_lease_pct,
            "annual_gpr_in_place": total_in_place_rent * 12,
            "annual_gpr_market": total_market_rent * 12
        }

        logger.info(f"Rent roll: {physical_occupancy:.1%} occupied, {loss_to_lease_pct:.1%} loss-to-lease")

        return analysis

    def calculate_unit_economics(self, property: MFProperty) -> pd.DataFrame:
        """Calculate per-unit economics

        Args:
            property: MF property

        Returns:
            DataFrame with unit-level metrics
        """

        records = []

        # Allocate expenses proportionally by SF
        total_annual_expenses = (
            property.annual_opex +
            property.annual_property_tax +
            property.annual_insurance
        )

        expense_per_sf = total_annual_expenses / property.total_sf if property.total_sf > 0 else 0.0

        for unit_type in property.unit_mix:
            # Revenue
            annual_market_rent = unit_type.market_rent * 12
            annual_in_place_rent = unit_type.current_avg_rent * 12

            # Expenses
            annual_expenses_per_unit = expense_per_sf * unit_type.avg_sf_per_unit

            # NOI
            noi_per_unit_market = annual_market_rent - annual_expenses_per_unit
            noi_per_unit_in_place = annual_in_place_rent - annual_expenses_per_unit

            # Cap rate (if property sold today)
            # Assume 5% market cap rate
            value_per_unit_market = noi_per_unit_market / 0.05

            record = {
                "unit_type": unit_type.unit_type,
                "unit_count": unit_type.unit_count,
                "occupied_count": unit_type.occupied_count,
                "avg_sf": unit_type.avg_sf_per_unit,
                "market_rent_monthly": unit_type.market_rent,
                "in_place_rent_monthly": unit_type.current_avg_rent,
                "market_rent_annual": annual_market_rent,
                "in_place_rent_annual": annual_in_place_rent,
                "expenses_annual": annual_expenses_per_unit,
                "noi_annual_market": noi_per_unit_market,
                "noi_annual_in_place": noi_per_unit_in_place,
                "value_per_unit": value_per_unit_market,
                "total_value": value_per_unit_market * unit_type.unit_count
            }

            records.append(record)

        df = pd.DataFrame(records)

        return df

    def compare_to_market(self, property: MFProperty, market_comps: List[MFProperty]) -> Dict:
        """Compare property to market comps

        Args:
            property: Subject property
            market_comps: List of comparable properties

        Returns:
            Dict with comparison metrics
        """

        # Calculate subject metrics
        subject_rent_roll = self.analyze_rent_roll(property)
        subject_avg_rent = subject_rent_roll["avg_market_rent"]
        subject_avg_sf = property.total_sf / property.total_units

        # Calculate market averages
        market_avg_rents = []
        market_avg_sf = []
        market_occupancies = []

        for comp in market_comps:
            comp_rent_roll = self.analyze_rent_roll(comp)
            market_avg_rents.append(comp_rent_roll["avg_market_rent"])
            market_avg_sf.append(comp.total_sf / comp.total_units)
            market_occupancies.append(comp_rent_roll["physical_occupancy_pct"])

        market_avg_rent = np.mean(market_avg_rents) if market_avg_rents else 0.0
        market_avg_sf_per_unit = np.mean(market_avg_sf) if market_avg_sf else 0.0
        market_avg_occupancy = np.mean(market_occupancies) if market_occupancies else 0.0

        # Calculate percentile rankings
        rent_percentile = np.searchsorted(sorted(market_avg_rents), subject_avg_rent) / len(market_avg_rents) if market_avg_rents else 0.5

        comparison = {
            "subject_avg_rent": subject_avg_rent,
            "market_avg_rent": market_avg_rent,
            "subject_rent_premium_discount": (subject_avg_rent - market_avg_rent) / market_avg_rent if market_avg_rent > 0 else 0.0,
            "subject_avg_sf": subject_avg_sf,
            "market_avg_sf": market_avg_sf_per_unit,
            "subject_occupancy": subject_rent_roll["physical_occupancy_pct"],
            "market_avg_occupancy": market_avg_occupancy,
            "rent_percentile": rent_percentile,
            "comps_count": len(market_comps)
        }

        return comparison


# ============================================================================
# Convenience Functions
# ============================================================================

def value_mf_property_simple(
    property_data: Dict,
    holding_period_years: int = 10,
    exit_cap_rate: float = 0.055
) -> Dict:
    """Simple MF valuation from property data dict

    Args:
        property_data: Property data from database
        holding_period_years: Investment horizon
        exit_cap_rate: Exit cap rate

    Returns:
        Dict with valuation summary
    """

    # Build MFProperty from dict
    unit_mix = []

    # Parse unit mix if available
    if "unit_mix" in property_data:
        for unit in property_data["unit_mix"]:
            unit_mix.append(UnitMix(
                unit_type=unit["unit_type"],
                unit_count=unit["unit_count"],
                avg_sf_per_unit=unit["avg_sf_per_unit"],
                market_rent=unit["market_rent"],
                current_avg_rent=unit.get("current_avg_rent", unit["market_rent"]),
                occupied_count=unit.get("occupied_count", unit["unit_count"])
            ))

    property = MFProperty(
        property_id=property_data["property_id"],
        property_name=property_data.get("property_name", "Unknown"),
        address=property_data.get("address", ""),
        total_units=property_data["total_units"],
        total_sf=property_data["total_sf"],
        year_built=property_data["year_built"],
        unit_mix=unit_mix,
        current_monthly_rent_roll=property_data.get("current_monthly_rent_roll", 0.0),
        annual_other_income=property_data.get("annual_other_income", 0.0),
        current_physical_vacancy_rate=property_data.get("current_physical_vacancy_rate", 0.05),
        economic_vacancy_rate=property_data.get("economic_vacancy_rate", 0.03),
        annual_opex=property_data.get("annual_opex", 0.0),
        annual_property_tax=property_data.get("annual_property_tax", 0.0),
        annual_insurance=property_data.get("annual_insurance", 0.0),
        market=property_data.get("market", "unknown"),
        market_rent_growth=property_data.get("market_rent_growth", 0.03)
    )

    # Value property
    engine = MFValuationEngine()
    result = engine.value_mf_property(
        property=property,
        holding_period_years=holding_period_years,
        exit_cap_rate=exit_cap_rate
    )

    # Convert to simple dict
    summary = {
        "property_id": property.property_id,
        "valuation_date": result.valuation_date.isoformat(),
        "valuation_method": "dcf_mf",
        "direct_cap_value": result.direct_cap_value,
        "npv": result.npv,
        "irr": result.irr,
        "equity_multiple": result.equity_multiple,
        "stabilized_noi": result.stabilized_noi,
        "avg_dscr": result.avg_dscr,
        "min_dscr": result.min_dscr,
        "total_equity_invested": result.total_equity_invested,
        "total_cash_distributed": result.total_cash_distributed,
        "holding_period_years": holding_period_years,
        "exit_cap_rate": exit_cap_rate
    }

    return summary
