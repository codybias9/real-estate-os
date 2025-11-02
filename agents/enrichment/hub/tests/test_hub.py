"""Tests for Enrichment Hub"""

from uuid import uuid4
import pytest

# Import contracts
import sys
sys.path.insert(0, '/home/user/real-estate-os/packages/contracts/src')
from contracts import PropertyRecord, Address, Geo

from enrichment_hub import EnrichmentHub, GeocodePlugin, BasicAttrsPlugin


@pytest.mark.asyncio
async def test_hub_register_plugin():
    """Test plugin registration"""
    tenant_id = uuid4()
    hub = EnrichmentHub(tenant_id)

    assert len(hub.plugins) == 0

    geocode = GeocodePlugin()
    hub.register_plugin(geocode)

    assert len(hub.plugins) == 1
    assert hub.plugins[0].name == "geocode"


@pytest.mark.asyncio
async def test_hub_plugin_priority_ordering():
    """Test plugins are executed in priority order"""
    tenant_id = uuid4()
    hub = EnrichmentHub(tenant_id)

    # Register in reverse priority order
    attrs = BasicAttrsPlugin()  # MEDIUM priority
    geocode = GeocodePlugin()   # CRITICAL priority

    hub.register_plugin(attrs)
    hub.register_plugin(geocode)

    # Should be sorted by priority (geocode first)
    assert hub.plugins[0].name == "geocode"
    assert hub.plugins[1].name == "basic_attrs"


@pytest.mark.asyncio
async def test_hub_enrich_single_plugin():
    """Test enrichment with single plugin"""
    tenant_id = uuid4()
    hub = EnrichmentHub(tenant_id)

    geocode = GeocodePlugin(mock=True)
    hub.register_plugin(geocode)

    record = PropertyRecord(
        apn="123",
        address=Address(line1="123 Main St", city="Las Vegas", state="NV", zip="89101"),
        source="test",
        source_id="test-1"
    )

    result = await hub.enrich(record)

    assert result.success is True
    assert len(result.plugins_executed) == 1
    assert result.plugins_executed[0].plugin_name == "geocode"
    assert result.total_fields_updated == 1
    assert result.total_provenance_added == 1
    assert record.geo is not None


@pytest.mark.asyncio
async def test_hub_enrich_multiple_plugins():
    """Test enrichment with multiple plugins"""
    tenant_id = uuid4()
    hub = EnrichmentHub(tenant_id)

    hub.register_plugin(GeocodePlugin(mock=True))
    hub.register_plugin(BasicAttrsPlugin(mock=True))

    record = PropertyRecord(
        apn="203-656-44",
        address=Address(line1="123 Main St", city="Las Vegas", state="NV", zip="89101"),
        source="test",
        source_id="test-1"
    )

    result = await hub.enrich(record)

    assert result.success is True
    assert len(result.plugins_executed) == 2
    assert result.total_fields_updated > 1
    assert result.total_provenance_added > 1

    # Both plugins should have executed
    plugin_names = [r.plugin_name for r in result.plugins_executed]
    assert "geocode" in plugin_names
    assert "basic_attrs" in plugin_names

    # Record should have both geo and attrs
    assert record.geo is not None
    assert record.attrs is not None


@pytest.mark.asyncio
async def test_hub_skips_disabled_plugins():
    """Test that disabled plugins are skipped"""
    tenant_id = uuid4()
    hub = EnrichmentHub(tenant_id)

    geocode = GeocodePlugin(mock=True)
    attrs = BasicAttrsPlugin(mock=True)

    hub.register_plugin(geocode)
    hub.register_plugin(attrs)

    # Disable geocode
    hub.disable_plugin("geocode")

    record = PropertyRecord(
        apn="123",
        address=Address(line1="123 Main St", city="Las Vegas", state="NV", zip="89101"),
        source="test",
        source_id="test-1"
    )

    result = await hub.enrich(record)

    assert result.success is True
    assert len(result.plugins_executed) == 1
    assert result.plugins_executed[0].plugin_name == "basic_attrs"
    assert record.geo is None  # Geocode was skipped
    assert record.attrs is not None


