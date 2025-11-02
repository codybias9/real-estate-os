"""
Wildfire Risk Assessment Integration

Integrates wildfire risk data from multiple sources:
- USGS Wildfire Hazard Potential (WHP)
- NOAA/NCDC wildfire history
- State fire hazard severity zones (California, etc.)
"""

import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import math

logger = logging.getLogger(__name__)


@dataclass
class WildfireRisk:
    """Wildfire risk assessment for a location"""
    risk_level: str  # very_low, low, moderate, high, very_high
    risk_score: float  # 0-1
    hazard_potential: str  # WHP classification
    fire_regime_group: Optional[int] = None  # 1-5
    distance_to_wildland: Optional[float] = None  # miles
    historical_fires_5yr: int = 0
    state_hazard_zone: Optional[str] = None  # CA: Moderate, High, Very High

    def get_insurance_multiplier(self) -> float:
        """Get insurance cost multiplier based on risk"""
        multipliers = {
            "very_low": 1.0,
            "low": 1.1,
            "moderate": 1.3,
            "high": 1.6,
            "very_high": 2.0
        }
        return multipliers.get(self.risk_level, 1.0)


class WildfireRiskService:
    """Service for assessing wildfire risk"""

    def __init__(self):
        # Fire Regime Groups (based on USGS classification)
        # 1: 0-35 year return, low severity
        # 2: 0-35 year return, high severity
        # 3: 35-100 year return, mixed severity
        # 4: 35-100 year return, high severity
        # 5: 100+ year return, high severity
        self.regime_risk_scores = {
            1: 0.3,
            2: 0.6,
            3: 0.5,
            4: 0.7,
            5: 0.4
        }

    def assess_wildfire_risk(
        self,
        latitude: float,
        longitude: float,
        state: str
    ) -> WildfireRisk:
        """
        Assess wildfire risk for a location

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            state: State code (for state-specific data)

        Returns:
            WildfireRisk object
        """
        logger.info(f"Assessing wildfire risk for ({latitude}, {longitude})")

        # Calculate distance to wildland interface
        # Simplified: actual implementation would use GIS data
        distance_to_wildland = self._estimate_wildland_distance(latitude, longitude, state)

        # Determine fire regime group based on location
        fire_regime = self._get_fire_regime_group(latitude, longitude, state)

        # Get state-specific hazard zone (California example)
        state_zone = None
        if state == "CA":
            state_zone = self._get_ca_fire_hazard_zone(latitude, longitude)

        # Calculate overall risk score
        risk_score = self._calculate_risk_score(
            distance_to_wildland=distance_to_wildland,
            fire_regime=fire_regime,
            state=state,
            state_zone=state_zone
        )

        # Classify risk level
        risk_level = self._classify_risk_level(risk_score)

        # Determine hazard potential
        hazard_potential = self._get_hazard_potential(risk_score)

        return WildfireRisk(
            risk_level=risk_level,
            risk_score=risk_score,
            hazard_potential=hazard_potential,
            fire_regime_group=fire_regime,
            distance_to_wildland=distance_to_wildland,
            historical_fires_5yr=0,  # Would query historical data
            state_hazard_zone=state_zone
        )

    def _estimate_wildland_distance(
        self,
        latitude: float,
        longitude: float,
        state: str
    ) -> float:
        """
        Estimate distance to wildland-urban interface

        Simplified implementation - real version would use GIS overlay
        """
        # High-risk states
        high_risk_states = ["CA", "OR", "WA", "CO", "MT", "ID", "NM", "AZ", "UT", "NV"]

        if state in high_risk_states:
            # Urban areas: typically farther from wildland
            # Rural areas: closer to wildland
            # Simplified distance estimation
            return 5.0  # 5 miles (example)
        else:
            return 10.0  # 10 miles (lower risk)

    def _get_fire_regime_group(
        self,
        latitude: float,
        longitude: float,
        state: str
    ) -> Optional[int]:
        """
        Get fire regime group for location

        Real implementation would query LANDFIRE data
        """
        # Western US: typically groups 1-4 (frequent fires)
        western_states = ["CA", "OR", "WA", "ID", "MT", "WY", "NV", "UT", "CO", "AZ", "NM"]

        if state in western_states:
            # Simplified: assign based on state
            if state in ["CA", "OR", "WA"]:
                return 2  # Frequent, high severity
            elif state in ["CO", "MT", "ID"]:
                return 3  # Moderate frequency, mixed severity
            else:
                return 4  # Moderate frequency, high severity
        else:
            # Eastern US: typically group 5 (infrequent fires)
            return 5

    def _get_ca_fire_hazard_zone(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[str]:
        """
        Get California Fire Hazard Severity Zone

        Real implementation would query CAL FIRE data
        """
        # Simplified classification based on latitude
        # Northern CA: higher risk
        # Coastal: moderate risk
        # Urban valleys: lower risk

        if latitude > 38.0:  # Northern CA
            return "High"
        elif latitude > 36.0:  # Central CA
            if longitude < -122.0:  # Coastal
                return "Moderate"
            else:  # Inland
                return "Very High"
        else:  # Southern CA
            if longitude < -118.5:  # Coastal LA/SD
                return "Moderate"
            else:  # Inland/desert
                return "High"

    def _calculate_risk_score(
        self,
        distance_to_wildland: float,
        fire_regime: Optional[int],
        state: str,
        state_zone: Optional[str]
    ) -> float:
        """
        Calculate composite wildfire risk score (0-1)
        """
        score = 0.0

        # Distance component (closer = higher risk)
        if distance_to_wildland < 1.0:
            distance_score = 1.0
        elif distance_to_wildland < 3.0:
            distance_score = 0.7
        elif distance_to_wildland < 5.0:
            distance_score = 0.5
        elif distance_to_wildland < 10.0:
            distance_score = 0.3
        else:
            distance_score = 0.1

        score += distance_score * 0.4  # 40% weight

        # Fire regime component
        if fire_regime:
            regime_score = self.regime_risk_scores.get(fire_regime, 0.3)
            score += regime_score * 0.3  # 30% weight

        # State-specific component
        state_risk_scores = {
            "CA": 0.8, "OR": 0.7, "WA": 0.7, "CO": 0.7, "MT": 0.6,
            "ID": 0.6, "NV": 0.6, "AZ": 0.7, "NM": 0.6, "UT": 0.6,
            "TX": 0.5, "OK": 0.4, "FL": 0.3
        }
        state_score = state_risk_scores.get(state, 0.2)
        score += state_score * 0.2  # 20% weight

        # State hazard zone component (if available)
        if state_zone:
            zone_scores = {
                "Very High": 1.0,
                "High": 0.7,
                "Moderate": 0.4,
                "Low": 0.2
            }
            zone_score = zone_scores.get(state_zone, 0.3)
            score += zone_score * 0.1  # 10% weight
        else:
            score += 0.0  # No bonus/penalty if unknown

        # Normalize to 0-1
        return min(max(score, 0.0), 1.0)

    def _classify_risk_level(self, risk_score: float) -> str:
        """Classify numeric score into risk level"""
        if risk_score >= 0.8:
            return "very_high"
        elif risk_score >= 0.6:
            return "high"
        elif risk_score >= 0.4:
            return "moderate"
        elif risk_score >= 0.2:
            return "low"
        else:
            return "very_low"

    def _get_hazard_potential(self, risk_score: float) -> str:
        """Get USGS Wildfire Hazard Potential classification"""
        if risk_score >= 0.7:
            return "Very High"
        elif risk_score >= 0.5:
            return "High"
        elif risk_score >= 0.3:
            return "Moderate"
        else:
            return "Low"


def calculate_wildfire_impact_on_value(
    property_value: float,
    wildfire_risk: WildfireRisk
) -> Dict:
    """
    Calculate impact of wildfire risk on property value

    Args:
        property_value: Current property value
        wildfire_risk: WildfireRisk object

    Returns:
        Dictionary with value adjustments
    """
    # Research-based adjustments:
    # Very high risk: 10-20% value reduction
    # High risk: 5-10% reduction
    # Moderate risk: 2-5% reduction
    # Low/very low: minimal impact

    adjustments = {
        "very_high": -0.15,   # -15% average
        "high": -0.075,       # -7.5% average
        "moderate": -0.035,   # -3.5% average
        "low": -0.01,         # -1% average
        "very_low": 0.00      # No adjustment
    }

    adjustment_pct = adjustments.get(wildfire_risk.risk_level, -0.05)
    adjustment_amount = property_value * adjustment_pct
    adjusted_value = property_value + adjustment_amount

    # Insurance cost impact
    base_insurance = property_value * 0.003  # 0.3% of value baseline
    insurance_multiplier = wildfire_risk.get_insurance_multiplier()
    annual_insurance_cost = base_insurance * insurance_multiplier

    # Wildfire prevention costs (defensible space, etc.)
    prevention_costs = 0
    if wildfire_risk.risk_level in ["high", "very_high"]:
        prevention_costs = 2000  # Annual vegetation management, etc.

    return {
        "original_value": property_value,
        "wildfire_adjustment_pct": adjustment_pct,
        "wildfire_adjustment_amount": adjustment_amount,
        "adjusted_value": adjusted_value,
        "annual_insurance_cost": annual_insurance_cost,
        "annual_prevention_costs": prevention_costs,
        "total_annual_cost_impact": annual_insurance_cost + prevention_costs
    }


if __name__ == "__main__":
    # Test wildfire risk assessment
    logging.basicConfig(level=logging.INFO)

    service = WildfireRiskService()

    # Test 1: San Francisco (moderate risk)
    print("\nTest 1: San Francisco, CA")
    risk = service.assess_wildfire_risk(37.7749, -122.4194, "CA")
    print(f"  Risk Level: {risk.risk_level}")
    print(f"  Risk Score: {risk.risk_score:.2f}")
    print(f"  Hazard Potential: {risk.hazard_potential}")
    print(f"  CA Fire Zone: {risk.state_hazard_zone}")

    # Test 2: Paradise, CA (very high risk)
    print("\nTest 2: Paradise, CA (Camp Fire area)")
    risk = service.assess_wildfire_risk(39.7596, -121.6219, "CA")
    print(f"  Risk Level: {risk.risk_level}")
    print(f"  Risk Score: {risk.risk_score:.2f}")
    print(f"  Hazard Potential: {risk.hazard_potential}")
    print(f"  CA Fire Zone: {risk.state_hazard_zone}")

    # Test 3: Value impact
    print("\nTest 3: Value Impact Analysis")
    impact = calculate_wildfire_impact_on_value(600000, risk)
    print(f"  Original Value: ${impact['original_value']:,.0f}")
    print(f"  Adjustment: {impact['wildfire_adjustment_pct']:.1%}")
    print(f"  Adjusted Value: ${impact['adjusted_value']:,.0f}")
    print(f"  Annual Insurance: ${impact['annual_insurance_cost']:,.0f}")
    print(f"  Prevention Costs: ${impact['annual_prevention_costs']:,.0f}")
    print(f"  Total Annual Impact: ${impact['total_annual_cost_impact']:,.0f}")
