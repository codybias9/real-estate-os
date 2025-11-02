"""Tests for enrichment plugins"""

from uuid import uuid4
import pytest

# Import contracts
import sys
sys.path.insert(0, '/home/user/real-estate-os/packages/contracts/src')
from contracts import PropertyRecord, Address, Geo, Attributes

from enrichment_hub.plugins import GeocodePlugin, BasicAttrsPlugin, PluginPriority


@pytest.mark.asyncio
async def test_geocode_plugin_can_enrich():
    """Test geocode plugin can_enrich logic"""
    plugin = GeocodePlugin(mock=True)

    # Can enrich: has address, no geo
    record1 = PropertyRecord(
        apn="123",
        address=Address(line1="123 Main St", city="Las Vegas", state="NV", zip="89101"),
        source="test",
        source_id="test-1"
    )
    assert plugin.can_enrich(record1) is True

    # Cannot enrich: already has geo
    record2 = PropertyRecord(
        apn="123",
        address=Address(line1="123 Main St", city="Las Vegas", state="NV", zip="89101"),
        geo=Geo(lat=36.1, lng=-115.1),
        source="test",
        source_id="test-2"
    )
    assert plugin.can_enrich(record2) is False

    # Test that address is required (PropertyRecord won't allow None for address)
    # So we skip this test case as the schema enforces the constraint


@pytest.mark.asyncio
async def test_geocode_plugin_enrich():
    """Test geocode plugin enrichment"""
    plugin = GeocodePlugin(mock=True)

    record = PropertyRecord(
        apn="123-456-78",
        address=Address(line1="123 Main St", city="Las Vegas", state="NV", zip="89101"),
        source="test",
        source_id="test-1"
    )

    result = await plugin.enrich(record)

    assert result.success is True
    assert result.plugin_name == "geocode"
    assert "geo" in result.fields_updated
    assert len(result.provenance_added) == 1

    # Check record was updated
    assert record.geo is not None
    assert record.geo.lat != 0
    assert record.geo.lng != 0
    assert record.geo.accuracy == "mock"

    # Check provenance
    prov = record.get_provenance("geo")
    assert prov is not None
    assert prov.source == "geocode"
    assert prov.confidence == 0.85


@pytest.mark.asyncio
async def test_geocode_plugin_deterministic():
    """Test that geocoding is deterministic for same address"""
    plugin = GeocodePlugin(mock=True)

    address = Address(line1="456 Oak Ave", city="Las Vegas", state="NV", zip="89102")

    record1 = PropertyRecord(apn="123", address=address, source="test", source_id="1")
    record2 = PropertyRecord(apn="456", address=address, source="test", source_id="2")

    await plugin.enrich(record1)
    await plugin.enrich(record2)

    # Same address should produce same coordinates
    assert record1.geo.lat == record2.geo.lat
    assert record1.geo.lng == record2.geo.lng


@pytest.mark.asyncio
async def test_geocode_plugin_priority():
    """Test geocode plugin has CRITICAL priority"""
    plugin = GeocodePlugin(mock=True)
    assert plugin.priority == PluginPriority.CRITICAL


@pytest.mark.asyncio
async def test_basic_attrs_plugin_can_enrich():
    """Test basic_attrs plugin can_enrich logic"""
    plugin = BasicAttrsPlugin(mock=True)

    # Can enrich: has APN, no attrs
    record1 = PropertyRecord(
        apn="123",
        address=Address(line1="123 Main St", city="Las Vegas", state="NV", zip="89101"),
        source="test",
        source_id="test-1"
    )
    assert plugin.can_enrich(record1) is True

    # Can enrich: has APN, attrs missing key fields
    record2 = PropertyRecord(
        apn="123",
        address=Address(line1="123 Main St", city="Las Vegas", state="NV", zip="89101"),
        attrs=Attributes(year_built=2000),  # Missing beds, baths, sqft
        source="test",
        source_id="test-2"
    )
    assert plugin.can_enrich(record2) is True

    # Cannot enrich: attrs complete
    record3 = PropertyRecord(
        apn="123",
        address=Address(line1="123 Main St", city="Las Vegas", state="NV", zip="89101"),
        attrs=Attributes(beds=3, baths=2.0, sqft=1800),
        source="test",
        source_id="test-3"
    )
    assert plugin.can_enrich(record3) is False


