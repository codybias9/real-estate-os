"""
Provenance Tracker with Write-Through Support.

Tracks field-level provenance data and writes it alongside main data.
Maintains complete audit trail of data transformations with trust scores.
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field, asdict
import uuid
import logging
import json

from provenance.trust_score import calculate_field_trust_score, SourceType

logger = logging.getLogger(__name__)


@dataclass
class FieldProvenance:
    """Provenance record for a single field."""

    provenance_id: str
    entity_type: str  # e.g., "property", "prospect"
    entity_id: str
    field_name: str
    field_value: Any

    # Source information
    source_type: str  # Maps to SourceType enum
    source_name: str  # e.g., "FEMA NFHL API", "User Input"
    source_system: Optional[str] = None
    source_version: Optional[str] = None

    # Lineage
    parent_provenance_ids: List[str] = field(default_factory=list)
    transformation_type: Optional[str] = None
    transformation_description: Optional[str] = None
    transformation_code: Optional[str] = None

    # Trust and quality
    trust_score: float = 0.0
    trust_score_breakdown: Dict[str, Any] = field(default_factory=dict)
    data_quality_checks_passed: int = 0
    data_quality_checks_total: int = 0

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    tenant_id: str = ""
    pipeline_run_id: Optional[str] = None

    # Evidence
    evidence_url: Optional[str] = None
    evidence_metadata: Dict[str, Any] = field(default_factory=dict)


class ProvenanceTracker:
    """Tracks and persists field-level provenance data."""

    def __init__(
        self,
        tenant_id: str,
        pipeline_run_id: Optional[str] = None,
        storage_backend: Optional[Any] = None
    ):
        """
        Initialize provenance tracker.

        Args:
            tenant_id: Tenant ID for multi-tenant isolation
            pipeline_run_id: Optional pipeline run identifier
            storage_backend: Optional storage backend (DB, file, etc.)
        """
        self.tenant_id = tenant_id
        self.pipeline_run_id = pipeline_run_id or str(uuid.uuid4())
        self.storage_backend = storage_backend

        # In-memory cache of provenance records
        self.provenance_cache: Dict[str, FieldProvenance] = {}

    def track_field(
        self,
        entity_type: str,
        entity_id: str,
        field_name: str,
        field_value: Any,
        source_type: str,
        source_name: str,
        parent_provenance_ids: Optional[List[str]] = None,
        transformation_type: Optional[str] = None,
        transformation_description: Optional[str] = None,
        model_confidence: Optional[float] = None,
        created_by: Optional[str] = None,
        evidence_url: Optional[str] = None,
        **kwargs
    ) -> FieldProvenance:
        """
        Track provenance for a single field.

        Args:
            entity_type: Type of entity (property, prospect, etc.)
            entity_id: Unique entity identifier
            field_name: Name of the field
            field_value: Value of the field
            source_type: Type of source (maps to SourceType)
            source_name: Name of source
            parent_provenance_ids: List of parent provenance IDs
            transformation_type: Type of transformation applied
            transformation_description: Description of transformation
            model_confidence: ML model confidence if applicable
            created_by: User/system that created the data
            evidence_url: URL to supporting evidence
            **kwargs: Additional metadata

        Returns:
            FieldProvenance record
        """
        provenance_id = str(uuid.uuid4())

        # Calculate trust score
        trust_result = calculate_field_trust_score(
            source_type=source_type,
            created_at=datetime.utcnow(),
            transformations=[transformation_type] if transformation_type else None,
            model_confidence=model_confidence,
            validation_result=kwargs.get('validation_result')
        )

        # Create provenance record
        provenance = FieldProvenance(
            provenance_id=provenance_id,
            entity_type=entity_type,
            entity_id=entity_id,
            field_name=field_name,
            field_value=field_value,
            source_type=source_type,
            source_name=source_name,
            source_system=kwargs.get('source_system'),
            source_version=kwargs.get('source_version'),
            parent_provenance_ids=parent_provenance_ids or [],
            transformation_type=transformation_type,
            transformation_description=transformation_description,
            transformation_code=kwargs.get('transformation_code'),
            trust_score=trust_result['trust_score'],
            trust_score_breakdown=trust_result['breakdown'],
            data_quality_checks_passed=kwargs.get('data_quality_checks_passed', 0),
            data_quality_checks_total=kwargs.get('data_quality_checks_total', 0),
            created_by=created_by,
            tenant_id=self.tenant_id,
            pipeline_run_id=self.pipeline_run_id,
            evidence_url=evidence_url,
            evidence_metadata=kwargs.get('evidence_metadata', {})
        )

        # Cache the record
        cache_key = f"{entity_type}:{entity_id}:{field_name}"
        self.provenance_cache[cache_key] = provenance

        logger.debug(
            f"Tracked provenance for {cache_key}: "
            f"trust_score={provenance.trust_score:.4f}, "
            f"source={source_name}"
        )

        return provenance

    def track_entity(
        self,
        entity_type: str,
        entity_id: str,
        field_provenances: Dict[str, Dict[str, Any]]
    ) -> List[FieldProvenance]:
        """
        Track provenance for all fields of an entity.

        Args:
            entity_type: Type of entity
            entity_id: Entity identifier
            field_provenances: Dict mapping field names to provenance info

        Returns:
            List of FieldProvenance records
        """
        records = []

        for field_name, prov_info in field_provenances.items():
            record = self.track_field(
                entity_type=entity_type,
                entity_id=entity_id,
                field_name=field_name,
                **prov_info
            )
            records.append(record)

        logger.info(
            f"Tracked provenance for {entity_type}:{entity_id} - "
            f"{len(records)} fields"
        )

        return records

    def get_field_provenance(
        self,
        entity_type: str,
        entity_id: str,
        field_name: str
    ) -> Optional[FieldProvenance]:
        """
        Get provenance for a specific field.

        Args:
            entity_type: Type of entity
            entity_id: Entity identifier
            field_name: Field name

        Returns:
            FieldProvenance record or None
        """
        cache_key = f"{entity_type}:{entity_id}:{field_name}"
        return self.provenance_cache.get(cache_key)

    def get_entity_provenance(
        self,
        entity_type: str,
        entity_id: str
    ) -> Dict[str, FieldProvenance]:
        """
        Get provenance for all fields of an entity.

        Args:
            entity_type: Type of entity
            entity_id: Entity identifier

        Returns:
            Dict mapping field names to FieldProvenance records
        """
        prefix = f"{entity_type}:{entity_id}:"
        return {
            key.split(":")[-1]: record
            for key, record in self.provenance_cache.items()
            if key.startswith(prefix)
        }

    def get_lineage_chain(
        self,
        provenance_id: str
    ) -> List[FieldProvenance]:
        """
        Get complete lineage chain for a field (traverses parents).

        Args:
            provenance_id: Starting provenance ID

        Returns:
            List of FieldProvenance records in lineage chain
        """
        chain = []
        visited = set()

        def traverse(prov_id: str):
            if prov_id in visited:
                return

            visited.add(prov_id)

            # Find record with this provenance_id
            record = None
            for cached_record in self.provenance_cache.values():
                if cached_record.provenance_id == prov_id:
                    record = cached_record
                    break

            if record:
                chain.append(record)

                # Traverse parents
                for parent_id in record.parent_provenance_ids:
                    traverse(parent_id)

        traverse(provenance_id)

        return chain

    def calculate_entity_trust_score(
        self,
        entity_type: str,
        entity_id: str,
        aggregation_method: str = "weighted_average"
    ) -> float:
        """
        Calculate aggregate trust score for an entity.

        Args:
            entity_type: Type of entity
            entity_id: Entity identifier
            aggregation_method: Method for aggregation (weighted_average, min, max)

        Returns:
            Aggregate trust score (0-1)
        """
        entity_prov = self.get_entity_provenance(entity_type, entity_id)

        if not entity_prov:
            logger.warning(f"No provenance found for {entity_type}:{entity_id}")
            return 0.0

        scores = [record.trust_score for record in entity_prov.values()]

        if aggregation_method == "weighted_average":
            # Simple average (could weight by field importance)
            return sum(scores) / len(scores)
        elif aggregation_method == "min":
            # Pessimistic: lowest score
            return min(scores)
        elif aggregation_method == "max":
            # Optimistic: highest score
            return max(scores)
        else:
            raise ValueError(f"Unknown aggregation method: {aggregation_method}")

    def write_through(
        self,
        flush_cache: bool = True
    ) -> int:
        """
        Write provenance records to storage backend.

        Args:
            flush_cache: Whether to clear cache after writing

        Returns:
            Number of records written
        """
        if not self.storage_backend:
            logger.warning("No storage backend configured, skipping write-through")
            return 0

        records_written = 0

        for record in self.provenance_cache.values():
            try:
                # Convert to dict for storage
                record_dict = asdict(record)

                # Write to storage
                self.storage_backend.insert_provenance(record_dict)
                records_written += 1

            except Exception as e:
                logger.error(
                    f"Failed to write provenance {record.provenance_id}: {e}"
                )

        logger.info(f"Wrote {records_written} provenance records to storage")

        if flush_cache:
            self.provenance_cache.clear()

        return records_written

    def export_to_json(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None
    ) -> str:
        """
        Export provenance records to JSON.

        Args:
            entity_type: Optional filter by entity type
            entity_id: Optional filter by entity ID

        Returns:
            JSON string
        """
        records_to_export = []

        for record in self.provenance_cache.values():
            # Apply filters
            if entity_type and record.entity_type != entity_type:
                continue
            if entity_id and record.entity_id != entity_id:
                continue

            # Convert to dict
            record_dict = asdict(record)

            # Convert datetime to ISO format
            record_dict['created_at'] = record.created_at.isoformat()

            records_to_export.append(record_dict)

        return json.dumps(
            {
                "provenance_records": records_to_export,
                "total_records": len(records_to_export),
                "tenant_id": self.tenant_id,
                "pipeline_run_id": self.pipeline_run_id,
                "exported_at": datetime.utcnow().isoformat()
            },
            indent=2
        )


class InMemoryProvenanceStorage:
    """In-memory storage backend for provenance (for testing)."""

    def __init__(self):
        self.records: List[Dict[str, Any]] = []

    def insert_provenance(self, record: Dict[str, Any]) -> None:
        """Insert provenance record."""
        self.records.append(record)

    def query_by_entity(
        self,
        entity_type: str,
        entity_id: str
    ) -> List[Dict[str, Any]]:
        """Query records by entity."""
        return [
            r for r in self.records
            if r['entity_type'] == entity_type and r['entity_id'] == entity_id
        ]

    def query_by_field(
        self,
        entity_type: str,
        entity_id: str,
        field_name: str
    ) -> Optional[Dict[str, Any]]:
        """Query single field record."""
        for r in self.records:
            if (
                r['entity_type'] == entity_type and
                r['entity_id'] == entity_id and
                r['field_name'] == field_name
            ):
                return r
        return None
