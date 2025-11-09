"""
ATTOM API Connector

ATTOM is a leading real estate data provider with property characteristics,
ownership, valuation, and transaction history.

API Documentation: https://api.developer.attomdata.com/docs
Pricing: ~$0.05-0.10 per API call
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


class ATTOMConnector(BaseConnector):
    """
    ATTOM API connector for property data.

    Supports:
    - Property details by APN
    - Property valuation (AVM)
    - Property characteristics
    - Owner information
    """

    DEFAULT_BASE_URL = "https://api.gateway.attomdata.com/propertyapi/v1.0.0"
    COST_PER_REQUEST = 0.08  # $0.08 per API call (average)

    def __init__(self, config: Optional[ConnectorConfig] = None):
        """
        Initialize ATTOM connector.

        Args:
            config: Connector configuration (uses env vars if not provided)
        """
        if config is None:
            config = ConnectorConfig(
                api_key=os.getenv("ATTOM_API_KEY"),
                base_url=os.getenv("ATTOM_BASE_URL", self.DEFAULT_BASE_URL),
                timeout=30,
                max_retries=3,
                rate_limit_per_minute=60,
                cost_per_request=self.COST_PER_REQUEST,
            )

        super().__init__(config)

        if not self.config.api_key:
            self.status = ConnectorStatus.UNAVAILABLE

    @property
    def connector_type(self) -> ConnectorType:
        return ConnectorType.ATTOM

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
        Get property data from ATTOM API.

        Args:
            apn: Assessor's Parcel Number
            state: State code (e.g., "CA")
            county: County name (optional but improves accuracy)

        Returns:
            ConnectorResponse with property data
        """
        if self.status == ConnectorStatus.UNAVAILABLE:
            return ConnectorResponse(
                success=False,
                connector=self.connector_type,
                error="ATTOM API key not configured",
            )

        try:
            # ATTOM API endpoint for property detail by APN
            url = f"{self.config.base_url}/property/detail"

            params = {
                "apn": apn,
                "state": state,
            }

            if county:
                params["county"] = county

            headers = {
                "apikey": self.config.api_key,
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

                # Check for errors
                if response.status_code != 200:
                    return ConnectorResponse(
                        success=False,
                        connector=self.connector_type,
                        error=f"API error: {response.status_code}",
                        cost=self.config.cost_per_request,
                    )

                # Parse response
                data = response.json()

                # Extract property data from ATTOM response
                property_data = self._parse_attom_response(data)

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

    def _parse_attom_response(self, data: dict) -> PropertyData:
        """
        Parse ATTOM API response into standardized PropertyData.

        Args:
            data: Raw ATTOM API response

        Returns:
            PropertyData object
        """
        # ATTOM response structure varies, but typically:
        # {
        #   "status": {...},
        #   "property": [{
        #     "identifier": {...},
        #     "address": {...},
        #     "lot": {...},
        #     "area": {...},
        #     "building": {...},
        #     "owner": {...},
        #     "assessment": {...},
        #     "vintage": {...}
        #   }]
        # }

        property_list = data.get("property", [])
        if not property_list:
            return PropertyData(raw_data=data)

        prop = property_list[0]

        # Extract address
        address = prop.get("address", {})

        # Extract lot info
        lot = prop.get("lot", {})

        # Extract building info
        building = prop.get("building", {})

        # Extract area info
        area = prop.get("area", {})

        # Extract owner info
        owner = prop.get("owner", {})

        # Extract assessment info
        assessment = prop.get("assessment", {})

        # Extract vintage info
        vintage = prop.get("vintage", {})

        return PropertyData(
            # Address
            street=address.get("oneLine"),
            city=address.get("locality"),
            state=address.get("countrySubd"),
            zip=address.get("postal1"),
            county=address.get("country"),
            # Location
            lat=address.get("latitude"),
            lng=address.get("longitude"),
            # Physical characteristics
            beds=building.get("rooms", {}).get("beds"),
            baths=building.get("rooms", {}).get("bathsTotal"),
            sqft=building.get("size", {}).get("bldgSize"),
            lot_sqft=lot.get("lotSize1"),
            year_built=vintage.get("lastModified"),
            # Ownership
            owner_name=owner.get("owner1", {}).get("fullName"),
            owner_type=owner.get("owner1", {}).get("ownershipType"),
            # Valuation
            assessed_value=assessment.get("assessed", {}).get("assdTtlValue"),
            market_value=assessment.get("market", {}).get("mktTtlValue"),
            last_sale_price=assessment.get("sale", {}).get("saleAmt"),
            last_sale_date=assessment.get("sale", {}).get("saleTransDate"),
            # Zoning
            zoning=lot.get("zoning"),
            land_use=prop.get("summary", {}).get("proptype"),
            # Raw data
            raw_data=data,
        )

    async def health_check(self) -> bool:
        """
        Check if ATTOM API is available.

        Returns:
            True if API is healthy
        """
        if not self.config.api_key:
            return False

        try:
            url = f"{self.config.base_url}/property/basicprofile"

            # Use a known test property
            params = {
                "address1": "123 Main St",
                "address2": "Los Angeles, CA",
            }

            headers = {
                "apikey": self.config.api_key,
                "Accept": "application/json",
            }

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, params=params, headers=headers)

                # Consider 200 or 404 as healthy (API is responding)
                if response.status_code in (200, 404):
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


def get_attom_connector(api_key: Optional[str] = None) -> ATTOMConnector:
    """
    Factory function to create ATTOM connector.

    Args:
        api_key: ATTOM API key (uses env var if not provided)

    Returns:
        ATTOMConnector instance
    """
    if api_key:
        config = ConnectorConfig(api_key=api_key)
        return ATTOMConnector(config)
    else:
        return ATTOMConnector()
