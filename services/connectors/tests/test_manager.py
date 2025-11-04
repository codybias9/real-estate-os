"""
Tests for Connector Manager
"""

import pytest
import httpx
import respx
from connectors.manager import (
    ConnectorManager,
    ConnectorStrategy,
    PolicyKernelIntegration,
    get_connector_manager,
)
from connectors.base import ConnectorType


@pytest.fixture
def manager():
    """Create connector manager for testing"""
    from connectors.base import ConnectorConfig
    from connectors.attom import ATTOMConnector
    from connectors.regrid import RegridConnector
    from connectors.openaddresses import OpenAddressesConnector

    manager = ConnectorManager(
        strategy=ConnectorStrategy.BALANCED, max_cost_per_property=0.20
    )

    # Configure connectors with test API keys
    manager.connectors[ConnectorType.ATTOM] = ATTOMConnector(
        ConnectorConfig(
            api_key="test-attom-key",
            base_url="https://api.gateway.attomdata.com/propertyapi/v1.0.0",
            cost_per_request=0.08,
        )
    )
    manager.connectors[ConnectorType.REGRID] = RegridConnector(
        ConnectorConfig(
            api_key="test-regrid-key",
            base_url="https://app.regrid.com/api/v1",
            cost_per_request=0.02,
        )
    )
    manager.connectors[ConnectorType.OPENADDRESSES] = OpenAddressesConnector()

    return manager


class TestConnectorManager:
    """Tests for connector manager"""

    def test_create_manager(self, manager):
        """Test creating connector manager"""
        assert manager.strategy == ConnectorStrategy.BALANCED
        assert manager.max_cost_per_property == 0.20
        assert len(manager.connectors) == 3

    def test_connector_order_balanced(self):
        """Test balanced strategy connector order"""
        manager = ConnectorManager(strategy=ConnectorStrategy.BALANCED)
        order = manager.get_connector_order()

        assert order == [
            ConnectorType.REGRID,
            ConnectorType.ATTOM,
            ConnectorType.OPENADDRESSES,
        ]

    def test_connector_order_cost_optimized(self):
        """Test cost-optimized strategy connector order"""
        manager = ConnectorManager(strategy=ConnectorStrategy.COST_OPTIMIZED)
        order = manager.get_connector_order()

        assert order == [
            ConnectorType.OPENADDRESSES,
            ConnectorType.REGRID,
            ConnectorType.ATTOM,
        ]

    def test_connector_order_quality_optimized(self):
        """Test quality-optimized strategy connector order"""
        manager = ConnectorManager(strategy=ConnectorStrategy.QUALITY_OPTIMIZED)
        order = manager.get_connector_order()

        assert order == [
            ConnectorType.ATTOM,
            ConnectorType.REGRID,
            ConnectorType.OPENADDRESSES,
        ]

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_property_data_with_fallback(self, manager):
        """Test property data retrieval with fallback"""
        # Mock Regrid failure
        respx.get(url__startswith="https://app.regrid.com").mock(
            return_value=httpx.Response(500)
        )

        # Mock ATTOM success
        respx.get(url__startswith="https://api.gateway.attomdata.com").mock(
            return_value=httpx.Response(
                200,
                json={
                    "property": [
                        {
                            "address": {
                                "oneLine": "123 Main St",
                                "locality": "Test City",
                                "countrySubd": "CA",
                            }
                        }
                    ]
                },
            )
        )

        response = await manager.get_property_data(apn="123", state="CA")

        # Should succeed with ATTOM after Regrid fails
        assert response.success is True
        assert response.connector == ConnectorType.ATTOM

    @pytest.mark.asyncio
    async def test_get_property_data_all_fail(self, manager):
        """Test when all connectors fail"""
        # Don't configure API keys, so all fail
        manager.connectors[ConnectorType.ATTOM].status = "unavailable"
        manager.connectors[ConnectorType.REGRID].status = "unavailable"

        response = await manager.get_property_data(apn="123", state="CA")

        assert response.success is False
        assert "All connectors failed" in response.error

    @pytest.mark.asyncio
    @respx.mock
    async def test_preferred_connector(self, manager):
        """Test using preferred connector"""
        # Mock ATTOM success
        route = respx.get(
            url__startswith="https://api.gateway.attomdata.com"
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    "property": [
                        {"address": {"oneLine": "123 Main St", "locality": "Test"}}
                    ]
                },
            )
        )

        response = await manager.get_property_data(
            apn="123", state="CA", preferred_connector=ConnectorType.ATTOM
        )

        assert response.success is True
        assert response.connector == ConnectorType.ATTOM
        assert route.called

    @pytest.mark.asyncio
    @respx.mock
    async def test_health_check_all(self, manager):
        """Test health check for all connectors"""
        # Mock health check responses
        respx.get(url__startswith="https://api.gateway.attomdata.com").mock(
            return_value=httpx.Response(200, json={})
        )
        respx.get(url__startswith="https://app.regrid.com").mock(
            return_value=httpx.Response(200, json={"results": []})
        )
        respx.get(url__startswith="https://nominatim.openstreetmap.org").mock(
            return_value=httpx.Response(200, json=[])
        )

        results = await manager.health_check_all()

        assert "attom" in results
        assert "regrid" in results
        assert "openaddresses" in results

    def test_get_stats(self, manager):
        """Test getting manager statistics"""
        stats = manager.get_stats()

        assert "strategy" in stats
        assert "total_cost" in stats
        assert "successful_requests" in stats
        assert "failed_requests" in stats
        assert "connectors" in stats
        assert len(stats["connectors"]) == 3

    def test_reset_stats(self, manager):
        """Test resetting statistics"""
        manager._total_cost = 10.0
        manager._successful_requests = 5
        manager._failed_requests = 2

        manager.reset_stats()

        assert manager._total_cost == 0.0
        assert manager._successful_requests == 0
        assert manager._failed_requests == 0

    def test_singleton(self):
        """Test global singleton"""
        manager1 = get_connector_manager()
        manager2 = get_connector_manager()

        assert manager1 is manager2


