"""
FEMA National Flood Hazard Layer (NFHL) Integration

This module integrates FEMA flood zone data to assess flood risk for properties.
Data source: FEMA Map Service Center API
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
import requests
from dataclasses import dataclass
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# FEMA API configuration
FEMA_API_BASE = "https://hazards.fema.gov/gis/nfhl/services/public/NFHL/MapServer"
FEMA_FLOOD_ZONES_LAYER = "28"  # S_FLD_HAZ_AR layer


@dataclass
class FloodZone:
    """FEMA flood zone information"""
    zone_type: str  # A, AE, AO, X, etc.
    zone_subtype: Optional[str] = None
    flood_risk: str = "unknown"  # low, moderate, high
    base_flood_elevation: Optional[float] = None
    annual_chance: Optional[str] = None  # "1%", "0.2%", etc.
    insurance_required: bool = False

    def get_risk_score(self) -> float:
        """
        Calculate numeric risk score (0-1)

        Returns:
            Float between 0 (lowest risk) and 1 (highest risk)
        """
        risk_mapping = {
            "low": 0.1,
            "moderate": 0.5,
            "high": 0.9,
            "very_high": 1.0,
            "unknown": 0.3  # Conservative default
        }
        return risk_mapping.get(self.flood_risk, 0.3)


class FEMAFloodService:
    """Service for querying FEMA flood zone data"""

    def __init__(self):
        self.base_url = FEMA_API_BASE
        self.session = requests.Session()

    def get_flood_zone_by_coordinates(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[FloodZone]:
        """
        Get flood zone for a specific location

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate

        Returns:
            FloodZone object or None if not in flood zone
        """
        logger.info(f"Querying FEMA flood zone for ({latitude}, {longitude})")

        # Query FEMA Map Service
        # Using identify operation to get flood zone at point
        url = f"{self.base_url}/identify"

        params = {
            "geometry": f"{longitude},{latitude}",
            "geometryType": "esriGeometryPoint",
            "layers": f"all:{FEMA_FLOOD_ZONES_LAYER}",
            "mapExtent": f"{longitude-0.01},{latitude-0.01},{longitude+0.01},{latitude+0.01}",
            "imageDisplay": "400,400,96",
            "returnGeometry": "false",
            "f": "json"
        }

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "results" in data and len(data["results"]) > 0:
                # Parse first result
                result = data["results"][0]
                attributes = result.get("attributes", {})

                zone_type = attributes.get("FLD_ZONE", "X")
                zone_subtype = attributes.get("ZONE_SUBTY")

                flood_zone = self._parse_flood_zone(zone_type, zone_subtype, attributes)

                logger.info(f"Found flood zone: {flood_zone.zone_type} (risk: {flood_zone.flood_risk})")
                return flood_zone
            else:
                # Not in a mapped flood zone - assume minimal risk
                logger.info("Location not in FEMA flood zone (minimal risk)")
                return FloodZone(
                    zone_type="X",
                    flood_risk="low",
                    insurance_required=False
                )

        except requests.exceptions.RequestException as e:
            logger.error(f"FEMA API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing FEMA response: {e}")
            return None

    def _parse_flood_zone(
        self,
        zone_type: str,
        zone_subtype: Optional[str],
        attributes: Dict
    ) -> FloodZone:
        """Parse FEMA flood zone attributes"""

        # Determine risk level based on zone type
        # Reference: https://www.fema.gov/flood-zones

        high_risk_zones = ["A", "AE", "A1-30", "AH", "AO", "AR", "V", "VE", "V1-30"]
        moderate_risk_zones = ["B", "X500"]  # 0.2% annual chance (500-year)
        low_risk_zones = ["C", "X"]

        if zone_type in high_risk_zones:
            flood_risk = "high"
            annual_chance = "1%"  # 100-year flood
            insurance_required = True
        elif zone_type in moderate_risk_zones:
            flood_risk = "moderate"
            annual_chance = "0.2%"  # 500-year flood
            insurance_required = False
        elif zone_type in low_risk_zones:
            flood_risk = "low"
            annual_chance = "<0.2%"
            insurance_required = False
        else:
            flood_risk = "unknown"
            annual_chance = None
            insurance_required = False

        # Extract base flood elevation if available
        bfe = attributes.get("STATIC_BFE")
        base_flood_elevation = float(bfe) if bfe and bfe != "0" else None

        return FloodZone(
            zone_type=zone_type,
            zone_subtype=zone_subtype,
            flood_risk=flood_risk,
            base_flood_elevation=base_flood_elevation,
            annual_chance=annual_chance,
            insurance_required=insurance_required
        )

    def batch_get_flood_zones(
        self,
        coordinates: List[Tuple[float, float]]
    ) -> List[Optional[FloodZone]]:
        """
        Get flood zones for multiple locations

        Args:
            coordinates: List of (latitude, longitude) tuples

        Returns:
            List of FloodZone objects (same order as input)
        """
        results = []

        for lat, lon in coordinates:
            flood_zone = self.get_flood_zone_by_coordinates(lat, lon)
            results.append(flood_zone)

        return results


# Helper functions for database integration

def enrich_property_with_flood_data(
    property_id: str,
    latitude: float,
    longitude: float
) -> Dict:
    """
    Enrich property with FEMA flood data

    Args:
        property_id: Property identifier
        latitude: Property latitude
        longitude: Property longitude

    Returns:
        Dictionary with flood data fields
    """
    service = FEMAFloodService()
    flood_zone = service.get_flood_zone_by_coordinates(latitude, longitude)

    if flood_zone:
        return {
            "property_id": property_id,
            "flood_zone_type": flood_zone.zone_type,
            "flood_zone_subtype": flood_zone.zone_subtype,
            "flood_risk": flood_zone.flood_risk,
            "flood_risk_score": flood_zone.get_risk_score(),
            "flood_insurance_required": flood_zone.insurance_required,
            "base_flood_elevation": flood_zone.base_flood_elevation,
            "annual_flood_chance": flood_zone.annual_chance,
            "data_source": "FEMA NFHL",
            "updated_at": datetime.utcnow().isoformat()
        }
    else:
        return {
            "property_id": property_id,
            "flood_zone_type": None,
            "flood_risk": "unknown",
            "flood_risk_score": 0.3,  # Conservative default
            "data_source": "FEMA NFHL",
            "updated_at": datetime.utcnow().isoformat()
        }


def calculate_flood_impact_on_value(
    property_value: float,
    flood_zone: FloodZone
) -> Dict:
    """
    Calculate impact of flood risk on property value

    Args:
        property_value: Current property value
        flood_zone: FloodZone object

    Returns:
        Dictionary with value adjustments
    """
    # Research-based adjustments:
    # High-risk flood zones typically see 5-15% value reduction
    # Moderate-risk zones: 2-5% reduction
    # Low-risk zones: minimal impact

    adjustments = {
        "high": -0.10,      # -10% average
        "moderate": -0.03,  # -3% average
        "low": 0.00,        # No adjustment
        "unknown": -0.02    # Small conservative adjustment
    }

    adjustment_pct = adjustments.get(flood_zone.flood_risk, -0.02)
    adjustment_amount = property_value * adjustment_pct
    adjusted_value = property_value + adjustment_amount

    # Insurance cost impact
    annual_insurance_cost = 0
    if flood_zone.insurance_required:
        # Average flood insurance: $700-2000/year
        # Use 1% of value as estimate, capped
        annual_insurance_cost = min(property_value * 0.01, 2000)

    return {
        "original_value": property_value,
        "flood_adjustment_pct": adjustment_pct,
        "flood_adjustment_amount": adjustment_amount,
        "adjusted_value": adjusted_value,
        "annual_insurance_cost": annual_insurance_cost,
        "total_annual_cost_impact": annual_insurance_cost
    }


if __name__ == "__main__":
    # Test FEMA integration
    logging.basicConfig(level=logging.INFO)

    service = FEMAFloodService()

    # Test location: San Francisco (low flood risk)
    print("\nTest 1: San Francisco")
    flood_zone = service.get_flood_zone_by_coordinates(37.7749, -122.4194)
    if flood_zone:
        print(f"  Zone: {flood_zone.zone_type}")
        print(f"  Risk: {flood_zone.flood_risk}")
        print(f"  Risk Score: {flood_zone.get_risk_score()}")
        print(f"  Insurance Required: {flood_zone.insurance_required}")

    # Test location: New Orleans (high flood risk)
    print("\nTest 2: New Orleans")
    flood_zone = service.get_flood_zone_by_coordinates(29.9511, -90.0715)
    if flood_zone:
        print(f"  Zone: {flood_zone.zone_type}")
        print(f"  Risk: {flood_zone.flood_risk}")
        print(f"  Risk Score: {flood_zone.get_risk_score()}")
        print(f"  Insurance Required: {flood_zone.insurance_required}")

    # Test value impact
    print("\nTest 3: Value Impact Analysis")
    if flood_zone:
        impact = calculate_flood_impact_on_value(500000, flood_zone)
        print(f"  Original Value: ${impact['original_value']:,.0f}")
        print(f"  Adjustment: {impact['flood_adjustment_pct']:.1%}")
        print(f"  Adjusted Value: ${impact['adjusted_value']:,.0f}")
        print(f"  Annual Insurance: ${impact['annual_insurance_cost']:,.0f}")
