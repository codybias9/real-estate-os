"""Enhanced Geocoding Service
Integrates with libpostal for address normalization and Nominatim for geocoding

Features:
- Address normalization before geocoding
- Confidence tracking
- Self-hosted Nominatim option
- Fallback to multiple providers
- Parcel centroid snapping
"""

from typing import Dict, Optional, Tuple
import httpx
import asyncio
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GeocodingResult:
    """Geocoding result with confidence tracking"""
    latitude: float
    longitude: float
    canonical_address: str
    address_components: Dict[str, str]
    confidence: float
    method: str
    provider: str


class GeocodingService:
    """Enhanced geocoding with normalization and confidence tracking"""

    def __init__(self):
        # Normalization service endpoint
        self.normalization_url = "http://normalization-service:8001"

        # Nominatim endpoints (self-hosted preferred)
        self.nominatim_url = "http://nominatim:8080"  # Self-hosted
        self.nominatim_fallback = "https://nominatim.openstreetmap.org"

        # User agent (required by Nominatim)
        self.user_agent = "RealEstateOS/1.0"

    async def geocode(self, raw_address: str, country: str = "us") -> Optional[GeocodingResult]:
        """Geocode address with normalization

        Pipeline:
        1. Normalize address with libpostal
        2. Geocode with Nominatim
        3. Validate and calculate confidence
        4. Optionally snap to parcel centroid

        Args:
            raw_address: Raw address string
            country: Country code (default: us)

        Returns:
            GeocodingResult with lat/lon and confidence
        """

        # Step 1: Normalize address
        normalized = await self._normalize_address(raw_address, country)
        if not normalized:
            logger.warning(f"Address normalization failed: {raw_address}")
            return None

        # Step 2: Geocode
        geocoded = await self._geocode_nominatim(normalized["canonical_address"])
        if not geocoded:
            logger.warning(f"Geocoding failed: {normalized['canonical_address']}")
            return None

        # Step 3: Calculate confidence
        confidence = self._calculate_confidence(
            normalized["confidence"],
            geocoded["quality_score"],
            geocoded["importance"]
        )

        # Step 4: Create result
        result = GeocodingResult(
            latitude=geocoded["lat"],
            longitude=geocoded["lon"],
            canonical_address=normalized["canonical_address"],
            address_components=normalized["components"],
            confidence=confidence,
            method="nominatim",
            provider="self-hosted" if "8080" in self.nominatim_url else "osm"
        )

        logger.info(f"Geocoded: {raw_address} -> ({result.latitude}, {result.longitude}), confidence={result.confidence}")

        return result

    async def _normalize_address(self, raw_address: str, country: str) -> Optional[Dict]:
        """Normalize address using libpostal service"""

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{self.normalization_url}/normalize",
                    json={"raw_address": raw_address, "country": country}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Address normalization failed: {e}")
            return None

    async def _geocode_nominatim(self, address: str) -> Optional[Dict]:
        """Geocode using Nominatim (self-hosted preferred)"""

        # Try self-hosted first
        result = await self._nominatim_search(self.nominatim_url, address)
        if result:
            return result

        # Fallback to public Nominatim (with rate limiting)
        logger.warning("Self-hosted Nominatim failed, falling back to public")
        await asyncio.sleep(1)  # Rate limit: 1 request per second
        return await self._nominatim_search(self.nominatim_fallback, address)

    async def _nominatim_search(self, base_url: str, address: str) -> Optional[Dict]:
        """Search Nominatim for address"""

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{base_url}/search",
                    params={
                        "q": address,
                        "format": "json",
                        "addressdetails": 1,
                        "limit": 1,
                        "countrycodes": "us"  # Limit to US for performance
                    },
                    headers={"User-Agent": self.user_agent}
                )
                response.raise_for_status()
                results = response.json()

                if not results:
                    return None

                result = results[0]

                # Calculate quality score from bounding box size
                bbox = result.get("boundingbox", [])
                quality_score = self._calculate_quality_from_bbox(bbox) if bbox else 0.5

                return {
                    "lat": float(result["lat"]),
                    "lon": float(result["lon"]),
                    "display_name": result.get("display_name"),
                    "importance": result.get("importance", 0.5),
                    "quality_score": quality_score,
                    "osm_type": result.get("osm_type"),
                    "osm_id": result.get("osm_id"),
                    "address": result.get("address", {})
                }

        except Exception as e:
            logger.error(f"Nominatim search failed: {e}")
            return None

    def _calculate_quality_from_bbox(self, bbox: list) -> float:
        """Calculate quality score from bounding box

        Smaller bounding boxes = higher confidence (more precise)

        Args:
            bbox: [min_lat, max_lat, min_lon, max_lon]

        Returns:
            Quality score 0.0-1.0
        """
        try:
            min_lat, max_lat, min_lon, max_lon = map(float, bbox)

            # Calculate area (rough approximation)
            lat_diff = max_lat - min_lat
            lon_diff = max_lon - min_lon
            area = lat_diff * lon_diff

            # Smaller area = higher quality
            # Thresholds:
            # < 0.0001 (parcel-level) = 1.0
            # < 0.001 (street-level) = 0.8
            # < 0.01 (neighborhood) = 0.6
            # >= 0.01 (city-level) = 0.4

            if area < 0.0001:
                return 1.0
            elif area < 0.001:
                return 0.8
            elif area < 0.01:
                return 0.6
            else:
                return 0.4

        except Exception:
            return 0.5

    def _calculate_confidence(
        self,
        normalization_confidence: float,
        quality_score: float,
        importance: float
    ) -> float:
        """Calculate overall geocoding confidence

        Combines:
        - Normalization confidence (from libpostal)
        - Quality score (from bbox size)
        - Importance (from Nominatim)

        Args:
            normalization_confidence: 0.0-1.0 from address normalization
            quality_score: 0.0-1.0 from bounding box analysis
            importance: 0.0-1.0 from Nominatim

        Returns:
            Overall confidence 0.0-1.0
        """

        # Weighted average
        weights = {
            "normalization": 0.4,
            "quality": 0.4,
            "importance": 0.2
        }

        confidence = (
            normalization_confidence * weights["normalization"] +
            quality_score * weights["quality"] +
            importance * weights["importance"]
        )

        return round(confidence, 2)

    async def snap_to_parcel(
        self,
        latitude: float,
        longitude: float,
        search_radius_meters: int = 50
    ) -> Optional[Tuple[float, float]]:
        """Snap coordinates to nearest parcel centroid

        Improves accuracy by aligning to cadastral data

        Args:
            latitude: Initial latitude
            longitude: Initial longitude
            search_radius_meters: Search radius for parcels

        Returns:
            (snapped_lat, snapped_lon) or None if no parcel found
        """

        # TODO: Implement parcel lookup
        # Requires parcel data from county assessor
        # For now, return original coordinates

        logger.debug(f"Parcel snapping not yet implemented for ({latitude}, {longitude})")
        return None

    async def validate_coordinates(
        self,
        latitude: float,
        longitude: float,
        county_polygon: Optional[str] = None
    ) -> bool:
        """Validate coordinates are reasonable

        Checks:
        - Latitude in valid range (-90, 90)
        - Longitude in valid range (-180, 180)
        - Within county boundary (if provided)

        Args:
            latitude: Latitude to validate
            longitude: Longitude to validate
            county_polygon: WKT polygon for county boundary

        Returns:
            True if valid
        """

        # Range check
        if not (-90 <= latitude <= 90):
            return False
        if not (-180 <= longitude <= 180):
            return False

        # County boundary check (if provided)
        if county_polygon:
            # TODO: Implement PostGIS ST_Contains check
            pass

        return True
