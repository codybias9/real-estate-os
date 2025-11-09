"""Tests for Discovery.Resolver"""

from uuid import uuid4
import pytest

from resolver import DiscoveryResolver, IntakeStatus, IntakeResult


def test_compute_apn_hash():
    """Test APN hash computation and normalization"""
    # Same APN in different formats should produce same hash
    hash1 = DiscoveryResolver.compute_apn_hash("203-656-44")
    hash2 = DiscoveryResolver.compute_apn_hash("203 656 44")
    hash3 = DiscoveryResolver.compute_apn_hash("20365644")
    hash4 = DiscoveryResolver.compute_apn_hash("203_656_44")

    assert hash1 == hash2 == hash3 == hash4
    assert len(hash1) == 16  # Truncated SHA256


def test_normalize_address_complete():
    """Test address normalization with complete data"""
    raw = {
        "street": "123 Main St",
        "city": "Las Vegas",
        "state": "NV",
        "zip": "89101"
    }

    addr = DiscoveryResolver.normalize_address(raw)

    assert addr is not None
    assert addr.line1 == "123 Main St"
    assert addr.city == "Las Vegas"
    assert addr.state == "NV"
    assert addr.zip == "89101"


def test_normalize_address_with_unit():
    """Test address with unit/apt"""
    raw = {
        "address": "456 Oak Ave",
        "unit": "Apt 2B",
        "city": "Henderson",
        "state": "nv",
        "zipcode": "89052"
    }

    addr = DiscoveryResolver.normalize_address(raw)

    assert addr is not None
    assert addr.line1 == "456 Oak Ave"
    assert addr.line2 == "Apt 2B"
    assert addr.state == "NV"  # Should be uppercase


def test_normalize_address_missing_fields():
    """Test address normalization with missing required fields"""
    raw = {
        "street": "123 Main St",
        "city": "Las Vegas"
        # Missing state and zip
    }

    addr = DiscoveryResolver.normalize_address(raw)
    assert addr is None


def test_normalize_geo_valid():
    """Test geo normalization with valid coordinates"""
    raw = {
        "latitude": 36.1699,
        "longitude": -115.1398,
        "accuracy": "rooftop"
    }

    geo = DiscoveryResolver.normalize_geo(raw)

    assert geo is not None
    assert geo.lat == 36.1699
    assert geo.lng == -115.1398
    assert geo.accuracy == "rooftop"


def test_normalize_geo_missing():
    """Test geo normalization with missing coordinates"""
    raw = {"accuracy": "rooftop"}

    geo = DiscoveryResolver.normalize_geo(raw)
    assert geo is None


def test_normalize_owner_person():
    """Test owner normalization for person"""
    raw = {"name": "John Doe"}

    owner = DiscoveryResolver.normalize_owner(raw)

    assert owner is not None
    assert owner.name == "John Doe"
    assert owner.type.value == "person"


def test_normalize_owner_company():
    """Test owner normalization for company"""
    raw = {"owner_name": "ABC Properties LLC"}

    owner = DiscoveryResolver.normalize_owner(raw)

    assert owner is not None
    assert owner.name == "ABC Properties LLC"
    assert owner.type.value == "llc"


def test_normalize_owner_trust():
    """Test owner normalization for trust"""
    raw = {"name": "Smith Family Trust"}

    owner = DiscoveryResolver.normalize_owner(raw)

    assert owner is not None
    assert owner.type.value == "trust"


def test_normalize_attributes():
    """Test property attributes normalization"""
    raw = {
        "beds": "3",
        "baths": "2.5",
        "sqft": "1800",
        "lot_sqft": "7200",
        "year_built": "1985",
        "pool": True
    }

    attrs = DiscoveryResolver.normalize_attributes(raw)

    assert attrs is not None
    assert attrs.beds == 3
    assert attrs.baths == 2.5
    assert attrs.sqft == 1800
    assert attrs.lot_sqft == 7200
    assert attrs.year_built == 1985
    assert attrs.pool is True


def test_normalize_attributes_empty():
    """Test attributes normalization with no data"""
    raw = {}

    attrs = DiscoveryResolver.normalize_attributes(raw)
    assert attrs is None  # All None values