@pytest.mark.asyncio
async def test_basic_attrs_plugin_enrich():
    """Test basic_attrs plugin enrichment"""
    plugin = BasicAttrsPlugin(mock=True)

    record = PropertyRecord(
        apn="203-656-44",
        address=Address(line1="123 Main St", city="Las Vegas", state="NV", zip="89101"),
        source="test",
        source_id="test-1"
    )

    result = await plugin.enrich(record)

    assert result.success is True
    assert result.plugin_name == "basic_attrs"
    assert len(result.fields_updated) > 0
    assert all(f.startswith("attrs.") for f in result.fields_updated)

    # Check record was updated
    assert record.attrs is not None
    assert record.attrs.beds is not None
    assert record.attrs.baths is not None
    assert record.attrs.sqft is not None
    assert record.attrs.lot_sqft is not None
    assert record.attrs.year_built is not None

    # Check provenance for each field
    for field in result.fields_updated:
        prov = record.get_provenance(field)
        assert prov is not None
        assert prov.source == "basic_attrs"


@pytest.mark.asyncio
async def test_basic_attrs_plugin_deterministic():
    """Test that attributes are deterministic for same APN"""
    plugin = BasicAttrsPlugin(mock=True)

    apn = "203-656-44"
    record1 = PropertyRecord(
        apn=apn,
        address=Address(line1="123 Main St", city="Las Vegas", state="NV", zip="89101"),
        source="test",
        source_id="1"
    )
    record2 = PropertyRecord(
        apn=apn,
        address=Address(line1="456 Oak Ave", city="Las Vegas", state="NV", zip="89102"),
        source="test",
        source_id="2"
    )

    await plugin.enrich(record1)
    await plugin.enrich(record2)

    # Same APN should produce same attributes
    assert record1.attrs.beds == record2.attrs.beds
    assert record1.attrs.baths == record2.attrs.baths
    assert record1.attrs.sqft == record2.attrs.sqft


@pytest.mark.asyncio
async def test_basic_attrs_plugin_merge():
    """Test that plugin merges with existing attributes"""
    plugin = BasicAttrsPlugin(mock=True)

    record = PropertyRecord(
        apn="203-656-44",
        address=Address(line1="123 Main St", city="Las Vegas", state="NV", zip="89101"),
        attrs=Attributes(year_built=1985, pool=True),  # Has some attrs already
        source="test",
        source_id="test-1"
    )

    await plugin.enrich(record)

    # Should have both original and new attributes
    assert record.attrs.year_built == 1985  # Original value preserved
    assert record.attrs.pool is True  # Original value preserved
    assert record.attrs.beds is not None  # New value added
    assert record.attrs.baths is not None  # New value added


@pytest.mark.asyncio
async def test_basic_attrs_reasonable_values():
    """Test that mock attributes are reasonable for a house"""
    plugin = BasicAttrsPlugin(mock=True)

    record = PropertyRecord(
        apn="test-apn",
        address=Address(line1="123 Main St", city="Las Vegas", state="NV", zip="89101"),
        source="test",
        source_id="test-1"
    )

    await plugin.enrich(record)

    attrs = record.attrs

    # Check reasonable ranges for single-family home
    assert 2 <= attrs.beds <= 5
    assert 1.0 <= attrs.baths <= 3.5
    assert 1200 <= attrs.sqft <= 3500
    assert 5000 <= attrs.lot_sqft <= 10000
    assert 1970 <= attrs.year_built <= 2020
    assert attrs.stories in [1, 2]
    assert 0 <= attrs.garage_spaces <= 3
    assert isinstance(attrs.pool, bool)
