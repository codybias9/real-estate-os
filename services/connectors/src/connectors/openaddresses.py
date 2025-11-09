"""
OpenAddresses Connector

OpenAddresses is a free, global database of address data.
No API key required, but limited data compared to commercial providers.

Data: https://openaddresses.io/
Pricing: Free
"""

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


class OpenAddressesConnector(BaseConnector):
    """
    OpenAddresses connector for basic address geocoding.

    Supports:
    - Address lookup and geocoding
    - Basic property location data
    - Free, no API key required

    Limitations:
    - No ownership data
    - No valuation data
    - No detailed characteristics
    - Best used as fallback when commercial APIs unavailable
    """

    # Using Nominatim (OpenStreetMap) for geocoding
    DEFAULT_BASE_URL = "https://nominatim.openstreetmap.org"
    COST_PER_REQUEST = 0.0  # Free

    def __init__(self, config: Optional[ConnectorConfig] = None):
        """
        Initialize OpenAddresses connector.

        Args:
            config: Connector configuration
        """
        if config is None:
            config = ConnectorConfig(
                base_url=self.DEFAULT_BASE_URL,
                timeout=30,
                max_retries=3,
                rate_limit_per_minute=60,  # Nominatim rate limit
                cost_per_request=self.COST_PER_REQUEST,
            )

        super().__init__(config)
        self.status = ConnectorStatus.AVAILABLE  # Always available (no API key)

    @property
    def connector_type(self) -> ConnectorType:
        return ConnectorType.OPENADDRESSES

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
        Get basic property data from OpenAddresses (via Nominatim).

        Note: APN is not directly supported by OpenAddresses.
        This method attempts to geocode if street address is available.

        Args:
            apn: Assessor's Parcel Number (not used, kept for interface compatibility)
            state: State code (e.g., "CA")
            county: County name (optional)

        Returns:
            ConnectorResponse with limited property data
        """
        try:
            # OpenAddresses/Nominatim doesn't support APN lookup
            # This is a limitation of free data sources
            return ConnectorResponse(
                success=False,
                connector=self.connector_type,
                error="OpenAddresses does not support APN lookup. Use address-based search instead.",
                cost=0.0,
            )

        except Exception as e:
            self.status = ConnectorStatus.ERROR
            return ConnectorResponse(
                success=False,
                connector=self.connector_type,
                error=str(e),
            )

    async def geocode_address(
        self,
        street: str,
        city: str,
        state: str,
        zip_code: Optional[str] = None,
    ) -> ConnectorResponse:
        """
        Geocode an address using Nominatim.

        Args:
            street: Street address
            city: City
            state: State code
            zip_code: ZIP code (optional)

        Returns:
            ConnectorResponse with geocoded location
        """
        try:
            url = f"{self.config.base_url}/search"

            # Build address string
            address_parts = [street, city, state]
            if zip_code:
                address_parts.append(zip_code)
            address = ", ".join(address_parts)

            params = {
                "q": address,
                "format": "json",
                "addressdetails": 1,
                "limit": 1,
            }

            headers = {
                "User-Agent": "RealEstateOS/1.0",  # Nominatim requires User-Agent
            }

            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.get(url, params=params, headers=headers)

                # Record request
                self._record_request(0.0)

                # Check for rate limiting
                if response.status_code == 429:
                    self.status = ConnectorStatus.RATE_LIMITED
                    return ConnectorResponse(
                        success=False,
                        connector=self.connector_type,
                        error="Rate limit exceeded",
                        cost=0.0,
                    )

                # Check for errors
                if response.status_code != 200:
                    return ConnectorResponse(
                        success=False,
                        connector=self.connector_type,
                        error=f"API error: {response.status_code}",
                        cost=0.0,
                    )

                # Parse response
                data = response.json()

                if not data or len(data) == 0:
                    return ConnectorResponse(
                        success=False,
                        connector=self.connector_type,
                        error="Address not found",
                        cost=0.0,
                    )

                # Extract property data from Nominatim response
                property_data = self._parse_nominatim_response(data[0])

                return ConnectorResponse(
                    success=True,
                    connector=self.connector_type,
                    data=property_data,
                    cost=0.0,
                )

        except httpx.TimeoutException:
            return ConnectorResponse(
                success=False,
                connector=self.connector_type,
                error="Request timeout",
                cost=0.0,
            )

        except Exception as e:
            self.status = ConnectorStatus.ERROR
            return ConnectorResponse(
                success=False,
                connector=self.connector_type,
                error=str(e),
            )

    def _parse_nominatim_response(self, data: dict) -> PropertyData:
        """
        Parse Nominatim response into standardized PropertyData.

        Args:
            data: Raw Nominatim response

        Returns:
            PropertyData object (with limited fields)
        """
        # Nominatim response structure:
        # {
        #   "lat": "...",
        #   "lon": "...",
        #   "display_name": "...",
        #   "address": {
        #     "house_number": "...",
        #     "road": "...",
        #     "city": "...",
        #     "state": "...",
        #     "postcode": "...",
        #     "county": "...",
        #     "country": "..."
        #   }
        # }

        address = data.get("address", {})

        # Build street address
        street_parts = []
        if address.get("house_number"):
            street_parts.append(address["house_number"])
        if address.get("road"):
            street_parts.append(address["road"])
        street = " ".join(street_parts) if street_parts else None

        return PropertyData(
            # Address
            street=street,
            city=address.get("city") or address.get("town") or address.get("village"),
            state=address.get("state"),
            zip=address.get("postcode"),
            county=address.get("county"),
            # Location
            lat=float(data.get("lat")) if data.get("lat") else None,
            lng=float(data.get("lon")) if data.get("lon") else None,
            # No other data available from OpenAddresses/Nominatim
            # Raw data
            raw_data=data,
        )

    async def health_check(self) -> bool:
        """
        Check if OpenAddresses (Nominatim) is available.

        Returns:
            True if service is healthy
        """
        try:
            url = f"{self.config.base_url}/search"

            params = {
                "q": "San Francisco, CA",
                "format": "json",
                "limit": 1,
            }

            headers = {
                "User-Agent": "RealEstateOS/1.0",
            }

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, params=params, headers=headers)

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


def get_openaddresses_connector() -> OpenAddressesConnector:
    """
    Factory function to create OpenAddresses connector.

    Returns:
        OpenAddressesConnector instance
    """
    return OpenAddressesConnector()
