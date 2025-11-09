"""
Basic Attributes Plugin - Enrich property physical attributes
In production, would call ATTOM, Regrid, or county assessor APIs
For MVP, uses mock data
"""

from datetime import datetime
from typing import Any

try:
    from contracts import PropertyRecord, Attributes, Provenance
except ImportError:
    import sys
    sys.path.insert(0, '/home/user/real-estate-os/packages/contracts/src')
    from contracts import PropertyRecord, Attributes, Provenance

from .base import EnrichmentPlugin, PluginResult, PluginPriority


class BasicAttrsPlugin(EnrichmentPlugin):
    """
    Enriches property with basic physical attributes.

    In production:
    - Call ATTOM API ($0.05/call) or Regrid ($0.03/call)
    - Respect Policy Kernel cost caps and quotas
    - Handle missing data gracefully
    - Store provenance for each field

    For MVP:
    - Uses deterministic mock data based on APN
    - Returns plausible values for single-family homes
    """

    def __init__(self, mock: bool = True):
        super().__init__(
            name="basic_attrs",
            priority=PluginPriority.MEDIUM
        )
        self.mock = mock

    def can_enrich(self, record: PropertyRecord) -> bool:
        """Can enrich if APN exists and attrs are missing or incomplete"""
        if not record.apn:
            return False

        # Can enrich if attrs is None or if key fields are missing
        if record.attrs is None:
            return True

        # Check if key fields are missing
        key_fields_missing = any([
            record.attrs.beds is None,
            record.attrs.baths is None,
            record.attrs.sqft is None
        ])

        return key_fields_missing

    def get_required_fields(self) -> list[str]:
        return ["apn"]

    async def enrich(self, record: PropertyRecord) -> PluginResult:
        """Add property attributes to record"""
        try:
            if not self.can_enrich(record):
                return PluginResult(
                    plugin_name=self.name,
                    success=False,
                    error="Cannot enrich: APN missing or attrs already complete"
                )

            # In production, call data provider API
            if self.mock:
                attrs_data = self._mock_attributes(record.apn)
            else:
                raise NotImplementedError("Real API not yet implemented")

            # Update record (merge with existing attrs if any)
            if record.attrs is None:
                record.attrs = Attributes(**attrs_data)
            else:
                # Update only missing fields
                for field, value in attrs_data.items():
                    if getattr(record.attrs, field, None) is None:
                        setattr(record.attrs, field, value)

            # Add provenance for each field
            provenance_added = []
            for field in attrs_data.keys():
                prov = Provenance(
                    field=f"attrs.{field}",
                    source=self.name,
                    fetched_at=datetime.utcnow(),
                    confidence=0.80 if self.mock else 0.92,
                    cost_cents=0 if self.mock else 5,  # ATTOM charges ~$0.05/call
                    license="mock" if self.mock else "https://api.attomdata.com/terms"
                )
                record.add_provenance(prov)
                provenance_added.append(prov)

            fields_updated = [f"attrs.{f}" for f in attrs_data.keys()]

            return PluginResult(
                plugin_name=self.name,
                success=True,
                fields_updated=fields_updated,
                provenance_added=provenance_added,
                metadata={"mock": self.mock, "field_count": len(attrs_data)}
            )

        except Exception as e:
            return PluginResult(
                plugin_name=self.name,
                success=False,
                error=str(e)
            )

    def _mock_attributes(self, apn: str) -> dict[str, Any]:
        """
        Generate mock property attributes.

        Uses hash of APN to generate deterministic but varied attributes
        typical for single-family homes in Las Vegas
        """
        # Simple hash for deterministic values
        apn_hash = sum(ord(c) for c in apn)

        # Beds: 2-5
        beds = 2 + (apn_hash % 4)

        # Baths: 1.0-3.5 (increments of 0.5)
        baths = 1.0 + ((apn_hash % 5) * 0.5)

        # Sqft: 1200-3500 (typical Vegas SFH)
        sqft = 1200 + ((apn_hash % 20) * 115)

        # Lot: 5000-10000 sqft (typical Vegas lot)
        lot_sqft = 5000 + ((apn_hash % 50) * 100)

        # Year: 1970-2020
        year_built = 1970 + (apn_hash % 50)

        # Stories: 1-2 (mostly single-story in Vegas)
        stories = 1 if apn_hash % 10 < 7 else 2

        # Garage: 0-3 spaces
        garage_spaces = (apn_hash % 4)

        # Pool: ~40% of Vegas homes have pools
        pool = (apn_hash % 10) < 4

        return {
            "beds": beds,
            "baths": baths,
            "sqft": sqft,
            "lot_sqft": lot_sqft,
            "year_built": year_built,
            "stories": stories,
            "garage_spaces": garage_spaces,
            "pool": pool
        }
