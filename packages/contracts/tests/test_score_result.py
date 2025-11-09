"""Tests for ScoreResult"""

from datetime import datetime
import pytest
from pydantic import ValidationError

from contracts import ScoreResult, ScoreReason, ScoreDirection


def test_score_reason_creation():
    """Test score reason creation"""
    reason = ScoreReason(
        feature="comp_delta",
        weight=0.35,
        direction=ScoreDirection.POSITIVE,
        note="Below median by 12%",
        raw_value=250000,
        benchmark=285000
    )

    assert reason.feature == "comp_delta"
    assert reason.weight == 0.35
    assert reason.direction == ScoreDirection.POSITIVE


def test_score_result_validation():
    """Test score result validation"""
    reasons = [
        ScoreReason(feature="comp_delta", weight=0.35, direction=ScoreDirection.POSITIVE, note="Below median"),
        ScoreReason(feature="days_on_market", weight=0.25, direction=ScoreDirection.POSITIVE, note="Fresh listing"),
        ScoreReason(feature="cap_rate", weight=0.20, direction=ScoreDirection.POSITIVE, note="Strong cash flow"),
    ]

    result = ScoreResult(
        score=78,
        reasons=reasons,
        computed_at=datetime.utcnow().isoformat()
    )

    assert result.score == 78
    assert len(result.reasons) == 3
    assert result.validate_weights() is True


def test_score_result_bounds():
    """Test score bounds enforcement"""
    reasons = [
        ScoreReason(feature="test", weight=0.8, direction=ScoreDirection.POSITIVE, note="Test")
    ]

    # Score too high
    with pytest.raises(ValidationError):
        ScoreResult(score=101, reasons=reasons, computed_at=datetime.utcnow().isoformat())

    # Score too low
    with pytest.raises(ValidationError):
        ScoreResult(score=-1, reasons=reasons, computed_at=datetime.utcnow().isoformat())


def test_score_result_requires_minimum_reasons():
    """Test that at least 3 reasons are required"""
    # Too few reasons
    with pytest.raises(ValidationError):
        ScoreResult(
            score=50,
            reasons=[
                ScoreReason(feature="test", weight=0.5, direction=ScoreDirection.POSITIVE, note="Test")
            ],
            computed_at=datetime.utcnow().isoformat()
        )


def test_score_result_weight_validation():
    """Test weight validation"""
    # Low total weight (< 0.7)
    reasons_low = [
        ScoreReason(feature="f1", weight=0.2, direction=ScoreDirection.POSITIVE, note="Test"),
        ScoreReason(feature="f2", weight=0.2, direction=ScoreDirection.POSITIVE, note="Test"),
        ScoreReason(feature="f3", weight=0.2, direction=ScoreDirection.POSITIVE, note="Test"),
    ]

    result_low = ScoreResult(score=50, reasons=reasons_low, computed_at=datetime.utcnow().isoformat())
    assert result_low.validate_weights() is False

    # Good total weight
    reasons_good = [
        ScoreReason(feature="f1", weight=0.35, direction=ScoreDirection.POSITIVE, note="Test"),
        ScoreReason(feature="f2", weight=0.30, direction=ScoreDirection.POSITIVE, note="Test"),
        ScoreReason(feature="f3", weight=0.25, direction=ScoreDirection.POSITIVE, note="Test"),
    ]

    result_good = ScoreResult(score=75, reasons=reasons_good, computed_at=datetime.utcnow().isoformat())
    assert result_good.validate_weights() is True
