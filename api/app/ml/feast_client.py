"""Feast Feature Store Client
Retrieve online features for scoring
"""

from feast import FeatureStore
from typing import Dict, List
from uuid import UUID
import os


class FeastClient:
    """Client for Feast feature store"""

    def __init__(self, repo_path: str = "ml/feature_repo"):
        self.store = FeatureStore(repo_path=repo_path)

    def get_property_features(self, property_id: UUID) -> Dict:
        """Get all property features for scoring"""

        entity_dict = {"property_id": str(property_id)}

        # Feature references
        feature_refs = [
            "property_physical_features:sqft",
            "property_physical_features:lot_size",
            "property_physical_features:year_built",
            "property_physical_features:bedrooms",
            "property_physical_features:bathrooms",
            "property_physical_features:condition_score",
            "property_financial_features:list_price",
            "property_financial_features:price_per_sqft",
            "property_financial_features:days_on_market",
            "property_financial_features:arv_estimate",
            "property_financial_features:cap_rate_estimate",
            "property_location_features:distance_to_cbd_km",
            "property_location_features:walk_score",
            "property_location_features:school_rating",
            "property_hazard_features:flood_risk_score",
            "property_hazard_features:wildfire_risk_score",
        ]

        # Fetch online features
        features = self.store.get_online_features(
            features=feature_refs,
            entity_rows=[entity_dict]
        ).to_dict()

        # Format as flat dict
        return {k: v[0] for k, v in features.items() if k != "property_id"}

    def get_market_features(self, market_id: str) -> Dict:
        """Get market-level features"""

        entity_dict = {"market_id": market_id}

        feature_refs = [
            "market_aggregate_features:median_list_price",
            "market_aggregate_features:median_dom",
            "market_aggregate_features:price_cut_rate",
            "market_aggregate_features:cap_rate_median",
            "market_aggregate_features:yoy_price_growth",
        ]

        features = self.store.get_online_features(
            features=feature_refs,
            entity_rows=[entity_dict]
        ).to_dict()

        return {k: v[0] for k, v in features.items() if k != "market_id"}

    def get_combined_features(self, property_id: UUID, market_id: str) -> Dict:
        """Get property + market features combined"""

        property_features = self.get_property_features(property_id)
        market_features = self.get_market_features(market_id)

        return {**property_features, **market_features}


# ============================================================================
# Integration with Scoring Service
# ============================================================================

def score_property_with_feast(property_id: UUID, market_id: str) -> Dict:
    """Score property using Feast features"""

    feast_client = FeastClient()

    # Get features from Feast
    features = feast_client.get_combined_features(property_id, market_id)

    # Load model
    import pickle
    with open("ml/models/property_scorer_v1.pkl", "rb") as f:
        model = pickle.load(f)

    # Predict
    import pandas as pd
    X = pd.DataFrame([features])
    score = model.predict(X)[0]

    return {
        "property_id": str(property_id),
        "score": float(score),
        "features_used": features
    }
