"""
Geocode Plugin - Add lat/lng to properties
In production, would call Google Maps API, Mapbox, or similar
For MVP, uses mock data
"""

from datetime import datetime
from typing import Any

try:
    from contracts import PropertyRecord, Geo, Provenance
except ImportError:
    import sys
    sys.path.insert(0, '/home/user/real-estate-os/packages/contracts/src')
    from contracts import PropertyRecord, Geo, Provenance

from .base import EnrichmentPlugin, PluginResult, PluginPriority


class GeocodePlugin(EnrichmentPlugin):
    """
    Geocodes property addresses to lat/lng coordinates.

    In production:
    - Call geocoding API (Google Maps, Mapbox, etc.)
    - Handle rate limits
    - Cache results
    - Respect cost caps via Policy Kernel

    For MVP:
    - Uses deterministic mock data based on address
    - Returns plausible coordinates for Las Vegas area
    """

    def __init__(self, mock: bool = True):
        super().__init__(
            name="geocode",
            priority=PluginPriority.CRITICAL  # Geocoding should run early
        )
        self.mock = mock

    def can_enrich(self, record: PropertyRecord) -> bool:
        """Can enrich if address exists and geo is missing"""
        return record.address is not None and record.geo is None

    def get_required_fields(self) -> list[str]:
        return ["address.line1", "address.city", "address.state", "address.zip"]

    async def enrich(self, record: PropertyRecord) -> PluginResult:
        """Add geocoded coordinates to property record"""
        try:
            if not self.can_enrich(record):
                return PluginResult(
                    plugin_name=self.name,
                    success=False,
                    error="Cannot enrich: address missing or geo already exists"
                )

            # In production, call geocoding API
            if self.mock:
                geo_data = self._mock_geocode(record.address.to_single_line())
            else:
                raise NotImplementedError("Real geocoding API not yet implemented")

            # Update record
            record.geo = Geo(
                lat=geo_data["lat"],
                lng=geo_data["lng"],
                accuracy=geo_data.get("accuracy", "mock"),
                parcel_polygon=geo_data.get("parcel_polygon")
            )

            # Add provenance
            prov = Provenance(
                field="geo",
                source=self.name,
                fetched_at=datetime.utcnow(),
                confidence=0.85 if self.mock else 0.95,
                cost_cents=0 if self.mock else 1,  # Real geocoding typically $0.01/call
                license="mock" if self.mock else "https://maps.googleapis.com/terms"
            )
            record.add_provenance(prov)

            return PluginResult(
                plugin_name=self.name,
                success=True,
                fields_updated=["geo"],
                provenance_added=[prov],
                metadata={"mock": self.mock}
            )

        except Exception as e:
            return PluginResult(
                plugin_name=self.name,
                success=False,
                error=str(e)
            )

    def _mock_geocode(self, address: str) -> dict[str, Any]:
        """
        Generate mock geocoded data.

        Uses hash of address to generate deterministic but varied coordinates
        within Las Vegas area (36.0° to 36.3° N, -115.3° to -115.0° W)
        """
        # Simple hash for deterministic coordinates
        addr_hash = sum(ord(c) for c in address)

        # Las Vegas area coordinates with variation
        base_lat = 36.1699
        base_lng = -115.1398

        # Add variation based on address hash (±0.1 degrees ~ 11km)
        lat_offset = ((addr_hash % 200) - 100) / 1000.0
        lng_offset = ((addr_hash % 300) - 150) / 1000.0

        return {
            "lat": base_lat + lat_offset,
            "lng": base_lng + lng_offset,
            "accuracy": "mock",
            "parcel_polygon": None
        }
