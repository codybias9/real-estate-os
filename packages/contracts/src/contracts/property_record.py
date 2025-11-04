"""
PropertyRecord - Canonical property data model
Normalized across all sources with provenance tracking
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class OwnerType(str, Enum):
    """Owner entity type"""
    PERSON = "person"
    COMPANY = "company"
    TRUST = "trust"
    LLC = "llc"
    UNKNOWN = "unknown"


class Address(BaseModel):
    """Normalized property address"""
    line1: str = Field(..., description="Street address")
    line2: Optional[str] = Field(None, description="Unit/Apt")
    city: str = Field(..., description="City")
    state: str = Field(..., min_length=2, max_length=2, description="State (2-letter)")
    zip: str = Field(..., description="ZIP code")

    def to_single_line(self) -> str:
        """Format as single-line address"""
        parts = [self.line1]
        if self.line2:
            parts.append(self.line2)
        parts.append(f"{self.city}, {self.state} {self.zip}")
        return ", ".join(parts)


class Geo(BaseModel):
    """Geocoded location and parcel geometry"""
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lng: float = Field(..., ge=-180, le=180, description="Longitude")
    parcel_polygon: Optional[str] = Field(None, description="WKT or GeoJSON polygon")
    accuracy: Optional[str] = Field(None, description="Geocode accuracy (rooftop|parcel|street)")


class Owner(BaseModel):
    """Property owner information"""
    name: str = Field(..., description="Owner name")
    type: OwnerType = Field(default=OwnerType.UNKNOWN, description="Owner entity type")
    mailing_address: Optional[Address] = Field(None, description="Mailing address (if different)")


class Attributes(BaseModel):
    """Property physical attributes"""
    beds: Optional[int] = Field(None, ge=0, description="Bedrooms")
    baths: Optional[float] = Field(None, ge=0, description="Bathrooms (0.5 increments)")
    sqft: Optional[int] = Field(None, ge=0, description="Living area square feet")
    lot_sqft: Optional[int] = Field(None, ge=0, description="Lot size square feet")
    year_built: Optional[int] = Field(None, ge=1700, le=2100, description="Year built")
    stories: Optional[int] = Field(None, ge=1, description="Number of stories")
    garage_spaces: Optional[int] = Field(None, ge=0, description="Garage spaces")
    pool: Optional[bool] = Field(None, description="Has pool")


class Provenance(BaseModel):
    """Per-field data source tracking"""
    field: str = Field(..., description="Field path (e.g., 'attrs.beds')")
    source: str = Field(..., description="Provider name (e.g., 'attom', 'regrid')")
    fetched_at: datetime = Field(..., description="Data retrieval timestamp")
    license: Optional[str] = Field(None, description="License/terms URL")
    confidence: float = Field(default=1.0, ge=0, le=1, description="Data confidence (0-1)")
    cost_cents: Optional[int] = Field(None, description="API call cost in cents")


class PropertyRecord(BaseModel):
    """
    Canonical property record with full provenance.

    This is the single source of truth after Discovery.Resolver normalization.
    All enrichment flows update this record with provenance tracking.
    """

    apn: str = Field(..., description="Assessor Parcel Number (primary key)")
    apn_hash: Optional[str] = Field(None, description="SHA-256 hash of normalized APN for deduplication")
    address: Address = Field(..., description="Normalized address")
    geo: Optional[Geo] = Field(None, description="Geocoded location")
    owner: Optional[Owner] = Field(None, description="Owner information")
    attrs: Optional[Attributes] = Field(None, description="Physical attributes")
    provenance: list[Provenance] = Field(default_factory=list, description="Per-field provenance")

    # Metadata
    source: str = Field(..., description="Original source identifier (spider name)")
    source_id: str = Field(..., description="Source-specific unique ID")
    url: Optional[str] = Field(None, description="Source URL")
    discovered_at: datetime = Field(default_factory=datetime.utcnow, description="Discovery timestamp")

    def get_provenance(self, field: str) -> Optional[Provenance]:
        """Get provenance for a specific field"""
        return next((p for p in self.provenance if p.field == field), None)

    def add_provenance(self, prov: Provenance) -> None:
        """Add or update provenance for a field"""
        # Remove existing provenance for this field
        self.provenance = [p for p in self.provenance if p.field != prov.field]
        self.provenance.append(prov)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
