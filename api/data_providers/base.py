"""
Base Data Provider Interface

All data provider implementations must inherit from DataProvider
and implement the required methods.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DataTier(str, Enum):
    """Data source tier classification"""
    GOVERNMENT = "government"  # Free government data
    COMMUNITY = "community"    # Free community data
    DERIVED = "derived"        # Computed from other sources
    PAID = "paid"             # Paid commercial data


class FieldConfidence(str, Enum):
    """Confidence level for enriched fields"""
    HIGH = "high"         # >90% accuracy, verified
    MEDIUM = "medium"     # 70-90% accuracy
    LOW = "low"          # <70% accuracy, needs verification
    COMPUTED = "computed" # Derived from other fields


@dataclass
class EnrichmentResult:
    """
    Result from data provider enrichment

    Attributes:
        provider_name: Name of the data provider
        success: Whether enrichment succeeded
        fields: Dict of field_name -> value
        provenance: Dict of field_name -> source metadata
        cost: Cost of this enrichment in USD
        errors: List of error messages if any
        rate_limited: Whether request was rate limited
    """
    provider_name: str
    success: bool
    fields: Dict[str, Any] = field(default_factory=dict)
    provenance: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    cost: float = 0.0
    errors: List[str] = field(default_factory=list)
    rate_limited: bool = False
    response_time_ms: Optional[int] = None

    def add_field(
        self,
        name: str,
        value: Any,
        confidence: FieldConfidence,
        source_url: Optional[str] = None,
        expires_days: int = 90
    ):
        """Add enriched field with provenance"""
        self.fields[name] = value
        self.provenance[name] = {
            "confidence": confidence.value,
            "source_url": source_url,
            "fetched_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=expires_days)).isoformat()
        }


class ProviderError(Exception):
    """Base exception for provider errors"""
    pass


class RateLimitError(ProviderError):
    """Rate limit exceeded"""
    def __init__(self, retry_after: Optional[int] = None):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds" if retry_after else "Rate limit exceeded")


class AuthenticationError(ProviderError):
    """Authentication failed"""
    pass


class DataProvider(ABC):
    """
    Abstract base class for data providers

    All providers must implement:
    - enrich_property(): Main enrichment method
    - get_cost_estimate(): Estimate cost before calling
    - check_availability(): Verify provider is accessible
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        tier: DataTier = DataTier.GOVERNMENT,
        cost_per_request: float = 0.0,
        rate_limit_per_minute: Optional[int] = None,
        timeout: int = 30,
        **kwargs
    ):
        """
        Initialize data provider

        Args:
            api_key: API key for authentication (if required)
            tier: Data source tier
            cost_per_request: Cost per API request in USD
            rate_limit_per_minute: Rate limit (None = unlimited)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.tier = tier
        self.cost_per_request = cost_per_request
        self.rate_limit_per_minute = rate_limit_per_minute
        self.timeout = timeout
        self.config = kwargs

        # Rate limiting state (simple in-memory - use Redis in production)
        self._request_times: List[datetime] = []

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name"""
        pass

    @property
    @abstractmethod
    def supported_fields(self) -> List[str]:
        """List of fields this provider can enrich"""
        pass

    @abstractmethod
    def enrich_property(
        self,
        address: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        zip_code: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        apn: Optional[str] = None,
        **kwargs
    ) -> EnrichmentResult:
        """
        Enrich property data

        Args:
            address: Street address
            city: City name
            state: State code (e.g., "CA")
            zip_code: ZIP code
            latitude: Latitude
            longitude: Longitude
            apn: Assessor's Parcel Number
            **kwargs: Provider-specific parameters

        Returns:
            EnrichmentResult with enriched fields

        Raises:
            ProviderError: If enrichment fails
            RateLimitError: If rate limit exceeded
            AuthenticationError: If authentication fails
        """
        pass

    def get_cost_estimate(self, **kwargs) -> float:
        """
        Estimate cost for enrichment request

        Returns:
            Estimated cost in USD
        """
        return self.cost_per_request

    def check_availability(self) -> bool:
        """
        Check if provider is available

        Returns:
            True if provider can be used

        Example use:
            if provider.check_availability():
                result = provider.enrich_property(...)
        """
        try:
            # Simple health check (override in subclass)
            return True
        except Exception as e:
            logger.error(f"{self.name} availability check failed: {str(e)}")
            return False

    def _check_rate_limit(self):
        """
        Check and enforce rate limiting

        Raises:
            RateLimitError: If rate limit would be exceeded
        """
        if self.rate_limit_per_minute is None:
            return  # No rate limit

        now = datetime.utcnow()
        one_minute_ago = now - timedelta(minutes=1)

        # Remove old requests
        self._request_times = [t for t in self._request_times if t > one_minute_ago]

        # Check limit
        if len(self._request_times) >= self.rate_limit_per_minute:
            oldest = min(self._request_times)
            retry_after = int((oldest + timedelta(minutes=1) - now).total_seconds())
            raise RateLimitError(retry_after=retry_after)

        # Record this request
        self._request_times.append(now)

    def _make_request(
        self,
        url: str,
        method: str = "GET",
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Dict:
        """
        Make HTTP request with error handling

        Args:
            url: Request URL
            method: HTTP method
            params: Query parameters
            json_data: JSON body
            headers: HTTP headers

        Returns:
            Response JSON

        Raises:
            ProviderError: If request fails
            RateLimitError: If rate limited
            AuthenticationError: If auth fails
        """
        import requests
        import time

        # Check rate limit before making request
        self._check_rate_limit()

        # Prepare headers
        req_headers = headers or {}
        if self.api_key:
            # Common auth header patterns (override in subclass if different)
            req_headers["Authorization"] = f"Bearer {self.api_key}"

        start_time = time.time()

        try:
            response = requests.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers=req_headers,
                timeout=self.timeout
            )

            response_time_ms = int((time.time() - start_time) * 1000)

            # Handle errors
            if response.status_code == 401:
                raise AuthenticationError(f"Authentication failed for {self.name}")
            elif response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                raise RateLimitError(retry_after=retry_after)
            elif response.status_code >= 400:
                raise ProviderError(f"{self.name} request failed: {response.status_code} {response.text}")

            return response.json(), response_time_ms

        except requests.exceptions.Timeout:
            raise ProviderError(f"{self.name} request timeout after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            raise ProviderError(f"{self.name} request error: {str(e)}")

    def _normalize_address(self, address: str, city: str, state: str, zip_code: Optional[str] = None) -> str:
        """
        Normalize address for API calls

        Args:
            address: Street address
            city: City
            state: State
            zip_code: ZIP code

        Returns:
            Normalized address string
        """
        parts = [address, city, state]
        if zip_code:
            parts.append(zip_code)
        return ", ".join(p.strip() for p in parts if p)

    def __repr__(self):
        return f"<{self.__class__.__name__} tier={self.tier.value} cost=${self.cost_per_request}>"
