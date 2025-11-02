"""
Unified Hazards ETL Pipeline

Orchestrates extraction, transformation, and loading of all hazard data:
- FEMA flood zones
- Wildfire risk
- Heat index
- Spatial joins to properties table
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import json

from hazards.fema_integration import FEMAFloodService, enrich_property_with_flood_data
from hazards.wildfire_integration import WildfireRiskService, calculate_wildfire_impact_on_value

logger = logging.getLogger(__name__)


@dataclass
class PropertyHazards:
    """Complete hazard assessment for a property"""
    property_id: str

    # Flood hazards
    flood_zone_type: Optional[str] = None
    flood_risk: Optional[str] = None
    flood_risk_score: float = 0.0
    flood_insurance_required: bool = False

    # Wildfire hazards
    wildfire_risk_level: Optional[str] = None
    wildfire_risk_score: float = 0.0
    wildfire_hazard_potential: Optional[str] = None
    ca_fire_zone: Optional[str] = None

    # Heat hazards
    avg_summer_temp: Optional[float] = None
    heat_wave_days_per_year: Optional[int] = None
    heat_risk_score: float = 0.0

    # Composite scores
    composite_hazard_score: float = 0.0  # 0-1, weighted average
    total_value_adjustment_pct: float = 0.0
    total_annual_cost_impact: float = 0.0

    # Metadata
    assessed_at: str = None

    def __post_init__(self):
        if self.assessed_at is None:
            self.assessed_at = datetime.utcnow().isoformat()

    def calculate_composite_score(self):
        """Calculate weighted composite hazard score"""
        # Weights: flood 40%, wildfire 40%, heat 20%
        self.composite_hazard_score = (
            self.flood_risk_score * 0.4 +
            self.wildfire_risk_score * 0.4 +
            self.heat_risk_score * 0.2
        )


class HazardsETLPipeline:
    """ETL pipeline for all hazard data"""

    def __init__(self):
        self.fema_service = FEMAFloodService()
        self.wildfire_service = WildfireRiskService()

    def process_property(
        self,
        property_id: str,
        latitude: float,
        longitude: float,
        state: str,
        property_value: float
    ) -> PropertyHazards:
        """
        Process all hazards for a single property

        Args:
            property_id: Property identifier
            latitude: Property latitude
            longitude: Property longitude
            state: State code
            property_value: Current property value

        Returns:
            PropertyHazards object with complete assessment
        """
        logger.info(f"Processing hazards for property {property_id}")

        hazards = PropertyHazards(property_id=property_id)

        # 1. Flood hazard assessment
        try:
            flood_zone = self.fema_service.get_flood_zone_by_coordinates(latitude, longitude)
            if flood_zone:
                hazards.flood_zone_type = flood_zone.zone_type
                hazards.flood_risk = flood_zone.flood_risk
                hazards.flood_risk_score = flood_zone.get_risk_score()
                hazards.flood_insurance_required = flood_zone.insurance_required
        except Exception as e:
            logger.error(f"Flood assessment failed for {property_id}: {e}")

        # 2. Wildfire risk assessment
        try:
            wildfire_risk = self.wildfire_service.assess_wildfire_risk(latitude, longitude, state)
            hazards.wildfire_risk_level = wildfire_risk.risk_level
            hazards.wildfire_risk_score = wildfire_risk.risk_score
            hazards.wildfire_hazard_potential = wildfire_risk.hazard_potential
            hazards.ca_fire_zone = wildfire_risk.state_hazard_zone
        except Exception as e:
            logger.error(f"Wildfire assessment failed for {property_id}: {e}")

        # 3. Heat hazard assessment
        try:
            heat_score = self._assess_heat_risk(latitude, longitude, state)
            hazards.heat_risk_score = heat_score
        except Exception as e:
            logger.error(f"Heat assessment failed for {property_id}: {e}")

        # 4. Calculate composite scores
        hazards.calculate_composite_score()

        # 5. Calculate financial impacts
        total_value_adj = 0.0
        total_annual_cost = 0.0

        if flood_zone:
            from hazards.fema_integration import calculate_flood_impact_on_value
            flood_impact = calculate_flood_impact_on_value(property_value, flood_zone)
            total_value_adj += flood_impact['flood_adjustment_pct']
            total_annual_cost += flood_impact['total_annual_cost_impact']

        if wildfire_risk:
            wildfire_impact = calculate_wildfire_impact_on_value(property_value, wildfire_risk)
            total_value_adj += wildfire_impact['wildfire_adjustment_pct']
            total_annual_cost += wildfire_impact['total_annual_cost_impact']

        hazards.total_value_adjustment_pct = total_value_adj
        hazards.total_annual_cost_impact = total_annual_cost

        logger.info(f"Hazards assessment complete: composite score {hazards.composite_hazard_score:.2f}")

        return hazards

    def _assess_heat_risk(self, latitude: float, longitude: float, state: str) -> float:
        """
        Assess heat risk for location

        Simplified implementation - real version would use climate data
        """
        # High heat risk states
        high_heat_states = {
            "AZ": 0.9, "NV": 0.8, "NM": 0.7, "TX": 0.8, "CA": 0.6,
            "FL": 0.7, "LA": 0.6, "GA": 0.5, "SC": 0.5, "AL": 0.5
        }

        # Latitude adjustment (lower latitude = hotter)
        if latitude < 30:
            lat_factor = 1.0
        elif latitude < 35:
            lat_factor = 0.8
        elif latitude < 40:
            lat_factor = 0.6
        else:
            lat_factor = 0.4

        base_score = high_heat_states.get(state, 0.3)
        heat_score = (base_score + lat_factor) / 2

        return min(max(heat_score, 0.0), 1.0)

    def batch_process_properties(
        self,
        properties: List[Dict]
    ) -> List[PropertyHazards]:
        """
        Process hazards for multiple properties

        Args:
            properties: List of property dictionaries with keys:
                       property_id, latitude, longitude, state, value

        Returns:
            List of PropertyHazards objects
        """
        results = []

        for prop in properties:
            try:
                hazards = self.process_property(
                    property_id=prop['property_id'],
                    latitude=prop['latitude'],
                    longitude=prop['longitude'],
                    state=prop['state'],
                    property_value=prop.get('value', 0)
                )
                results.append(hazards)
            except Exception as e:
                logger.error(f"Failed to process property {prop.get('property_id')}: {e}")
                # Add placeholder with error
                error_hazards = PropertyHazards(property_id=prop['property_id'])
                results.append(error_hazards)

        return results

    def export_to_database(self, hazards: PropertyHazards, connection) -> bool:
        """
        Export hazards data to database

        Args:
            hazards: PropertyHazards object
            connection: Database connection

        Returns:
            True if successful
        """
        try:
            # SQL to insert/update hazards
            sql = """
                INSERT INTO property_hazards (
                    property_id,
                    flood_zone_type,
                    flood_risk,
                    flood_risk_score,
                    flood_insurance_required,
                    wildfire_risk_level,
                    wildfire_risk_score,
                    wildfire_hazard_potential,
                    ca_fire_zone,
                    heat_risk_score,
                    composite_hazard_score,
                    total_value_adjustment_pct,
                    total_annual_cost_impact,
                    assessed_at
                ) VALUES (
                    %(property_id)s,
                    %(flood_zone_type)s,
                    %(flood_risk)s,
                    %(flood_risk_score)s,
                    %(flood_insurance_required)s,
                    %(wildfire_risk_level)s,
                    %(wildfire_risk_score)s,
                    %(wildfire_hazard_potential)s,
                    %(ca_fire_zone)s,
                    %(heat_risk_score)s,
                    %(composite_hazard_score)s,
                    %(total_value_adjustment_pct)s,
                    %(total_annual_cost_impact)s,
                    %(assessed_at)s
                )
                ON CONFLICT (property_id)
                DO UPDATE SET
                    flood_zone_type = EXCLUDED.flood_zone_type,
                    flood_risk = EXCLUDED.flood_risk,
                    flood_risk_score = EXCLUDED.flood_risk_score,
                    flood_insurance_required = EXCLUDED.flood_insurance_required,
                    wildfire_risk_level = EXCLUDED.wildfire_risk_level,
                    wildfire_risk_score = EXCLUDED.wildfire_risk_score,
                    wildfire_hazard_potential = EXCLUDED.wildfire_hazard_potential,
                    ca_fire_zone = EXCLUDED.ca_fire_zone,
                    heat_risk_score = EXCLUDED.heat_risk_score,
                    composite_hazard_score = EXCLUDED.composite_hazard_score,
                    total_value_adjustment_pct = EXCLUDED.total_value_adjustment_pct,
                    total_annual_cost_impact = EXCLUDED.total_annual_cost_impact,
                    assessed_at = EXCLUDED.assessed_at
            """

            cursor = connection.cursor()
            cursor.execute(sql, asdict(hazards))
            connection.commit()

            logger.info(f"Exported hazards for property {hazards.property_id}")
            return True

        except Exception as e:
            logger.error(f"Database export failed: {e}")
            connection.rollback()
            return False


# Airflow integration
def run_hazards_etl(**context):
    """
    Airflow task to run hazards ETL

    Usage:
        PythonOperator(
            task_id='enrich_hazards',
            python_callable=run_hazards_etl
        )
    """
    pipeline = HazardsETLPipeline()

    # Get properties to process from XCom or database
    # Example: process properties ingested in previous task

    properties = [
        # Would pull from database in production
        {
            'property_id': 'prop_001',
            'latitude': 37.7749,
            'longitude': -122.4194,
            'state': 'CA',
            'value': 1200000
        }
    ]

    results = pipeline.batch_process_properties(properties)

    # Return summary stats
    return {
        "properties_processed": len(results),
        "avg_composite_score": sum(h.composite_hazard_score for h in results) / len(results) if results else 0
    }


if __name__ == "__main__":
    # Test ETL pipeline
    logging.basicConfig(level=logging.INFO)

    pipeline = HazardsETLPipeline()

    # Test property: San Francisco
    print("\n" + "="*80)
    print("Testing Hazards ETL Pipeline")
    print("="*80)

    hazards = pipeline.process_property(
        property_id="test_prop_sf",
        latitude=37.7749,
        longitude=-122.4194,
        state="CA",
        property_value=1200000
    )

    print(f"\nProperty: test_prop_sf (San Francisco, CA)")
    print(f"  Value: $1,200,000")
    print(f"\nFlood Assessment:")
    print(f"  Zone: {hazards.flood_zone_type}")
    print(f"  Risk: {hazards.flood_risk}")
    print(f"  Risk Score: {hazards.flood_risk_score:.2f}")
    print(f"  Insurance Required: {hazards.flood_insurance_required}")

    print(f"\nWildfire Assessment:")
    print(f"  Risk Level: {hazards.wildfire_risk_level}")
    print(f"  Risk Score: {hazards.wildfire_risk_score:.2f}")
    print(f"  Hazard Potential: {hazards.wildfire_hazard_potential}")
    print(f"  CA Fire Zone: {hazards.ca_fire_zone}")

    print(f"\nHeat Assessment:")
    print(f"  Heat Risk Score: {hazards.heat_risk_score:.2f}")

    print(f"\nComposite Assessment:")
    print(f"  Overall Hazard Score: {hazards.composite_hazard_score:.2f}")
    print(f"  Value Adjustment: {hazards.total_value_adjustment_pct:.2%}")
    print(f"  Annual Cost Impact: ${hazards.total_annual_cost_impact:,.0f}")

    # Export to JSON
    print(f"\nJSON Export:")
    print(json.dumps(asdict(hazards), indent=2))
