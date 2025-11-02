"""
Field-Level Provenance Tracking

Provides comprehensive data lineage tracking at the field level, enabling
trust scoring, audit trails, and data quality monitoring.

Features:
- Track all data changes with source, method, confidence
- Automatic trust score calculation
- Timeline view of data history
- Entity-level trust aggregation
- Multi-tenant isolation
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import json

logger = logging.getLogger(__name__)


class Operation(str, Enum):
    """Data operation types"""
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    ENRICH = "ENRICH"


class ChangeType(str, Enum):
    """Change significance types"""
    INITIAL = "INITIAL"
    NO_CHANGE = "NO_CHANGE"
    MODIFICATION = "MODIFICATION"
    DELETION = "DELETION"


class Source(str, Enum):
    """Common data sources"""
    MLS_API = "mls_api"
    USER_INPUT = "user_input"
    ML_MODEL = "ml_model"
    EXTERNAL_ENRICHMENT = "external_enrichment"
    FEMA_API = "fema_api"
    USGS_API = "usgs_api"
    CENSUS_API = "census_api"
    SPATIAL_JOIN = "spatial_join"
    BATCH_IMPORT = "batch_import"
    MANUAL_CORRECTION = "manual_correction"


class Method(str, Enum):
    """Data collection methods"""
    API_FETCH = "api_fetch"
    MANUAL_ENTRY = "manual_entry"
    MODEL_INFERENCE = "model_inference"
    SPATIAL_JOIN = "spatial_join"
    DATABASE_MIGRATION = "database_migration"
    ENRICHMENT_PIPELINE = "enrichment_pipeline"
    USER_UPLOAD = "user_upload"


@dataclass
class FieldProvenance:
    """Complete provenance record for a single field"""
    entity_type: str
    entity_id: str
    field_name: str
    tenant_id: str

    field_value: Optional[str] = None
    previous_value: Optional[str] = None

    source: str = Source.USER_INPUT.value
    method: str = Method.MANUAL_ENTRY.value
    confidence: float = 1.0

    evidence_uri: Optional[str] = None
    evidence_metadata: Optional[Dict] = None

    source_reliability: float = 0.8
    freshness_score: float = 1.0
    validation_score: float = 1.0
    trust_score: float = 0.8

    operation: str = Operation.CREATE.value
    changed_by: Optional[str] = None
    changed_by_type: str = "system"

    id: Optional[str] = None
    created_at: Optional[str] = None
    expires_at: Optional[str] = None

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()

        # Auto-calculate trust score
        self.trust_score = self.calculate_trust_score()

    def calculate_trust_score(self) -> float:
        """
        Calculate composite trust score

        Formula: weighted average of:
        - Source reliability (30%)
        - Freshness (20%)
        - Validation (30%)
        - Confidence (20%)
        """
        trust = (
            self.source_reliability * 0.30 +
            self.freshness_score * 0.20 +
            self.validation_score * 0.30 +
            self.confidence * 0.20
        )

        return max(0.0, min(1.0, trust))  # Clamp to [0, 1]

    def to_dict(self) -> Dict:
        """Convert to dictionary for database insert"""
        data = asdict(self)
        # Convert metadata to JSON string
        if data['evidence_metadata']:
            data['evidence_metadata'] = json.dumps(data['evidence_metadata'])
        return data


class ProvenanceTracker:
    """Service for tracking and querying field-level provenance"""

    # Source reliability scores (configurable)
    SOURCE_RELIABILITY = {
        Source.MLS_API: 0.95,
        Source.USER_INPUT: 0.70,
        Source.ML_MODEL: 0.85,
        Source.EXTERNAL_ENRICHMENT: 0.80,
        Source.FEMA_API: 0.95,
        Source.USGS_API: 0.90,
        Source.CENSUS_API: 0.95,
        Source.SPATIAL_JOIN: 0.85,
        Source.BATCH_IMPORT: 0.75,
        Source.MANUAL_CORRECTION: 0.90,
    }

    def __init__(self, connection=None):
        """
        Initialize provenance tracker

        Args:
            connection: Database connection (optional, uses default if None)
        """
        self.connection = connection

    def track_field_change(
        self,
        entity_type: str,
        entity_id: str,
        field_name: str,
        field_value: Any,
        tenant_id: str,
        source: str = Source.USER_INPUT.value,
        method: str = Method.MANUAL_ENTRY.value,
        confidence: float = 1.0,
        previous_value: Optional[Any] = None,
        operation: str = Operation.UPDATE.value,
        changed_by: Optional[str] = None,
        changed_by_type: str = "system",
        evidence_uri: Optional[str] = None,
        evidence_metadata: Optional[Dict] = None,
        validation_passed: bool = True,
    ) -> FieldProvenance:
        """
        Track a field change with full provenance

        Args:
            entity_type: Type of entity (e.g., 'property', 'prospect')
            entity_id: UUID of the entity
            field_name: Name of the field
            field_value: New value
            tenant_id: Tenant UUID
            source: Data source
            method: Collection method
            confidence: Confidence score (0-1)
            previous_value: Previous value (for UPDATE operations)
            operation: Type of operation
            changed_by: User/system that made the change
            changed_by_type: 'user', 'system', or 'ml_model'
            evidence_uri: Link to supporting evidence
            evidence_metadata: Additional context
            validation_passed: Did the value pass validation?

        Returns:
            FieldProvenance object
        """
        # Convert values to strings for storage
        field_value_str = self._serialize_value(field_value)
        previous_value_str = self._serialize_value(previous_value) if previous_value else None

        # Get source reliability
        source_reliability = self.SOURCE_RELIABILITY.get(source, 0.7)

        # Calculate validation score
        validation_score = 1.0 if validation_passed else 0.5

        # Calculate freshness (1.0 for new data)
        freshness_score = 1.0

        # Create provenance record
        provenance = FieldProvenance(
            entity_type=entity_type,
            entity_id=entity_id,
            field_name=field_name,
            tenant_id=tenant_id,
            field_value=field_value_str,
            previous_value=previous_value_str,
            source=source,
            method=method,
            confidence=confidence,
            evidence_uri=evidence_uri,
            evidence_metadata=evidence_metadata,
            source_reliability=source_reliability,
            freshness_score=freshness_score,
            validation_score=validation_score,
            operation=operation,
            changed_by=changed_by,
            changed_by_type=changed_by_type,
        )

        # Persist to database
        if self.connection:
            self._persist_provenance(provenance)

        logger.info(
            f"Tracked {operation} for {entity_type}.{field_name} "
            f"(entity={entity_id}, trust={provenance.trust_score:.2f})"
        )

        return provenance

    def track_bulk_changes(
        self,
        entity_type: str,
        entity_id: str,
        field_changes: Dict[str, Any],
        tenant_id: str,
        source: str = Source.USER_INPUT.value,
        method: str = Method.MANUAL_ENTRY.value,
        operation: str = Operation.UPDATE.value,
        **kwargs
    ) -> List[FieldProvenance]:
        """
        Track multiple field changes for a single entity

        Args:
            entity_type: Type of entity
            entity_id: UUID of the entity
            field_changes: Dictionary of field_name -> new_value
            tenant_id: Tenant UUID
            source: Data source
            method: Collection method
            operation: Type of operation
            **kwargs: Additional arguments passed to track_field_change

        Returns:
            List of FieldProvenance objects
        """
        provenance_records = []

        for field_name, field_value in field_changes.items():
            provenance = self.track_field_change(
                entity_type=entity_type,
                entity_id=entity_id,
                field_name=field_name,
                field_value=field_value,
                tenant_id=tenant_id,
                source=source,
                method=method,
                operation=operation,
                **kwargs
            )
            provenance_records.append(provenance)

        logger.info(
            f"Tracked {len(provenance_records)} field changes for "
            f"{entity_type} {entity_id}"
        )

        return provenance_records

    def get_field_history(
        self,
        entity_type: str,
        entity_id: str,
        field_name: str,
        tenant_id: str,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get complete history for a specific field

        Args:
            entity_type: Type of entity
            entity_id: UUID of the entity
            field_name: Name of the field
            tenant_id: Tenant UUID
            limit: Maximum number of records to return

        Returns:
            List of provenance records ordered by timestamp (newest first)
        """
        if not self.connection:
            logger.warning("No database connection, returning empty history")
            return []

        query = """
            SELECT *
            FROM field_provenance_timeline
            WHERE tenant_id = %s
              AND entity_type = %s
              AND entity_id = %s
              AND field_name = %s
            ORDER BY created_at DESC
            LIMIT %s;
        """

        cursor = self.connection.cursor()
        cursor.execute(query, (tenant_id, entity_type, entity_id, field_name, limit))

        columns = [desc[0] for desc in cursor.description]
        history = []
        for row in cursor.fetchall():
            record = dict(zip(columns, row))
            # Convert timestamp to ISO format
            if record.get('created_at'):
                record['created_at'] = record['created_at'].isoformat()
            history.append(record)

        cursor.close()

        logger.info(
            f"Retrieved {len(history)} provenance records for "
            f"{entity_type}.{field_name} (entity={entity_id})"
        )

        return history

    def get_entity_provenance(
        self,
        entity_type: str,
        entity_id: str,
        tenant_id: str
    ) -> Dict[str, Dict]:
        """
        Get latest provenance for all fields of an entity

        Args:
            entity_type: Type of entity
            entity_id: UUID of the entity
            tenant_id: Tenant UUID

        Returns:
            Dictionary mapping field_name -> provenance record
        """
        if not self.connection:
            logger.warning("No database connection, returning empty provenance")
            return {}

        query = """
            SELECT *
            FROM latest_field_provenance
            WHERE tenant_id = %s
              AND entity_type = %s
              AND entity_id = %s
            ORDER BY field_name;
        """

        cursor = self.connection.cursor()
        cursor.execute(query, (tenant_id, entity_type, entity_id))

        columns = [desc[0] for desc in cursor.description]
        provenance_map = {}
        for row in cursor.fetchall():
            record = dict(zip(columns, row))
            field_name = record['field_name']
            # Convert timestamp to ISO format
            if record.get('created_at'):
                record['created_at'] = record['created_at'].isoformat()
            provenance_map[field_name] = record

        cursor.close()

        logger.info(
            f"Retrieved provenance for {len(provenance_map)} fields of "
            f"{entity_type} {entity_id}"
        )

        return provenance_map

    def get_entity_trust_score(
        self,
        entity_type: str,
        entity_id: str,
        tenant_id: str
    ) -> Optional[Dict]:
        """
        Get aggregated trust score for an entity

        Args:
            entity_type: Type of entity
            entity_id: UUID of the entity
            tenant_id: Tenant UUID

        Returns:
            Dictionary with trust metrics, or None if not found
        """
        if not self.connection:
            logger.warning("No database connection, returning None")
            return None

        query = """
            SELECT *
            FROM entity_trust_scores
            WHERE tenant_id = %s
              AND entity_type = %s
              AND entity_id = %s;
        """

        cursor = self.connection.cursor()
        cursor.execute(query, (tenant_id, entity_type, entity_id))

        columns = [desc[0] for desc in cursor.description]
        row = cursor.fetchone()
        cursor.close()

        if not row:
            return None

        trust_metrics = dict(zip(columns, row))

        logger.info(
            f"Entity {entity_type} {entity_id} has avg trust score "
            f"{trust_metrics['avg_trust_score']:.2f} ({trust_metrics['field_count']} fields)"
        )

        return trust_metrics

    def get_low_trust_fields(
        self,
        entity_type: str,
        entity_id: str,
        tenant_id: str,
        threshold: float = 0.5
    ) -> List[Dict]:
        """
        Get fields with trust score below threshold

        Args:
            entity_type: Type of entity
            entity_id: UUID of the entity
            tenant_id: Tenant UUID
            threshold: Trust score threshold (default: 0.5)

        Returns:
            List of low-trust field provenance records
        """
        if not self.connection:
            logger.warning("No database connection, returning empty list")
            return []

        query = """
            SELECT *
            FROM latest_field_provenance
            WHERE tenant_id = %s
              AND entity_type = %s
              AND entity_id = %s
              AND trust_score < %s
            ORDER BY trust_score ASC;
        """

        cursor = self.connection.cursor()
        cursor.execute(query, (tenant_id, entity_type, entity_id, threshold))

        columns = [desc[0] for desc in cursor.description]
        low_trust_fields = []
        for row in cursor.fetchall():
            record = dict(zip(columns, row))
            # Convert timestamp to ISO format
            if record.get('created_at'):
                record['created_at'] = record['created_at'].isoformat()
            low_trust_fields.append(record)

        cursor.close()

        logger.warning(
            f"Found {len(low_trust_fields)} low-trust fields (<{threshold}) for "
            f"{entity_type} {entity_id}"
        )

        return low_trust_fields

    def refresh_materialized_views(self):
        """Refresh materialized views for latest provenance"""
        if not self.connection:
            logger.warning("No database connection")
            return

        logger.info("Refreshing latest_field_provenance materialized view")

        cursor = self.connection.cursor()
        cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY latest_field_provenance;")
        self.connection.commit()
        cursor.close()

        logger.info("Materialized view refreshed successfully")

    def _persist_provenance(self, provenance: FieldProvenance):
        """Persist provenance record to database"""
        sql = """
            INSERT INTO field_provenance (
                id,
                entity_type,
                entity_id,
                field_name,
                tenant_id,
                field_value,
                previous_value,
                source,
                method,
                confidence,
                evidence_uri,
                evidence_metadata,
                source_reliability,
                freshness_score,
                validation_score,
                trust_score,
                operation,
                changed_by,
                changed_by_type,
                created_at
            ) VALUES (
                %(id)s,
                %(entity_type)s,
                %(entity_id)s,
                %(field_name)s,
                %(tenant_id)s,
                %(field_value)s,
                %(previous_value)s,
                %(source)s,
                %(method)s,
                %(confidence)s,
                %(evidence_uri)s,
                %(evidence_metadata)s,
                %(source_reliability)s,
                %(freshness_score)s,
                %(validation_score)s,
                %(trust_score)s,
                %(operation)s,
                %(changed_by)s,
                %(changed_by_type)s,
                %(created_at)s
            );
        """

        cursor = self.connection.cursor()
        cursor.execute(sql, provenance.to_dict())
        self.connection.commit()
        cursor.close()

    @staticmethod
    def _serialize_value(value: Any) -> str:
        """Serialize value to string for storage"""
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return str(value)

    @staticmethod
    def calculate_freshness_score(created_at: datetime) -> float:
        """
        Calculate freshness score based on age

        Uses exponential decay with half-life of 90 days:
        freshness = 0.5^(age_days / 90)

        Args:
            created_at: Timestamp of data creation

        Returns:
            Freshness score (0-1)
        """
        age = datetime.utcnow() - created_at
        age_days = age.total_seconds() / 86400

        if age_days <= 0:
            return 1.0
        if age_days >= 365:
            return 0.1  # Floor at 0.1 for data older than 1 year

        # Exponential decay
        freshness = 0.5 ** (age_days / 90.0)

        return max(0.0, min(1.0, freshness))