class TestPolicyKernelIntegration:
    """Tests for Policy Kernel integration"""

    def test_create_policy_kernel(self):
        """Test creating Policy Kernel integration"""
        policy = PolicyKernelIntegration(
            tenant_id="tenant-123", monthly_budget=100.0
        )

        assert policy.tenant_id == "tenant-123"
        assert policy.monthly_budget == 100.0

    def test_can_make_request(self):
        """Test budget checking"""
        policy = PolicyKernelIntegration(
            tenant_id="tenant-123", monthly_budget=10.0
        )

        # Within budget
        assert policy.can_make_request(5.0) is True

        # Exceeds budget
        assert policy.can_make_request(15.0) is False

    def test_record_cost(self):
        """Test recording costs"""
        policy = PolicyKernelIntegration(
            tenant_id="tenant-123", monthly_budget=100.0
        )

        policy.record_cost(10.0)
        policy.record_cost(5.0)

        assert policy._spent_this_month == 15.0
        assert policy.get_remaining_budget() == 85.0

    def test_get_usage_stats(self):
        """Test getting usage statistics"""
        policy = PolicyKernelIntegration(
            tenant_id="tenant-123", monthly_budget=100.0
        )

        policy.record_cost(25.0)

        stats = policy.get_usage_stats()

        assert stats["tenant_id"] == "tenant-123"
        assert stats["monthly_budget"] == 100.0
        assert stats["spent_this_month"] == 25.0
        assert stats["remaining"] == 75.0
        assert stats["usage_percentage"] == 25.0

    def test_budget_exceeded(self):
        """Test when budget is exceeded"""
        policy = PolicyKernelIntegration(tenant_id="tenant-123", monthly_budget=10.0)

        policy.record_cost(12.0)

        assert policy.get_remaining_budget() == 0.0
        assert policy.can_make_request(1.0) is False
