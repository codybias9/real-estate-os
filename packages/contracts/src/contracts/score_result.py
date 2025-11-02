"""
ScoreResult - Explainable property scoring
Deterministic score (0-100) with contribution breakdown
"""

from enum import Enum
from pydantic import BaseModel, Field


class ScoreDirection(str, Enum):
    """Score contribution direction"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class ScoreReason(BaseModel):
    """
    Single scoring factor contribution.

    Provides transparency: "Why did this property score 78?"
    """

    feature: str = Field(..., description="Feature name (e.g., 'comp_delta', 'days_on_market')")
    weight: float = Field(..., ge=0, le=1, description="Contribution weight (0-1)")
    direction: ScoreDirection = Field(..., description="Impact direction")
    note: str = Field(..., description="Human-readable explanation")

    # Optional: raw values for drill-down
    raw_value: float | None = Field(None, description="Raw feature value")
    benchmark: float | None = Field(None, description="Benchmark/threshold value")


class ScoreResult(BaseModel):
    """
    Property investment score with explainability.

    Requirements:
    - Score range: 0-100 (higher = better opportunity)
    - Reasons: 3-7 top contributions (sum of weights should be ~1.0)
    - Monotonicity: same inputs → same score (deterministic)
    """

    score: int = Field(..., ge=0, le=100, description="Investment score (0-100)")
    reasons: list[ScoreReason] = Field(
        ...,
        min_length=3,
        max_length=7,
        description="Top scoring factors (descending by weight)"
    )
    model_version: str = Field(default="deterministic-v1", description="Scoring model version")
    computed_at: str = Field(..., description="Computation timestamp (ISO-8601)")

    def validate_weights(self) -> bool:
        """Check that top reasons explain most of the score"""
        total_weight = sum(r.weight for r in self.reasons)
        return 0.7 <= total_weight <= 1.1  # Allow some slack
