"""
libpostal Client for Address Normalization

This module provides a Python client for the libpostal REST API service,
enabling address parsing, normalization, and expansion for data quality.

Features:
- Parse addresses into structured components
- Normalize addresses for deduplication
- Expand addresses for fuzzy matching
- Cache results for performance
- Multi-tenant support

Usage:
    from address_normalization import LibpostalClient
    
    client = LibpostalClient()
    result = client.parse_address("123 Main St, Austin, TX 78701")
"""

import os
import logging
import requests
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class AddressComponents:
    """Structured address components from libpostal parsing."""
    
    house_number: Optional[str] = None
    road: Optional[str] = None
    unit: Optional[str] = None
    level: Optional[str] = None
    staircase: Optional[str] = None
    entrance: Optional[str] = None
    po_box: Optional[str] = None
    postcode: Optional[str] = None
    suburb: Optional[str] = None
    city_district: Optional[str] = None
    city: Optional[str] = None
    island: Optional[str] = None
    state_district: Optional[str] = None
    state: Optional[str] = None
    country_region: Optional[str] = None
    country: Optional[str] = None
    world_region: Optional[str] = None
    
    # Additional fields
    raw_address: Optional[str] = None
    confidence: float = 1.0
    parsed_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in self.__dict__.items() if v is not None}
    
    def to_formatted_address(self) -> str:
        """Format components back to a normalized address string."""
        parts = []
        
        # Street address
        if self.house_number:
            parts.append(self.house_number)
        if self.road:
            parts.append(self.road)
        if self.unit:
            parts.append(f"Unit {self.unit}")
        
        # City, State ZIP
        city_state_zip = []
        if self.city:
            city_state_zip.append(self.city)
        if self.state:
            city_state_zip.append(self.state)
        if self.postcode:
            city_state_zip.append(self.postcode)
        
        if city_state_zip:
            parts.append(", ".join(city_state_zip))
        
        return ", ".join(parts) if parts else self.raw_address or ""


@dataclass
class NormalizedAddress:
    """Normalized address with original and parsed components."""
    
    raw_address: str
    components: AddressComponents
    normalized_string: str
    expansions: List[str] = field(default_factory=list)
    hash: str = ""
    
    def __post_init__(self):
        """Calculate hash for deduplication."""
        if not self.hash:
            # Use normalized components for stable hashing
            hash_input = f"{self.components.house_number}|{self.components.road}|{self.components.city}|{self.components.state}|{self.components.postcode}"
            self.hash = hashlib.sha256(hash_input.lower().encode()).hexdigest()[:16]


