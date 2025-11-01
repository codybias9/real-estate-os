"""Comp-Critic: 3-Stage Comparable Selection and Adjustment
Stage 1: Retrieval (broad spatial + structural filters)
Stage 2: Ranking (Learn-to-Rank with LambdaMART)
Stage 3: Hedonic Adjustment (Quantile Regression)
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import numpy as np
from math import exp, radians, cos, sin, asin, sqrt
import pickle


class CompCritic:
    """3-stage comp selection and valuation"""

    def __init__(self, db: Session):
        self.db = db
        # Load pre-trained ranker and adjuster models
        try:
            with open("ml/models/comp_ranker_v1.pkl", "rb") as f:
                self.ranker_model = pickle.load(f)
            with open("ml/models/hedonic_adjuster_v1.pkl", "rb") as f:
                self.adjuster_model = pickle.load(f)
        except FileNotFoundError:
            self.ranker_model = None
            self.adjuster_model = None

    # ========================================================================
    # Stage 1: Retrieval
    # ========================================================================

    def retrieve_comps(
        self,
        subject_property: Dict,
        radius_meters: float = 3218,  # 2 miles
        recency_days: int = 180,
        k: int = 50
    ) -> List[Dict]:
        """Broad retrieval with spatial + structural filters

        Args:
            subject_property: Property to value
            radius_meters: Search radius (default 2 miles)
            recency_days: Max days since sale (default 180)
            k: Number of comps to retrieve

        Returns:
            List of comp properties with weights
        """

        from db.models_provenance import Property

        # Filters
        cutoff_date = datetime.now() - timedelta(days=recency_days)
        size_min = subject_property["sqft"] * 0.7
        size_max = subject_property["sqft"] * 1.3

        # Spatial query (PostGIS)
        subject_point = func.ST_SetSRID(
            func.ST_MakePoint(
                subject_property["longitude"],
                subject_property["latitude"]
            ),
            4326
        )

        comps_query = self.db.query(Property).filter(
            and_(
                # Spatial
                func.ST_DWithin(
                    func.ST_Transform(Property.geom, 4326),
                    subject_point,
                    radius_meters
                ),
                # Structural
                Property.asset_type == subject_property["asset_type"],
                Property.sqft.between(size_min, size_max),
                # Temporal
                Property.sale_date >= cutoff_date,
                Property.sale_date != None,
                Property.sale_price != None,
                # Exclude subject
                Property.id != subject_property["id"]
            )
        ).limit(k * 2).all()  # Retrieve extra for ranking

        # Calculate weights
        comps_with_weights = []

        for comp in comps_query:
            # Spatial weight (Gaussian kernel)
            d_spatial = self._haversine_distance(
                subject_property["latitude"],
                subject_property["longitude"],
                comp.latitude,
                comp.longitude
            )
            sigma_d = radius_meters / 3.0  # ~3 sigma = radius
            w_spatial = exp(-(d_spatial / sigma_d) ** 2)

            # Temporal weight
            d_temporal = (datetime.now() - comp.sale_date).days
            sigma_t = recency_days / 3.0
            w_temporal = exp(-(d_temporal / sigma_t) ** 2)

            # Combined weight
            weight = w_spatial * w_temporal

            comps_with_weights.append({
                "property": comp,
                "distance_m": d_spatial,
                "recency_days": d_temporal,
                "weight": weight
            })

        # Sort by weight
        comps_with_weights.sort(key=lambda x: x["weight"], reverse=True)

        return comps_with_weights[:k]

    # ========================================================================
    # Stage 2: Ranking (Learn-to-Rank)
    # ========================================================================

    def rank_comps(
        self,
        subject_property: Dict,
        comps: List[Dict]
    ) -> List[Tuple[Dict, float]]:
        """Re-rank comps using LambdaMART model

        Features:
        - Distance (spatial + structural)
        - Recency
        - Size delta
        - Vintage delta
        - Renovation match
        - Micro-market match

        Returns:
            List of (comp, rank_score) tuples
        """

        if not self.ranker_model:
            # Fallback to retrieval weights if model not available
            return [(c, c["weight"]) for c in comps]

        # Extract features
        features = []
        for comp in comps:
            prop = comp["property"]

            features.append({
                "distance_m": comp["distance_m"],
                "recency_days": comp["recency_days"],
                "size_delta_pct": abs(prop.sqft - subject_property["sqft"]) / subject_property["sqft"],
                "vintage_delta": abs(prop.year_built - subject_property["year_built"]),
                "renovation_match": int(
                    (prop.renovation_date is not None) ==
                    (subject_property.get("renovation_date") is not None)
                ),
                "micro_market_match": int(prop.zip_code == subject_property["zip_code"]),
                "condition_delta": abs(
                    (prop.condition_score or 5) - (subject_property.get("condition_score") or 5)
                ),
            })

        # Predict rank scores
        import pandas as pd
        X = pd.DataFrame(features)
        rank_scores = self.ranker_model.predict(X)

        # Combine with comps
        ranked = list(zip(comps, rank_scores))
        ranked.sort(key=lambda x: x[1], reverse=True)

        return ranked

    # ========================================================================
    # Stage 3: Hedonic Adjustment
    # ========================================================================

    def adjust_comps(
        self,
        subject_property: Dict,
        ranked_comps: List[Tuple[Dict, float]]
    ) -> List[Dict]:
        """Apply hedonic adjustments to comp prices

        Uses quantile regression to estimate price adjustments
        based on feature deltas.

        Returns:
            List of comps with adjusted prices and adjustment breakdowns
        """

        if not self.adjuster_model:
            # Fallback: no adjustments
            return [
                {
                    "comp": c[0],
                    "rank_score": c[1],
                    "unadjusted_price": c[0]["property"].sale_price,
                    "adjusted_price": c[0]["property"].sale_price,
                    "adjustments": {}
                }
                for c in ranked_comps
            ]

        adjusted_comps = []

        for comp, rank_score in ranked_comps:
            prop = comp["property"]

            # Calculate feature deltas (comp - subject)
            delta_features = {
                "delta_sqft": prop.sqft - subject_property["sqft"],
                "delta_lot_size": (prop.lot_size or 0) - (subject_property.get("lot_size") or 0),
                "delta_year_built": prop.year_built - subject_property["year_built"],
                "delta_bedrooms": (prop.bedrooms or 0) - (subject_property.get("bedrooms") or 0),
                "delta_bathrooms": (prop.bathrooms or 0) - (subject_property.get("bathrooms") or 0),
                "delta_condition": (prop.condition_score or 5) - (subject_property.get("condition_score") or 5),
                "has_pool_delta": int((prop.pool or False) != (subject_property.get("pool") or False)),
                "has_garage_delta": int((prop.garage_spaces or 0) > 0) - int((subject_property.get("garage_spaces") or 0) > 0),
            }

            # Predict price delta using hedonic model
            import pandas as pd
            X = pd.DataFrame([delta_features])
            delta_price = self.adjuster_model.predict(X)[0]

            # Adjusted price: comp price - delta
            # (If comp is BETTER than subject, delta_price > 0, so subtract to get subject value)
            adjusted_price = prop.sale_price - delta_price

            # Break down adjustments by feature
            adjustments_breakdown = self._explain_adjustments(
                delta_features,
                self.adjuster_model.coef_ if hasattr(self.adjuster_model, "coef_") else None
            )

            adjusted_comps.append({
                "comp": comp,
                "rank_score": rank_score,
                "unadjusted_price": prop.sale_price,
                "adjusted_price": adjusted_price,
                "unadjusted_price_per_sqft": prop.sale_price / prop.sqft,
                "adjusted_price_per_sqft": adjusted_price / subject_property["sqft"],
                "adjustments": adjustments_breakdown,
                "property_id": str(prop.id),
                "address": prop.address,
                "sale_date": prop.sale_date.isoformat() if prop.sale_date else None,
                "distance_m": comp["distance_m"],
                "recency_days": comp["recency_days"]
            })

        return adjusted_comps

    # ========================================================================
    # Final Valuation
    # ========================================================================

    def value_property(
        self,
        subject_property: Dict,
        top_n: int = 10
    ) -> Dict:
        """Complete 3-stage comp valuation

        Returns:
            Valuation with estimated value, confidence interval, and comp details
        """

        # Stage 1: Retrieve
        comps = self.retrieve_comps(subject_property)

        if len(comps) < 3:
            return {
                "error": "Insufficient comps",
                "comps_found": len(comps)
            }

        # Stage 2: Rank
        ranked = self.rank_comps(subject_property, comps)

        # Stage 3: Adjust
        adjusted = self.adjust_comps(subject_property, ranked[:top_n])

        # Estimate value (weighted average of adjusted prices)
        total_weight = sum(c["rank_score"] for c in adjusted)
        weighted_avg = sum(
            c["adjusted_price"] * c["rank_score"]
            for c in adjusted
        ) / total_weight

        # Confidence interval (bootstrap or percentile-based)
        prices = [c["adjusted_price"] for c in adjusted]
        ci_low = np.percentile(prices, 10)
        ci_high = np.percentile(prices, 90)

        # Top drivers
        drivers = self._calculate_drivers(subject_property, adjusted)

        return {
            "estimated_value": weighted_avg,
            "confidence_interval": [ci_low, ci_high],
            "comps_used": len(adjusted),
            "comps": adjusted,
            "drivers": drivers,
            "method": "comp_critic_3stage"
        }

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _haversine_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """Calculate great-circle distance in meters"""
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371000  # Radius of Earth in meters
        return c * r

    def _explain_adjustments(
        self,
        delta_features: Dict,
        coefficients: np.ndarray
    ) -> Dict:
        """Break down adjustments by feature"""
        if coefficients is None:
            return {}

        adjustments = {}
        for i, (feat_name, delta_val) in enumerate(delta_features.items()):
            if i < len(coefficients):
                adj_amount = delta_val * coefficients[i]
                if abs(adj_amount) > 100:  # Only show significant adjustments
                    adjustments[feat_name] = adj_amount

        return adjustments

    def _calculate_drivers(
        self,
        subject_property: Dict,
        adjusted_comps: List[Dict]
    ) -> List[Dict]:
        """Calculate top value drivers from comp analysis"""

        # Aggregate adjustment amounts by feature
        agg_adjustments = {}
        for comp in adjusted_comps:
            for feat, amt in comp["adjustments"].items():
                agg_adjustments[feat] = agg_adjustments.get(feat, 0) + amt

        # Sort by absolute impact
        drivers = [
            {"feature": feat, "impact": amt}
            for feat, amt in agg_adjustments.items()
        ]
        drivers.sort(key=lambda x: abs(x["impact"]), reverse=True)

        return drivers[:5]  # Top 5
