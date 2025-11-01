"""Base API client with rate limiting, caching, and error handling

All API clients should inherit from this base class.
"""
import logging
import time
import hashlib
import json
from typing import Optional, Dict, Any, Callable
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter using token bucket algorithm"""

    def __init__(self, calls_per_second: float):
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call_time = 0

    def wait(self):
        """Wait if necessary to respect rate limit"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time

        if time_since_last_call < self.min_interval:
            sleep_time = self.min_interval - time_since_last_call
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self.last_call_time = time.time()


class SimpleCache:
    """Simple in-memory cache with TTL

    In production, this should be replaced with Redis.
    """

    def __init__(self, ttl_seconds: int = 3600):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_seconds = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() < entry['expires_at']:
                logger.debug(f"Cache hit: {key}")
                return entry['value']
            else:
                logger.debug(f"Cache expired: {key}")
                del self.cache[key]

        logger.debug(f"Cache miss: {key}")
        return None

    def set(self, key: str, value: Any):
        """Set value in cache with expiration"""
        self.cache[key] = {
            'value': value,
            'expires_at': datetime.now() + timedelta(seconds=self.ttl_seconds)
        }
        logger.debug(f"Cache set: {key}")

    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
        logger.info("Cache cleared")


class BaseAPIClient(ABC):
    """
    Abstract base class for all API clients

    Provides:
    - HTTP session with retries
    - Rate limiting
    - Response caching
    - Error handling
    - Request logging
    - Cost tracking
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        rate_limit_per_second: float = 1.0,
        cache_ttl_seconds: int = 3600,
        timeout_seconds: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize API client

        Args:
            api_key: API key for authentication
            rate_limit_per_second: Maximum requests per second
            cache_ttl_seconds: Cache time-to-live in seconds
            timeout_seconds: Request timeout
            max_retries: Maximum retry attempts
        """
        self.api_key = api_key
        self.timeout = timeout_seconds

        # Setup HTTP session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Rate limiting
        self.rate_limiter = RateLimiter(rate_limit_per_second)

        # Caching
        self.cache = SimpleCache(ttl_seconds=cache_ttl_seconds)

        # Statistics
        self.stats = {
            'requests_made': 0,
            'cache_hits': 0,
            'errors': 0,
            'total_cost': 0.0
        }

    @abstractmethod
    def get_name(self) -> str:
        """Return the name of this API client"""
        pass

    @abstractmethod
    def get_cost_per_call(self) -> float:
        """Return the cost per API call in USD"""
        pass

    def _make_cache_key(self, method: str, url: str, params: Optional[Dict] = None) -> str:
        """Generate cache key from request parameters"""
        key_parts = [self.get_name(), method, url]

        if params:
            # Sort params for consistent hashing
            param_str = json.dumps(params, sort_keys=True)
            key_parts.append(param_str)

        key_string = ":".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    def _request(
        self,
        method: str,
        url: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Make HTTP request with rate limiting, caching, and error handling

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            params: Query parameters
            data: Request body data
            headers: Request headers
            use_cache: Whether to use cache for GET requests

        Returns:
            Response data as dictionary

        Raises:
            requests.RequestException: On request failure
        """
        # Check cache for GET requests
        if method.upper() == 'GET' and use_cache:
            cache_key = self._make_cache_key(method, url, params)
            cached_response = self.cache.get(cache_key)

            if cached_response is not None:
                self.stats['cache_hits'] += 1
                return cached_response

        # Apply rate limiting
        self.rate_limiter.wait()

        # Make request
        try:
            logger.info(f"[{self.get_name()}] {method} {url}")

            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=headers,
                timeout=self.timeout
            )

            response.raise_for_status()

            # Parse JSON response
            response_data = response.json()

            # Update statistics
            self.stats['requests_made'] += 1
            self.stats['total_cost'] += self.get_cost_per_call()

            # Cache GET requests
            if method.upper() == 'GET' and use_cache:
                cache_key = self._make_cache_key(method, url, params)
                self.cache.set(cache_key, response_data)

            return response_data

        except requests.RequestException as e:
            self.stats['errors'] += 1
            logger.error(f"[{self.get_name()}] Request failed: {e}")
            raise

    def get(self, url: str, params: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """Make GET request"""
        return self._request('GET', url, params=params, **kwargs)

    def post(self, url: str, data: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """Make POST request"""
        return self._request('POST', url, data=data, **kwargs)

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        return {
            'client': self.get_name(),
            **self.stats,
            'cache_hit_rate': (
                self.stats['cache_hits'] / max(self.stats['requests_made'], 1)
                if self.stats['requests_made'] > 0
                else 0
            )
        }

    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            'requests_made': 0,
            'cache_hits': 0,
            'errors': 0,
            'total_cost': 0.0
        }
        logger.info(f"[{self.get_name()}] Statistics reset")
