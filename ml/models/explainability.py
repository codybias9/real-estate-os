"""
Explainability Module: SHAP + DiCE for Model Interpretability

Provides:
1. SHAP (SHapley Additive exPlanations) for feature importance
2. DiCE (Diverse Counterfactual Explanations) for what-if analysis
3. Caching for low-latency serving
"""

import json
import numpy as np
from typing import Dict, Any, List, Tuple
from datetime import datetime
import hashlib


class SHAPExplainer:
    """
    SHAP explainer for scoring model

    In production: Use actual shap.TreeExplainer or shap.KernelExplainer
    """

    def __init__(self, model=None, background_data=None):
        self.model = model
        self.background_data = background_data
        self.cache = {}  # Simple in-memory cache

    def explain(
        self,
        features: Dict[str, float],
        top_k: int = 10,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Compute SHAP values for a prediction

        Returns top-k feature importances with directionality
        """
        # Generate cache key
        feature_hash = hashlib.md5(
            json.dumps(features, sort_keys=True).encode()
        ).hexdigest()

        if use_cache and feature_hash in self.cache:
            return self.cache[feature_hash]

        # Simulate SHAP computation
        # In production: shap_values = explainer.shap_values(features)

        # Mock SHAP values based on feature values
        shap_values = {}

        # Property features
        if "building_sqft" in features:
            shap_values["building_sqft"] = (features["building_sqft"] - 2000) * 0.05

        if "lot_size_sqft" in features:
            shap_values["lot_size_sqft"] = (features["lot_size_sqft"] - 7000) * 0.02

        if "condition_score" in features:
            shap_values["condition_score"] = (features["condition_score"] - 7.0) * 0.15

        if "property_age" in features:
            shap_values["property_age"] = -(features["property_age"] - 15) * 0.03

        if "bedrooms" in features:
            shap_values["bedrooms"] = (features["bedrooms"] - 3) * 0.08

        if "bathrooms" in features:
            shap_values["bathrooms"] = (features["bathrooms"] - 2.5) * 0.10

        # Market features
        if "inventory_level" in features:
            shap_values["inventory_level"] = -(features["inventory_level"] - 3.0) * 0.12

        if "price_trend_30d" in features:
            shap_values["price_trend_30d"] = (features["price_trend_30d"] - 1.0) * 0.20

        if "median_dom" in features:
            shap_values["median_dom"] = -(features["median_dom"] - 40) * 0.02

        if "market_temperature" in features:
            shap_values["market_temperature"] = (features["market_temperature"] - 0.5) * 0.18

        # Location features
        if "walk_score" in features:
            shap_values["walk_score"] = (features["walk_score"] - 50) * 0.02

        if "school_district_rating" in features:
            shap_values["school_district_rating"] = (features["school_district_rating"] - 5) * 0.08

        # Sort by absolute value
        sorted_features = sorted(
            shap_values.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )[:top_k]

        # Base prediction (mean)
        base_value = 0.5

        # Compute final prediction
        prediction = base_value + sum(shap_values.values())
        prediction = max(0, min(1, prediction))  # Clip to [0, 1]

        result = {
            "prediction": round(prediction, 4),
            "base_value": base_value,
            "top_k_features": [
                {
                    "feature": feat,
                    "shap_value": round(val, 4),
                    "feature_value": features.get(feat),
                    "impact": "positive" if val > 0 else "negative",
                    "magnitude": abs(round(val, 4))
                }
                for feat, val in sorted_features
            ],
            "total_shap": round(sum(shap_values.values()), 4),
            "timestamp": datetime.utcnow().isoformat()
        }

        # Cache result
        if use_cache:
            self.cache[feature_hash] = result

        return result


class DiCEGenerator:
    """
    DiCE (Diverse Counterfactual Explanations) generator

    Generates actionable "what-if" scenarios
    """

    def __init__(self, model=None, feature_ranges=None):
        self.model = model
        self.feature_ranges = feature_ranges or self._default_ranges()

    def _default_ranges(self) -> Dict[str, Dict[str, float]]:
        """Define valid ranges for features"""
        return {
            "building_sqft": {"min": 800, "max": 5000, "mutable": False},
            "condition_score": {"min": 1.0, "max": 10.0, "mutable": True},
            "property_age": {"min": 0, "max": 100, "mutable": False},
            "bedrooms": {"min": 1, "max": 7, "mutable": False},
            "bathrooms": {"min": 1.0, "max": 5.0, "mutable": False},
            "list_price": {"min": 50000, "max": 2000000, "mutable": True},
            "price_per_sqft": {"min": 50, "max": 500, "mutable": True},
            "renovation_year": {"min": 1950, "max": 2024, "mutable": True},
            "hoa_fee_monthly": {"min": 0, "max": 1000, "mutable": True}
        }

    def generate_counterfactuals(
        self,
        current_features: Dict[str, float],
        desired_outcome: float,
        n_counterfactuals: int = 5,
        diversity_weight: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Generate diverse counterfactual explanations

        Args:
            current_features: Current feature values
            desired_outcome: Target prediction value (0-1)
            n_counterfactuals: Number of counterfactuals to generate
            diversity_weight: Weight for diversity vs proximity

        Returns:
            List of counterfactual scenarios with changes
        """
        counterfactuals = []

        # Get current prediction
        current_pred = self._predict(current_features)
        delta_needed = desired_outcome - current_pred

        # Generate diverse counterfactuals
        for i in range(n_counterfactuals):
            cf = current_features.copy()
            changes = []

            # Strategy varies by counterfactual to ensure diversity
            if i == 0:
                # Strategy 1: Improve condition
                if "condition_score" in cf and self.feature_ranges["condition_score"]["mutable"]:
                    new_condition = min(
                        cf["condition_score"] + 1.5,
                        self.feature_ranges["condition_score"]["max"]
                    )
                    if new_condition != cf["condition_score"]:
                        changes.append({
                            "feature": "condition_score",
                            "from": cf["condition_score"],
                            "to": new_condition,
                            "change": new_condition - cf["condition_score"]
                        })
                        cf["condition_score"] = new_condition

            elif i == 1:
                # Strategy 2: Reduce price
                if "list_price" in cf and self.feature_ranges["list_price"]["mutable"]:
                    reduction = 0.05  # 5% reduction
                    new_price = cf["list_price"] * (1 - reduction)
                    changes.append({
                        "feature": "list_price",
                        "from": cf["list_price"],
                        "to": new_price,
                        "change": -(cf["list_price"] - new_price)
                    })
                    cf["list_price"] = new_price

            elif i == 2:
                # Strategy 3: Recent renovation
                if "renovation_year" in cf and self.feature_ranges["renovation_year"]["mutable"]:
                    new_reno = 2023
                    if cf.get("renovation_year", 2000) < new_reno:
                        changes.append({
                            "feature": "renovation_year",
                            "from": cf.get("renovation_year", 2000),
                            "to": new_reno,
                            "change": new_reno - cf.get("renovation_year", 2000)
                        })
                        cf["renovation_year"] = new_reno

            elif i == 3:
                # Strategy 4: Lower HOA
                if "hoa_fee_monthly" in cf and self.feature_ranges["hoa_fee_monthly"]["mutable"]:
                    new_hoa = max(0, cf.get("hoa_fee_monthly", 50) - 30)
                    changes.append({
                        "feature": "hoa_fee_monthly",
                        "from": cf.get("hoa_fee_monthly", 50),
                        "to": new_hoa,
                        "change": -(cf.get("hoa_fee_monthly", 50) - new_hoa)
                    })
                    cf["hoa_fee_monthly"] = new_hoa

            elif i == 4:
                # Strategy 5: Combined improvements
                if "condition_score" in cf:
                    new_condition = min(cf["condition_score"] + 1.0, 10.0)
                    if new_condition != cf["condition_score"]:
                        changes.append({
                            "feature": "condition_score",
                            "from": cf["condition_score"],
                            "to": new_condition,
                            "change": new_condition - cf["condition_score"]
                        })
                        cf["condition_score"] = new_condition

                if "list_price" in cf:
                    new_price = cf["list_price"] * 0.97
                    changes.append({
                        "feature": "list_price",
                        "from": cf["list_price"],
                        "to": new_price,
                        "change": -(cf["list_price"] - new_price)
                    })
                    cf["list_price"] = new_price

            # Compute new prediction
            cf_pred = self._predict(cf)

            # Calculate feasibility and proximity
            proximity = self._calculate_proximity(current_features, cf)
            feasibility = self._assess_feasibility(changes)

            counterfactuals.append({
                "counterfactual_id": i + 1,
                "changes": changes,
                "current_prediction": round(current_pred, 4),
                "counterfactual_prediction": round(cf_pred, 4),
                "prediction_change": round(cf_pred - current_pred, 4),
                "proximity_score": round(proximity, 3),
                "feasibility_score": round(feasibility, 3),
                "features": cf
            })

        return counterfactuals

    def _predict(self, features: Dict[str, float]) -> float:
        """Simulate model prediction"""
        # Simple scoring function
        score = 0.5
        score += features.get("condition_score", 7.0) * 0.05
        score -= features.get("property_age", 15) * 0.003
        score += features.get("bedrooms", 3) * 0.02
        score -= features.get("list_price", 400000) / 1000000 * 0.1
        return max(0, min(1, score))

    def _calculate_proximity(
        self,
        original: Dict[str, float],
        counterfactual: Dict[str, float]
    ) -> float:
        """Calculate how close counterfactual is to original (0-1)"""
        distances = []
        for key in original:
            if key in counterfactual and key in self.feature_ranges:
                orig_val = original[key]
                cf_val = counterfactual[key]
                range_span = self.feature_ranges[key]["max"] - self.feature_ranges[key]["min"]
                if range_span > 0:
                    normalized_dist = abs(cf_val - orig_val) / range_span
                    distances.append(normalized_dist)

        avg_dist = np.mean(distances) if distances else 0
        proximity = 1 - avg_dist
        return max(0, min(1, proximity))

    def _assess_feasibility(self, changes: List[Dict[str, Any]]) -> float:
        """Assess how feasible the changes are (0-1)"""
        if not changes:
            return 1.0

        # Penalize many changes and large magnitude changes
        num_changes_penalty = 1.0 / (1 + len(changes) * 0.2)

        # Consider nature of changes
        feasibility_scores = []
        for change in changes:
            feat = change["feature"]
            if feat in ["condition_score", "renovation_year"]:
                feasibility_scores.append(0.7)  # Moderately feasible (requires work)
            elif feat in ["list_price", "hoa_fee_monthly"]:
                feasibility_scores.append(0.9)  # Highly feasible (just numbers)
            else:
                feasibility_scores.append(0.5)

        avg_feasibility = np.mean(feasibility_scores) if feasibility_scores else 1.0

        return num_changes_penalty * avg_feasibility


def test_explainability(property_id: str = "DEMO123"):
    """Test SHAP and DiCE explainability"""
    # Sample features
    features = {
        "building_sqft": 2400,
        "lot_size_sqft": 7500,
        "condition_score": 6.5,
        "property_age": 20,
        "bedrooms": 4,
        "bathrooms": 3.0,
        "inventory_level": 3.2,
        "price_trend_30d": 1.02,
        "median_dom": 45,
        "market_temperature": 0.55,
        "walk_score": 42,
        "school_district_rating": 7,
        "list_price": 425000,
        "hoa_fee_monthly": 75,
        "renovation_year": 2015
    }

    # SHAP explanation
    shap_explainer = SHAPExplainer()
    shap_result = shap_explainer.explain(features, top_k=10)

    with open(f'artifacts/explainability/shap-topk-{property_id}.json', 'w') as f:
        json.dump(shap_result, f, indent=2)

    # DiCE counterfactuals
    dice_generator = DiCEGenerator()
    counterfactuals = dice_generator.generate_counterfactuals(
        features,
        desired_outcome=0.75,  # Want to increase score to 0.75
        n_counterfactuals=5
    )

    dice_result = {
        "property_id": property_id,
        "current_features": features,
        "desired_outcome": 0.75,
        "counterfactuals": counterfactuals,
        "timestamp": datetime.utcnow().isoformat()
    }

    with open(f'artifacts/explainability/dice-whatifs-{property_id}.json', 'w') as f:
        json.dump(dice_result, f, indent=2)

    return {
        "shap": shap_result,
        "dice": dice_result
    }


if __name__ == "__main__":
    result = test_explainability("DEMO123")
    print("Explainability artifacts generated")
