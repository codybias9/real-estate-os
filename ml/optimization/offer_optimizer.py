"""Offer Optimization using Mixed-Integer Programming
Maximizes utility subject to profit, cash, and risk constraints
"""

from ortools.linear_solver import pywraplp
from typing import Dict, List
import pickle
import numpy as np


class OfferOptimizer:
    """MIP-based offer optimization"""

    def __init__(self):
        # Load acceptance probability model
        try:
            with open("ml/models/offer_acceptance_model_v1.pkl", "rb") as f:
                self.acceptance_model = pickle.load(f)
        except FileNotFoundError:
            self.acceptance_model = None

    def optimize_offer(
        self,
        property_data: Dict,
        tenant_policy: Dict,
        market_regime: str
    ) -> Dict:
        """Optimize offer using MIP

        Args:
            property_data: Property details (arv, list_price, risk_score, etc.)
            tenant_policy: Tenant constraints and preferences
            market_regime: Current market regime (hot/warm/cool/cold)

        Returns:
            Optimal offer with decision variables and utility
        """

        solver = pywraplp.Solver.CreateSolver('SCIP')
        if not solver:
            raise Exception("SCIP solver not available")

        # ====================================================================
        # Decision Variables
        # ====================================================================

        # Price (continuous)
        price = solver.NumVar(
            property_data["arv"] * 0.70,  # Min 70% of ARV
            property_data["arv"] * 0.98,  # Max 98% of ARV
            'price'
        )

        # Earnest money (continuous)
        earnest = solver.NumVar(
            property_data["arv"] * 0.005,  # Min 0.5%
            property_data["arv"] * 0.03,   # Max 3%
            'earnest'
        )

        # Due diligence days (integer)
        dd_days = solver.IntVar(7, 30, 'dd_days')

        # Close days (integer)
        close_days = solver.IntVar(14, 60, 'close_days')

        # Contingencies (binary)
        inspection_contingency = solver.BoolVar('inspection')
        financing_contingency = solver.BoolVar('financing')
        appraisal_contingency = solver.BoolVar('appraisal')

        # Repair credit (continuous)
        repair_credit = solver.NumVar(0, 10000, 'repair_credit')

        # Escalation clause (binary)
        escalation_clause = solver.BoolVar('escalation')

        # ====================================================================
        # Constraints
        # ====================================================================

        # 1. Profit Margin Constraint
        rehab_budget = tenant_policy.get("rehab_budget", 20000)
        carry_costs = tenant_policy.get("carry_costs_per_month", 1500) * (close_days / 30.0)
        fees = property_data["arv"] * 0.08  # Closing costs, realtor fees

        # Linearized profit calculation (simplified)
        min_profit = property_data["arv"] * tenant_policy.get("min_margin", 0.15)
        solver.Add(
            property_data["arv"] - price - rehab_budget - carry_costs - fees >= min_profit
        )

        # 2. DSCR Constraint (for rental properties)
        if property_data.get("strategy") == "buy_and_hold":
            projected_rent = property_data.get("projected_rent_monthly", 0)
            if projected_rent > 0:
                noi_annual = projected_rent * 12 * 0.65  # 65% after opex
                ltv = tenant_policy.get("max_ltv", 0.75)
                interest_rate = tenant_policy.get("interest_rate", 0.05)

                # Simplified debt service (P&I only)
                # Monthly payment approximation: P * r * (1+r)^n / ((1+r)^n - 1)
                # For 30-year: ~0.0053 * loan_amount per month
                debt_service_monthly = price * ltv * 0.0053
                debt_service_annual = debt_service_monthly * 12

                # DSCR = NOI / Debt Service >= 1.25
                solver.Add(noi_annual >= 1.25 * debt_service_annual)

        # 3. Cash Constraint
        down_payment = price * (1 - tenant_policy.get("max_ltv", 0.75))
        total_cash_needed = down_payment + earnest + fees
        solver.Add(
            total_cash_needed <= tenant_policy.get("available_cash", 100000)
        )

        # 4. Hazard Constraint
        if property_data.get("flood_zone") in ["A", "AE", "V", "VE"]:
            # Cap price at 90% of ARV for high flood risk
            solver.Add(price <= property_data["arv"] * 0.90)

        if property_data.get("wildfire_risk_score", 0) > 0.7:
            solver.Add(price <= property_data["arv"] * 0.92)

        # 5. Regime Constraint
        regime_policies = {
            "hot": 0.98,
            "warm": 0.95,
            "cool": 0.90,
            "cold": 0.85
        }
        max_offer_pct = regime_policies.get(market_regime, 0.95)
        solver.Add(price <= property_data["list_price"] * max_offer_pct)

        # 6. Earnest as % of price
        solver.Add(earnest >= price * 0.005)
        solver.Add(earnest <= price * 0.03)

        # ====================================================================
        # Objective: Maximize Utility
        # ====================================================================

        # Estimate P(accept) using logistic model
        # For MIP, use linearized approximation or piecewise linear
        # Simplified: P(accept) ≈ sigmoid-like function of (price / list_price)

        offer_pct = price / property_data["list_price"]

        # Approximate acceptance probability (linear for MIP)
        # Real model would be logistic: 1 / (1 + exp(-k*(x - x0)))
        # Linear approximation: slope around x0=0.95
        # P(accept) ≈ 0.5 + 10 * (offer_pct - 0.95)
        # Clamped to [0, 1]

        # For now, use a simplified utility that MIP can handle
        # Utility = alpha * (price / list_price) + beta * profit - gamma * time - delta * risk

        # Profit (linearized)
        profit = property_data["arv"] - price - rehab_budget - fees

        # Time penalty
        time_penalty = close_days * tenant_policy.get("time_penalty_per_day", 10)

        # Risk penalty
        risk_penalty = property_data.get("risk_score", 0.5) * 1000

        # Utility weights
        alpha = tenant_policy.get("alpha", 0.3)  # Weight on acceptance
        beta = tenant_policy.get("beta", 0.5)    # Weight on profit
        gamma = tenant_policy.get("gamma", 0.1)  # Weight on time
        delta = tenant_policy.get("delta", 0.1)  # Weight on risk

        # Objective: Maximize utility
        # Note: For true P(accept), would need piecewise linear or MINLP
        utility = (
            alpha * (price / property_data["list_price"]) +
            beta * (profit / 10000) -  # Normalize
            gamma * (time_penalty / 100) -
            delta * risk_penalty
        )

        solver.Maximize(utility)

        # ====================================================================
        # Solve
        # ====================================================================

        status = solver.Solve()

        if status == pywraplp.Solver.OPTIMAL:
            # Extract solution
            solution = {
                "price": price.solution_value(),
                "earnest": earnest.solution_value(),
                "dd_days": int(dd_days.solution_value()),
                "close_days": int(close_days.solution_value()),
                "contingencies": {
                    "inspection": bool(inspection_contingency.solution_value()),
                    "financing": bool(financing_contingency.solution_value()),
                    "appraisal": bool(appraisal_contingency.solution_value())
                },
                "repair_credit": repair_credit.solution_value(),
                "escalation_clause": bool(escalation_clause.solution_value()),
                "expected_utility": solver.Objective().Value(),
                "offer_pct_of_list": price.solution_value() / property_data["list_price"],
                "estimated_profit": property_data["arv"] - price.solution_value() - rehab_budget - fees
            }

            # Calculate P(accept) with real model if available
            if self.acceptance_model:
                p_accept = self._calculate_acceptance_probability(
                    property_data,
                    solution,
                    market_regime
                )
                solution["p_accept"] = p_accept
                solution["expected_profit"] = solution["estimated_profit"] * p_accept

            return solution

        elif status == pywraplp.Solver.INFEASIBLE:
            raise Exception("No feasible offer found - constraints too tight")
        else:
            raise Exception(f"Solver failed with status: {status}")

    def generate_pareto_frontier(
        self,
        property_data: Dict,
        tenant_policy: Dict,
        market_regime: str,
        n_points: int = 10
    ) -> List[Dict]:
        """Generate Pareto frontier by varying alpha (acceptance weight)

        Returns multiple optimal offers trading off acceptance vs profit
        """

        pareto_offers = []

        # Sweep alpha from 0.1 to 0.9
        for alpha in np.linspace(0.1, 0.9, n_points):
            policy_copy = tenant_policy.copy()
            policy_copy["alpha"] = alpha
            policy_copy["beta"] = 1 - alpha  # Complementary weight on profit

            try:
                offer = self.optimize_offer(property_data, policy_copy, market_regime)
                offer["alpha"] = alpha
                pareto_offers.append(offer)
            except Exception as e:
                # Skip infeasible points
                pass

        return pareto_offers

    def _calculate_acceptance_probability(
        self,
        property_data: Dict,
        offer: Dict,
        market_regime: str
    ) -> float:
        """Calculate P(accept) using trained logistic model"""

        if not self.acceptance_model:
            # Fallback: simple heuristic
            offer_pct = offer["price"] / property_data["list_price"]
            return 1 / (1 + np.exp(-10 * (offer_pct - 0.95)))

        # Feature vector for acceptance model
        import pandas as pd

        regime_map = {"hot": 3, "warm": 2, "cool": 1, "cold": 0}

        features = pd.DataFrame([{
            "offer_pct_of_list": offer["price"] / property_data["list_price"],
            "earnest_pct": offer["earnest"] / offer["price"],
            "dd_days": offer["dd_days"],
            "close_days": offer["close_days"],
            "inspection_contingency": int(offer["contingencies"]["inspection"]),
            "financing_contingency": int(offer["contingencies"]["financing"]),
            "appraisal_contingency": int(offer["contingencies"]["appraisal"]),
            "repair_credit": offer["repair_credit"],
            "escalation_clause": int(offer["escalation_clause"]),
            "days_on_market": property_data.get("dom", 30),
            "market_regime_idx": regime_map.get(market_regime, 1)
        }])

        p_accept = self.acceptance_model.predict_proba(features)[0][1]
        return p_accept