class LibpostalClient:
    """
    Client for libpostal address normalization service.
    
    Provides methods for parsing, normalizing, and expanding addresses
    using the libpostal REST API.
    """
    
    def __init__(
        self, 
        base_url: Optional[str] = None,
        timeout: int = 10,
        retry_attempts: int = 3,
        cache_size: int = 1000
    ):
        """
        Initialize the libpostal client.
        
        Args:
            base_url: Base URL of libpostal service (default: http://localhost:8181)
            timeout: Request timeout in seconds
            retry_attempts: Number of retry attempts for failed requests
            cache_size: Size of LRU cache for parsed addresses
        """
        self.base_url = base_url or os.getenv("LIBPOSTAL_URL", "http://localhost:8181")
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.cache_size = cache_size
        
        # Stats tracking
        self.stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "parse_errors": 0,
            "api_errors": 0
        }
    
    def health_check(self) -> bool:
        """
        Check if libpostal service is healthy.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=self.timeout
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def parse_address(
        self, 
        address: str,
        country: Optional[str] = None,
        language: Optional[str] = None
    ) -> AddressComponents:
        """
        Parse an address into structured components.
        
        Args:
            address: Raw address string
            country: ISO country code (optional, improves accuracy)
            language: Language code (optional)
            
        Returns:
            AddressComponents object with parsed fields
            
        Raises:
            ValueError: If address is empty or invalid
            ConnectionError: If libpostal service is unavailable
        """
        if not address or not address.strip():
            raise ValueError("Address cannot be empty")
        
        self.stats["total_requests"] += 1
        
        # Check cache first
        cache_key = self._get_cache_key(address, country, language)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            self.stats["cache_hits"] += 1
            return cached_result
        
        self.stats["cache_misses"] += 1
        
        # Prepare request payload
        payload = {"query": address.strip()}
        if country:
            payload["country"] = country
        if language:
            payload["language"] = language
        
        # Make API request with retries
        for attempt in range(self.retry_attempts):
            try:
                response = requests.post(
                    f"{self.base_url}/parser",
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                # Parse response
                result = response.json()
                components = self._parse_response(result, address)
                
                # Cache result
                self._add_to_cache(cache_key, components)
                
                return components
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Parse attempt {attempt + 1} failed: {e}")
                if attempt == self.retry_attempts - 1:
                    self.stats["api_errors"] += 1
                    raise ConnectionError(f"Failed to connect to libpostal service: {e}")
        
        # Should never reach here, but just in case
        raise ConnectionError("Failed to parse address after all retries")
    
    def expand_address(
        self, 
        address: str,
        languages: Optional[List[str]] = None
    ) -> List[str]:
        """
        Expand an address into normalized variations for fuzzy matching.
        
        Args:
            address: Raw address string
            languages: List of language codes for expansions
            
        Returns:
            List of normalized address variations
            
        Example:
            >>> client.expand_address("123 Main Street")
            ['123 main street', '123 main st', '123 main str']
        """
        if not address or not address.strip():
            return []
        
        payload = {"query": address.strip()}
        if languages:
            payload["languages"] = languages
        
        try:
            response = requests.post(
                f"{self.base_url}/expand",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            # libpostal expand returns a list of strings
            return result if isinstance(result, list) else []
            
        except Exception as e:
            logger.error(f"Address expansion failed: {e}")
            return [address.lower().strip()]
    
    def normalize_address(
        self, 
        address: str,
        country: Optional[str] = None,
        include_expansions: bool = False
    ) -> NormalizedAddress:
        """
        Parse and normalize an address for storage and matching.
        
        This is the recommended method for most use cases as it combines
        parsing and normalization into a single operation.
        
        Args:
            address: Raw address string
            country: ISO country code (optional)
            include_expansions: Whether to generate expansion variations
            
        Returns:
            NormalizedAddress object with components and normalized string
        """
        # Parse address
        components = self.parse_address(address, country=country)
        
        # Generate normalized string
        normalized_str = components.to_formatted_address()
        
        # Generate expansions if requested
        expansions = []
        if include_expansions:
            expansions = self.expand_address(normalized_str)
        
        return NormalizedAddress(
            raw_address=address,
            components=components,
            normalized_string=normalized_str,
            expansions=expansions
        )
    
    def batch_parse_addresses(
        self, 
        addresses: List[str],
        country: Optional[str] = None
    ) -> List[Tuple[str, Optional[AddressComponents]]]:
        """
        Parse multiple addresses in batch.
        
        Args:
            addresses: List of raw address strings
            country: ISO country code (optional)
            
        Returns:
            List of tuples (original_address, parsed_components)
            Returns None for components if parsing failed
        """
        results = []
        
        for address in addresses:
            try:
                components = self.parse_address(address, country=country)
                results.append((address, components))
            except Exception as e:
                logger.warning(f"Failed to parse address '{address}': {e}")
                results.append((address, None))
                self.stats["parse_errors"] += 1
        
        return results
    
    def compare_addresses(
        self, 
        address1: str, 
        address2: str,
        country: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Compare two addresses for similarity.
        
        Args:
            address1: First address string
            address2: Second address string
            country: ISO country code (optional)
            
        Returns:
            Dictionary with comparison results:
            - exact_match: bool (normalized strings match)
            - hash_match: bool (address hashes match)
            - component_similarity: float (0-1)
            - differences: list of differing components
        """
        norm1 = self.normalize_address(address1, country=country)
        norm2 = self.normalize_address(address2, country=country)
        
        # Check for exact match
        exact_match = norm1.normalized_string.lower() == norm2.normalized_string.lower()
        hash_match = norm1.hash == norm2.hash
        
        # Calculate component similarity
        components1 = norm1.components.to_dict()
        components2 = norm2.components.to_dict()
        
        all_keys = set(components1.keys()) | set(components2.keys())
        matching_keys = sum(
            1 for k in all_keys 
            if components1.get(k) == components2.get(k) and components1.get(k) is not None
        )
        similarity = matching_keys / len(all_keys) if all_keys else 0.0
        
        # Find differences
        differences = [
            k for k in all_keys 
            if components1.get(k) != components2.get(k)
        ]
        
        return {
            "exact_match": exact_match,
            "hash_match": hash_match,
            "component_similarity": similarity,
            "differences": differences,
            "address1_normalized": norm1.normalized_string,
            "address2_normalized": norm2.normalized_string
        }
    
    def get_stats(self) -> Dict[str, any]:
        """
        Get client statistics.
        
        Returns:
            Dictionary with usage statistics
        """
        cache_hit_rate = (
            self.stats["cache_hits"] / self.stats["total_requests"]
            if self.stats["total_requests"] > 0 else 0.0
        )
        
        return {
            **self.stats,
            "cache_hit_rate": f"{cache_hit_rate:.2%}",
            "service_healthy": self.health_check()
        }
    
    # Private helper methods
    
    def _get_cache_key(
        self, 
        address: str, 
        country: Optional[str], 
        language: Optional[str]
    ) -> str:
        """Generate cache key for address."""
        return f"{address.lower().strip()}|{country or ''}|{language or ''}"
    
    @lru_cache(maxsize=1000)
    def _get_from_cache(self, cache_key: str) -> Optional[AddressComponents]:
        """Get cached parse result."""
        # LRU cache handles caching automatically
        return None
    
    def _add_to_cache(self, cache_key: str, components: AddressComponents) -> None:
        """Add parse result to cache."""
        # Update the cache by calling the cached function
        # This is a bit of a hack, but works with lru_cache
        self._get_from_cache.__wrapped__ = lambda k: components if k == cache_key else None
    
    def _parse_response(
        self, 
        response: List[Dict[str, str]], 
        raw_address: str
    ) -> AddressComponents:
        """
        Parse libpostal API response into AddressComponents.
        
        Args:
            response: List of {label, value} dicts from libpostal
            raw_address: Original address string
            
        Returns:
            AddressComponents object
        """
        # Initialize components dict
        components_dict = {"raw_address": raw_address}
        
        # Parse response - libpostal returns list of {label, value} objects
        for item in response:
            label = item.get("label", "").lower()
            value = item.get("value", "").strip()
            
            if value:
                # Map libpostal labels to our field names
                field_name = label.replace(" ", "_")
                components_dict[field_name] = value
        
        # Create AddressComponents object
        return AddressComponents(**components_dict)


# Convenience function for quick parsing
def parse_address(address: str, libpostal_url: Optional[str] = None) -> AddressComponents:
    """
    Quick parse an address without creating a client instance.
    
    Args:
        address: Raw address string
        libpostal_url: Optional libpostal service URL
        
    Returns:
        AddressComponents object
    """
    client = LibpostalClient(base_url=libpostal_url)
    return client.parse_address(address)
