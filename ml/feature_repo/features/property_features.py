"""Property Features for ML Models
Physical, financial, and location-based features
"""

from feast import Entity, Feature, FeatureView, Field, ValueType
from feast.types import Float64, Int64, String, UnixTimestamp
from datetime import timedelta


# ============================================================================
# Entities
# ============================================================================

property_entity = Entity(
    name="property",
    join_keys=["property_id"],
    description="Property entity"
)

# ============================================================================
# Property Physical Features
# ============================================================================

property_physical_features = FeatureView(
    name="property_physical_features",
    entities=[property_entity],
    ttl=timedelta(days=30),
    schema=[
        Field(name="sqft", dtype=Float64),
        Field(name="lot_size", dtype=Float64),
        Field(name="year_built", dtype=Int64),
        Field(name="bedrooms", dtype=Int64),
        Field(name="bathrooms", dtype=Float64),
        Field(name="stories", dtype=Int64),
        Field(name="garage_spaces", dtype=Int64),
        Field(name="pool", dtype=Int64),  # Boolean as int
        Field(name="fireplace", dtype=Int64),
        Field(name="condition_score", dtype=Float64),  # 1-10
        Field(name="renovation_years_ago", dtype=Int64),
    ],
    online=True,
    source="postgres_source",  # Defined in data_sources.py
    tags={"team": "ml", "category": "physical"}
)

# ============================================================================
# Property Financial Features
# ============================================================================

property_financial_features = FeatureView(
    name="property_financial_features",
    entities=[property_entity],
    ttl=timedelta(days=1),
    schema=[
        Field(name="list_price", dtype=Float64),
        Field(name="price_per_sqft", dtype=Float64),
        Field(name="assessed_value", dtype=Float64),
        Field(name="tax_amount_annual", dtype=Float64),
        Field(name="hoa_monthly", dtype=Float64),
        Field(name="days_on_market", dtype=Int64),
        Field(name="price_reductions", dtype=Int64),
        Field(name="last_reduction_pct", dtype=Float64),
        Field(name="arv_estimate", dtype=Float64),  # After-repair value
        Field(name="projected_rent_monthly", dtype=Float64),
        Field(name="cap_rate_estimate", dtype=Float64),
    ],
    online=True,
    source="postgres_source",
    tags={"team": "ml", "category": "financial"}
)

# ============================================================================
# Property Location Features
# ============================================================================

property_location_features = FeatureView(
    name="property_location_features",
    entities=[property_entity],
    ttl=timedelta(days=90),
    schema=[
        Field(name="latitude", dtype=Float64),
        Field(name="longitude", dtype=Float64),
        Field(name="distance_to_cbd_km", dtype=Float64),
        Field(name="distance_to_transit_m", dtype=Float64),
        Field(name="distance_to_school_m", dtype=Float64),
        Field(name="school_rating", dtype=Float64),
        Field(name="walk_score", dtype=Int64),
        Field(name="crime_index", dtype=Float64),
        Field(name="noise_level", dtype=Float64),
        Field(name="median_income_census_tract", dtype=Float64),
        Field(name="population_density_per_sqkm", dtype=Float64),
    ],
    online=True,
    source="postgres_source",
    tags={"team": "ml", "category": "location"}
)

# ============================================================================
# Property Hazard Features
# ============================================================================

property_hazard_features = FeatureView(
    name="property_hazard_features",
    entities=[property_entity],
    ttl=timedelta(days=180),
    schema=[
        Field(name="flood_zone", dtype=String),
        Field(name="flood_risk_score", dtype=Float64),  # 0-1
        Field(name="wildfire_risk_score", dtype=Float64),  # 0-1
        Field(name="heat_island_intensity", dtype=Float64),  # degrees above baseline
        Field(name="seismic_zone", dtype=String),
        Field(name="in_100yr_floodplain", dtype=Int64),  # Boolean
        Field(name="in_500yr_floodplain", dtype=Int64),
        Field(name="elevation_m", dtype=Float64),
    ],
    online=True,
    source="postgres_source",
    tags={"team": "ml", "category": "hazard"}
)
