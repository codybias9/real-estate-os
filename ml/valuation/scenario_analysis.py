"""Scenario Analysis and Monte Carlo Simulation
Probabilistic DCF valuation with sensitivity analysis

Features:
- Monte Carlo simulation (10,000+ runs)
- Sensitivity analysis on key drivers
- Scenario comparison (base, optimistic, pessimistic)
- Value-at-Risk (VaR) and Conditional VaR
- Tornado charts for variable importance
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from scipy import stats
import logging

from .dcf_engine import DCFEngine, DCFAssumptions, DCFResult

logger = logging.getLogger(__name__)


@dataclass
class ScenarioAssumptions:
    """Scenario-specific assumptions"""
    scenario_name: str

    # Revenue assumptions
    rent_growth_annual: float
    vacancy_rate: float
    other_income_growth: float = 0.0

    # Expense assumptions
    expense_growth_annual: float
    opex_change_pct: float = 0.0  # Change from base

    # Market assumptions
    exit_cap_rate: float
    market_cap_rate: float = 0.05


@dataclass
class MonteCarloParameters:
    """Monte Carlo simulation parameters"""

    # Number of simulations
    n_simulations: int = 10000

    # Random variable distributions
    # Format: (mean, std_dev, distribution_type)
    rent_growth: Tuple[float, float, str] = (0.03, 0.015, "normal")  # 3% ± 1.5%
    expense_growth: Tuple[float, float, str] = (0.025, 0.01, "normal")
    vacancy_rate: Tuple[float, float, str] = (0.05, 0.02, "normal")
    exit_cap_rate: Tuple[float, float, str] = (0.055, 0.01, "normal")
    discount_rate: Tuple[float, float, str] = (0.12, 0.02, "normal")

    # Correlation matrix (optional)
    # Rent growth and exit cap rate are typically negatively correlated
    correlations: Optional[Dict[Tuple[str, str], float]] = None


@dataclass
class ScenarioResult:
    """Result from scenario analysis"""
    scenario_name: str
    base_assumptions: DCFAssumptions
    dcf_result: DCFResult

    # Key metrics
    npv: float
    irr: float
    equity_multiple: float
    direct_cap_value: float


@dataclass
class MonteCarloResult:
    """Result from Monte Carlo simulation"""

    # Simulated values
    npv_distribution: np.ndarray
    irr_distribution: np.ndarray
    equity_multiple_distribution: np.ndarray

    # Summary statistics
    npv_mean: float
    npv_std: float
    npv_percentiles: Dict[int, float]  # 5th, 25th, 50th, 75th, 95th

    irr_mean: float
    irr_std: float
    irr_percentiles: Dict[int, float]

    # Risk metrics
    npv_var_95: float  # Value at Risk (5th percentile)
    npv_cvar_95: float  # Conditional VaR (expected loss beyond VaR)
    probability_positive_npv: float

    # Sensitivity
    sensitivity_analysis: pd.DataFrame


class ScenarioAnalysisEngine:
    """Scenario analysis and Monte Carlo engine"""

    def __init__(self):
        self.dcf_engine = DCFEngine()

    def run_scenario_analysis(
        self,
        base_assumptions: DCFAssumptions,
        scenarios: List[ScenarioAssumptions]
    ) -> List[ScenarioResult]:
        """Run scenario analysis (base, optimistic, pessimistic)

        Args:
            base_assumptions: Base DCF assumptions
            scenarios: List of scenario assumptions

        Returns:
            List of scenario results
        """

        results = []

        for scenario in scenarios:
            # Create modified assumptions for this scenario
            modified_assumptions = DCFAssumptions(
                property_id=base_assumptions.property_id,
                valuation_date=base_assumptions.valuation_date,
                holding_period_years=base_assumptions.holding_period_years,

                # Revenue
                gross_potential_rent=base_assumptions.gross_potential_rent,
                vacancy_rate=scenario.vacancy_rate,
                concessions_rate=base_assumptions.concessions_rate,
                other_income=base_assumptions.other_income * (1 + scenario.other_income_growth),

                # Expenses
                opex_per_sf_annual=base_assumptions.opex_per_sf_annual * (1 + scenario.opex_change_pct),
                opex_pct_egi=base_assumptions.opex_pct_egi,
                property_tax_rate=base_assumptions.property_tax_rate,
                insurance_annual=base_assumptions.insurance_annual,
                utilities_annual=base_assumptions.utilities_annual,
                management_fee_pct=base_assumptions.management_fee_pct,

                # Reserves
                replacement_reserve_per_unit=base_assumptions.replacement_reserve_per_unit,
                ti_reserve_per_sf=base_assumptions.ti_reserve_per_sf,
                lc_reserve_per_sf=base_assumptions.lc_reserve_per_sf,

                # Growth
                rent_growth_annual=scenario.rent_growth_annual,
                expense_growth_annual=scenario.expense_growth_annual,

                # Debt
                loan_to_value=base_assumptions.loan_to_value,
                interest_rate=base_assumptions.interest_rate,
                amortization_years=base_assumptions.amortization_years,
                interest_only_years=base_assumptions.interest_only_years,

                # Exit
                exit_cap_rate=scenario.exit_cap_rate,
                selling_costs_pct=base_assumptions.selling_costs_pct,

                # Discount rate
                discount_rate=base_assumptions.discount_rate,

                # Physical
                rentable_sf=base_assumptions.rentable_sf,
                unit_count=base_assumptions.unit_count,

                # Market
                market_cap_rate=scenario.market_cap_rate
            )

            # Run DCF
            dcf_result = self.dcf_engine.calculate_dcf(modified_assumptions)

            result = ScenarioResult(
                scenario_name=scenario.scenario_name,
                base_assumptions=modified_assumptions,
                dcf_result=dcf_result,
                npv=dcf_result.npv,
                irr=dcf_result.irr,
                equity_multiple=dcf_result.equity_multiple,
                direct_cap_value=dcf_result.direct_cap_value
            )

            results.append(result)

            logger.info(f"Scenario '{scenario.scenario_name}': NPV=${result.npv:,.0f}, IRR={result.irr:.2%}")

        return results

    def run_monte_carlo(
        self,
        base_assumptions: DCFAssumptions,
        parameters: MonteCarloParameters
    ) -> MonteCarloResult:
        """Run Monte Carlo simulation

        Args:
            base_assumptions: Base DCF assumptions
            parameters: Monte Carlo parameters

        Returns:
            Monte Carlo result with distributions and risk metrics
        """

        n_sim = parameters.n_simulations

        # Initialize arrays for results
        npv_results = np.zeros(n_sim)
        irr_results = np.zeros(n_sim)
        equity_multiple_results = np.zeros(n_sim)

        # Generate random samples for each variable
        rent_growth_samples = self._sample_distribution(parameters.rent_growth, n_sim)
        expense_growth_samples = self._sample_distribution(parameters.expense_growth, n_sim)
        vacancy_rate_samples = self._sample_distribution(parameters.vacancy_rate, n_sim)
        exit_cap_rate_samples = self._sample_distribution(parameters.exit_cap_rate, n_sim)
        discount_rate_samples = self._sample_distribution(parameters.discount_rate, n_sim)

        # Apply correlations if specified
        if parameters.correlations:
            # For simplicity, apply correlation between rent growth and exit cap rate
            # (typically negative: higher growth → lower cap rates)
            corr_rent_cap = parameters.correlations.get(("rent_growth", "exit_cap_rate"), 0.0)
            if corr_rent_cap != 0.0:
                # Induce correlation using Cholesky decomposition
                exit_cap_rate_samples = self._correlate_samples(
                    rent_growth_samples,
                    exit_cap_rate_samples,
                    corr_rent_cap
                )

        # Run simulations
        logger.info(f"Running {n_sim:,} Monte Carlo simulations...")

        for i in range(n_sim):
            # Create assumptions for this simulation
            sim_assumptions = DCFAssumptions(
                property_id=base_assumptions.property_id,
                valuation_date=base_assumptions.valuation_date,
                holding_period_years=base_assumptions.holding_period_years,

                # Revenue
                gross_potential_rent=base_assumptions.gross_potential_rent,
                vacancy_rate=max(0.0, min(0.5, vacancy_rate_samples[i])),  # Clamp to [0, 0.5]
                concessions_rate=base_assumptions.concessions_rate,
                other_income=base_assumptions.other_income,

                # Expenses
                opex_per_sf_annual=base_assumptions.opex_per_sf_annual,
                opex_pct_egi=base_assumptions.opex_pct_egi,
                property_tax_rate=base_assumptions.property_tax_rate,
                insurance_annual=base_assumptions.insurance_annual,
                utilities_annual=base_assumptions.utilities_annual,
                management_fee_pct=base_assumptions.management_fee_pct,

                # Reserves
                replacement_reserve_per_unit=base_assumptions.replacement_reserve_per_unit,
                ti_reserve_per_sf=base_assumptions.ti_reserve_per_sf,
                lc_reserve_per_sf=base_assumptions.lc_reserve_per_sf,

                # Growth (randomized)
                rent_growth_annual=max(-0.05, min(0.15, rent_growth_samples[i])),  # Clamp to [-5%, 15%]
                expense_growth_annual=max(0.0, min(0.10, expense_growth_samples[i])),

                # Debt
                loan_to_value=base_assumptions.loan_to_value,
                interest_rate=base_assumptions.interest_rate,
                amortization_years=base_assumptions.amortization_years,
                interest_only_years=base_assumptions.interest_only_years,

                # Exit (randomized)
                exit_cap_rate=max(0.03, min(0.15, exit_cap_rate_samples[i])),  # Clamp to [3%, 15%]
                selling_costs_pct=base_assumptions.selling_costs_pct,

                # Discount rate (randomized)
                discount_rate=max(0.05, min(0.30, discount_rate_samples[i])),

                # Physical
                rentable_sf=base_assumptions.rentable_sf,
                unit_count=base_assumptions.unit_count,

                # Market
                market_cap_rate=base_assumptions.market_cap_rate
            )

            # Run DCF
            try:
                result = self.dcf_engine.calculate_dcf(sim_assumptions)
                npv_results[i] = result.npv
                irr_results[i] = result.irr
                equity_multiple_results[i] = result.equity_multiple
            except Exception as e:
                # If DCF fails, use NaN
                logger.warning(f"Simulation {i} failed: {e}")
                npv_results[i] = np.nan
                irr_results[i] = np.nan
                equity_multiple_results[i] = np.nan

        # Remove NaN results
        valid_mask = ~np.isnan(npv_results)
        npv_results = npv_results[valid_mask]
        irr_results = irr_results[valid_mask]
        equity_multiple_results = equity_multiple_results[valid_mask]

        logger.info(f"Completed {len(npv_results):,} valid simulations")

        # Calculate statistics
        npv_mean = np.mean(npv_results)
        npv_std = np.std(npv_results)
        npv_percentiles = {
            5: np.percentile(npv_results, 5),
            25: np.percentile(npv_results, 25),
            50: np.percentile(npv_results, 50),
            75: np.percentile(npv_results, 75),
            95: np.percentile(npv_results, 95)
        }

        irr_mean = np.mean(irr_results)
        irr_std = np.std(irr_results)
        irr_percentiles = {
            5: np.percentile(irr_results, 5),
            25: np.percentile(irr_results, 25),
            50: np.percentile(irr_results, 50),
            75: np.percentile(irr_results, 75),
            95: np.percentile(irr_results, 95)
        }

        # Risk metrics
        npv_var_95 = npv_percentiles[5]  # 5th percentile
        npv_cvar_95 = np.mean(npv_results[npv_results <= npv_var_95])  # Expected loss beyond VaR
        probability_positive_npv = np.sum(npv_results > 0) / len(npv_results)

        # Sensitivity analysis
        sensitivity_df = self._calculate_sensitivity(
            base_assumptions,
            npv_results,
            rent_growth_samples[valid_mask],
            expense_growth_samples[valid_mask],
            vacancy_rate_samples[valid_mask],
            exit_cap_rate_samples[valid_mask],
            discount_rate_samples[valid_mask]
        )

        result = MonteCarloResult(
            npv_distribution=npv_results,
            irr_distribution=irr_results,
            equity_multiple_distribution=equity_multiple_results,
            npv_mean=npv_mean,
            npv_std=npv_std,
            npv_percentiles=npv_percentiles,
            irr_mean=irr_mean,
            irr_std=irr_std,
            irr_percentiles=irr_percentiles,
            npv_var_95=npv_var_95,
            npv_cvar_95=npv_cvar_95,
            probability_positive_npv=probability_positive_npv,
            sensitivity_analysis=sensitivity_df
        )

        logger.info(f"Monte Carlo complete: NPV=${npv_mean:,.0f} ± ${npv_std:,.0f}, P(NPV>0)={probability_positive_npv:.1%}")

        return result

    def _sample_distribution(
        self,
        params: Tuple[float, float, str],
        n_samples: int
    ) -> np.ndarray:
        """Sample from a distribution

        Args:
            params: (mean, std_dev, distribution_type)
            n_samples: Number of samples

        Returns:
            Array of samples
        """

        mean, std_dev, dist_type = params

        if dist_type == "normal":
            return np.random.normal(mean, std_dev, n_samples)
        elif dist_type == "lognormal":
            # For lognormal, mean and std are for underlying normal
            return np.random.lognormal(np.log(mean), std_dev, n_samples)
        elif dist_type == "uniform":
            # Use std_dev as range
            return np.random.uniform(mean - std_dev, mean + std_dev, n_samples)
        elif dist_type == "triangular":
            # Triangular with mode at mean
            lower = mean - std_dev
            upper = mean + std_dev
            return np.random.triangular(lower, mean, upper, n_samples)
        else:
            raise ValueError(f"Unknown distribution type: {dist_type}")

    def _correlate_samples(
        self,
        x: np.ndarray,
        y: np.ndarray,
        correlation: float
    ) -> np.ndarray:
        """Induce correlation between two sample arrays

        Uses a simple linear combination approach

        Args:
            x: First sample array
            y: Second sample array (will be modified)
            correlation: Target correlation [-1, 1]

        Returns:
            Modified y array with induced correlation
        """

        # Standardize both arrays
        x_std = (x - np.mean(x)) / np.std(x)
        y_std = (y - np.mean(y)) / np.std(y)

        # Create correlated y using linear combination
        y_corr = correlation * x_std + np.sqrt(1 - correlation ** 2) * y_std

        # Rescale to original mean and std
        y_new = y_corr * np.std(y) + np.mean(y)

        return y_new

    def _calculate_sensitivity(
        self,
        base_assumptions: DCFAssumptions,
        npv_results: np.ndarray,
        rent_growth: np.ndarray,
        expense_growth: np.ndarray,
        vacancy_rate: np.ndarray,
        exit_cap_rate: np.ndarray,
        discount_rate: np.ndarray
    ) -> pd.DataFrame:
        """Calculate sensitivity of NPV to each variable

        Uses correlation as a measure of sensitivity

        Args:
            base_assumptions: Base assumptions
            npv_results: NPV results from Monte Carlo
            rent_growth: Rent growth samples
            expense_growth: Expense growth samples
            vacancy_rate: Vacancy rate samples
            exit_cap_rate: Exit cap rate samples
            discount_rate: Discount rate samples

        Returns:
            DataFrame with sensitivity metrics
        """

        # Calculate correlation between each variable and NPV
        correlations = {
            "rent_growth": np.corrcoef(rent_growth, npv_results)[0, 1],
            "expense_growth": np.corrcoef(expense_growth, npv_results)[0, 1],
            "vacancy_rate": np.corrcoef(vacancy_rate, npv_results)[0, 1],
            "exit_cap_rate": np.corrcoef(exit_cap_rate, npv_results)[0, 1],
            "discount_rate": np.corrcoef(discount_rate, npv_results)[0, 1]
        }

        # Create DataFrame sorted by absolute correlation
        records = []
        for variable, correlation in correlations.items():
            records.append({
                "variable": variable,
                "correlation": correlation,
                "abs_correlation": abs(correlation)
            })

        df = pd.DataFrame(records).sort_values("abs_correlation", ascending=False)

        return df

    def create_tornado_chart_data(
        self,
        base_assumptions: DCFAssumptions,
        variables: List[str] = None
    ) -> pd.DataFrame:
        """Create data for tornado chart (sensitivity analysis)

        For each variable, calculate NPV at -/+ 1 std dev

        Args:
            base_assumptions: Base DCF assumptions
            variables: Variables to analyze (default: all key variables)

        Returns:
            DataFrame with tornado chart data
        """

        if variables is None:
            variables = [
                "rent_growth_annual",
                "expense_growth_annual",
                "vacancy_rate",
                "exit_cap_rate",
                "discount_rate"
            ]

        # Calculate base case NPV
        base_result = self.dcf_engine.calculate_dcf(base_assumptions)
        base_npv = base_result.npv

        records = []

        for variable in variables:
            # Get base value
            base_value = getattr(base_assumptions, variable)

            # Calculate NPV at -1 std dev
            modified_assumptions_low = self._modify_assumption(base_assumptions, variable, -0.1)
            result_low = self.dcf_engine.calculate_dcf(modified_assumptions_low)
            npv_low = result_low.npv

            # Calculate NPV at +1 std dev
            modified_assumptions_high = self._modify_assumption(base_assumptions, variable, +0.1)
            result_high = self.dcf_engine.calculate_dcf(modified_assumptions_high)
            npv_high = result_high.npv

            # Calculate range
            npv_range = npv_high - npv_low

            records.append({
                "variable": variable,
                "base_value": base_value,
                "npv_low": npv_low,
                "npv_high": npv_high,
                "npv_range": npv_range,
                "impact_pct": (npv_high - npv_low) / base_npv if base_npv != 0 else 0.0
            })

        df = pd.DataFrame(records).sort_values("npv_range", ascending=False)

        return df

    def _modify_assumption(
        self,
        assumptions: DCFAssumptions,
        variable: str,
        change_pct: float
    ) -> DCFAssumptions:
        """Create modified assumptions with one variable changed

        Args:
            assumptions: Base assumptions
            variable: Variable name to modify
            change_pct: Percentage change (e.g., 0.1 = +10%)

        Returns:
            Modified DCFAssumptions
        """

        # Get current value
        current_value = getattr(assumptions, variable)

        # Calculate new value
        new_value = current_value * (1 + change_pct)

        # Create new assumptions with modified value
        modified = DCFAssumptions(
            property_id=assumptions.property_id,
            valuation_date=assumptions.valuation_date,
            holding_period_years=assumptions.holding_period_years,
            gross_potential_rent=assumptions.gross_potential_rent,
            vacancy_rate=assumptions.vacancy_rate,
            concessions_rate=assumptions.concessions_rate,
            other_income=assumptions.other_income,
            opex_per_sf_annual=assumptions.opex_per_sf_annual,
            opex_pct_egi=assumptions.opex_pct_egi,
            property_tax_rate=assumptions.property_tax_rate,
            insurance_annual=assumptions.insurance_annual,
            utilities_annual=assumptions.utilities_annual,
            management_fee_pct=assumptions.management_fee_pct,
            replacement_reserve_per_unit=assumptions.replacement_reserve_per_unit,
            ti_reserve_per_sf=assumptions.ti_reserve_per_sf,
            lc_reserve_per_sf=assumptions.lc_reserve_per_sf,
            rent_growth_annual=assumptions.rent_growth_annual,
            expense_growth_annual=assumptions.expense_growth_annual,
            loan_to_value=assumptions.loan_to_value,
            interest_rate=assumptions.interest_rate,
            amortization_years=assumptions.amortization_years,
            interest_only_years=assumptions.interest_only_years,
            exit_cap_rate=assumptions.exit_cap_rate,
            selling_costs_pct=assumptions.selling_costs_pct,
            discount_rate=assumptions.discount_rate,
            rentable_sf=assumptions.rentable_sf,
            unit_count=assumptions.unit_count,
            market_cap_rate=assumptions.market_cap_rate
        )

        # Set the modified variable
        setattr(modified, variable, new_value)

        return modified


# ============================================================================
# Convenience Functions
# ============================================================================

def create_standard_scenarios(base_assumptions: DCFAssumptions) -> List[ScenarioAssumptions]:
    """Create standard scenarios (base, optimistic, pessimistic)

    Args:
        base_assumptions: Base DCF assumptions

    Returns:
        List of 3 scenarios
    """

    scenarios = [
        ScenarioAssumptions(
            scenario_name="base",
            rent_growth_annual=base_assumptions.rent_growth_annual,
            vacancy_rate=base_assumptions.vacancy_rate,
            expense_growth_annual=base_assumptions.expense_growth_annual,
            exit_cap_rate=base_assumptions.exit_cap_rate,
            market_cap_rate=base_assumptions.market_cap_rate
        ),
        ScenarioAssumptions(
            scenario_name="optimistic",
            rent_growth_annual=base_assumptions.rent_growth_annual * 1.5,  # 50% higher growth
            vacancy_rate=base_assumptions.vacancy_rate * 0.7,  # 30% lower vacancy
            expense_growth_annual=base_assumptions.expense_growth_annual * 0.8,  # 20% lower expense growth
            exit_cap_rate=base_assumptions.exit_cap_rate * 0.9,  # 10% lower cap rate (higher value)
            market_cap_rate=base_assumptions.market_cap_rate
        ),
        ScenarioAssumptions(
            scenario_name="pessimistic",
            rent_growth_annual=base_assumptions.rent_growth_annual * 0.5,  # 50% lower growth
            vacancy_rate=base_assumptions.vacancy_rate * 1.5,  # 50% higher vacancy
            expense_growth_annual=base_assumptions.expense_growth_annual * 1.3,  # 30% higher expense growth
            exit_cap_rate=base_assumptions.exit_cap_rate * 1.2,  # 20% higher cap rate (lower value)
            market_cap_rate=base_assumptions.market_cap_rate
        )
    ]

    return scenarios
