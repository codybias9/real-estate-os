"""
Base connector interface for external data sources
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class ConnectorType(str, Enum):
    """Data connector types"""

    ATTOM = "attom"
    REGRID = "regrid"
    OPENADDRESSES = "openaddresses"


class ConnectorStatus(str, Enum):
    """Connector status"""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"


class PropertyData(BaseModel):
    """Standardized property data from connectors"""

    # Address
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    county: Optional[str] = None

    # Location
    lat: Optional[float] = None
    lng: Optional[float] = None

    # Physical characteristics
    beds: Optional[int] = None
    baths: Optional[float] = None
    sqft: Optional[int] = None
    lot_sqft: Optional[int] = None
    year_built: Optional[int] = None

    # Ownership
    owner_name: Optional[str] = None
    owner_type: Optional[str] = None

    # Valuation
    assessed_value: Optional[float] = None
    market_value: Optional[float] = None
    last_sale_price: Optional[float] = None
    last_sale_date: Optional[str] = None

    # Zoning
    zoning: Optional[str] = None
    land_use: Optional[str] = None

    # Raw data from connector
    raw_data: Dict[str, Any] = Field(default_factory=dict)


class ConnectorResponse(BaseModel):
    """Connector response with metadata"""

    success: bool
    connector: ConnectorType
    data: Optional[PropertyData] = None
    error: Optional[str] = None
    cost: float = 0.0  # API call cost in USD
    cached: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConnectorConfig(BaseModel):
    """Configuration for a connector"""

    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    rate_limit_per_minute: int = 60
    cost_per_request: float = 0.0


class BaseConnector(ABC):
    """
    Base class for external data connectors.

    All connectors must implement:
    - get_property_data(apn, state, county)
    - health_check()
    """

    def __init__(self, config: ConnectorConfig):
        """
        Initialize connector.

        Args:
            config: Connector configuration
        """
        self.config = config
        self.status = ConnectorStatus.AVAILABLE
        self._request_count = 0
        self._total_cost = 0.0

    @property
    def connector_type(self) -> ConnectorType:
        """Get connector type"""
        raise NotImplementedError

    @abstractmethod
    async def get_property_data(
        self,
        apn: str,
        state: str,
        county: Optional[str] = None,
    ) -> ConnectorResponse:
        """
        Get property data from connector.

        Args:
            apn: Assessor's Parcel Number
            state: State code (e.g., "CA", "TX")
            county: County name (optional)

        Returns:
            ConnectorResponse with property data
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if connector is healthy.

        Returns:
            True if connector is available
        """
        pass

    def _record_request(self, cost: float = 0.0):
        """Record API request for tracking"""
        self._request_count += 1
        self._total_cost += cost

    def get_stats(self) -> Dict[str, Any]:
        """
        Get connector statistics.

        Returns:
            Dictionary with request count and total cost
        """
        return {
            "connector": self.connector_type.value,
            "status": self.status.value,
            "request_count": self._request_count,
            "total_cost": round(self._total_cost, 2),
        }
