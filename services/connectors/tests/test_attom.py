"""
Tests for ATTOM API connector
"""

import pytest
import httpx
import respx
from connectors.attom import ATTOMConnector, get_attom_connector
from connectors.base import ConnectorConfig, ConnectorStatus, ConnectorType


@pytest.fixture
def attom_config():
    """Create ATTOM config for testing"""
    return ConnectorConfig(
        api_key="test-api-key",
        base_url="https://test-api.attomdata.com",
        timeout=10,
        cost_per_request=0.08,
    )


@pytest.fixture
def attom_connector(attom_config):
    """Create ATTOM connector for testing"""
    return ATTOMConnector(attom_config)


class TestATTOMConnector:
    """Tests for ATTOM connector"""

    def test_create_connector(self, attom_connector):
        """Test creating ATTOM connector"""
        assert attom_connector.connector_type == ConnectorType.ATTOM
        assert attom_connector.status == ConnectorStatus.AVAILABLE
        assert attom_connector.config.api_key == "test-api-key"

    def test_create_connector_no_api_key(self):
        """Test creating connector without API key"""
        config = ConnectorConfig(api_key=None)
        connector = ATTOMConnector(config)
        assert connector.status == ConnectorStatus.UNAVAILABLE

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_property_data_success(self, attom_connector):
        """Test successful property data retrieval"""
        # Mock API response
        mock_response = {
            "status": {"code": 0},
            "property": [
                {
                    "address": {
                        "oneLine": "123 Main St, Los Angeles, CA 90001",
                        "locality": "Los Angeles",
                        "countrySubd": "CA",
                        "postal1": "90001",
                        "latitude": 34.0522,
                        "longitude": -118.2437,
                    },
                    "building": {
                        "rooms": {"beds": 3, "bathsTotal": 2.0},
                        "size": {"bldgSize": 1500},
                    },
                    "lot": {"lotSize1": 5000, "zoning": "R1"},
                    "owner": {
                        "owner1": {
                            "fullName": "John Doe",
                            "ownershipType": "Individual",
                        }
                    },
                    "assessment": {
                        "assessed": {"assdTtlValue": 500000},
                        "market": {"mktTtlValue": 550000},
                    },
                }
            ],
        }

        route = respx.get(
            f"{attom_connector.config.base_url}/property/detail"
        ).mock(return_value=httpx.Response(200, json=mock_response))

        # Call connector
        response = await attom_connector.get_property_data(
            apn="123-456-789", state="CA", county="Los Angeles"
        )

        # Assertions
        assert response.success is True
        assert response.connector == ConnectorType.ATTOM
        assert response.data is not None
        assert response.data.city == "Los Angeles"
        assert response.data.state == "CA"
        assert response.data.beds == 3
        assert response.data.baths == 2.0
        assert response.cost == 0.08
        assert route.called

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_property_data_not_found(self, attom_connector):
        """Test property not found"""
        route = respx.get(
            f"{attom_connector.config.base_url}/property/detail"
        ).mock(return_value=httpx.Response(404))

        response = await attom_connector.get_property_data(
            apn="999-999-999", state="CA"
        )

        assert response.success is False
        assert response.error is not None
        assert "404" in response.error
        assert route.called

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_property_data_rate_limited(self, attom_connector):
        """Test rate limiting"""
        route = respx.get(
            f"{attom_connector.config.base_url}/property/detail"
        ).mock(return_value=httpx.Response(429))

        response = await attom_connector.get_property_data(
            apn="123-456-789", state="CA"
        )

        assert response.success is False
        assert attom_connector.status == ConnectorStatus.RATE_LIMITED
        assert "Rate limit" in response.error
        assert route.called

    @pytest.mark.asyncio
    async def test_get_property_data_no_api_key(self):
        """Test without API key"""
        config = ConnectorConfig(api_key=None)
        connector = ATTOMConnector(config)

        response = await connector.get_property_data(apn="123", state="CA")

        assert response.success is False
        assert "not configured" in response.error

    @pytest.mark.asyncio
    @respx.mock
    async def test_health_check_success(self, attom_connector):
        """Test successful health check"""
        route = respx.get(
            f"{attom_connector.config.base_url}/property/basicprofile"
        ).mock(return_value=httpx.Response(200, json={}))

        healthy = await attom_connector.health_check()

        assert healthy is True
        assert attom_connector.status == ConnectorStatus.AVAILABLE
        assert route.called

    @pytest.mark.asyncio
    @respx.mock
    async def test_health_check_failure(self, attom_connector):
        """Test failed health check"""
        route = respx.get(
            f"{attom_connector.config.base_url}/property/basicprofile"
        ).mock(return_value=httpx.Response(500))

        healthy = await attom_connector.health_check()

        assert healthy is False
        assert attom_connector.status == ConnectorStatus.ERROR
        assert route.called

    def test_get_stats(self, attom_connector):
        """Test getting connector stats"""
        stats = attom_connector.get_stats()

        assert stats["connector"] == "attom"
        assert stats["status"] == "available"
        assert stats["request_count"] == 0
        assert stats["total_cost"] == 0.0

    def test_factory_function(self):
        """Test get_attom_connector factory"""
        connector = get_attom_connector(api_key="test-key")
        assert connector.config.api_key == "test-key"
