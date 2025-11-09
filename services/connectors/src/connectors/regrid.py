"""
Regrid API Connector

Regrid provides nationwide parcel data with property boundaries,
ownership, and characteristics.

API Documentation: https://regrid.com/docs/api
Pricing: ~$0.01-0.05 per API call
"""

import os
from typing import Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import (
    BaseConnector,
    ConnectorConfig,
    ConnectorResponse,
    ConnectorType,
    ConnectorStatus,
    PropertyData,
)


class RegridConnector(BaseConnector):
    """
    Regrid API connector for parcel data.

    Supports:
    - Parcel lookup by APN
    - Property boundaries (GeoJSON)
    - Owner information
    - Property characteristics
    """

    DEFAULT_BASE_URL = "https://app.regrid.com/api/v1"
    COST_PER_REQUEST = 0.02  # $0.02 per API call (average)

    def __init__(self, config: Optional[ConnectorConfig] = None):
        """
        Initialize Regrid connector.

        Args:
            config: Connector configuration (uses env vars if not provided)
        """
        if config is None:
            config = ConnectorConfig(
                api_key=os.getenv("REGRID_API_KEY"),
                base_url=os.getenv("REGRID_BASE_URL", self.DEFAULT_BASE_URL),
                timeout=30,
                max_retries=3,
                rate_limit_per_minute=120,
                cost_per_request=self.COST_PER_REQUEST,
            )

        super().__init__(config)

        if not self.config.api_key:
            self.status = ConnectorStatus.UNAVAILABLE

    @property
    def connector_type(self) -> ConnectorType:
        return ConnectorType.REGRID

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def get_property_data(
        self,
        apn: str,
        state: str,
        county: Optional[str] = None,
    ) -> ConnectorResponse:
        """
        Get property data from Regrid API.

        Args:
            apn: Assessor's Parcel Number
            state: State code (e.g., "CA")
            county: County name (optional)

        Returns:
            ConnectorResponse with property data
        """
        if self.status == ConnectorStatus.UNAVAILABLE:
            return ConnectorResponse(
                success=False,
                connector=self.connector_type,
                error="Regrid API key not configured",
            )

        try:
            # Regrid API endpoint for parcel lookup
            # Format: /parcels/{state}/{county}/{apn}
            # Or search: /parcels?apn={apn}&state={state}

            url = f"{self.config.base_url}/parcels"

            params = {
                "apn": apn,
                "state": state.upper(),
                "limit": 1,
            }

            if county:
                params["county"] = county

            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Accept": "application/json",
            }

            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.get(url, params=params, headers=headers)

                # Record request
                self._record_request(self.config.cost_per_request)

                # Check for rate limiting
                if response.status_code == 429:
                    self.status = ConnectorStatus.RATE_LIMITED
                    return ConnectorResponse(
                        success=False,
                        connector=self.connector_type,
                        error="Rate limit exceeded",
                        cost=self.config.cost_per_request,
                    )

                # Check for authentication errors
                if response.status_code == 401:
                    self.status = ConnectorStatus.ERROR
                    return ConnectorResponse(
                        success=False,
                        connector=self.connector_type,
                        error="Invalid API key",
                        cost=self.config.cost_per_request,
                    )

                # Check for not found
                if response.status_code == 404:
                    return ConnectorResponse(
                        success=False,
                        connector=self.connector_type,
                        error="Property not found",
                        cost=self.config.cost_per_request,
                    )

                # Check for other errors
                if response.status_code != 200:
                    return ConnectorResponse(
                        success=False,
                        connector=self.connector_type,
                        error=f"API error: {response.status_code}",
                        cost=self.config.cost_per_request,
                    )

                # Parse response
                data = response.json()

                # Extract property data from Regrid response
                property_data = self._parse_regrid_response(data)

                return ConnectorResponse(
                    success=True,
                    connector=self.connector_type,
                    data=property_data,
                    cost=self.config.cost_per_request,
                )

        except httpx.TimeoutException:
            return ConnectorResponse(
                success=False,
                connector=self.connector_type,
                error="Request timeout",
                cost=self.config.cost_per_request,
            )

        except Exception as e:
            self.status = ConnectorStatus.ERROR
            return ConnectorResponse(
                success=False,
                connector=self.connector_type,
                error=str(e),
            )

    def _parse_regrid_response(self, data: dict) -> PropertyData:
        """
        Parse Regrid API response into standardized PropertyData.

        Args:
            data: Raw Regrid API response

        Returns:
            PropertyData object
        """
        # Regrid response structure:
        # {
        #   "results": [{
        #     "parcel_id": "...",
        #     "address": {...},
        #     "owner": {...},
        #     "properties": {...},
        #     "geometry": {...}
        #   }]
        # }

        results = data.get("results", [])
        if not results:
            return PropertyData(raw_data=data)

        parcel = results[0]

        # Extract address
        address = parcel.get("address", {})

        # Extract properties
        properties = parcel.get("properties", {})

        # Extract owner
        owner = parcel.get("owner", {})

        # Extract geometry for coordinates
        geometry = parcel.get("geometry", {})
        coordinates = geometry.get("coordinates", [])

        # Get centroid (Regrid typically provides polygon, we need center)
        lat, lng = None, None
        if coordinates and len(coordinates) > 0:
            # Simple centroid calculation
            if isinstance(coordinates[0], list):
                lngs = [c[0] for c in coordinates[0] if isinstance(c, list)]
                lats = [c[1] for c in coordinates[0] if isinstance(c, list)]
                if lngs and lats:
                    lng = sum(lngs) / len(lngs)
                    lat = sum(lats) / len(lats)

        return PropertyData(
            # Address
            street=address.get("street"),
            city=address.get("city"),
            state=address.get("state"),
            zip=address.get("zip"),
            county=address.get("county"),
            # Location
            lat=lat,
            lng=lng,
            # Physical characteristics
            beds=properties.get("bedrooms"),
            baths=properties.get("bathrooms"),
            sqft=properties.get("building_sqft"),
            lot_sqft=properties.get("lot_sqft"),
            year_built=properties.get("year_built"),
            # Ownership
            owner_name=owner.get("name"),
            owner_type=owner.get("type"),
            # Valuation
            assessed_value=properties.get("assessed_value"),
            market_value=properties.get("market_value"),
            last_sale_price=properties.get("sale_price"),
            last_sale_date=properties.get("sale_date"),
            # Zoning
            zoning=properties.get("zoning"),
            land_use=properties.get("land_use"),
            # Raw data
            raw_data=data,
        )

    async def health_check(self) -> bool:
        """
        Check if Regrid API is available.

        Returns:
            True if API is healthy
        """
        if not self.config.api_key:
            return False

        try:
            # Use the parcels count endpoint for health check
            url = f"{self.config.base_url}/parcels"

            params = {
                "state": "CA",
                "limit": 1,
            }

            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Accept": "application/json",
            }

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, params=params, headers=headers)

                # Consider 200 as healthy
                if response.status_code == 200:
                    self.status = ConnectorStatus.AVAILABLE
                    return True
                elif response.status_code == 429:
                    self.status = ConnectorStatus.RATE_LIMITED
                    return False
                else:
                    self.status = ConnectorStatus.ERROR
                    return False

        except Exception:
            self.status = ConnectorStatus.ERROR
            return False


def get_regrid_connector(api_key: Optional[str] = None) -> RegridConnector:
    """
    Factory function to create Regrid connector.

    Args:
        api_key: Regrid API key (uses env var if not provided)

    Returns:
        RegridConnector instance
    """
    if api_key:
        config = ConnectorConfig(api_key=api_key)
        return RegridConnector(config)
    else:
        return RegridConnector()
