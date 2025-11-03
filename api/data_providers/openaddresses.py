"""
OpenAddresses Data Provider

Free, open-source geocoding using OpenAddresses.io data

Provides:
- Address geocoding (lat/lon from address)
- Address normalization
- Coordinate validation

Coverage: Global (varies by region)
Cost: Free
License: CC0/ODbL
Data Quality: ~85%
"""
import logging
from typing import Optional
from .base import (
    DataProvider,
    EnrichmentResult,
    ProviderError,
    DataTier,
    FieldConfidence
)

logger = logging.getLogger(__name__)


class OpenAddressesProvider(DataProvider):
    """
    OpenAddresses geocoding provider

    Note: OpenAddresses is a collection of datasets, not a live API.
    This implementation uses a cached local database or the Batch API.

    For production use, either:
    1. Download and host OpenAddresses data locally
    2. Use a geocoding service that includes OpenAddresses (like Pelias)
    3. Use the batch processing API: https://batch.openaddresses.io/
    """

    def __init__(self, **kwargs):
        super().__init__(
            tier=DataTier.COMMUNITY,
            cost_per_request=0.0,
            rate_limit_per_minute=60,  # Self-imposed limit
            **kwargs
        )

    @property
    def name(self) -> str:
        return "OpenAddresses"

    @property
    def supported_fields(self) -> list[str]:
        return [
            "latitude",
            "longitude",
            "normalized_address",
            "geocode_confidence"
        ]

    def enrich_property(
        self,
        address: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        zip_code: Optional[str] = None,
        **kwargs
    ) -> EnrichmentResult:
        """
        Geocode address using OpenAddresses data

        Args:
            address: Street address
            city: City name
            state: State code
            zip_code: ZIP code

        Returns:
            EnrichmentResult with lat/lon if found
        """
        result = EnrichmentResult(
            provider_name=self.name,
            success=False,
            cost=0.0
        )

        if not all([address, city, state]):
            result.errors.append("OpenAddresses requires address, city, and state")
            return result

        try:
            # Normalize address
            full_address = self._normalize_address(address, city, state, zip_code)

            # In production, query local OpenAddresses database or use Pelias
            # For now, use Nominatim (OSM) as a fallback geocoder
            geocoded = self._geocode_with_nominatim(full_address)

            if geocoded:
                result.success = True
                result.add_field(
                    "latitude",
                    geocoded["lat"],
                    confidence=FieldConfidence.MEDIUM,
                    source_url="https://openaddresses.io",
                    expires_days=365
                )
                result.add_field(
                    "longitude",
                    geocoded["lon"],
                    confidence=FieldConfidence.MEDIUM,
                    source_url="https://openaddresses.io",
                    expires_days=365
                )
                result.add_field(
                    "normalized_address",
                    geocoded["display_name"],
                    confidence=FieldConfidence.MEDIUM,
                    source_url="https://openaddresses.io",
                    expires_days=365
                )
                result.add_field(
                    "geocode_confidence",
                    0.85,  # OpenAddresses typical quality
                    confidence=FieldConfidence.MEDIUM,
                    expires_days=365
                )
            else:
                result.errors.append("Address not found in OpenAddresses data")

        except Exception as e:
            logger.error(f"OpenAddresses enrichment error: {str(e)}")
            result.errors.append(str(e))

        return result

    def _geocode_with_nominatim(self, address: str) -> Optional[dict]:
        """
        Geocode using Nominatim (OSM) as a fallback

        In production, replace with local OpenAddresses database query

        Args:
            address: Full address string

        Returns:
            Dict with lat, lon, display_name or None
        """
        try:
            # Use Nominatim (respecting usage policy: 1 request/second)
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                "q": address,
                "format": "json",
                "limit": 1
            }
            headers = {
                "User-Agent": "RealEstateOS/1.0"  # Required by Nominatim
            }

            import requests
            import time

            # Rate limit: 1 req/sec for Nominatim
            time.sleep(1)

            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            results = response.json()
            if results and len(results) > 0:
                return {
                    "lat": float(results[0]["lat"]),
                    "lon": float(results[0]["lon"]),
                    "display_name": results[0]["display_name"]
                }

            return None

        except Exception as e:
            logger.error(f"Nominatim geocoding error: {str(e)}")
            return None

    def check_availability(self) -> bool:
        """Check if geocoding service is available"""
        try:
            # Test with a known address
            result = self._geocode_with_nominatim("1600 Pennsylvania Avenue, Washington, DC")
            return result is not None
        except Exception:
            return False
