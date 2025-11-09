"""Tests for Score Engine"""

from uuid import uuid4
import pytest

import sys
sys.path.insert(0, '/home/user/real-estate-os/packages/contracts/src')
from contracts import PropertyRecord, Address, Attributes, Geo

from score_engine import ScoreEngine


def test_score_engine_creation():
    """Test score engine creation"""
    tenant_id = uuid4()
    engine = ScoreEngine(tenant_id)

    assert engine.tenant_id == tenant_id
    assert engine.model_version == "deterministic-v1"


def test_score_complete_property():
    """Test scoring a complete property"""
    tenant_id = uuid4()
    engine = ScoreEngine(tenant_id)

    record = PropertyRecord(
        apn="203-656-44",
        address=Address(line1="123 Main St", city="Las Vegas", state="NV", zip="89101"),
        geo=Geo(lat=36.1699, lng=-115.1398),
        attrs=Attributes(
            beds=3,
            baths=2.0,
            sqft=1800,
            lot_sqft=6500,
            year_built=2010
        ),
        source="test",
        source_id="test-1"
    )

    result = engine.score(record)

    assert result.success is True
    assert result.score_result is not None
    assert 0 <= result.score_result.score <= 100
    assert len(result.score_result.reasons) == 5  # 5 factors
    assert result.score_result.model_version == "deterministic-v1"


def test_score_reasons_have_weights():
    """Test that all reasons have proper weights"""
    tenant_id = uuid4()
    engine = ScoreEngine(tenant_id)

    record = PropertyRecord(
        apn="test",
        address=Address(line1="123 Main St", city="Las Vegas", state="NV", zip="89101"),
        attrs=Attributes(beds=3, baths=2.0, sqft=1800, year_built=2010),
        source="test",
        source_id="test-1"
    )

    result = engine.score(record)

    # Check that weights sum to ~1.0
    total_weight = sum(r.weight for r in result.score_result.reasons)
    assert 0.9 <= total_weight <= 1.1

    # Check that reasons are sorted by weight (descending)
    weights = [r.weight for r in result.score_result.reasons]
    assert weights == sorted(weights, reverse=True)


def test_score_missing_attributes_fails():
    """Test that scoring fails without attributes"""
    tenant_id = uuid4()
    engine = ScoreEngine(tenant_id)

    record = PropertyRecord(
        apn="test",
        address=Address(line1="123 Main St", city="Las Vegas", state="NV", zip="89101"),
        attrs=None,  # Missing attributes
        source="test",
        source_id="test-1"
    )

    result = engine.score(record)

    assert result.success is False
    assert "Missing property attributes" in result.error


def test_score_deterministic():
    """Test that scoring is deterministic"""
    tenant_id = uuid4()
    engine = ScoreEngine(tenant_id)

    record = PropertyRecord(
        apn="test",
        address=Address(line1="123 Main St", city="Las Vegas", state="NV", zip="89101"),
        geo=Geo(lat=36.17, lng=-115.14),
        attrs=Attributes(
            beds=3,
            baths=2.0,
            sqft=1800,
            lot_sqft=6500,
            year_built=2010
        ),
        source="test",
        source_id="test-1"
    )

    result1 = engine.score(record)
    result2 = engine.score(record)

    # Same inputs should produce same score
    assert result1.score_result.score == result2.score_result.score

    # Same reasons
    assert len(result1.score_result.reasons) == len(result2.score_result.reasons)


def test_score_new_property_higher():
    """Test that newer properties score higher on condition"""
    tenant_id = uuid4()
    engine = ScoreEngine(tenant_id)

    # Newer property
    record_new = PropertyRecord(
        apn="new",
        address=Address(line1="123 Main St", city="Las Vegas", state="NV", zip="89101"),
        attrs=Attributes(beds=3, baths=2.0, sqft=1800, year_built=2020),
        source="test",
        source_id="new"
    )

    # Older property
    record_old = PropertyRecord(
        apn="old",
        address=Address(line1="456 Oak Ave", city="Las Vegas", state="NV", zip="89101"),
        attrs=Attributes(beds=3, baths=2.0, sqft=1800, year_built=1970),
        source="test",
        source_id="old"
    )

    result_new = engine.score(record_new)
    result_old = engine.score(record_old)

    # Newer should score higher
    assert result_new.score_result.score > result_old.score_result.score


def test_create_score_event():
    """Test score event envelope creation"""
    tenant_id = uuid4()
    engine = ScoreEngine(tenant_id)

    record = PropertyRecord(
        apn="test",
        address=Address(line1="123 Main St", city="Las Vegas", state="NV", zip="89101"),
        attrs=Attributes(beds=3, baths=2.0, sqft=1800, year_built=2010),
        source="test_spider",
        source_id="test-123"
    )

    result = engine.score(record)
    envelope = engine.create_score_event(result)

    assert envelope.subject == "event.score.created"
    assert envelope.tenant_id == tenant_id
    assert envelope.idempotency_key == "test_spider:test-123:scored"
    assert envelope.schema_version == "1.0"
    assert envelope.payload == result.score_result


def test_create_score_event_failed_scoring_raises():
    """Test that creating event for failed scoring raises error"""
    tenant_id = uuid4()
    engine = ScoreEngine(tenant_id)

    record = PropertyRecord(
        apn="test",
        address=Address(line1="123 Main St", city="Las Vegas", state="NV", zip="89101"),
        attrs=None,  # Will cause scoring to fail
        source="test",
        source_id="test-1"
    )

    result = engine.score(record)

    with pytest.raises(ValueError, match="failed scoring"):
        engine.create_score_event(result)


def test_score_validates_weight_sum():
    """Test that score result validates weight sum"""
    tenant_id = uuid4()
    engine = ScoreEngine(tenant_id)

    record = PropertyRecord(
        apn="test",
        address=Address(line1="123 Main St", city="Las Vegas", state="NV", zip="89101"),
        attrs=Attributes(beds=3, baths=2.0, sqft=1800, year_built=2010),
        source="test",
        source_id="test-1"
    )

    result = engine.score(record)

    # ScoreResult has validate_weights method
    assert result.score_result.validate_weights() is True


def test_score_range_bounds():
    """Test that score is always in 0-100 range"""
    tenant_id = uuid4()
    engine = ScoreEngine(tenant_id)

    # Various property configurations
    configs = [
        {"beds": 1, "baths": 1.0, "sqft": 800, "year_built": 1960},
        {"beds": 5, "baths": 4.0, "sqft": 4000, "year_built": 2023},
        {"beds": 3, "baths": 2.0, "sqft": 1800, "year_built": 2010},
    ]

    for attrs_data in configs:
        record = PropertyRecord(
            apn="test",
            address=Address(line1="123 Main St", city="Las Vegas", state="NV", zip="89101"),
            attrs=Attributes(**attrs_data),
            source="test",
            source_id="test-1"
        )

        result = engine.score(record)

        assert 0 <= result.score_result.score <= 100
