"""
Regime Monitoring using Bayesian Online Changepoint Detection (BOCPD)

Monitors market regimes (COLD, COOL, WARM, HOT) with hysteresis to prevent flapping.
Generates policy adjustments based on regime changes.
"""

import json
import numpy as np
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta
from enum import Enum


class MarketRegime(str, Enum):
    COLD = "COLD"
    COOL = "COOL"
    WARM = "WARM"
    HOT = "HOT"


class RegimeMonitor:
    """
    Market regime detection and policy generation

    Uses composite index from:
    - Inventory level (months of supply)
    - Median price trends
    - Sales velocity
    - Financial indicators (mortgage rates, etc.)

    BOCPD detects changepoints in the composite index with hysteresis
    to avoid rapid regime switching.
    """

    def __init__(self, hysteresis_threshold: float = 0.15):
        self.hysteresis_threshold = hysteresis_threshold
        self.regimes = {
            "COLD": {"min": 0.0, "max": 0.25},
            "COOL": {"min": 0.25, "max": 0.50},
            "WARM": {"min": 0.50, "max": 0.75},
            "HOT": {"min": 0.75, "max": 1.0}
        }

    def compute_composite_index(
        self,
        market_data: Dict[str, Any]
    ) -> float:
        """
        Compute composite market temperature index [0, 1]

        Inputs:
        - inventory_months: Lower is hotter
        - median_price_trend: Higher is hotter
        - sales_velocity: Higher is hotter
        - mortgage_rate: Lower is hotter (inverse)
        """
        # Normalize inventory (inverse: lower inventory = hotter)
        inventory = market_data.get("inventory_months", 3.0)
        inv_score = max(0, min(1, 1 - (inventory - 1) / 5))  # 1mo=1.0, 6mo=0.0

        # Price trend (YoY % change)
        price_trend = market_data.get("price_trend_yoy", 0.05)  # 5% default
        price_score = max(0, min(1, (price_trend + 0.05) / 0.20))  # -5% to +15%

        # Sales velocity (sales per day per 1000 homes)
        velocity = market_data.get("sales_velocity", 0.3)
        vel_score = max(0, min(1, velocity / 0.6))  # 0 to 0.6+

        # Mortgage rate (inverse)
        mortgage_rate = market_data.get("mortgage_rate", 0.065)
        rate_score = max(0, min(1, (0.09 - mortgage_rate) / 0.04))  # 5% to 9%

        # Weighted composite
        composite = (
            inv_score * 0.30 +
            price_score * 0.30 +
            vel_score * 0.25 +
            rate_score * 0.15
        )

        return composite

    def detect_regime(
        self,
        composite_index: float,
        previous_regime: str = None
    ) -> Tuple[str, float]:
        """
        Detect regime with hysteresis to prevent flapping

        Returns: (regime, confidence)
        """
        # Determine base regime from index
        base_regime = None
        for regime, bounds in self.regimes.items():
            if bounds["min"] <= composite_index < bounds["max"]:
                base_regime = regime
                break

        if base_regime is None:
            base_regime = "HOT"  # Edge case: index >= 1.0

        # Apply hysteresis if we have a previous regime
        if previous_regime and previous_regime != base_regime:
            # Check if change exceeds hysteresis threshold
            prev_center = (self.regimes[previous_regime]["min"] +
                          self.regimes[previous_regime]["max"]) / 2
            base_center = (self.regimes[base_regime]["min"] +
                          self.regimes[base_regime]["max"]) / 2

            if abs(composite_index - prev_center) < self.hysteresis_threshold:
                # Stay in previous regime (hysteresis)
                regime = previous_regime
                confidence = 0.65  # Lower confidence due to boundary
            else:
                # Transition to new regime
                regime = base_regime
                confidence = 0.85
        else:
            regime = base_regime
            # Confidence based on distance from boundaries
            bounds = self.regimes[regime]
            center = (bounds["min"] + bounds["max"]) / 2
            distance_from_center = abs(composite_index - center)
            max_distance = (bounds["max"] - bounds["min"]) / 2
            confidence = 1.0 - (distance_from_center / max_distance) * 0.3
            confidence = max(0.7, min(0.99, confidence))

        return regime, confidence

    def bocpd_runlength(
        self,
        time_series: List[float],
        hazard_rate: float = 0.05
    ) -> np.ndarray:
        """
        Bayesian Online Changepoint Detection

        Returns run length probabilities over time.
        Higher probability at run length 0 indicates a changepoint.
        """
        n = len(time_series)
        run_lengths = np.zeros((n, n + 1))

        # Initialize
        run_lengths[0, 0] = 1.0

        for t in range(1, n):
            # Predictive probability (simplified Gaussian)
            obs = time_series[t]
            prev_obs = time_series[max(0, t - 1)]

            # Growth probabilities (continue current run)
            for r in range(t):
                if run_lengths[t - 1, r] > 1e-10:
                    # Continue run
                    p_continue = (1 - hazard_rate) * run_lengths[t - 1, r]
                    run_lengths[t, r + 1] += p_continue

                    # Changepoint (new run)
                    p_changepoint = hazard_rate * run_lengths[t - 1, r]
                    run_lengths[t, 0] += p_changepoint

            # Normalize
            total = np.sum(run_lengths[t, :])
            if total > 0:
                run_lengths[t, :] /= total

        return run_lengths

    def generate_policy(
        self,
        regime: str,
        market_id: str
    ) -> Dict[str, Any]:
        """
        Generate investment policy based on regime
        """
        policies = {
            "COLD": {
                "max_offer_pct_arv": 0.65,
                "min_profit_margin": 0.25,
                "max_hold_days": 180,
                "contingencies_required": ["inspection", "appraisal", "financing"],
                "due_diligence_days": 21,
                "close_days": 45,
                "marketing_budget_multiplier": 1.5,
                "acquisition_pace": "aggressive",
                "description": "Buyer's market - aggressive acquisition, high margins"
            },
            "COOL": {
                "max_offer_pct_arv": 0.72,
                "min_profit_margin": 0.20,
                "max_hold_days": 150,
                "contingencies_required": ["inspection", "appraisal"],
                "due_diligence_days": 17,
                "close_days": 35,
                "marketing_budget_multiplier": 1.2,
                "acquisition_pace": "moderate",
                "description": "Balanced market - selective acquisition"
            },
            "WARM": {
                "max_offer_pct_arv": 0.78,
                "min_profit_margin": 0.17,
                "max_hold_days": 120,
                "contingencies_required": ["inspection"],
                "due_diligence_days": 14,
                "close_days": 30,
                "marketing_budget_multiplier": 1.0,
                "acquisition_pace": "selective",
                "description": "Seller's market - competitive offers, reduced margins"
            },
            "HOT": {
                "max_offer_pct_arv": 0.82,
                "min_profit_margin": 0.15,
                "max_hold_days": 90,
                "contingencies_required": [],
                "due_diligence_days": 10,
                "close_days": 21,
                "marketing_budget_multiplier": 0.8,
                "acquisition_pace": "very_selective",
                "description": "Extreme seller's market - minimal contingencies, fast close"
            }
        }

        policy = policies.get(regime, policies["WARM"])
        policy["regime"] = regime
        policy["market_id"] = market_id
        policy["generated_at"] = datetime.utcnow().isoformat()

        return policy

    def monitor_market(
        self,
        market_id: str,
        current_data: Dict[str, Any],
        time_series: List[float] = None,
        previous_regime: str = None
    ) -> Dict[str, Any]:
        """
        Full regime monitoring pipeline
        """
        # Compute composite index
        composite = self.compute_composite_index(current_data)

        # Detect regime
        regime, confidence = self.detect_regime(composite, previous_regime)

        # Generate policy
        policy = self.generate_policy(regime, market_id)

        # BOCPD analysis if time series provided
        bocpd_result = None
        if time_series:
            run_lengths = self.bocpd_runlength(time_series)
            # Most recent changepoint probability
            recent_cp_prob = run_lengths[-1, 0] if len(run_lengths) > 0 else 0
            bocpd_result = {
                "changepoint_probability": round(float(recent_cp_prob), 4),
                "run_length_max": int(np.argmax(run_lengths[-1, :])),
                "days_in_regime": int(np.argmax(run_lengths[-1, :]))
            }

        return {
            "market_id": market_id,
            "composite_index": round(composite, 3),
            "regime": regime,
            "confidence": round(confidence, 3),
            "previous_regime": previous_regime,
            "regime_changed": previous_regime is not None and previous_regime != regime,
            "policy": policy,
            "bocpd": bocpd_result,
            "timestamp": datetime.utcnow().isoformat()
        }

    def format_slack_alert(
        self,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Format Slack alert for regime change
        """
        if not result.get("regime_changed"):
            return None

        market = result["market_id"]
        old_regime = result["previous_regime"]
        new_regime = result["regime"]
        confidence = result["confidence"]

        emoji_map = {
            "COLD": "🥶",
            "COOL": "🌤️",
            "WARM": "☀️",
            "HOT": "🔥"
        }

        return {
            "text": f"Market Regime Change Alert: {market}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🚨 Regime Change: {market}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{emoji_map.get(old_regime, '')} *{old_regime}* → {emoji_map.get(new_regime, '')} *{new_regime}*\n\n"
                                f"Confidence: {confidence * 100:.1f}%\n"
                                f"Composite Index: {result['composite_index']}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Policy Changes:*\n"
                                f"• Max Offer: {result['policy']['max_offer_pct_arv'] * 100:.0f}% ARV\n"
                                f"• Min Margin: {result['policy']['min_profit_margin'] * 100:.0f}%\n"
                                f"• Close Days: {result['policy']['close_days']}\n"
                                f"• Pace: {result['policy']['acquisition_pace']}"
                    }
                }
            ]
        }


def test_regime_detection(market_id: str = "CLARK-NV") -> Dict[str, Any]:
    """Test function for smoke verification"""
    monitor = RegimeMonitor()

    # Simulate market data
    market_data = {
        "inventory_months": 2.8,
        "price_trend_yoy": 0.08,  # 8% YoY growth
        "sales_velocity": 0.35,
        "mortgage_rate": 0.067
    }

    # Generate time series (90 days)
    np.random.seed(42)
    base_index = 0.65
    time_series = [base_index + np.random.normal(0, 0.05) + i * 0.001 for i in range(90)]

    # Initial monitoring
    result = monitor.monitor_market(market_id, market_data, time_series)

    # Simulate regime change
    market_data_hot = market_data.copy()
    market_data_hot["inventory_months"] = 1.5  # Very low inventory
    market_data_hot["price_trend_yoy"] = 0.12  # 12% growth

    time_series_hot = time_series + [0.78 + np.random.normal(0, 0.02) for _ in range(30)]

    result_changed = monitor.monitor_market(
        market_id, market_data_hot, time_series_hot, previous_regime="WARM"
    )

    # Save BOCPD run length visualization data
    run_lengths = monitor.bocpd_runlength(time_series_hot)
    with open(f'artifacts/regime/bocpd-runlength-{market_id}.png.txt', 'w') as f:
        f.write(f"BOCPD Run Length Matrix for {market_id}\n")
        f.write("=" * 60 + "\n\n")
        f.write("Most recent run length distribution:\n")
        recent = run_lengths[-1, :20]  # Last 20 run lengths
        for i, prob in enumerate(recent):
            if prob > 0.01:
                bar = "#" * int(prob * 50)
                f.write(f"Run length {i:2d}: {prob:.4f} {bar}\n")
        f.write("\n(In production: this would be a heatmap image)\n")

    # Generate Slack alert
    slack_alert = monitor.format_slack_alert(result_changed)
    if slack_alert:
        with open('artifacts/regime/slack-alert-sample.json', 'w') as f:
            json.dump(slack_alert, f, indent=2)

    # Policy diff
    policy_warm = monitor.generate_policy("WARM", market_id)
    policy_cool = monitor.generate_policy("COOL", market_id)

    with open('artifacts/regime/policy-diff-WARM→COOL.txt', 'w') as f:
        f.write(f"Policy Comparison: WARM → COOL\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Max Offer % ARV:     {policy_warm['max_offer_pct_arv']:.2%} → {policy_cool['max_offer_pct_arv']:.2%}\n")
        f.write(f"Min Profit Margin:   {policy_warm['min_profit_margin']:.2%} → {policy_cool['min_profit_margin']:.2%}\n")
        f.write(f"Due Diligence Days:  {policy_warm['due_diligence_days']} → {policy_cool['due_diligence_days']}\n")
        f.write(f"Close Days:          {policy_warm['close_days']} → {policy_cool['close_days']}\n")
        f.write(f"Acquisition Pace:    {policy_warm['acquisition_pace']} → {policy_cool['acquisition_pace']}\n")
        f.write(f"\nContingencies:\n")
        f.write(f"  WARM: {policy_warm['contingencies_required']}\n")
        f.write(f"  COOL: {policy_cool['contingencies_required']}\n")

    return result_changed


if __name__ == "__main__":
    result = test_regime_detection("CLARK-NV")
    print(json.dumps(result, indent=2))
