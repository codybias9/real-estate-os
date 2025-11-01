"""County Assessor API client

Each county has different data access methods. This module provides:
- Abstract base class for assessor clients
- Generic web scraping approach
- Specific implementations for major counties

Note: Most counties don't have proper APIs, so web scraping is often necessary.
"""
import logging
import random
from typing import Optional
from abc import ABC, abstractmethod
from .base_client import BaseAPIClient
from .models import AssessorResponse
from decimal import Decimal
from datetime import date, timedelta

logger = logging.getLogger(__name__)


class BaseAssessorClient(BaseAPIClient, ABC):
    """
    Abstract base class for county assessor clients

    Each county implementation should override:
    - get_property_by_apn()
    - get_property_by_address()
    """

    def __init__(self, county_name: str, **kwargs):
        self.county_name = county_name
        super().__init__(
            rate_limit_per_second=0.5,  # Be respectful to county servers
            cache_ttl_seconds=86400,  # Cache for 24 hours
            **kwargs
        )

    def get_name(self) -> str:
        return f"{self.county_name} County Assessor"

    def get_cost_per_call(self) -> float:
        return 0.0  # County data is free

    @abstractmethod
    def get_property_by_apn(self, apn: str) -> Optional[AssessorResponse]:
        """Get property data by Assessor Parcel Number"""
        pass

    @abstractmethod
    def get_property_by_address(self, address: str) -> Optional[AssessorResponse]:
        """Get property data by address"""
        pass


class MockAssessorClient(BaseAssessorClient):
    """
    Mock assessor client for testing and demonstration

    Generates realistic-looking data for development.
    In production, replace with real county API implementations.
    """

    def __init__(self, county_name: str = "Mock County", **kwargs):
        super().__init__(county_name, **kwargs)

    def get_property_by_apn(self, apn: str) -> Optional[AssessorResponse]:
        """Generate mock property data by APN"""
        logger.info(f"Fetching mock assessor data for APN: {apn}")

        return self._generate_mock_data(apn=apn)

    def get_property_by_address(self, address: str) -> Optional[AssessorResponse]:
        """Generate mock property data by address"""
        logger.info(f"Fetching mock assessor data for address: {address}")

        # Generate APN from address hash
        apn = f"{hash(address) % 1000:03d}-{hash(address) % 1000:03d}-{hash(address) % 100:02d}"

        return self._generate_mock_data(
            apn=apn,
            property_address=address
        )

    def _generate_mock_data(
        self,
        apn: Optional[str] = None,
        property_address: Optional[str] = None
    ) -> AssessorResponse:
        """Generate realistic mock assessor data"""

        # Generate realistic values with some randomness
        base_seed = hash(apn or property_address or "default") % 10000

        random.seed(base_seed)

        return AssessorResponse(
            apn=apn or f"{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(10, 99)}",
            owner_name=self._generate_owner_name(),
            owner_address=f"{random.randint(100, 9999)} Main St, Anytown, USA {random.randint(10000, 99999)}",
            property_address=property_address or f"{random.randint(100, 9999)} Oak Ave, Somecity, ST {random.randint(10000, 99999)}",
            assessed_value=Decimal(random.randint(200000, 1500000)),
            market_value=Decimal(random.randint(250000, 1800000)),
            square_footage=random.randint(1000, 5000),
            bedrooms=random.randint(2, 6),
            bathrooms=Decimal(str(round(random.uniform(1.0, 4.5), 1))),
            year_built=random.randint(1950, 2023),
            lot_size=random.randint(4000, 20000),
            property_type=random.choice(["Single Family", "Townhouse", "Condo", "Multi-Family"]),
            zoning=random.choice(["R-1", "R-2", "R-3", "C-1", "M-1"]),
            last_sale_date=date.today() - timedelta(days=random.randint(30, 3650)),
            last_sale_price=Decimal(random.randint(150000, 1200000)),
            annual_tax=Decimal(random.randint(3000, 15000)),
            raw_data={
                "source": "mock_assessor",
                "generated": True,
                "timestamp": date.today().isoformat()
            }
        )

    @staticmethod
    def _generate_owner_name() -> str:
        """Generate random owner name"""
        first_names = ["John", "Jane", "Michael", "Sarah", "David", "Lisa", "Robert", "Mary"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]

        first = random.choice(first_names)
        last = random.choice(last_names)

        # Sometimes add "Trust" or "LLC"
        if random.random() < 0.2:
            return f"{first} {last} Family Trust"
        elif random.random() < 0.1:
            return f"{last} Holdings LLC"
        else:
            return f"{first} {last}"


class ClarkCountyAssessorClient(BaseAssessorClient):
    """
    Clark County, Nevada Assessor Client

    Uses web scraping to fetch property data.

    Note: This is a template. Real implementation would need:
    - Playwright/Selenium for JavaScript rendering
    - Proper HTML parsing
    - Error handling for website changes
    """

    def __init__(self, **kwargs):
        super().__init__(county_name="Clark County, NV", **kwargs)
        self.base_url = "https://gis.clarkcountynv.gov/assessor/"

    def get_property_by_apn(self, apn: str) -> Optional[AssessorResponse]:
        """
        Fetch property data by APN

        Note: This is a placeholder. Real implementation would:
        1. Use Playwright to render JavaScript
        2. Parse HTML tables/JSON responses
        3. Extract and normalize data
        4. Handle errors and rate limiting
        """
        logger.warning("ClarkCountyAssessorClient not fully implemented - using mock data")

        # For now, fall back to mock client
        mock_client = MockAssessorClient("Clark County, NV")
        return mock_client.get_property_by_apn(apn)

    def get_property_by_address(self, address: str) -> Optional[AssessorResponse]:
        """Fetch property data by address"""
        logger.warning("ClarkCountyAssessorClient not fully implemented - using mock data")

        mock_client = MockAssessorClient("Clark County, NV")
        return mock_client.get_property_by_address(address)


def get_assessor_client(county_config: dict) -> BaseAssessorClient:
    """
    Factory function to get appropriate assessor client for a county

    Args:
        county_config: County configuration from YAML

    Returns:
        Appropriate assessor client instance
    """
    county_name = county_config.get('county_info', {}).get('name', 'Unknown')

    # Map counties to specific clients
    # In production, add more county implementations
    county_clients = {
        "Clark County": ClarkCountyAssessorClient,
        # "Maricopa County": MaricopaCountyAssessorClient,  # Future
        # "San Diego County": SanDiegoCountyAssessorClient,  # Future
    }

    client_class = county_clients.get(county_name, MockAssessorClient)

    logger.info(f"Using {client_class.__name__} for {county_name}")

    return client_class()
