"""
Trust Score Calculation Engine.

Calculates trust scores for data based on multiple factors:
- Source quality (authoritative vs. user-generated)
- Data freshness (age decay function)
- Transformation quality (lossless vs. lossy)
- Model confidence (for ML-derived fields)
- Validation pass rate (data quality checks)
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import logging
import math

logger = logging.getLogger(__name__)


class SourceType(Enum):
    """Types of data sources with intrinsic trust scores."""
    AUTHORITATIVE_GOVERNMENT = 0.95  # FEMA, USGS, Census
    COMMERCIAL_VERIFIED = 0.85       # MLS, CoreLogic, Zillow API
    ML_MODEL_VALIDATED = 0.75        # Internally trained + validated
    USER_INPUT = 0.70                # User-provided data
    THIRD_PARTY_UNVERIFIED = 0.50    # Scraped or unverified sources
    UNKNOWN = 0.30                   # Unknown provenance


class TransformationType(Enum):
    """Types of data transformations with quality scores."""
    LOSSLESS = 1.0              # Copy, rename, type cast (safe)
    VALIDATED_NORMALIZATION = 0.90  # libpostal, geocoding (validated)
    STATISTICAL_IMPUTATION = 0.70   # Filling nulls with stats
    HEURISTIC_ESTIMATE = 0.50       # Rule-based guesses
    UNKNOWN = 0.30              # Untracked transformation


class TrustScoreCalculator:
    """Calculator for data trust scores using multi-factor methodology."""

    def __init__(
        self,
        source_quality_weight: float = 0.30,
        data_freshness_weight: float = 0.20,
        transformation_quality_weight: float = 0.20,
        model_confidence_weight: float = 0.20,
        validation_pass_rate_weight: float = 0.10
    ):
        """
        Initialize trust score calculator.

        Args:
            source_quality_weight: Weight for source authority (0-1)
            data_freshness_weight: Weight for data recency (0-1)
            transformation_quality_weight: Weight for transform quality (0-1)
            model_confidence_weight: Weight for model confidence (0-1)
            validation_pass_rate_weight: Weight for validation pass rate (0-1)
        """
        # Validate weights sum to 1.0
        total_weight = (
            source_quality_weight +
            data_freshness_weight +
            transformation_quality_weight +
            model_confidence_weight +
            validation_pass_rate_weight
        )

        if not math.isclose(total_weight, 1.0, abs_tol=0.01):
            raise ValueError(
                f"Weights must sum to 1.0, got {total_weight}. "
                "Adjust weights to ensure proper normalization."
            )

        self.source_quality_weight = source_quality_weight
        self.data_freshness_weight = data_freshness_weight
        self.transformation_quality_weight = transformation_quality_weight
        self.model_confidence_weight = model_confidence_weight
        self.validation_pass_rate_weight = validation_pass_rate_weight

    def calculate_source_quality_score(
        self,
        source_type: SourceType
    ) -> float:
        """
        Calculate source quality score.

        Args:
            source_type: Type of data source

        Returns:
            Source quality score (0-1)
        """
        return source_type.value

    def calculate_freshness_score(
        self,
        data_age_days: int,
        half_life_days: int = 90
    ) -> float:
        """
        Calculate freshness score using exponential decay.

        Score decays by 50% every half_life_days.

        Args:
            data_age_days: Age of data in days
            half_life_days: Days for 50% decay (default 90 days)

        Returns:
            Freshness score (0-1)
        """
        if data_age_days < 0:
            raise ValueError(f"Data age cannot be negative: {data_age_days}")

        # Exponential decay: score = 2^(-age / half_life)
        decay_factor = -(data_age_days / half_life_days)
        score = math.pow(2, decay_factor)

        # Clamp to [0, 1]
        return max(0.0, min(1.0, score))

    def calculate_transformation_quality_score(
        self,
        transformation_chain: List[TransformationType]
    ) -> float:
        """
        Calculate transformation quality score.

        Uses product of transformation quality scores (compounding degradation).

        Args:
            transformation_chain: List of transformations applied

        Returns:
            Transformation quality score (0-1)
        """
        if not transformation_chain:
            return 1.0  # No transformations = perfect quality

        # Product of all transformation scores
        score = 1.0
        for transform in transformation_chain:
            score *= transform.value

        return score

    def calculate_model_confidence_score(
        self,
        model_confidence: Optional[float]
    ) -> float:
        """
        Calculate model confidence score.

        Args:
            model_confidence: Model's confidence score (0-1), None if not ML-derived

        Returns:
            Model confidence score (0-1)
        """
        if model_confidence is None:
            return 1.0  # Not ML-derived, assume perfect confidence

        if not 0 <= model_confidence <= 1:
            raise ValueError(
                f"Model confidence must be in [0, 1], got {model_confidence}"
            )

        return model_confidence

    def calculate_validation_pass_rate_score(
        self,
        rules_passed: int,
        rules_total: int
    ) -> float:
        """
        Calculate validation pass rate score.

        Args:
            rules_passed: Number of validation rules passed
            rules_total: Total number of validation rules

        Returns:
            Validation pass rate score (0-1)
        """
        if rules_total == 0:
            return 1.0  # No validation rules = assume valid

        if rules_passed < 0 or rules_total < 0:
            raise ValueError("Rule counts cannot be negative")

        if rules_passed > rules_total:
            raise ValueError(
                f"Passed rules ({rules_passed}) cannot exceed total ({rules_total})"
            )

        return rules_passed / rules_total

    def calculate_trust_score(
        self,
        source_type: SourceType,
        data_age_days: int = 0,
        transformation_chain: Optional[List[TransformationType]] = None,
        model_confidence: Optional[float] = None,
        rules_passed: int = 0,
        rules_total: int = 0
    ) -> Dict[str, Any]:
        """
        Calculate overall trust score using weighted factors.

        Args:
            source_type: Type of data source
            data_age_days: Age of data in days
            transformation_chain: List of transformations applied
            model_confidence: Model confidence if ML-derived
            rules_passed: Number of validation rules passed
            rules_total: Total validation rules

        Returns:
            Dictionary with trust score and breakdown
        """
        # Calculate individual factor scores
        source_quality = self.calculate_source_quality_score(source_type)

        freshness = self.calculate_freshness_score(data_age_days)

        transformation_quality = self.calculate_transformation_quality_score(
            transformation_chain or []
        )

        model_conf = self.calculate_model_confidence_score(model_confidence)

        validation_pass_rate = self.calculate_validation_pass_rate_score(
            rules_passed, rules_total
        )

        # Calculate weighted trust score
        trust_score = (
            (source_quality * self.source_quality_weight) +
            (freshness * self.data_freshness_weight) +
            (transformation_quality * self.transformation_quality_weight) +
            (model_conf * self.model_confidence_weight) +
            (validation_pass_rate * self.validation_pass_rate_weight)
        )

        return {
            "trust_score": round(trust_score, 4),
            "breakdown": {
                "source_quality": {
                    "score": round(source_quality, 4),
                    "weight": self.source_quality_weight,
                    "contribution": round(source_quality * self.source_quality_weight, 4)
                },
                "data_freshness": {
                    "score": round(freshness, 4),
                    "weight": self.data_freshness_weight,
                    "contribution": round(freshness * self.data_freshness_weight, 4),
                    "age_days": data_age_days
                },
                "transformation_quality": {
                    "score": round(transformation_quality, 4),
                    "weight": self.transformation_quality_weight,
                    "contribution": round(transformation_quality * self.transformation_quality_weight, 4),
                    "transformations": len(transformation_chain or [])
                },
                "model_confidence": {
                    "score": round(model_conf, 4),
                    "weight": self.model_confidence_weight,
                    "contribution": round(model_conf * self.model_confidence_weight, 4)
                },
                "validation_pass_rate": {
                    "score": round(validation_pass_rate, 4),
                    "weight": self.validation_pass_rate_weight,
                    "contribution": round(validation_pass_rate * self.validation_pass_rate_weight, 4),
                    "rules_passed": rules_passed,
                    "rules_total": rules_total
                }
            }
        }


# Global calculator instance with default weights
default_calculator = TrustScoreCalculator()


def calculate_field_trust_score(
    source_type: str,
    created_at: datetime,
    transformations: Optional[List[str]] = None,
    model_confidence: Optional[float] = None,
    validation_result: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    Convenience function to calculate trust score for a field.

    Args:
        source_type: Source type string (maps to SourceType enum)
        created_at: Timestamp when data was created
        transformations: List of transformation type strings
        model_confidence: Model confidence score (0-1)
        validation_result: Dict with 'passed' and 'total' keys

    Returns:
        Trust score result dictionary
    """
    # Map source type string to enum
    source_mapping = {
        "authoritative_government": SourceType.AUTHORITATIVE_GOVERNMENT,
        "commercial_verified": SourceType.COMMERCIAL_VERIFIED,
        "ml_model_validated": SourceType.ML_MODEL_VALIDATED,
        "user_input": SourceType.USER_INPUT,
        "third_party_unverified": SourceType.THIRD_PARTY_UNVERIFIED,
        "unknown": SourceType.UNKNOWN
    }

    source_enum = source_mapping.get(
        source_type.lower(),
        SourceType.UNKNOWN
    )

    # Calculate data age
    now = datetime.utcnow()
    age_delta = now - created_at
    data_age_days = age_delta.days

    # Map transformation strings to enums
    transform_mapping = {
        "lossless": TransformationType.LOSSLESS,
        "validated_normalization": TransformationType.VALIDATED_NORMALIZATION,
        "statistical_imputation": TransformationType.STATISTICAL_IMPUTATION,
        "heuristic_estimate": TransformationType.HEURISTIC_ESTIMATE,
        "unknown": TransformationType.UNKNOWN
    }

    transformation_chain = []
    if transformations:
        for transform_str in transformations:
            transform_enum = transform_mapping.get(
                transform_str.lower(),
                TransformationType.UNKNOWN
            )
            transformation_chain.append(transform_enum)

    # Extract validation results
    rules_passed = 0
    rules_total = 0
    if validation_result:
        rules_passed = validation_result.get('passed', 0)
        rules_total = validation_result.get('total', 0)

    # Calculate trust score
    result = default_calculator.calculate_trust_score(
        source_type=source_enum,
        data_age_days=data_age_days,
        transformation_chain=transformation_chain,
        model_confidence=model_confidence,
        rules_passed=rules_passed,
        rules_total=rules_total
    )

    return result
