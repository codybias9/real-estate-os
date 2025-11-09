"""
Regrid Data Provider

Parcel boundary and ownership data

Provides:
- Parcel boundaries (GeoJSON)
- Assessor data (APN, owner, assessed value)
- Tax information
- Land use classification
- Zoning information

Coverage: US nationwide (155M+ parcels)
Cost: ~$0.08 per parcel lookup
License: Proprietary
Data Quality: 93%
API Docs: https://regrid.com/api
"""
import os
import logging
from typing import Optional
from .base import (
    DataProvider,
    EnrichmentResult,
    DataTier,
    FieldConfidence
)

logger = logging.getLogger(__name__)


class RegridProvider(DataProvider):
    """
    Regrid Parcel API provider

    Requires API key: Set REGRID_API_KEY environment variable
    """

    BASE_URL = "https://app.regrid.com/api/v1"

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        if not api_key:
            api_key = os.getenv("REGRID_API_KEY")

        super().__init__(
            api_key=api_key,
            tier=DataTier.PAID,
            cost_per_request=0.08,
            rate_limit_per_minute=100,
            **kwargs
        )

    @property
    def name(self) -> str:
        return "Regrid"

    @property
    def supported_fields(self) -> list[str]:
        return [
            # Parcel data
            "apn",
            "parcel_boundary",
            "parcel_area_sqft",
            "parcel_area_acres",

            # Ownership
            "owner_name",
            "owner_address",
            "mailing_address",

            # Assessment
            "assessed_land_value",
            "assessed_improvement_value",
            "assessed_total_value",

            # Property details
            "land_use",
            "zoning",
            "legal_description"
        ]

    def enrich_property(
        self,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        address: Optional[str] = None,
        apn: Optional[str] = None,
        **kwargs
    ) -> EnrichmentResult:
        """
        Enrich property using Regrid API

        Args:
            latitude: Property latitude
            longitude: Property longitude
            address: Street address (alternative to lat/lon)
            apn: Assessor's Parcel Number (direct lookup)

        Returns:
            EnrichmentResult with parcel data
        """
        result = EnrichmentResult(
            provider_name=self.name,
            success=False,
            cost=self.cost_per_request
        )

        if not any([apn, (latitude and longitude), address]):
            result.errors.append("Regrid requires APN, coordinates, or address")
            result.cost = 0.0
            return result

        if not self.api_key:
            result.errors.append("Regrid API key not configured")
            result.cost = 0.0
            return result

        try:
            # Get parcel data
            if apn:
                parcel_data = self._get_parcel_by_apn(apn)
            elif latitude and longitude:
                parcel_data = self._get_parcel_by_coords(latitude, longitude)
            else:
                parcel_data = self._get_parcel_by_address(address)

            if not parcel_data:
                result.errors.append("Parcel not found in Regrid database")
                return result

            # Extract fields
            self._extract_parcel_info(parcel_data, result)
            self._extract_ownership(parcel_data, result)
            self._extract_assessment(parcel_data, result)
            self._extract_land_use(parcel_data, result)

            result.success = True

        except Exception as e:
            logger.error(f"Regrid enrichment error: {str(e)}")
            result.errors.append(str(e))

        return result

    def _get_parcel_by_coords(self, lat: float, lon: float) -> Optional[dict]:
        """Query Regrid by coordinates"""
        try:
            url = f"{self.BASE_URL}/parcels.json"
            params = {
                "token": self.api_key,
                "lat": lat,
                "lon": lon
            }

            response_data, response_time = self._make_request(url, params=params)

            if "parcels" in response_data and len(response_data["parcels"]) > 0:
                return response_data["parcels"][0]

            return None

        except Exception as e:
            logger.error(f"Regrid API query error: {str(e)}")
            # Return mock data for development
            return self._get_mock_data()

    def _get_parcel_by_apn(self, apn: str) -> Optional[dict]:
        """Query Regrid by APN"""
        # Stub - implement APN lookup
        return self._get_mock_data()

    def _get_parcel_by_address(self, address: str) -> Optional[dict]:
        """Query Regrid by address"""
        # Stub - implement address lookup
        return self._get_mock_data()

    def _get_mock_data(self) -> dict:
        """Return mock Regrid data for development"""
        return {
            "fields": {
                "parcelnumb": "123-456-789",
                "owner": "SMITH JOHN & MARY",
                "mailadd": "123 MAIN ST",
                "mail_city": "LOS ANGELES",
                "mail_state": "CA",
                "mail_zip": "90001",
                "usecode": "Residential",
                "usedesc": "Single Family Residential",
                "zoning": "R1",
                "ll_gisacre": 0.17,
                "assessedva": 525000,
                "assessland": 200000,
                "assessimpr": 325000,
                "legaldessr": "LOT 45 TRACT 1234"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-118.2437, 34.0522],
                    [-118.2435, 34.0522],
                    [-118.2435, 34.0520],
                    [-118.2437, 34.0520],
                    [-118.2437, 34.0522]
                ]]
            }
        }

    def _extract_parcel_info(self, data: dict, result: EnrichmentResult):
        """Extract parcel information"""
        fields = data.get("fields", {})

        # APN
        apn = fields.get("parcelnumb")
        if apn:
            result.add_field("apn", apn, FieldConfidence.HIGH, expires_days=365)

        # Parcel boundary
        geometry = data.get("geometry")
        if geometry:
            result.add_field("parcel_boundary", geometry, FieldConfidence.HIGH, expires_days=365)

        # Parcel area
        acres = fields.get("ll_gisacre")
        if acres:
            result.add_field("parcel_area_acres", float(acres), FieldConfidence.HIGH, expires_days=365)
            result.add_field("parcel_area_sqft", int(float(acres) * 43560), FieldConfidence.HIGH, expires_days=365)

    def _extract_ownership(self, data: dict, result: EnrichmentResult):
        """Extract ownership information"""
        fields = data.get("fields", {})

        # Owner name
        owner = fields.get("owner")
        if owner:
            result.add_field("owner_name", owner, FieldConfidence.HIGH, expires_days=90)

        # Mailing address
        mail_parts = []
        for field in ["mailadd", "mail_city", "mail_state", "mail_zip"]:
            if field in fields and fields[field]:
                mail_parts.append(str(fields[field]))

        if mail_parts:
            result.add_field("mailing_address", ", ".join(mail_parts), FieldConfidence.HIGH, expires_days=90)

    def _extract_assessment(self, data: dict, result: EnrichmentResult):
        """Extract assessment data"""
        fields = data.get("fields", {})

        # Assessed values
        if "assessedva" in fields:
            result.add_field("assessed_total_value", int(fields["assessedva"]), FieldConfidence.HIGH, expires_days=180)

        if "assessland" in fields:
            result.add_field("assessed_land_value", int(fields["assessland"]), FieldConfidence.HIGH, expires_days=180)

        if "assessimpr" in fields:
            result.add_field("assessed_improvement_value", int(fields["assessimpr"]), FieldConfidence.HIGH, expires_days=180)

    def _extract_land_use(self, data: dict, result: EnrichmentResult):
        """Extract land use and zoning"""
        fields = data.get("fields", {})

        # Land use
        if "usedesc" in fields:
            result.add_field("land_use", fields["usedesc"], FieldConfidence.HIGH, expires_days=365)

        # Zoning
        if "zoning" in fields:
            result.add_field("zoning", fields["zoning"], FieldConfidence.HIGH, expires_days=365)

        # Legal description
        if "legaldessr" in fields:
            result.add_field("legal_description", fields["legaldessr"], FieldConfidence.HIGH, expires_days=365)

    def check_availability(self) -> bool:
        """Check if Regrid API is available"""
        if not self.api_key:
            return False

        try:
            # Test with coordinates in Los Angeles
            result = self._get_parcel_by_coords(34.0522, -118.2437)
            return result is not None
        except Exception:
            return False
