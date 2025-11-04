"""
Tests for Regrid API connector
"""

import pytest
import httpx
import respx
from connectors.regrid import RegridConnector, get_regrid_connector
from connectors.base import ConnectorConfig, ConnectorStatus, ConnectorType


@pytest.fixture
def regrid_config():
    """Create Regrid config for testing"""
    return ConnectorConfig(
        api_key="test-api-key",
        base_url="https://test-api.regrid.com",
        timeout=10,
        cost_per_request=0.02,
    )


@pytest.fixture
def regrid_connector(regrid_config):
    """Create Regrid connector for testing"""
    return RegridConnector(regrid_config)


class TestRegridConnector:
    """Tests for Regrid connector"""

    def test_create_connector(self, regrid_connector):
        """Test creating Regrid connector"""
        assert regrid_connector.connector_type == ConnectorType.REGRID
        assert regrid_connector.status == ConnectorStatus.AVAILABLE
        assert regrid_connector.config.api_key == "test-api-key"

    def test_create_connector_no_api_key(self):
        """Test creating connector without API key"""
        config = ConnectorConfig(api_key=None)
        connector = RegridConnector(config)
        assert connector.status == ConnectorStatus.UNAVAILABLE

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_property_data_success(self, regrid_connector):
        """Test successful property data retrieval"""
        # Mock API response
        mock_response = {
            "results": [
                {
                    "parcel_id": "12345",
                    "address": {
                        "street": "123 Main St",
                        "city": "San Francisco",
                        "state": "CA",
                        "zip": "94102",
                        "county": "San Francisco",
                    },
                    "properties": {
                        "bedrooms": 4,
                        "bathrooms": 3.0,
                        "building_sqft": 2000,
                        "lot_sqft": 6000,
                        "year_built": 1950,
                        "assessed_value": 800000,
                        "zoning": "RH-2",
                        "land_use": "Residential",
                    },
                    "owner": {
                        "name": "Jane Smith",
                        "type": "Individual",
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [-122.4194, 37.7749],
                                [-122.4194, 37.7750],
                                [-122.4193, 37.7750],
                                [-122.4193, 37.7749],
                            ]
                        ],
                    },
                }
            ]
        }

        route = respx.get(f"{regrid_connector.config.base_url}/parcels").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        # Call connector
        response = await regrid_connector.get_property_data(
            apn="123-456-789", state="CA", county="San Francisco"
        )

        # Assertions
        assert response.success is True
        assert response.connector == ConnectorType.REGRID
        assert response.data is not None
        assert response.data.city == "San Francisco"
        assert response.data.state == "CA"
        assert response.data.beds == 4
        assert response.data.baths == 3.0
        assert response.cost == 0.02
        assert route.called

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_property_data_not_found(self, regrid_connector):
        """Test property not found"""
        route = respx.get(f"{regrid_connector.config.base_url}/parcels").mock(
            return_value=httpx.Response(404)
        )

        response = await regrid_connector.get_property_data(
            apn="999-999-999", state="CA"
        )

        assert response.success is False
        assert response.error is not None
        assert "not found" in response.error.lower()
        assert route.called

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_property_data_rate_limited(self, regrid_connector):
        """Test rate limiting"""
        route = respx.get(f"{regrid_connector.config.base_url}/parcels").mock(
            return_value=httpx.Response(429)
        )

        response = await regrid_connector.get_property_data(
            apn="123-456-789", state="CA"
        )

        assert response.success is False
        assert regrid_connector.status == ConnectorStatus.RATE_LIMITED
        assert "Rate limit" in response.error
        assert route.called

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_property_data_invalid_api_key(self, regrid_connector):
        """Test invalid API key"""
        route = respx.get(f"{regrid_connector.config.base_url}/parcels").mock(
            return_value=httpx.Response(401)
        )

        response = await regrid_connector.get_property_data(
            apn="123-456-789", state="CA"
        )

        assert response.success is False
        assert regrid_connector.status == ConnectorStatus.ERROR
        assert "Invalid API key" in response.error
        assert route.called

    @pytest.mark.asyncio
    async def test_get_property_data_no_api_key(self):
        """Test without API key"""
        config = ConnectorConfig(api_key=None)
        connector = RegridConnector(config)

        response = await connector.get_property_data(apn="123", state="CA")

        assert response.success is False
        assert "not configured" in response.error

    @pytest.mark.asyncio
    @respx.mock
    async def test_health_check_success(self, regrid_connector):
        """Test successful health check"""
        route = respx.get(f"{regrid_connector.config.base_url}/parcels").mock(
            return_value=httpx.Response(200, json={"results": []})
        )

        healthy = await regrid_connector.health_check()

        assert healthy is True
        assert regrid_connector.status == ConnectorStatus.AVAILABLE
        assert route.called

    @pytest.mark.asyncio
    @respx.mock
    async def test_health_check_failure(self, regrid_connector):
        """Test failed health check"""
        route = respx.get(f"{regrid_connector.config.base_url}/parcels").mock(
            return_value=httpx.Response(500)
        )

        healthy = await regrid_connector.health_check()

        assert healthy is False
        assert regrid_connector.status == ConnectorStatus.ERROR
        assert route.called

    def test_factory_function(self):
        """Test get_regrid_connector factory"""
        connector = get_regrid_connector(api_key="test-key")
        assert connector.config.api_key == "test-key"
