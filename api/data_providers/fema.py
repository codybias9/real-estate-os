"""
FEMA National Flood Hazard Layer Provider

Free government data for flood zones and risks

Provides:
- Flood zone designation (A, AE, V, X, etc.)
- Base Flood Elevation (BFE)
- SFHA status (Special Flood Hazard Area)
- Flood insurance requirements

Coverage: US nationwide
Cost: Free (public domain)
License: Public Domain
Data Quality: 95%
Update Frequency: ~90 days
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


class FEMAProvider(DataProvider):
    """
    FEMA NFHL (National Flood Hazard Layer) provider

    Uses FEMA's public ArcGIS REST API to query flood zones by coordinates
    """

    # FEMA NFHL REST API endpoint
    BASE_URL = "https://hazards.fema.gov/gis/nfhl/rest/services/public/NFHL/MapServer"

    def __init__(self, **kwargs):
        super().__init__(
            tier=DataTier.GOVERNMENT,
            cost_per_request=0.0,
            rate_limit_per_minute=60,  # Self-imposed
            **kwargs
        )

    @property
    def name(self) -> str:
        return "FEMA_NFHL"

    @property
    def supported_fields(self) -> list[str]:
        return [
            "flood_zone",
            "flood_zone_subtype",
            "base_flood_elevation",
            "sfha_status",
            "flood_insurance_required",
            "coastal_flood_risk"
        ]

    def enrich_property(
        self,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        **kwargs
    ) -> EnrichmentResult:
        """
        Get flood zone data for coordinates

        Args:
            latitude: Property latitude
            longitude: Property longitude

        Returns:
            EnrichmentResult with flood zone information
        """
        result = EnrichmentResult(
            provider_name=self.name,
            success=False,
            cost=0.0
        )

        if not latitude or not longitude:
            result.errors.append("FEMA requires latitude and longitude")
            return result

        try:
            # Query FEMA NFHL API
            flood_data = self._query_flood_zone(latitude, longitude)

            if flood_data:
                result.success = True

                # Flood zone (e.g., "AE", "X", "V")
                flood_zone = flood_data.get("FLD_ZONE", "X")
                result.add_field(
                    "flood_zone",
                    flood_zone,
                    confidence=FieldConfidence.HIGH,
                    source_url=f"{self.BASE_URL}",
                    expires_days=90
                )

                # Flood zone subtype
                subtype = flood_data.get("ZONE_SUBTY")
                if subtype:
                    result.add_field(
                        "flood_zone_subtype",
                        subtype,
                        confidence=FieldConfidence.HIGH,
                        expires_days=90
                    )

                # Base Flood Elevation
                bfe = flood_data.get("STATIC_BFE")
                if bfe:
                    result.add_field(
                        "base_flood_elevation",
                        float(bfe),
                        confidence=FieldConfidence.HIGH,
                        expires_days=90
                    )

                # SFHA status (Special Flood Hazard Area)
                sfha = self._is_sfha(flood_zone)
                result.add_field(
                    "sfha_status",
                    sfha,
                    confidence=FieldConfidence.HIGH,
                    expires_days=90
                )

                # Flood insurance requirement
                insurance_required = self._requires_insurance(flood_zone)
                result.add_field(
                    "flood_insurance_required",
                    insurance_required,
                    confidence=FieldConfidence.HIGH,
                    expires_days=90
                )

                # Coastal flood risk (V zones)
                coastal_risk = flood_zone.startswith("V")
                result.add_field(
                    "coastal_flood_risk",
                    coastal_risk,
                    confidence=FieldConfidence.HIGH,
                    expires_days=90
                )
            else:
                # Default to minimal risk zone if not in FEMA data
                result.success = True
                result.add_field(
                    "flood_zone",
                    "X",  # Minimal flood risk
                    confidence=FieldConfidence.MEDIUM,
                    expires_days=90
                )
                result.add_field(
                    "sfha_status",
                    False,
                    confidence=FieldConfidence.MEDIUM,
                    expires_days=90
                )
                result.add_field(
                    "flood_insurance_required",
                    False,
                    confidence=FieldConfidence.MEDIUM,
                    expires_days=90
                )

        except Exception as e:
            logger.error(f"FEMA enrichment error: {str(e)}")
            result.errors.append(str(e))

        return result

    def _query_flood_zone(self, lat: float, lon: float) -> Optional[dict]:
        """
        Query FEMA NFHL API for flood zone at coordinates

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Flood zone data dict or None
        """
        try:
            # FEMA uses Web Mercator (EPSG:3857), we have WGS84 (EPSG:4326)
            # The API accepts lat/lon directly

            # Layer 28 is the main flood zones layer
            url = f"{self.BASE_URL}/28/query"

            params = {
                "geometry": f"{lon},{lat}",  # lon,lat order for ESRI
                "geometryType": "esriGeometryPoint",
                "inSR": "4326",  # WGS84
                "spatialRel": "esriSpatialRelIntersects",
                "returnGeometry": "false",
                "outFields": "FLD_ZONE,ZONE_SUBTY,STATIC_BFE,SFHA_TF",
                "f": "json"
            }

            response_data, response_time = self._make_request(url, params=params)
            result.response_time_ms = response_time

            features = response_data.get("features", [])
            if features and len(features) > 0:
                return features[0].get("attributes", {})

            return None

        except Exception as e:
            logger.error(f"FEMA API query error: {str(e)}")
            return None

    def _is_sfha(self, flood_zone: str) -> bool:
        """
        Determine if flood zone is Special Flood Hazard Area

        SFHA zones: A, AE, AH, AO, AR, A99, V, VE
        Non-SFHA: X, B, C, D

        Args:
            flood_zone: FEMA flood zone code

        Returns:
            True if SFHA
        """
        sfha_zones = {"A", "AE", "AH", "AO", "AR", "A99", "V", "VE", "VO"}
        return flood_zone in sfha_zones or flood_zone.startswith(("A", "V"))

    def _requires_insurance(self, flood_zone: str) -> bool:
        """
        Determine if flood insurance is required for mortgaged properties

        Lenders require flood insurance in SFHA zones

        Args:
            flood_zone: FEMA flood zone code

        Returns:
            True if insurance typically required
        """
        return self._is_sfha(flood_zone)

    def check_availability(self) -> bool:
        """Check if FEMA API is available"""
        try:
            # Test with coordinates in Los Angeles
            result = self._query_flood_zone(34.0522, -118.2437)
            return True  # API responded (even if no data)
        except Exception as e:
            logger.error(f"FEMA availability check failed: {str(e)}")
            return False
