"""Tests for PropertyRecord and related models"""

from datetime import datetime
import pytest
from pydantic import ValidationError

from contracts import PropertyRecord, Address, Geo, Owner, Attributes, Provenance, OwnerType


def test_address_validation():
    """Test address creation and validation"""
    addr = Address(
        line1="123 Main St",
        city="Las Vegas",
        state="NV",
        zip="89101"
    )
    assert addr.to_single_line() == "123 Main St, Las Vegas, NV 89101"


def test_address_with_unit():
    """Test address with unit/apt"""
    addr = Address(
        line1="123 Main St",
        line2="Apt 4B",
        city="Las Vegas",
        state="NV",
        zip="89101"
    )
    assert addr.to_single_line() == "123 Main St, Apt 4B, Las Vegas, NV 89101"


def test_geo_lat_lng_bounds():
    """Test geographic coordinate validation"""
    # Valid coords
    geo = Geo(lat=36.1699, lng=-115.1398)
    assert geo.lat == 36.1699

    # Invalid latitude
    with pytest.raises(ValidationError):
        Geo(lat=91.0, lng=0.0)

    # Invalid longitude
    with pytest.raises(ValidationError):
        Geo(lat=0.0, lng=181.0)


def test_property_record_minimal():
    """Test minimal property record creation"""
    record = PropertyRecord(
        apn="203-656-44",
        address=Address(
            line1="123 Main St",
            city="Las Vegas",
            state="NV",
            zip="89101"
        ),
        source="test_spider",
        source_id="test-123"
    )

    assert record.apn == "203-656-44"
    assert record.address.city == "Las Vegas"
    assert record.geo is None
    assert record.owner is None
    assert len(record.provenance) == 0


def test_property_record_with_provenance():
    """Test provenance tracking"""
    record = PropertyRecord(
        apn="203-656-44",
        address=Address(line1="123 Main St", city="Las Vegas", state="NV", zip="89101"),
        source="test",
        source_id="test-123",
        attrs=Attributes(beds=3, baths=2.0, sqft=1800)
    )

    # Add provenance
    prov = Provenance(
        field="attrs.beds",
        source="attom",
        fetched_at=datetime.utcnow(),
        confidence=0.95,
        cost_cents=5
    )
    record.add_provenance(prov)

    assert len(record.provenance) == 1
    assert record.get_provenance("attrs.beds") is not None
    assert record.get_provenance("attrs.beds").source == "attom"
    assert record.get_provenance("attrs.baths") is None


def test_property_record_provenance_update():
    """Test that adding provenance for same field updates it"""
    record = PropertyRecord(
        apn="203-656-44",
        address=Address(line1="123 Main St", city="Las Vegas", state="NV", zip="89101"),
        source="test",
        source_id="test-123"
    )

    # Add initial provenance
    prov1 = Provenance(field="attrs.beds", source="source1", fetched_at=datetime.utcnow())
    record.add_provenance(prov1)
    assert len(record.provenance) == 1

    # Update with new source
    prov2 = Provenance(field="attrs.beds", source="source2", fetched_at=datetime.utcnow())
    record.add_provenance(prov2)

    # Should still be 1 provenance entry, but updated
    assert len(record.provenance) == 1
    assert record.get_provenance("attrs.beds").source == "source2"


def test_attributes_validation():
    """Test property attributes validation"""
    attrs = Attributes(
        beds=3,
        baths=2.5,
        sqft=1800,
        lot_sqft=7200,
        year_built=1985,
        stories=2,
        garage_spaces=2,
        pool=True
    )

    assert attrs.beds == 3
    assert attrs.baths == 2.5
    assert attrs.pool is True

    # Invalid values should raise validation error
    with pytest.raises(ValidationError):
        Attributes(beds=-1)  # Negative beds

    with pytest.raises(ValidationError):
        Attributes(year_built=1600)  # Too old
