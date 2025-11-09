"""
USGS Earthquake Hazard Provider

Free government data for seismic risks

Provides:
- Earthquake zone classification
- Seismic hazard level
- PGA (Peak Ground Acceleration)
- Historical earthquake data

Coverage: US nationwide
Cost: Free (public domain)
License: Public Domain
Data Quality: 93%
"""
import logging
from typing import Optional
from .base import (
    DataProvider,
    EnrichmentResult,
    DataTier,
    FieldConfidence
)

logger = logging.getLogger(__name__)


class USGSProvider(DataProvider):
    """USGS Earthquake Hazard Data Provider"""

    BASE_URL = "https://earthquake.usgs.gov/ws/designmaps"

    def __init__(self, **kwargs):
        super().__init__(
            tier=DataTier.GOVERNMENT,
            cost_per_request=0.0,
            rate_limit_per_minute=60,
            **kwargs
        )

    @property
    def name(self) -> str:
        return "USGS_Earthquake"

    @property
    def supported_fields(self) -> list[str]:
        return [
            "seismic_zone",
            "peak_ground_acceleration",
            "earthquake_risk_level"
        ]

    def enrich_property(
        self,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        **kwargs
    ) -> EnrichmentResult:
        """Get seismic hazard data"""
        result = EnrichmentResult(
            provider_name=self.name,
            success=False,
            cost=0.0
        )

        if not latitude or not longitude:
            result.errors.append("USGS requires latitude and longitude")
            return result

        try:
            # Query USGS Design Maps API
            url = f"{self.BASE_URL}/asce7-16.json"
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "riskCategory": "II",
                "siteClass": "C",
                "title": "Real Estate OS Query"
            }

            response_data, response_time = self._make_request(url, params=params)
            result.response_time_ms = response_time

            if "response" in response_data and "data" in response_data["response"]:
                data = response_data["response"]["data"]

                # Peak Ground Acceleration (PGA)
                pga = data.get("pga")
                if pga:
                    result.add_field(
                        "peak_ground_acceleration",
                        float(pga),
                        confidence=FieldConfidence.HIGH,
                        source_url=self.BASE_URL,
                        expires_days=365
                    )

                # Determine seismic zone and risk level
                risk_level = self._classify_seismic_risk(float(pga) if pga else 0.0)
                result.add_field(
                    "seismic_zone",
                    risk_level["zone"],
                    confidence=FieldConfidence.HIGH,
                    expires_days=365
                )
                result.add_field(
                    "earthquake_risk_level",
                    risk_level["level"],
                    confidence=FieldConfidence.HIGH,
                    expires_days=365
                )

                result.success = True

        except Exception as e:
            logger.error(f"USGS enrichment error: {str(e)}")
            result.errors.append(str(e))

        return result

    def _classify_seismic_risk(self, pga: float) -> dict:
        """Classify seismic risk based on PGA"""
        if pga >= 0.4:
            return {"zone": "4", "level": "very_high"}
        elif pga >= 0.3:
            return {"zone": "3", "level": "high"}
        elif pga >= 0.15:
            return {"zone": "2", "level": "moderate"}
        elif pga >= 0.05:
            return {"zone": "1", "level": "low"}
        else:
            return {"zone": "0", "level": "minimal"}
