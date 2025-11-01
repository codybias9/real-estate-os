"""DCF Engine
Core discounted cash flow valuation engine for income-producing properties

Supports:
- Multi-period cash flow projections (up to 10 years)
- NPV, IRR, equity multiple calculations
- DSCR, DCCR debt coverage metrics
- Scenario analysis with sensitivity
- Monte Carlo simulation for probabilistic outcomes
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from scipy.optimize import newton
import logging

logger = logging.getLogger(__name__)


@dataclass
class DCFAssumptions:
    """DCF input assumptions"""

    # Property basics
    property_id: str
    valuation_date: datetime
    holding_period_years: int = 10

    # Revenue assumptions
    gross_potential_rent: float  # Annual GPR at stabilization
    vacancy_rate: float = 0.05  # Physical + economic vacancy
    concessions_rate: float = 0.01  # Free rent, TI, etc.
    other_income: float = 0.0  # Parking, laundry, pet fees

    # Expense assumptions
    opex_per_sf_annual: float = 0.0  # Operating expenses per SF
    opex_pct_egi: float = 0.35  # Alternatively, as % of EGI
    property_tax_rate: float = 0.012  # As % of assessed value
    insurance_annual: float = 0.0
    utilities_annual: float = 0.0
    management_fee_pct: float = 0.03  # % of EGI

    # Reserves
    replacement_reserve_per_unit: float = 250.0  # Annual per unit
    ti_reserve_per_sf: float = 0.0  # Tenant improvements for CRE
    lc_reserve_per_sf: float = 0.0  # Leasing commissions for CRE

    # Growth assumptions
    rent_growth_annual: float = 0.03  # 3% annual rent growth
    expense_growth_annual: float = 0.025  # 2.5% annual expense growth

    # Debt assumptions
    loan_to_value: float = 0.70
    interest_rate: float = 0.055  # 5.5% annual
    amortization_years: int = 30
    interest_only_years: int = 0

    # Exit assumptions
    exit_cap_rate: float = 0.055
    selling_costs_pct: float = 0.02  # Broker, legal fees

    # Discount rate
    discount_rate: float = 0.12  # Required return on equity

    # Physical
    rentable_sf: float = 0.0
    unit_count: int = 0

    # Market
    market_cap_rate: float = 0.05
    market_rent_psf: Optional[float] = None


@dataclass
class CashFlowPeriod:
    """Cash flow for a single period"""
    year: int

    # Revenue
    gross_potential_rent: float
    vacancy_loss: float
    concessions: float
    other_income: float
    effective_gross_income: float

    # Expenses
    operating_expenses: float
    property_tax: float
    insurance: float
    utilities: float
    management_fee: float
    replacement_reserves: float
    ti_reserves: float
    lc_reserves: float
    total_expenses: float

    # NOI
    net_operating_income: float

    # Debt service
    debt_service: float
    principal_payment: float
    interest_payment: float

    # Cash flow
    cash_flow_before_tax: float

    # Exit (if applicable)
    exit_proceeds: float = 0.0
    selling_costs: float = 0.0

    # Debt metrics
    dscr: float = 0.0  # Debt service coverage ratio
    dccr: float = 0.0  # Debt coverage charge ratio


@dataclass
class DCFResult:
    """DCF valuation result"""

    # Valuation
    npv: float
    irr: float
    equity_multiple: float

    # Direct cap valuation
    stabilized_noi: float
    direct_cap_value: float

    # Debt metrics
    avg_dscr: float
    min_dscr: float
    loan_amount: float

    # Cash flows
    cash_flows: List[CashFlowPeriod]

    # Summary
    total_equity_invested: float
    total_cash_distributed: float

    # Assumptions used
    assumptions: DCFAssumptions

    # Metadata
    valuation_date: datetime
    calculated_at: datetime = field(default_factory=datetime.now)


class DCFEngine:
    """Core DCF calculation engine"""

    def __init__(self):
        pass

    def calculate_dcf(self, assumptions: DCFAssumptions) -> DCFResult:
        """Run full DCF valuation

        Args:
            assumptions: DCF input assumptions

        Returns:
            DCFResult with NPV, IRR, cash flows, and metrics
        """

        # Step 1: Project cash flows
        cash_flows = self._project_cash_flows(assumptions)

        # Step 2: Calculate valuation metrics
        npv = self._calculate_npv(cash_flows, assumptions)
        irr = self._calculate_irr(cash_flows, assumptions)
        equity_multiple = self._calculate_equity_multiple(cash_flows, assumptions)

        # Step 3: Calculate debt metrics
        avg_dscr = np.mean([cf.dscr for cf in cash_flows if cf.dscr > 0])
        min_dscr = min([cf.dscr for cf in cash_flows if cf.dscr > 0], default=0.0)

        # Step 4: Direct cap valuation (Year 1 stabilized NOI)
        stabilized_noi = cash_flows[0].net_operating_income
        direct_cap_value = stabilized_noi / assumptions.market_cap_rate

        # Step 5: Calculate equity invested
        total_equity_invested = direct_cap_value * (1 - assumptions.loan_to_value)

        # Step 6: Calculate total cash distributed
        total_cash_distributed = sum(cf.cash_flow_before_tax for cf in cash_flows)
        total_cash_distributed += cash_flows[-1].exit_proceeds  # Add exit proceeds

        result = DCFResult(
            npv=npv,
            irr=irr,
            equity_multiple=equity_multiple,
            stabilized_noi=stabilized_noi,
            direct_cap_value=direct_cap_value,
            avg_dscr=avg_dscr,
            min_dscr=min_dscr,
            loan_amount=direct_cap_value * assumptions.loan_to_value,
            cash_flows=cash_flows,
            total_equity_invested=total_equity_invested,
            total_cash_distributed=total_cash_distributed,
            assumptions=assumptions,
            valuation_date=assumptions.valuation_date
        )

        logger.info(f"DCF complete: NPV=${npv:,.0f}, IRR={irr:.2%}, EM={equity_multiple:.2f}x")

        return result

    def _project_cash_flows(self, assumptions: DCFAssumptions) -> List[CashFlowPeriod]:
        """Project cash flows for holding period

        Returns:
            List of CashFlowPeriod for each year
        """

        cash_flows = []

        # Calculate loan amount and debt service
        purchase_price = assumptions.gross_potential_rent / assumptions.market_cap_rate
        loan_amount = purchase_price * assumptions.loan_to_value
        annual_debt_service = self._calculate_debt_service(
            loan_amount=loan_amount,
            interest_rate=assumptions.interest_rate,
            amortization_years=assumptions.amortization_years,
            interest_only_years=assumptions.interest_only_years
        )

        for year in range(1, assumptions.holding_period_years + 1):
            # Revenue projections
            gpr = assumptions.gross_potential_rent * ((1 + assumptions.rent_growth_annual) ** (year - 1))
            vacancy_loss = gpr * assumptions.vacancy_rate
            concessions = gpr * assumptions.concessions_rate
            other_income = assumptions.other_income * ((1 + assumptions.rent_growth_annual) ** (year - 1))
            egi = gpr - vacancy_loss - concessions + other_income

            # Expense projections
            if assumptions.opex_per_sf_annual > 0 and assumptions.rentable_sf > 0:
                opex = assumptions.opex_per_sf_annual * assumptions.rentable_sf * (
                    (1 + assumptions.expense_growth_annual) ** (year - 1)
                )
            else:
                opex = egi * assumptions.opex_pct_egi * ((1 + assumptions.expense_growth_annual) ** (year - 1))

            property_tax = purchase_price * assumptions.property_tax_rate * (
                (1 + assumptions.expense_growth_annual) ** (year - 1)
            )

            insurance = assumptions.insurance_annual * ((1 + assumptions.expense_growth_annual) ** (year - 1))
            utilities = assumptions.utilities_annual * ((1 + assumptions.expense_growth_annual) ** (year - 1))
            management_fee = egi * assumptions.management_fee_pct

            # Reserves
            replacement_reserves = (
                assumptions.replacement_reserve_per_unit * assumptions.unit_count
                if assumptions.unit_count > 0 else 0
            )

            ti_reserves = assumptions.ti_reserve_per_sf * assumptions.rentable_sf if assumptions.rentable_sf > 0 else 0
            lc_reserves = assumptions.lc_reserve_per_sf * assumptions.rentable_sf if assumptions.rentable_sf > 0 else 0

            total_expenses = (
                opex + property_tax + insurance + utilities + management_fee +
                replacement_reserves + ti_reserves + lc_reserves
            )

            # NOI
            noi = egi - total_expenses

            # Debt service breakdown
            if year <= assumptions.interest_only_years:
                interest_payment = loan_amount * assumptions.interest_rate
                principal_payment = 0.0
            else:
                # Calculate remaining balance and split payment
                periods_elapsed = year - assumptions.interest_only_years - 1
                remaining_balance = self._calculate_loan_balance(
                    loan_amount=loan_amount,
                    interest_rate=assumptions.interest_rate,
                    amortization_years=assumptions.amortization_years,
                    periods_elapsed=periods_elapsed
                )
                interest_payment = remaining_balance * assumptions.interest_rate
                principal_payment = annual_debt_service - interest_payment

            # Cash flow
            cfbt = noi - annual_debt_service

            # Debt metrics
            dscr = noi / annual_debt_service if annual_debt_service > 0 else 0.0
            dccr = (noi - replacement_reserves - ti_reserves - lc_reserves) / annual_debt_service if annual_debt_service > 0 else 0.0

            # Exit proceeds (only in final year)
            exit_proceeds = 0.0
            selling_costs = 0.0

            if year == assumptions.holding_period_years:
                exit_value = noi / assumptions.exit_cap_rate
                selling_costs = exit_value * assumptions.selling_costs_pct

                # Calculate remaining loan balance
                remaining_balance = self._calculate_loan_balance(
                    loan_amount=loan_amount,
                    interest_rate=assumptions.interest_rate,
                    amortization_years=assumptions.amortization_years,
                    periods_elapsed=year - assumptions.interest_only_years
                )

                exit_proceeds = exit_value - selling_costs - remaining_balance

            period = CashFlowPeriod(
                year=year,
                gross_potential_rent=gpr,
                vacancy_loss=vacancy_loss,
                concessions=concessions,
                other_income=other_income,
                effective_gross_income=egi,
                operating_expenses=opex,
                property_tax=property_tax,
                insurance=insurance,
                utilities=utilities,
                management_fee=management_fee,
                replacement_reserves=replacement_reserves,
                ti_reserves=ti_reserves,
                lc_reserves=lc_reserves,
                total_expenses=total_expenses,
                net_operating_income=noi,
                debt_service=annual_debt_service,
                principal_payment=principal_payment,
                interest_payment=interest_payment,
                cash_flow_before_tax=cfbt,
                exit_proceeds=exit_proceeds,
                selling_costs=selling_costs,
                dscr=dscr,
                dccr=dccr
            )

            cash_flows.append(period)

        return cash_flows

    def _calculate_debt_service(
        self,
        loan_amount: float,
        interest_rate: float,
        amortization_years: int,
        interest_only_years: int = 0
    ) -> float:
        """Calculate annual debt service payment

        Args:
            loan_amount: Principal amount
            interest_rate: Annual interest rate
            amortization_years: Full amortization period
            interest_only_years: Number of interest-only years

        Returns:
            Annual debt service payment
        """

        if interest_only_years > 0:
            # After IO period, payment is based on remaining amortization
            effective_amortization = amortization_years - interest_only_years
        else:
            effective_amortization = amortization_years

        if effective_amortization <= 0:
            return loan_amount * interest_rate  # Interest only

        # Annual payment formula: P * [r(1+r)^n] / [(1+r)^n - 1]
        n = effective_amortization
        r = interest_rate

        if r == 0:
            return loan_amount / n

        payment = loan_amount * (r * (1 + r) ** n) / ((1 + r) ** n - 1)

        return payment

    def _calculate_loan_balance(
        self,
        loan_amount: float,
        interest_rate: float,
        amortization_years: int,
        periods_elapsed: int
    ) -> float:
        """Calculate remaining loan balance after periods_elapsed

        Args:
            loan_amount: Original principal
            interest_rate: Annual interest rate
            amortization_years: Amortization period
            periods_elapsed: Years elapsed

        Returns:
            Remaining balance
        """

        if periods_elapsed <= 0:
            return loan_amount

        if periods_elapsed >= amortization_years:
            return 0.0

        # Calculate payment
        payment = self._calculate_debt_service(loan_amount, interest_rate, amortization_years)

        # Remaining balance formula: P * [(1+r)^n - (1+r)^p] / [(1+r)^n - 1]
        n = amortization_years
        p = periods_elapsed
        r = interest_rate

        if r == 0:
            return loan_amount * (1 - p / n)

        remaining_balance = loan_amount * ((1 + r) ** n - (1 + r) ** p) / ((1 + r) ** n - 1)

        return remaining_balance

    def _calculate_npv(self, cash_flows: List[CashFlowPeriod], assumptions: DCFAssumptions) -> float:
        """Calculate Net Present Value

        Args:
            cash_flows: Projected cash flows
            assumptions: DCF assumptions

        Returns:
            NPV of equity cash flows
        """

        # Initial equity investment
        purchase_price = assumptions.gross_potential_rent / assumptions.market_cap_rate
        equity_invested = purchase_price * (1 - assumptions.loan_to_value)

        # Discount all cash flows
        pv_sum = 0.0
        for cf in cash_flows:
            total_cf = cf.cash_flow_before_tax

            # Add exit proceeds in final year
            if cf.year == assumptions.holding_period_years:
                total_cf += cf.exit_proceeds

            pv = total_cf / ((1 + assumptions.discount_rate) ** cf.year)
            pv_sum += pv

        npv = pv_sum - equity_invested

        return npv

    def _calculate_irr(self, cash_flows: List[CashFlowPeriod], assumptions: DCFAssumptions) -> float:
        """Calculate Internal Rate of Return

        Uses Newton's method to find the discount rate where NPV = 0

        Args:
            cash_flows: Projected cash flows
            assumptions: DCF assumptions

        Returns:
            IRR as decimal (e.g., 0.15 = 15%)
        """

        # Initial equity investment (negative cash flow at t=0)
        purchase_price = assumptions.gross_potential_rent / assumptions.market_cap_rate
        equity_invested = purchase_price * (1 - assumptions.loan_to_value)

        # Build cash flow array
        cf_array = [-equity_invested]  # t=0

        for cf in cash_flows:
            total_cf = cf.cash_flow_before_tax

            # Add exit proceeds in final year
            if cf.year == assumptions.holding_period_years:
                total_cf += cf.exit_proceeds

            cf_array.append(total_cf)

        # Define NPV function
        def npv_func(rate):
            return sum(cf / ((1 + rate) ** i) for i, cf in enumerate(cf_array))

        # Use Newton's method to solve for IRR
        try:
            irr = newton(npv_func, x0=assumptions.discount_rate, maxiter=100)
        except RuntimeError:
            # Fallback to simple iteration
            irr = self._irr_fallback(cf_array)

        return irr

    def _irr_fallback(self, cash_flows: List[float]) -> float:
        """Fallback IRR calculation using simple iteration"""

        best_rate = 0.0
        best_npv = float('inf')

        for rate in np.linspace(-0.5, 0.5, 1000):
            npv = sum(cf / ((1 + rate) ** i) for i, cf in enumerate(cash_flows))
            if abs(npv) < abs(best_npv):
                best_npv = npv
                best_rate = rate

        return best_rate

    def _calculate_equity_multiple(
        self,
        cash_flows: List[CashFlowPeriod],
        assumptions: DCFAssumptions
    ) -> float:
        """Calculate equity multiple (cash-on-cash return)

        Args:
            cash_flows: Projected cash flows
            assumptions: DCF assumptions

        Returns:
            Equity multiple (total distributed / total invested)
        """

        # Initial equity investment
        purchase_price = assumptions.gross_potential_rent / assumptions.market_cap_rate
        equity_invested = purchase_price * (1 - assumptions.loan_to_value)

        # Total cash distributed
        total_distributed = sum(cf.cash_flow_before_tax for cf in cash_flows)
        total_distributed += cash_flows[-1].exit_proceeds  # Add exit proceeds

        equity_multiple = total_distributed / equity_invested if equity_invested > 0 else 0.0

        return equity_multiple

    def to_dataframe(self, result: DCFResult) -> pd.DataFrame:
        """Convert DCF result to pandas DataFrame for analysis

        Args:
            result: DCF result

        Returns:
            DataFrame with cash flows by year
        """

        records = []

        for cf in result.cash_flows:
            record = {
                'Year': cf.year,
                'GPR': cf.gross_potential_rent,
                'Vacancy': -cf.vacancy_loss,
                'Concessions': -cf.concessions,
                'Other Income': cf.other_income,
                'EGI': cf.effective_gross_income,
                'OpEx': -cf.operating_expenses,
                'Property Tax': -cf.property_tax,
                'Insurance': -cf.insurance,
                'Utilities': -cf.utilities,
                'Management Fee': -cf.management_fee,
                'Replacement Reserves': -cf.replacement_reserves,
                'TI Reserves': -cf.ti_reserves,
                'LC Reserves': -cf.lc_reserves,
                'Total Expenses': -cf.total_expenses,
                'NOI': cf.net_operating_income,
                'Debt Service': -cf.debt_service,
                'Interest': -cf.interest_payment,
                'Principal': -cf.principal_payment,
                'CFBT': cf.cash_flow_before_tax,
                'Exit Proceeds': cf.exit_proceeds,
                'Selling Costs': -cf.selling_costs,
                'DSCR': cf.dscr,
                'DCCR': cf.dccr
            }

            records.append(record)

        df = pd.DataFrame(records)

        return df
