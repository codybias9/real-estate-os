"""
Discovery Resolver - Normalize and deduplicate property records
Single producer of: event.discovery.intake
"""

import hashlib
import logging
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

# Note: In production, import from packages/contracts
# For now, we'll use relative path or assume contracts is installed
try:
    from contracts import (
        PropertyRecord, Address, Geo, Owner, OwnerType,
        Attributes, Provenance, Envelope
    )
except ImportError:
    # Fallback for development
    import sys
    sys.path.insert(0, '/home/user/real-estate-os/packages/contracts/src')
    from contracts import (
        PropertyRecord, Address, Geo, Owner, OwnerType,
        Attributes, Provenance, Envelope
    )


logger = logging.getLogger(__name__)


class IntakeStatus(str, Enum):
    """Intake processing status"""
    NEW = "new"
    DUPLICATE = "duplicate"
    UPDATED = "updated"
    REJECTED = "rejected"


class IntakeResult(BaseModel):
    """Result of intake processing"""
    status: IntakeStatus
    property_record: PropertyRecord | None
    apn_hash: str
    reason: str
    envelope_id: UUID


class DiscoveryResolver:
    """
    Normalizes raw scraped data into canonical PropertyRecord format.

    Responsibilities:
    - Map source-specific fields to PropertyRecord schema
    - Compute APN hash for deduplication
    - Generate idempotency keys
    - Emit event.discovery.intake with Envelope
    - Handle missing/invalid data gracefully
    """

    def __init__(self, tenant_id: UUID):
        self.tenant_id = tenant_id
        self.logger = logging.getLogger(f"{__name__}.{tenant_id}")

    @staticmethod
    def compute_apn_hash(apn: str) -> str:
        """
        Compute deterministic hash for APN deduplication.

        Normalizes APN (remove spaces, dashes, uppercase) before hashing.
        """
        normalized = apn.upper().replace(" ", "").replace("-", "").replace("_", "")
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    @staticmethod
    def normalize_address(raw_address: dict[str, Any]) -> Address | None:
        """
        Normalize address from various source formats.

        Handles:
        - Missing fields (returns None)
        - Combined address lines
        - State abbreviation validation
        """
        try:
            # Extract fields with fallbacks
            line1 = raw_address.get("street") or raw_address.get("address") or raw_address.get("line1")
            line2 = raw_address.get("unit") or raw_address.get("apt") or raw_address.get("line2")
            city = raw_address.get("city")
            state = raw_address.get("state")
            zip_code = raw_address.get("zip") or raw_address.get("zipcode") or raw_address.get("postal_code")

            if not all([line1, city, state, zip_code]):
                return None

            # Validate state (2-letter)
            state = str(state).upper()[:2]

            return Address(
                line1=str(line1).strip(),
                line2=str(line2).strip() if line2 else None,
                city=str(city).strip(),
                state=state,
                zip=str(zip_code).strip()
            )
        except Exception as e:
            logger.warning(f"Failed to normalize address: {e}")
            return None

    @staticmethod
    def normalize_geo(raw_geo: dict[str, Any]) -> Geo | None:
        """Normalize geocoded location"""
        try:
            lat = raw_geo.get("latitude") or raw_geo.get("lat")
            lng = raw_geo.get("longitude") or raw_geo.get("lng") or raw_geo.get("lon")

            if lat is None or lng is None:
                return None

            return Geo(
                lat=float(lat),
                lng=float(lng),
                parcel_polygon=raw_geo.get("parcel_polygon"),
                accuracy=raw_geo.get("accuracy")
            )
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to normalize geo: {e}")
            return None

    @staticmethod
    def normalize_owner(raw_owner: dict[str, Any]) -> Owner | None:
        """Normalize owner information"""
        try:
            name = raw_owner.get("name") or raw_owner.get("owner_name")
            if not name:
                return None

            # Infer owner type from name (check most specific first)
            owner_type = OwnerType.UNKNOWN
            name_lower = str(name).lower()
            if "trust" in name_lower:
                owner_type = OwnerType.TRUST
            elif "llc" in name_lower:
                owner_type = OwnerType.LLC
            elif any(x in name_lower for x in ["inc", "corp", "company", "properties"]):
                owner_type = OwnerType.COMPANY
            else:
                owner_type = OwnerType.PERSON

            # Mailing address (if different from property address)
            mailing = None
            if raw_owner.get("mailing_address"):
                mailing = DiscoveryResolver.normalize_address(raw_owner["mailing_address"])

            return Owner(
                name=str(name).strip(),
                type=owner_type,
                mailing_address=mailing
            )
        except Exception as e:
            logger.warning(f"Failed to normalize owner: {e}")
            return None

    @staticmethod
    def normalize_attributes(raw_attrs: dict[str, Any]) -> Attributes | None:
        """Normalize property physical attributes"""
        try:
            attrs = Attributes(
                beds=int(raw_attrs["beds"]) if raw_attrs.get("beds") else None,
                baths=float(raw_attrs["baths"]) if raw_attrs.get("baths") else None,
                sqft=int(raw_attrs["sqft"]) if raw_attrs.get("sqft") else None,
                lot_sqft=int(raw_attrs["lot_sqft"]) if raw_attrs.get("lot_sqft") else None,
                year_built=int(raw_attrs["year_built"]) if raw_attrs.get("year_built") else None,
                stories=int(raw_attrs["stories"]) if raw_attrs.get("stories") else None,
                garage_spaces=int(raw_attrs["garage_spaces"]) if raw_attrs.get("garage_spaces") else None,
                pool=bool(raw_attrs["pool"]) if raw_attrs.get("pool") is not None else None
            )

            # Return None if all attributes are None (no useful data)
            if all(v is None for v in attrs.model_dump().values()):
                return None

            return attrs
        except (ValueError, TypeError, KeyError) as e:
            logger.warning(f"Failed to normalize attributes: {e}")
            return None

    def normalize(self, raw_data: dict[str, Any], source: str, source_id: str) -> PropertyRecord | None:
        """
        Normalize raw scraped data to PropertyRecord.

        Args:
            raw_data: Raw scraped data (source-specific format)
            source: Source identifier (spider name)
            source_id: Source-specific unique ID

        Returns:
            PropertyRecord or None if data is invalid
        """
        try:
            # Required: APN
            apn = raw_data.get("apn") or raw_data.get("parcel_number") or raw_data.get("assessor_parcel_number")
            if not apn:
                self.logger.warning(f"Missing APN in source_id={source_id}")
                return None

            # Required: Address
            address = self.normalize_address(raw_data.get("address", {}))
            if not address:
                self.logger.warning(f"Invalid address for APN={apn}")
                return None

            # Optional fields
            geo = self.normalize_geo(raw_data.get("geo", {})) if raw_data.get("geo") else None
            owner = self.normalize_owner(raw_data.get("owner", {})) if raw_data.get("owner") else None
            attrs = self.normalize_attributes(raw_data.get("attributes", {})) if raw_data.get("attributes") else None

            # Build PropertyRecord
            record = PropertyRecord(
                apn=str(apn).strip(),
                address=address,
                geo=geo,
                owner=owner,
                attrs=attrs,
                provenance=[],  # Will be added by enrichment
                source=source,
                source_id=source_id,
                url=raw_data.get("url"),
                discovered_at=datetime.utcnow()
            )

            return record

        except Exception as e:
            self.logger.error(f"Failed to normalize source_id={source_id}: {e}")
            return None

    def process_intake(
        self,
        raw_data: dict[str, Any],
        source: str,
        source_id: str,
        existing_apn_hashes: set[str] | None = None
    ) -> IntakeResult:
        """
        Process raw intake data and generate event.discovery.intake.

        Args:
            raw_data: Raw scraped data
            source: Source identifier
            source_id: Source-specific unique ID
            existing_apn_hashes: Set of already-processed APN hashes (for deduplication)

        Returns:
            IntakeResult with status and PropertyRecord
        """
        envelope_id = uuid4()

        # Normalize data
        record = self.normalize(raw_data, source, source_id)

        if not record:
            return IntakeResult(
                status=IntakeStatus.REJECTED,
                property_record=None,
                apn_hash="",
                reason="Failed to normalize data (missing required fields)",
                envelope_id=envelope_id
            )

        # Compute APN hash for deduplication
        apn_hash = self.compute_apn_hash(record.apn)

        # Check for duplicates
        if existing_apn_hashes and apn_hash in existing_apn_hashes:
            return IntakeResult(
                status=IntakeStatus.DUPLICATE,
                property_record=record,
                apn_hash=apn_hash,
                reason=f"APN hash {apn_hash} already exists",
                envelope_id=envelope_id
            )

        # Success - new record
        return IntakeResult(
            status=IntakeStatus.NEW,
            property_record=record,
            apn_hash=apn_hash,
            reason="Successfully normalized and ready for ingestion",
            envelope_id=envelope_id
        )

    def create_intake_event(
        self,
        result: IntakeResult,
        correlation_id: UUID | None = None,
        causation_id: UUID | None = None
    ) -> Envelope[PropertyRecord]:
        """
        Create event.discovery.intake envelope.

        This is the single producer of discovery intake events.
        """
        if not result.property_record:
            raise ValueError("Cannot create intake event for rejected record")

        envelope = Envelope[PropertyRecord](
            id=result.envelope_id,
            tenant_id=self.tenant_id,
            subject="event.discovery.intake",
            schema_version="1.0",
            idempotency_key=f"{result.property_record.source}:{result.property_record.source_id}",
            correlation_id=correlation_id or uuid4(),
            causation_id=causation_id or result.envelope_id,
            at=datetime.utcnow(),
            payload=result.property_record
        )

        return envelope