# ============================================================================
# API Integration
# ============================================================================

def optimize_offer_api(property_id: str, tenant_id: str) -> Dict:
    """API endpoint wrapper for offer optimization"""

    from sqlalchemy.orm import Session
    from api.app.database import get_db
    from db.models_provenance import Property, Tenant

    db = next(get_db())

    # Fetch property
    property = db.query(Property).filter(
        Property.id == property_id,
        Property.tenant_id == tenant_id
    ).first()

    if not property:
        return {"error": "Property not found"}

    # Fetch tenant policy
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    tenant_policy = tenant.policy if tenant and hasattr(tenant, "policy") else {}

    # Default policy
    default_policy = {
        "rehab_budget": 20000,
        "carry_costs_per_month": 1500,
        "min_margin": 0.15,
        "max_ltv": 0.75,
        "interest_rate": 0.05,
        "available_cash": 100000,
        "time_penalty_per_day": 10,
        "alpha": 0.4,
        "beta": 0.5,
        "gamma": 0.05,
        "delta": 0.05
    }
    tenant_policy = {**default_policy, **tenant_policy}

    # Property data
    property_data = {
        "arv": property.arv_estimate or property.list_price * 1.1,
        "list_price": property.list_price,
        "risk_score": property.risk_score or 0.5,
        "flood_zone": property.flood_zone,
        "wildfire_risk_score": property.wildfire_risk_score or 0,
        "strategy": property.strategy or "flip",
        "projected_rent_monthly": property.projected_rent or 0,
        "dom": property.dom or 30
    }

    # Determine market regime (from regime service)
    market_regime = "warm"  # Placeholder

    # Optimize
    optimizer = OfferOptimizer()
    optimal_offer = optimizer.optimize_offer(property_data, tenant_policy, market_regime)

    # Generate Pareto frontier
    pareto = optimizer.generate_pareto_frontier(property_data, tenant_policy, market_regime, n_points=5)

    return {
        "optimal_offer": optimal_offer,
        "pareto_frontier": pareto,
        "property_id": property_id,
        "market_regime": market_regime
    }
