"""US Census Bureau API client

Fetches demographic and economic data for properties.

API Documentation: https://www.census.gov/data/developers/data-sets.html
"""
import logging
from typing import Optional, Dict, Any
from .base_client import BaseAPIClient
from .models import CensusResponse

logger = logging.getLogger(__name__)


class CensusAPIClient(BaseAPIClient):
    """
    Client for US Census Bureau API

    Provides:
    - Demographic data by ZIP code
    - Income statistics
    - Housing occupancy rates
    - Population data

    Usage:
        client = CensusAPIClient(api_key="your_key")
        data = client.get_zip_demographics("89101")
    """

    BASE_URL = "https://api.census.gov/data"

    # American Community Survey 5-Year Data (most detailed)
    ACS5_YEAR = "2021/acs/acs5"

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """
        Initialize Census API client

        Get a free API key at: https://api.census.gov/data/key_signup.html

        Args:
            api_key: Census API key (free)
        """
        super().__init__(
            api_key=api_key,
            rate_limit_per_second=0.5,  # Conservative rate limit
            cache_ttl_seconds=86400,  # Cache for 24 hours (data doesn't change often)
            **kwargs
        )

    def get_name(self) -> str:
        return "US Census Bureau"

    def get_cost_per_call(self) -> float:
        return 0.0  # Free API

    def get_zip_demographics(self, zip_code: str) -> Optional[CensusResponse]:
        """
        Get demographic data for a ZIP code

        Args:
            zip_code: 5-digit ZIP code

        Returns:
            CensusResponse with demographic data
        """
        try:
            # Variables to fetch from ACS5
            # B01003_001E: Total Population
            # B19013_001E: Median Household Income
            # B01002_001E: Median Age
            # B25003_002E: Owner Occupied Housing Units
            # B25003_003E: Renter Occupied Housing Units
            # B25077_001E: Median Home Value
            # B23025_005E: Unemployed

            variables = [
                "B01003_001E",  # Population
                "B19013_001E",  # Median Income
                "B01002_001E",  # Median Age
                "B25003_002E",  # Owner Occupied
                "B25003_003E",  # Renter Occupied
                "B25077_001E",  # Median Home Value
                "B23025_005E",  # Unemployed
                "B23025_002E",  # Labor Force
            ]

            url = f"{self.BASE_URL}/{self.ACS5_YEAR}"
            params = {
                "get": ",".join(variables),
                "for": f"zip code tabulation area:{zip_code}",
            }

            if self.api_key:
                params["key"] = self.api_key

            response_data = self.get(url, params=params)

            # Parse response
            # Format: [[headers], [values]]
            if not response_data or len(response_data) < 2:
                logger.warning(f"No data found for ZIP code: {zip_code}")
                return None

            headers = response_data[0]
            values = response_data[1]

            # Map to dictionary
            data_dict = dict(zip(headers, values))

            # Parse values
            population = self._parse_int(data_dict.get("B01003_001E"))
            median_income = self._parse_decimal(data_dict.get("B19013_001E"))
            median_age = self._parse_decimal(data_dict.get("B01002_001E"))
            owner_occupied = self._parse_int(data_dict.get("B25003_002E"))
            renter_occupied = self._parse_int(data_dict.get("B25003_003E"))
            median_home_value = self._parse_decimal(data_dict.get("B25077_001E"))
            unemployed = self._parse_int(data_dict.get("B23025_005E"))
            labor_force = self._parse_int(data_dict.get("B23025_002E"))

            # Calculate rates
            total_occupied = (owner_occupied or 0) + (renter_occupied or 0)
            owner_rate = (owner_occupied / total_occupied) if total_occupied > 0 else None
            renter_rate = (renter_occupied / total_occupied) if total_occupied > 0 else None
            unemployment_rate = (unemployed / labor_force) if labor_force and labor_force > 0 else None

            return CensusResponse(
                zip_code=zip_code,
                population=population,
                median_household_income=median_income,
                median_age=median_age,
                owner_occupied_rate=owner_rate,
                renter_occupied_rate=renter_rate,
                median_home_value=median_home_value,
                unemployment_rate=unemployment_rate,
                raw_data=data_dict
            )

        except Exception as e:
            logger.error(f"Failed to fetch Census data for {zip_code}: {e}")
            return None

    def get_county_demographics(self, state_fips: str, county_fips: str) -> Optional[Dict[str, Any]]:
        """
        Get demographic data for a county

        Args:
            state_fips: 2-digit state FIPS code (e.g., "06" for California)
            county_fips: 3-digit county FIPS code (e.g., "073" for San Diego)

        Returns:
            Dictionary with demographic data
        """
        try:
            variables = [
                "B01003_001E",  # Population
                "B19013_001E",  # Median Income
                "B01002_001E",  # Median Age
                "B25077_001E",  # Median Home Value
            ]

            url = f"{self.BASE_URL}/{self.ACS5_YEAR}"
            params = {
                "get": ",".join(variables),
                "for": f"county:{county_fips}",
                "in": f"state:{state_fips}",
            }

            if self.api_key:
                params["key"] = self.api_key

            response_data = self.get(url, params=params)

            if not response_data or len(response_data) < 2:
                logger.warning(f"No data found for county: {state_fips}-{county_fips}")
                return None

            headers = response_data[0]
            values = response_data[1]
            data_dict = dict(zip(headers, values))

            return {
                'population': self._parse_int(data_dict.get("B01003_001E")),
                'median_income': self._parse_decimal(data_dict.get("B19013_001E")),
                'median_age': self._parse_decimal(data_dict.get("B01002_001E")),
                'median_home_value': self._parse_decimal(data_dict.get("B25077_001E")),
                'raw_data': data_dict
            }

        except Exception as e:
            logger.error(f"Failed to fetch county Census data: {e}")
            return None

    @staticmethod
    def _parse_int(value: Any) -> Optional[int]:
        """Parse integer value, handling null/-666666666"""
        if value is None or value == -666666666 or value == "-666666666":
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_decimal(value: Any) -> Optional[float]:
        """Parse decimal value, handling null/-666666666"""
        if value is None or value == -666666666 or value == "-666666666":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