@pytest.mark.asyncio
async def test_hub_enable_disable_plugin():
    """Test enable/disable plugin functionality"""
    tenant_id = uuid4()
    hub = EnrichmentHub(tenant_id)

    geocode = GeocodePlugin(mock=True)
    hub.register_plugin(geocode)

    # Disable
    assert hub.disable_plugin("geocode") is True
    assert geocode.enabled is False

    # Enable
    assert hub.enable_plugin("geocode") is True
    assert geocode.enabled is True

    # Non-existent plugin
    assert hub.enable_plugin("nonexistent") is False
    assert hub.disable_plugin("nonexistent") is False


@pytest.mark.asyncio
async def test_hub_continues_on_plugin_failure():
    """Test that hub continues executing other plugins if one plugin can't enrich"""
    tenant_id = uuid4()
    hub = EnrichmentHub(tenant_id)

    # Create plugins
    geocode = GeocodePlugin(mock=True)
    attrs = BasicAttrsPlugin(mock=True)

    hub.register_plugin(geocode)
    hub.register_plugin(attrs)

    # Record with address and existing geo (geocode can't enrich)
    record = PropertyRecord(
        apn="123",
        address=Address(line1="123 Main St", city="Las Vegas", state="NV", zip="89101"),
        geo=Geo(lat=36.1, lng=-115.1),  # Already has geo
        source="test",
        source_id="test-1"
    )

    result = await hub.enrich(record)

    # Overall success should still be True if at least one plugin succeeded
    # basic_attrs should run successfully
    plugin_names = [r.plugin_name for r in result.plugins_executed if r.success]

    # Geocode should not run (can_enrich returns False)
    # basic_attrs should run successfully
    assert "basic_attrs" in plugin_names
    assert record.attrs is not None


@pytest.mark.asyncio
async def test_hub_create_enrichment_event():
    """Test enrichment event envelope creation"""
    tenant_id = uuid4()
    hub = EnrichmentHub(tenant_id)

    hub.register_plugin(GeocodePlugin(mock=True))

    record = PropertyRecord(
        apn="123",
        address=Address(line1="123 Main St", city="Las Vegas", state="NV", zip="89101"),
        source="test_spider",
        source_id="test-123"
    )

    result = await hub.enrich(record)
    envelope = hub.create_enrichment_event(result)

    assert envelope.subject == "event.enrichment.features"
    assert envelope.tenant_id == tenant_id
    assert envelope.idempotency_key == "test_spider:test-123:enriched"
    assert envelope.schema_version == "1.0"
    assert envelope.payload == result.property_record


@pytest.mark.asyncio
async def test_hub_duration_tracking():
    """Test that enrichment duration is tracked"""
    tenant_id = uuid4()
    hub = EnrichmentHub(tenant_id)

    hub.register_plugin(GeocodePlugin(mock=True))

    record = PropertyRecord(
        apn="123",
        address=Address(line1="123 Main St", city="Las Vegas", state="NV", zip="89101"),
        source="test",
        source_id="test-1"
    )

    result = await hub.enrich(record)

    assert result.duration_ms is not None
    assert result.duration_ms >= 0


@pytest.mark.asyncio
async def test_hub_get_plugin():
    """Test getting plugin by name"""
    tenant_id = uuid4()
    hub = EnrichmentHub(tenant_id)

    geocode = GeocodePlugin(mock=True)
    hub.register_plugin(geocode)

    found = hub.get_plugin("geocode")
    assert found is not None
    assert found.name == "geocode"

    not_found = hub.get_plugin("nonexistent")
    assert not_found is None


@pytest.mark.asyncio
async def test_hub_provenance_tracking():
    """Test that all provenance is tracked correctly"""
    tenant_id = uuid4()
    hub = EnrichmentHub(tenant_id)

    hub.register_plugin(GeocodePlugin(mock=True))
    hub.register_plugin(BasicAttrsPlugin(mock=True))

    record = PropertyRecord(
        apn="203-656-44",
        address=Address(line1="123 Main St", city="Las Vegas", state="NV", zip="89101"),
        source="test",
        source_id="test-1"
    )

    result = await hub.enrich(record)

    # Check that provenance was added
    assert len(record.provenance) > 0

    # Should have provenance for geo
    geo_prov = record.get_provenance("geo")
    assert geo_prov is not None
    assert geo_prov.source == "geocode"

    # Should have provenance for attrs fields
    beds_prov = record.get_provenance("attrs.beds")
    assert beds_prov is not None
    assert beds_prov.source == "basic_attrs"
