"""Commercial Real Estate Valuation
Income approach for office, retail, industrial properties

Features:
- Lease rollover modeling
- TI (Tenant Improvements) and LC (Leasing Commissions) reserves
- Credit-weighted vacancy
- Rent escalations and free rent periods
- Suite-level cash flow analysis
- Rollover risk assessment
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import numpy as np
import pandas as pd
import logging

from .dcf_engine import DCFEngine, DCFAssumptions, DCFResult

logger = logging.getLogger(__name__)


class PropertyType(Enum):
    """CRE property types"""
    OFFICE = "office"
    RETAIL = "retail"
    INDUSTRIAL = "industrial"
    FLEX = "flex"
    MIXED_USE = "mixed_use"


class TenantCreditRating(Enum):
    """Tenant credit ratings"""
    AAA = "AAA"  # Investment grade, <1% default
    AA = "AA"
    A = "A"
    BBB = "BBB"  # Lower investment grade
    BB = "BB"  # Speculative grade
    B = "B"
    CCC = "CCC"  # High risk
    UNRATED = "unrated"


@dataclass
class Lease:
    """Individual lease contract"""
    lease_id: str
    tenant_name: str
    suite_number: str

    # Space
    leased_sf: float

    # Term
    lease_start_date: datetime
    lease_end_date: datetime
    lease_term_months: int

    # Rent
    base_rent_psf_annual: float  # Current annual rent per SF
    annual_escalation_pct: float = 0.03  # Annual rent increases
    free_rent_months: int = 0  # Already consumed

    # Recovery
    expense_recovery_type: str = "NNN"  # NNN, Modified Gross, Full Service
    cam_recovery_psf: float = 0.0  # CAM, property tax, insurance

    # Tenant credit
    credit_rating: TenantCreditRating = TenantCreditRating.UNRATED
    renewal_probability: float = 0.65  # Probability of renewal

    # TI and LC at lease-up
    ti_psf_at_renewal: float = 15.0  # Typical TI for new lease
    lc_pct_of_rent: float = 0.05  # 5% of first year rent

    # Status
    occupied: bool = True


@dataclass
class CREProperty:
    """Commercial property profile"""
    property_id: str
    property_name: str
    address: str

    # Physical
    property_type: PropertyType
    total_sf: float
    year_built: int
    year_renovated: Optional[int] = None

    # Leasing
    leases: List[Lease] = field(default_factory=list)
    occupied_sf: float = 0.0
    vacant_sf: float = 0.0

    # Financials
    annual_opex_psf: float = 8.0  # Office: $8-12, Retail: $6-10, Industrial: $3-5
    annual_property_tax: float = 0.0
    annual_insurance: float = 0.0

    # Market
    market: str = "unknown"
    submarket: str = "unknown"
    market_rent_psf: float = 25.0  # Annual market rent PSF
    market_vacancy_rate: float = 0.10
    market_rent_growth: float = 0.025

    # Assumptions
    downtime_months: int = 6  # Months between tenants
    credit_loss_pct: float = 0.01  # Bad debt


class CREValuationEngine:
    """Commercial real estate valuation engine"""

    # Default TI/LC by property type (PSF)
    DEFAULT_TI_PSF = {
        PropertyType.OFFICE: 40.0,
        PropertyType.RETAIL: 25.0,
        PropertyType.INDUSTRIAL: 10.0,
        PropertyType.FLEX: 15.0,
        PropertyType.MIXED_USE: 30.0
    }

    # Default LC as % of first year rent
    DEFAULT_LC_PCT = {
        PropertyType.OFFICE: 0.06,
        PropertyType.RETAIL: 0.08,
        PropertyType.INDUSTRIAL: 0.04,
        PropertyType.FLEX: 0.05,
        PropertyType.MIXED_USE: 0.06
    }

    def __init__(self):
        self.dcf_engine = DCFEngine()

    def value_cre_property(
        self,
        property: CREProperty,
        holding_period_years: int = 10,
        exit_cap_rate: float = 0.065,
        discount_rate: float = 0.13,
        loan_to_value: float = 0.65,
        interest_rate: float = 0.06,
        amortization_years: int = 25
    ) -> DCFResult:
        """Value CRE property using DCF with lease rollover

        Args:
            property: CRE property data
            holding_period_years: Investment horizon
            exit_cap_rate: Cap rate at sale
            discount_rate: Required return on equity
            loan_to_value: LTV ratio
            interest_rate: Loan rate
            amortization_years: Loan term

        Returns:
            DCFResult with valuation and cash flows
        """

        # Step 1: Calculate stabilized GPR
        # Use in-place rents for occupied space, market rents for vacant
        stabilized_gpr = self._calculate_stabilized_gpr(property)

        # Step 2: Calculate effective vacancy
        # Includes credit loss and structural vacancy
        effective_vacancy_rate = property.credit_loss_pct + (property.vacant_sf / property.total_sf)

        # Step 3: Calculate TI and LC reserves
        # Reserve for future lease rollover
        avg_ti_psf = self.DEFAULT_TI_PSF.get(property.property_type, 25.0)
        avg_lc_pct = self.DEFAULT_LC_PCT.get(property.property_type, 0.06)

        # Amortize TI over average lease term (assume 5 years)
        avg_lease_term_years = 5
        ti_reserve_psf_annual = avg_ti_psf / avg_lease_term_years

        # LC reserve as % of rent
        lc_reserve_psf_annual = property.market_rent_psf * avg_lc_pct / avg_lease_term_years

        # Step 4: Build DCF assumptions
        assumptions = DCFAssumptions(
            property_id=property.property_id,
            valuation_date=datetime.now(),
            holding_period_years=holding_period_years,

            # Revenue
            gross_potential_rent=stabilized_gpr,
            vacancy_rate=effective_vacancy_rate,
            concessions_rate=0.0,  # Already in effective vacancy
            other_income=0.0,  # Parking, storage if applicable

            # Expenses
            opex_per_sf_annual=property.annual_opex_psf,
            opex_pct_egi=0.0,  # Use per-SF method
            property_tax_rate=property.annual_property_tax / (stabilized_gpr / 0.06) if property.annual_property_tax > 0 else 0.015,
            insurance_annual=property.annual_insurance,
            utilities_annual=0.0,  # Typically tenant-paid in NNN
            management_fee_pct=0.03,

            # Reserves
            replacement_reserve_per_unit=0.0,  # Not applicable for CRE
            ti_reserve_per_sf=ti_reserve_psf_annual,
            lc_reserve_per_sf=lc_reserve_psf_annual,

            # Growth
            rent_growth_annual=property.market_rent_growth,
            expense_growth_annual=0.025,

            # Debt
            loan_to_value=loan_to_value,
            interest_rate=interest_rate,
            amortization_years=amortization_years,
            interest_only_years=2,  # 2 years IO common for CRE

            # Exit
            exit_cap_rate=exit_cap_rate,
            selling_costs_pct=0.02,

            # Discount rate
            discount_rate=discount_rate,

            # Physical
            rentable_sf=property.total_sf,
            unit_count=0,

            # Market
            market_cap_rate=0.06
        )

        # Step 5: Run DCF
        result = self.dcf_engine.calculate_dcf(assumptions)

        logger.info(f"CRE Valuation complete for {property.property_name}: Value=${result.direct_cap_value:,.0f}")

        return result

    def _calculate_stabilized_gpr(self, property: CREProperty) -> float:
        """Calculate stabilized gross potential rent

        Uses in-place rents for occupied space, market rents for vacant

        Args:
            property: CRE property

        Returns:
            Annual GPR
        """

        # In-place rent from leases
        total_in_place_rent = sum(
            lease.base_rent_psf_annual * lease.leased_sf
            for lease in property.leases
            if lease.occupied
        )

        # Market rent for vacant space
        vacant_rent = property.vacant_sf * property.market_rent_psf

        # Total GPR
        total_gpr = total_in_place_rent + vacant_rent

        logger.info(f"Stabilized GPR: ${total_gpr:,.0f} ({property.occupied_sf:,.0f} SF occupied @ in-place, {property.vacant_sf:,.0f} SF vacant @ market)")

        return total_gpr

    def analyze_rent_roll(self, property: CREProperty) -> Dict:
        """Analyze current rent roll

        Args:
            property: CRE property

        Returns:
            Dict with rent roll analysis
        """

        if not property.leases:
            return {
                "occupancy_rate": 0.0,
                "avg_in_place_rent_psf": 0.0,
                "avg_market_rent_psf": property.market_rent_psf,
                "wale_months": 0.0,
                "rollover_risk_pct": 0.0
            }

        # Calculate weighted metrics
        total_leased_sf = sum(lease.leased_sf for lease in property.leases if lease.occupied)
        total_in_place_rent = sum(
            lease.base_rent_psf_annual * lease.leased_sf
            for lease in property.leases if lease.occupied
        )

        avg_in_place_rent_psf = total_in_place_rent / total_leased_sf if total_leased_sf > 0 else 0.0

        # Weighted average lease expiration (WALE)
        now = datetime.now()
        total_weighted_months = sum(
            ((lease.lease_end_date - now).days / 30.44) * lease.leased_sf
            for lease in property.leases if lease.occupied and lease.lease_end_date > now
        )
        wale_months = total_weighted_months / total_leased_sf if total_leased_sf > 0 else 0.0

        # Rollover risk (leases expiring in next 12 months)
        rollover_sf = sum(
            lease.leased_sf
            for lease in property.leases
            if lease.occupied and 0 < (lease.lease_end_date - now).days <= 365
        )
        rollover_risk_pct = rollover_sf / property.total_sf if property.total_sf > 0 else 0.0

        # Loss to lease
        loss_to_lease_psf = property.market_rent_psf - avg_in_place_rent_psf
        loss_to_lease_pct = loss_to_lease_psf / property.market_rent_psf if property.market_rent_psf > 0 else 0.0

        # Occupancy
        occupancy_rate = total_leased_sf / property.total_sf if property.total_sf > 0 else 0.0

        analysis = {
            "total_sf": property.total_sf,
            "occupied_sf": total_leased_sf,
            "vacant_sf": property.total_sf - total_leased_sf,
            "occupancy_rate": occupancy_rate,
            "avg_in_place_rent_psf": avg_in_place_rent_psf,
            "avg_market_rent_psf": property.market_rent_psf,
            "loss_to_lease_psf": loss_to_lease_psf,
            "loss_to_lease_pct": loss_to_lease_pct,
            "wale_months": wale_months,
            "wale_years": wale_months / 12,
            "rollover_sf_12mo": rollover_sf,
            "rollover_risk_pct": rollover_risk_pct,
            "lease_count": len([l for l in property.leases if l.occupied])
        }

        logger.info(f"Rent roll: {occupancy_rate:.1%} occupied, WALE={wale_months/12:.1f}y, {rollover_risk_pct:.1%} rolling next 12mo")

        return analysis

    def project_lease_rollover(
        self,
        property: CREProperty,
        projection_years: int = 10
    ) -> pd.DataFrame:
        """Project lease expirations and rollover

        Args:
            property: CRE property
            projection_years: Years to project

        Returns:
            DataFrame with rollover schedule
        """

        records = []
        now = datetime.now()

        for year in range(1, projection_years + 1):
            year_start = now + timedelta(days=365 * (year - 1))
            year_end = now + timedelta(days=365 * year)

            # Find leases expiring in this year
            expiring_leases = [
                lease for lease in property.leases
                if lease.occupied and year_start <= lease.lease_end_date < year_end
            ]

            expiring_sf = sum(lease.leased_sf for lease in expiring_leases)
            expiring_rent = sum(lease.base_rent_psf_annual * lease.leased_sf for lease in expiring_leases)

            # Calculate expected renewals based on credit and probability
            expected_renewal_sf = sum(
                lease.leased_sf * lease.renewal_probability
                for lease in expiring_leases
            )

            expected_backfill_sf = expiring_sf - expected_renewal_sf

            # Calculate TI and LC costs
            avg_ti_psf = self.DEFAULT_TI_PSF.get(property.property_type, 25.0)
            avg_lc_pct = self.DEFAULT_LC_PCT.get(property.property_type, 0.06)

            # Renewals typically get lower TI (50% of new tenant)
            renewal_ti_cost = expected_renewal_sf * (avg_ti_psf * 0.5)
            renewal_lc_cost = expected_renewal_sf * property.market_rent_psf * (avg_lc_pct * 0.5)

            # New tenants get full TI/LC
            new_tenant_ti_cost = expected_backfill_sf * avg_ti_psf
            new_tenant_lc_cost = expected_backfill_sf * property.market_rent_psf * avg_lc_pct

            total_ti_lc_cost = renewal_ti_cost + renewal_lc_cost + new_tenant_ti_cost + new_tenant_lc_cost

            # Downtime loss (only for non-renewals)
            downtime_loss = (expected_backfill_sf * property.market_rent_psf * property.downtime_months / 12)

            record = {
                "year": year,
                "year_start": year_start,
                "year_end": year_end,
                "expiring_lease_count": len(expiring_leases),
                "expiring_sf": expiring_sf,
                "expiring_rent": expiring_rent,
                "expiring_pct_of_total": expiring_sf / property.total_sf if property.total_sf > 0 else 0.0,
                "expected_renewal_sf": expected_renewal_sf,
                "expected_backfill_sf": expected_backfill_sf,
                "renewal_ti_cost": renewal_ti_cost,
                "renewal_lc_cost": renewal_lc_cost,
                "new_tenant_ti_cost": new_tenant_ti_cost,
                "new_tenant_lc_cost": new_tenant_lc_cost,
                "total_ti_lc_cost": total_ti_lc_cost,
                "downtime_loss": downtime_loss,
                "total_rollover_cost": total_ti_lc_cost + downtime_loss
            }

            records.append(record)

        df = pd.DataFrame(records)

        return df

    def calculate_tenant_concentration_risk(self, property: CREProperty) -> Dict:
        """Calculate tenant concentration risk

        Args:
            property: CRE property

        Returns:
            Dict with concentration metrics
        """

        if not property.leases:
            return {"hhi_index": 0.0, "top_tenant_pct": 0.0, "top_3_tenants_pct": 0.0}

        # Calculate rent by tenant
        tenant_rents = {}
        total_rent = 0.0

        for lease in property.leases:
            if lease.occupied:
                rent = lease.base_rent_psf_annual * lease.leased_sf
                tenant_rents[lease.tenant_name] = tenant_rents.get(lease.tenant_name, 0.0) + rent
                total_rent += rent

        # Calculate market shares
        market_shares = [rent / total_rent for rent in tenant_rents.values()] if total_rent > 0 else []

        # Herfindahl-Hirschman Index (HHI)
        # 0-0.15: Low concentration, 0.15-0.25: Moderate, >0.25: High
        hhi_index = sum(share ** 2 for share in market_shares)

        # Top tenant concentration
        sorted_shares = sorted(market_shares, reverse=True)
        top_tenant_pct = sorted_shares[0] if len(sorted_shares) > 0 else 0.0
        top_3_tenants_pct = sum(sorted_shares[:3]) if len(sorted_shares) >= 3 else sum(sorted_shares)

        risk = {
            "hhi_index": hhi_index,
            "top_tenant_pct": top_tenant_pct,
            "top_3_tenants_pct": top_3_tenants_pct,
            "tenant_count": len(tenant_rents),
            "concentration_risk": "High" if hhi_index > 0.25 else "Moderate" if hhi_index > 0.15 else "Low"
        }

        logger.info(f"Tenant concentration: HHI={hhi_index:.3f}, Top tenant={top_tenant_pct:.1%}")

        return risk

    def calculate_credit_weighted_vacancy(self, property: CREProperty) -> float:
        """Calculate vacancy rate weighted by tenant credit

        Lower credit tenants have higher implied vacancy risk

        Args:
            property: CRE property

        Returns:
            Credit-weighted vacancy rate
        """

        # Default rates by credit rating
        DEFAULT_RATES = {
            TenantCreditRating.AAA: 0.005,
            TenantCreditRating.AA: 0.01,
            TenantCreditRating.A: 0.015,
            TenantCreditRating.BBB: 0.025,
            TenantCreditRating.BB: 0.05,
            TenantCreditRating.B: 0.10,
            TenantCreditRating.CCC: 0.20,
            TenantCreditRating.UNRATED: 0.08  # Assume BB equivalent
        }

        weighted_vacancy = 0.0
        total_rent = 0.0

        for lease in property.leases:
            if lease.occupied:
                rent = lease.base_rent_psf_annual * lease.leased_sf
                default_rate = DEFAULT_RATES.get(lease.credit_rating, 0.08)
                weighted_vacancy += rent * default_rate
                total_rent += rent

        credit_weighted_vacancy_rate = weighted_vacancy / total_rent if total_rent > 0 else 0.05

        return credit_weighted_vacancy_rate


# ============================================================================
# Convenience Functions
# ============================================================================

def value_cre_property_simple(
    property_data: Dict,
    holding_period_years: int = 10,
    exit_cap_rate: float = 0.065
) -> Dict:
    """Simple CRE valuation from property data dict

    Args:
        property_data: Property data from database
        holding_period_years: Investment horizon
        exit_cap_rate: Exit cap rate

    Returns:
        Dict with valuation summary
    """

    # Build CREProperty from dict
    property_type = PropertyType(property_data.get("property_type", "office"))

    leases = []
    if "leases" in property_data:
        for lease_data in property_data["leases"]:
            leases.append(Lease(
                lease_id=lease_data["lease_id"],
                tenant_name=lease_data["tenant_name"],
                suite_number=lease_data.get("suite_number", ""),
                leased_sf=lease_data["leased_sf"],
                lease_start_date=datetime.fromisoformat(lease_data["lease_start_date"]),
                lease_end_date=datetime.fromisoformat(lease_data["lease_end_date"]),
                lease_term_months=lease_data["lease_term_months"],
                base_rent_psf_annual=lease_data["base_rent_psf_annual"],
                annual_escalation_pct=lease_data.get("annual_escalation_pct", 0.03),
                credit_rating=TenantCreditRating(lease_data.get("credit_rating", "unrated")),
                renewal_probability=lease_data.get("renewal_probability", 0.65)
            ))

    property = CREProperty(
        property_id=property_data["property_id"],
        property_name=property_data.get("property_name", "Unknown"),
        address=property_data.get("address", ""),
        property_type=property_type,
        total_sf=property_data["total_sf"],
        year_built=property_data["year_built"],
        leases=leases,
        occupied_sf=property_data.get("occupied_sf", 0.0),
        vacant_sf=property_data.get("vacant_sf", 0.0),
        annual_opex_psf=property_data.get("annual_opex_psf", 8.0),
        annual_property_tax=property_data.get("annual_property_tax", 0.0),
        annual_insurance=property_data.get("annual_insurance", 0.0),
        market=property_data.get("market", "unknown"),
        market_rent_psf=property_data.get("market_rent_psf", 25.0),
        market_vacancy_rate=property_data.get("market_vacancy_rate", 0.10),
        market_rent_growth=property_data.get("market_rent_growth", 0.025)
    )

    # Value property
    engine = CREValuationEngine()
    result = engine.value_cre_property(
        property=property,
        holding_period_years=holding_period_years,
        exit_cap_rate=exit_cap_rate
    )

    # Convert to simple dict
    summary = {
        "property_id": property.property_id,
        "valuation_date": result.valuation_date.isoformat(),
        "valuation_method": "dcf_cre",
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
