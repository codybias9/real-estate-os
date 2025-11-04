"""
Score Engine - Deterministic property investment scoring
Single producer of: event.score.created
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

try:
    from contracts import PropertyRecord, ScoreResult, ScoreReason, ScoreDirection, Envelope
except ImportError:
    import sys
    sys.path.insert(0, '/home/user/real-estate-os/packages/contracts/src')
    from contracts import PropertyRecord, ScoreResult, ScoreReason, ScoreDirection, Envelope


class ScoringResult(BaseModel):
    """Result of scoring operation"""
    property_record: PropertyRecord
    score_result: ScoreResult | None
    success: bool
    error: str | None = None


class ScoreEngine:
    """
    Deterministic property investment scoring engine.

    Scoring Factors (simplified model for MVP):
    1. Property Condition (30%): Based on year_built and estimated condition
    2. Location Quality (25%): Based on lat/lng proximity to downtown
    3. Value Potential (20%): Based on price-to-sqft ratio
    4. Size Appropriateness (15%): Beds/baths/sqft in target range
    5. Lot Size (10%): Lot sqft desirability

    Future: Replace with trained LightGBM model on historical deal data
    """

    def __init__(self, tenant_id: UUID, model_version: str = "deterministic-v1"):
        self.tenant_id = tenant_id
        self.model_version = model_version

    def score(self, record: PropertyRecord) -> ScoringResult:
        """
        Score a property record.

        Args:
            record: Enriched PropertyRecord with attrs

        Returns:
            ScoringResult with 0-100 score and 3-7 reasons
        """
        try:
            # Check required fields
            if not record.attrs:
                return ScoringResult(
                    property_record=record,
                    score_result=None,
                    success=False,
                    error="Missing property attributes (required for scoring)"
                )

            # Calculate individual factor scores
            factors = []

            # 1. Property Condition (30%)
            condition_score, condition_reason = self._score_condition(record)
            factors.append((condition_score, 0.30, condition_reason))

            # 2. Location Quality (25%)
            location_score, location_reason = self._score_location(record)
            factors.append((location_score, 0.25, location_reason))

            # 3. Value Potential (20%)
            value_score, value_reason = self._score_value(record)
            factors.append((value_score, 0.20, value_reason))

            # 4. Size Appropriateness (15%)
            size_score, size_reason = self._score_size(record)
            factors.append((size_score, 0.15, size_reason))

            # 5. Lot Size (10%)
            lot_score, lot_reason = self._score_lot(record)
            factors.append((lot_score, 0.10, lot_reason))

            # Calculate weighted score (0-100)
            weighted_score = sum(score * weight for score, weight, _ in factors)
            final_score = int(round(weighted_score))

            # Build reasons list (sorted by weight)
            reasons = []
            for score, weight, reason_data in sorted(factors, key=lambda x: x[1], reverse=True):
                direction = ScoreDirection.POSITIVE if score > 50 else ScoreDirection.NEGATIVE
                reasons.append(ScoreReason(
                    feature=reason_data['feature'],
                    weight=weight,
                    direction=direction,
                    note=reason_data['note'],
                    raw_value=reason_data.get('raw_value'),
                    benchmark=reason_data.get('benchmark')
                ))

            score_result = ScoreResult(
                score=final_score,
                reasons=reasons,
                model_version=self.model_version,
                computed_at=datetime.utcnow().isoformat()
            )

            return ScoringResult(
                property_record=record,
                score_result=score_result,
                success=True
            )

        except Exception as e:
            return ScoringResult(
                property_record=record,
                score_result=None,
                success=False,
                error=str(e)
            )

    def _score_condition(self, record: PropertyRecord) -> tuple[float, dict[str, Any]]:
        """Score property condition (0-100) based on age"""
        year_built = record.attrs.year_built or 1980
        current_year = datetime.utcnow().year
        age = current_year - year_built

        # Newer is better, but not linearly
        if age < 5:
            score = 95
            note = f"Excellent condition (built {year_built}, {age} years old)"
        elif age < 15:
            score = 80
            note = f"Good condition (built {year_built}, {age} years old)"
        elif age < 30:
            score = 65
            note = f"Average condition (built {year_built}, {age} years old)"
        elif age < 50:
            score = 45
            note = f"Dated construction (built {year_built}, {age} years old)"
        else:
            score = 30
            note = f"Significant age concerns (built {year_built}, {age} years old)"

        return score, {
            'feature': 'property_condition',
            'note': note,
            'raw_value': age,
            'benchmark': 15  # Target age
        }

    def _score_location(self, record: PropertyRecord) -> tuple[float, dict[str, Any]]:
        """Score location quality based on proximity to downtown Las Vegas"""
        if not record.geo:
            # Default to neutral if no geo data
            return 50.0, {
                'feature': 'location_quality',
                'note': 'Location data unavailable',
                'raw_value': None,
                'benchmark': None
            }

        # Downtown Las Vegas coords
        downtown_lat, downtown_lng = 36.1699, -115.1398

        # Calculate rough distance (not precise, but deterministic)
        lat_diff = abs(record.geo.lat - downtown_lat)
        lng_diff = abs(record.geo.lng - downtown_lng)
        distance = (lat_diff ** 2 + lng_diff ** 2) ** 0.5  # Euclidean distance

        # Score based on distance (closer is generally better in Vegas)
        if distance < 0.05:  # Very close
            score = 85
            note = "Prime location (central Las Vegas)"
        elif distance < 0.10:
            score = 75
            note = "Good location (near downtown)"
        elif distance < 0.20:
            score = 65
            note = "Acceptable location (suburban)"
        else:
            score = 50
            note = "Distant location (outer suburbs)"

        return score, {
            'feature': 'location_quality',
            'note': note,
            'raw_value': round(distance, 4),
            'benchmark': 0.10
        }

    def _score_value(self, record: PropertyRecord) -> tuple[float, dict[str, Any]]:
        """Score value potential (price-to-sqft ratio)"""
        sqft = record.attrs.sqft
        if not sqft or sqft == 0:
            return 50.0, {
                'feature': 'value_potential',
                'note': 'Square footage unavailable',
                'raw_value': None,
                'benchmark': None
            }

        # Mock price based on property characteristics (in production, use actual listing price)
        # Vegas median: ~$200/sqft
        mock_price = sqft * 200  # Baseline

        price_per_sqft = mock_price / sqft

        # Score based on price per sqft (lower is better for investment)
        if price_per_sqft < 150:
            score = 90
            note = f"Excellent value (${price_per_sqft:.0f}/sqft vs $200 median)"
        elif price_per_sqft < 180:
            score = 75
            note = f"Good value (${price_per_sqft:.0f}/sqft vs $200 median)"
        elif price_per_sqft < 220:
            score = 60
            note = f"Fair value (${price_per_sqft:.0f}/sqft vs $200 median)"
        else:
            score = 40
            note = f"Above market (${price_per_sqft:.0f}/sqft vs $200 median)"

        return score, {
            'feature': 'value_potential',
            'note': note,
            'raw_value': price_per_sqft,
            'benchmark': 200.0
        }

    def _score_size(self, record: PropertyRecord) -> tuple[float, dict[str, Any]]:
        """Score size appropriateness (beds, baths, sqft in target range)"""
        beds = record.attrs.beds or 0
        baths = record.attrs.baths or 0
        sqft = record.attrs.sqft or 0

        # Target: 3-4 bed, 2-3 bath, 1500-2500 sqft (typical single-family)
        bed_score = 100 if 3 <= beds <= 4 else 70 if 2 <= beds <= 5 else 50
        bath_score = 100 if 2.0 <= baths <= 3.0 else 70 if 1.5 <= baths <= 3.5 else 50
        sqft_score = 100 if 1500 <= sqft <= 2500 else 70 if 1200 <= sqft <= 3500 else 50

        # Average
        score = (bed_score + bath_score + sqft_score) / 3

        note = f"{beds}bed/{baths}bath, {sqft}sqft"
        if score >= 90:
            note += " - ideal size for target market"
        elif score >= 70:
            note += " - acceptable size"
        else:
            note += " - non-standard size"

        return score, {
            'feature': 'size_appropriateness',
            'note': note,
            'raw_value': sqft,
            'benchmark': 2000  # Target sqft
        }

    def _score_lot(self, record: PropertyRecord) -> tuple[float, dict[str, Any]]:
        """Score lot size desirability"""
        lot_sqft = record.attrs.lot_sqft or 0

        # Vegas typical: 5000-8000 sqft lots
        if 5000 <= lot_sqft <= 8000:
            score = 85
            note = f"{lot_sqft:,} sqft lot - ideal size"
        elif 4000 <= lot_sqft <= 10000:
            score = 70
            note = f"{lot_sqft:,} sqft lot - acceptable"
        elif lot_sqft > 10000:
            score = 60
            note = f"{lot_sqft:,} sqft lot - oversized (higher maintenance)"
        elif lot_sqft > 0:
            score = 50
            note = f"{lot_sqft:,} sqft lot - small"
        else:
            score = 50
            note = "Lot size unavailable"

        return score, {
            'feature': 'lot_size',
            'note': note,
            'raw_value': lot_sqft,
            'benchmark': 6500
        }

    def create_score_event(
        self,
        result: ScoringResult,
        correlation_id: UUID | None = None,
        causation_id: UUID | None = None
    ) -> Envelope[ScoreResult]:
        """
        Create event.score.created envelope.

        This is the single producer of score events.
        """
        if not result.score_result:
            raise ValueError("Cannot create score event for failed scoring")

        envelope_id = uuid4()

        envelope = Envelope[ScoreResult](
            id=envelope_id,
            tenant_id=self.tenant_id,
            subject="event.score.created",
            schema_version="1.0",
            idempotency_key=f"{result.property_record.source}:{result.property_record.source_id}:scored",
            correlation_id=correlation_id or uuid4(),
            causation_id=causation_id or envelope_id,
            at=datetime.utcnow(),
            payload=result.score_result
        )

        return envelope