# Example usage and integration points
def track_property_enrichment(
    property_id: str,
    enrichment_data: Dict[str, Any],
    tenant_id: str,
    source: str = Source.EXTERNAL_ENRICHMENT.value,
    tracker: Optional[ProvenanceTracker] = None
):
    """
    Example: Track property enrichment from external API

    Args:
        property_id: Property UUID
        enrichment_data: Dictionary of enriched fields
        tenant_id: Tenant UUID
        source: Data source
        tracker: ProvenanceTracker instance
    """
    if tracker is None:
        tracker = ProvenanceTracker()

    provenance_records = tracker.track_bulk_changes(
        entity_type='property',
        entity_id=property_id,
        field_changes=enrichment_data,
        tenant_id=tenant_id,
        source=source,
        method=Method.ENRICHMENT_PIPELINE.value,
        operation=Operation.ENRICH.value,
        changed_by_type='system',
        confidence=0.9,
        validation_passed=True,
    )

    return provenance_records


if __name__ == "__main__":
    # Demo usage
    logging.basicConfig(level=logging.INFO)

    tracker = ProvenanceTracker()

    # Example 1: Track a single field change
    provenance = tracker.track_field_change(
        entity_type='property',
        entity_id='123e4567-e89b-12d3-a456-426614174000',
        field_name='price',
        field_value=500000,
        tenant_id='00000000-0000-0000-0000-000000000001',
        source=Source.MLS_API.value,
        method=Method.API_FETCH.value,
        confidence=0.95,
        operation=Operation.UPDATE.value,
        previous_value=475000,
        evidence_uri='s3://real-estate-os/mls/response_2024-11-02.json',
        validation_passed=True,
    )

    print(f"\nProvenance tracked:")
    print(f"  Field: {provenance.field_name}")
    print(f"  Value: {provenance.field_value}")
    print(f"  Previous: {provenance.previous_value}")
    print(f"  Source: {provenance.source}")
    print(f"  Trust Score: {provenance.trust_score:.2f}")

    # Example 2: Track bulk changes
    hazard_data = {
        'flood_zone_type': 'AE',
        'flood_risk_score': 0.85,
        'wildfire_risk_score': 0.45,
        'composite_hazard_score': 0.62,
    }

    provenance_records = tracker.track_bulk_changes(
        entity_type='property',
        entity_id='123e4567-e89b-12d3-a456-426614174000',
        field_changes=hazard_data,
        tenant_id='00000000-0000-0000-0000-000000000001',
        source=Source.FEMA_API.value,
        method=Method.ENRICHMENT_PIPELINE.value,
        operation=Operation.ENRICH.value,
        confidence=0.9,
    )

    print(f"\n{len(provenance_records)} hazard fields tracked")
    for p in provenance_records:
        print(f"  {p.field_name}: {p.field_value} (trust={p.trust_score:.2f})")
