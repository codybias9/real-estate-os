"""Market Features
Submarket-level aggregate features for context
"""

from feast import Entity, FeatureView, Field
from feast.types import Float64, Int64, String
from datetime import timedelta


# ============================================================================
# Entities
# ============================================================================

market_entity = Entity(
    name="market",
    join_keys=["market_id"],
    description="Submarket entity (e.g., 'Clark-NV-89101')"
)

# ============================================================================
# Market Aggregate Features
# ============================================================================

market_aggregate_features = FeatureView(
    name="market_aggregate_features",
    entities=[market_entity],
    ttl=timedelta(days=7),
    schema=[
        Field(name="median_list_price", dtype=Float64),
        Field(name="median_price_per_sqft", dtype=Float64),
        Field(name="median_dom", dtype=Int64),
        Field(name="active_inventory", dtype=Int64),
        Field(name="new_listings_30d", dtype=Int64),
        Field(name="sold_count_30d", dtype=Int64),
        Field(name="price_cut_rate", dtype=Float64),  # % with price reductions
        Field(name="median_rent", dtype=Float64),
        Field(name="vacancy_rate", dtype=Float64),
        Field(name="cap_rate_median", dtype=Float64),
        Field(name="yoy_price_growth", dtype=Float64),
        Field(name="yoy_rent_growth", dtype=Float64),
    ],
    online=True,
    source="postgres_source",
    tags={"team": "ml", "category": "market"}
)