def test_normalize_complete_record():
    """Test full record normalization"""
    tenant_id = uuid4()
    resolver = DiscoveryResolver(tenant_id)

    raw_data = {
        "apn": "203-656-44",
        "address": {
            "street": "123 Main St",
            "city": "Las Vegas",
            "state": "NV",
            "zip": "89101"
        },
        "geo": {
            "lat": 36.1699,
            "lng": -115.1398
        },
        "owner": {
            "name": "John Doe"
        },
        "attributes": {
            "beds": 3,
            "baths": 2.0,
            "sqft": 1800
        },
        "url": "https://example.com/property/123"
    }

    record = resolver.normalize(raw_data, "test_spider", "test-123")

    assert record is not None
    assert record.apn == "203-656-44"
    assert record.address.city == "Las Vegas"
    assert record.geo.lat == 36.1699
    assert record.owner.name == "John Doe"
    assert record.attrs.beds == 3
    assert record.source == "test_spider"
    assert record.source_id == "test-123"


def test_normalize_missing_apn():
    """Test normalization fails without APN"""
    tenant_id = uuid4()
    resolver = DiscoveryResolver(tenant_id)

    raw_data = {
        "address": {
            "street": "123 Main St",
            "city": "Las Vegas",
            "state": "NV",
            "zip": "89101"
        }
    }

    record = resolver.normalize(raw_data, "test_spider", "test-123")
    assert record is None


def test_process_intake_success():
    """Test successful intake processing"""
    tenant_id = uuid4()
    resolver = DiscoveryResolver(tenant_id)

    raw_data = {
        "apn": "203-656-44",
        "address": {
            "street": "123 Main St",
            "city": "Las Vegas",
            "state": "NV",
            "zip": "89101"
        }
    }

    result = resolver.process_intake(raw_data, "test_spider", "test-123")

    assert result.status == IntakeStatus.NEW
    assert result.property_record is not None
    assert result.apn_hash
    assert "Successfully normalized" in result.reason


def test_process_intake_duplicate():
    """Test duplicate detection"""
    tenant_id = uuid4()
    resolver = DiscoveryResolver(tenant_id)

    raw_data = {
        "apn": "203-656-44",
        "address": {
            "street": "123 Main St",
            "city": "Las Vegas",
            "state": "NV",
            "zip": "89101"
        }
    }

    # First intake
    result1 = resolver.process_intake(raw_data, "test_spider", "test-123")
    existing_hashes = {result1.apn_hash}

    # Second intake with same APN
    result2 = resolver.process_intake(raw_data, "test_spider", "test-456", existing_hashes)

    assert result2.status == IntakeStatus.DUPLICATE
    assert "already exists" in result2.reason


def test_process_intake_rejected():
    """Test rejected intake (missing required fields)"""
    tenant_id = uuid4()
    resolver = DiscoveryResolver(tenant_id)

    raw_data = {
        "apn": "203-656-44"
        # Missing address
    }

    result = resolver.process_intake(raw_data, "test_spider", "test-123")

    assert result.status == IntakeStatus.REJECTED
    assert result.property_record is None
    assert "Failed to normalize" in result.reason


def test_create_intake_event():
    """Test intake event envelope creation"""
    tenant_id = uuid4()
    resolver = DiscoveryResolver(tenant_id)

    raw_data = {
        "apn": "203-656-44",
        "address": {
            "street": "123 Main St",
            "city": "Las Vegas",
            "state": "NV",
            "zip": "89101"
        }
    }

    result = resolver.process_intake(raw_data, "test_spider", "test-123")
    envelope = resolver.create_intake_event(result)

    assert envelope.subject == "event.discovery.intake"
    assert envelope.tenant_id == tenant_id
    assert envelope.idempotency_key == "test_spider:test-123"
    assert envelope.schema_version == "1.0"
    assert envelope.payload == result.property_record


def test_create_intake_event_rejected_fails():
    """Test that creating event for rejected record raises error"""
    tenant_id = uuid4()
    resolver = DiscoveryResolver(tenant_id)

    raw_data = {"apn": "123"}  # Missing address
    result = resolver.process_intake(raw_data, "test_spider", "test-123")

    with pytest.raises(ValueError, match="rejected"):
        resolver.create_intake_event(result)


def test_idempotency_key_format():
    """Test idempotency key follows source:source_id format"""
    tenant_id = uuid4()
    resolver = DiscoveryResolver(tenant_id)

    raw_data = {
        "apn": "203-656-44",
        "address": {
            "street": "123 Main St",
            "city": "Las Vegas",
            "state": "NV",
            "zip": "89101"
        }
    }

    result = resolver.process_intake(raw_data, "clark_county", "prop-456")
    envelope = resolver.create_intake_event(result)

    assert envelope.idempotency_key == "clark_county:prop-456"
