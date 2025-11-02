"""
Property Processing Pipeline with Provenance Write-Through.

This DAG demonstrates field-level provenance tracking with trust scores.
Provenance is written alongside the main data for complete audit trail.

Each field has:
- Source attribution
- Transformation lineage
- Trust score (0-1)
- Data quality metrics
- Complete audit trail
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from typing import List, Dict, Any
import logging

from provenance.provenance_tracker import ProvenanceTracker, InMemoryProvenanceStorage
from provenance.trust_score import SourceType

logger = logging.getLogger(__name__)


# Global storage for provenance (in production, use PostgreSQL)
provenance_storage = InMemoryProvenanceStorage()


# =============================================================================
# Pipeline Tasks with Provenance Tracking
# =============================================================================

def ingest_with_provenance(**context) -> List[Dict]:
    """Ingest properties and track provenance for each field."""
    logger.info("Ingesting properties with provenance tracking...")

    tenant_id = "550e8400-e29b-41d4-a716-446655440000"
    pipeline_run_id = context['dag_run'].run_id

    # Initialize provenance tracker
    tracker = ProvenanceTracker(
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        storage_backend=provenance_storage
    )

    # Simulate ingestion from CSV
    properties = [
        {
            "id": "prop_001",
            "address": "123 Main St, Austin, TX",
            "listing_price": 450000,
            "bedrooms": 3,
            "bathrooms": 2,
            "sqft": 1500
        },
        {
            "id": "prop_002",
            "address": "456 Oak Ave, Austin, TX",
            "listing_price": 625000,
            "bedrooms": 2,
            "bathrooms": 2,
            "sqft": 1200
        }
    ]

    # Track provenance for each property's fields
    for prop in properties:
        entity_id = prop['id']

        # Track each field with its provenance
        tracker.track_field(
            entity_type="property",
            entity_id=entity_id,
            field_name="address",
            field_value=prop['address'],
            source_type="user_input",
            source_name="CSV Upload",
            source_system="file://data/raw/properties.csv",
            created_by="data_import_job",
            validation_result={'passed': 1, 'total': 1}  # Address not null
        )

        tracker.track_field(
            entity_type="property",
            entity_id=entity_id,
            field_name="listing_price",
            field_value=prop['listing_price'],
            source_type="commercial_verified",
            source_name="MLS Feed",
            source_system="mls://austin_board",
            source_version="2024-Q4",
            created_by="mls_sync_job",
            validation_result={'passed': 2, 'total': 2}  # Not null + positive
        )

        tracker.track_field(
            entity_type="property",
            entity_id=entity_id,
            field_name="bedrooms",
            field_value=prop['bedrooms'],
            source_type="user_input",
            source_name="Property Listing",
            created_by="listing_agent",
            validation_result={'passed': 2, 'total': 2}  # Not null + range 0-50
        )

        tracker.track_field(
            entity_type="property",
            entity_id=entity_id,
            field_name="bathrooms",
            field_value=prop['bathrooms'],
            source_type="user_input",
            source_name="Property Listing",
            created_by="listing_agent",
            validation_result={'passed': 2, 'total': 2}
        )

        tracker.track_field(
            entity_type="property",
            entity_id=entity_id,
            field_name="sqft",
            field_value=prop['sqft'],
            source_type="commercial_verified",
            source_name="County Assessor",
            source_system="assessor://travis_county",
            created_by="assessor_sync_job",
            validation_result={'passed': 2, 'total': 2}  # Not null + range
        )

    # Write provenance to storage
    records_written = tracker.write_through(flush_cache=False)

    logger.info(
        f"Ingested {len(properties)} properties with "
        f"{records_written} provenance records"
    )

    # Store in XCom
    context['ti'].xcom_push(key='properties', value=properties)
    context['ti'].xcom_push(key='tracker', value=tracker)

    return properties


def normalize_with_provenance(**context) -> List[Dict]:
    """Normalize addresses and track derived fields."""
    logger.info("Normalizing addresses with provenance...")

    ti = context['ti']
    properties = ti.xcom_pull(task_ids='ingest', key='properties')
    tenant_id = "550e8400-e29b-41d4-a716-446655440000"

    # New tracker for this stage
    tracker = ProvenanceTracker(
        tenant_id=tenant_id,
        pipeline_run_id=context['dag_run'].run_id,
        storage_backend=provenance_storage
    )

    normalized = []

    for prop in properties:
        # Normalize address (simulated)
        normalized_address = prop['address'].upper()
        latitude = 30.2672 + (hash(prop['id']) % 100) / 1000
        longitude = -97.7431 - (hash(prop['id']) % 100) / 1000
        address_hash = prop['address'][:16]

        normalized_prop = {
            **prop,
            "normalized_address": normalized_address,
            "latitude": latitude,
            "longitude": longitude,
            "address_hash": address_hash,
            "geocoding_confidence": 0.95
        }

        # Get parent provenance ID for address field
        parent_storage_records = provenance_storage.query_by_field(
            "property", prop['id'], "address"
        )
        parent_prov_id = parent_storage_records['provenance_id'] if parent_storage_records else None

        # Track derived fields
        tracker.track_field(
            entity_type="property",
            entity_id=prop['id'],
            field_name="normalized_address",
            field_value=normalized_address,
            source_type="user_input",  # Derived from user input
            source_name="libpostal Normalization",
            source_system="libpostal://v1.1.0",
            parent_provenance_ids=[parent_prov_id] if parent_prov_id else [],
            transformation_type="validated_normalization",
            transformation_description="Normalized address using libpostal",
            transformation_code="address.upper()",
            validation_result={'passed': 1, 'total': 1}
        )

        tracker.track_field(
            entity_type="property",
            entity_id=prop['id'],
            field_name="latitude",
            field_value=latitude,
            source_type="commercial_verified",
            source_name="Google Geocoding API",
            source_system="https://maps.googleapis.com/maps/api/geocode",
            parent_provenance_ids=[parent_prov_id] if parent_prov_id else [],
            transformation_type="validated_normalization",
            transformation_description="Geocoded from address",
            model_confidence=0.95,
            validation_result={'passed': 1, 'total': 1},  # Range -90 to 90
            evidence_metadata={
                "geocoder_response": {"location_type": "ROOFTOP"},
                "api_version": "v3"
            }
        )

        tracker.track_field(
            entity_type="property",
            entity_id=prop['id'],
            field_name="longitude",
            field_value=longitude,
            source_type="commercial_verified",
            source_name="Google Geocoding API",
            source_system="https://maps.googleapis.com/maps/api/geocode",
            parent_provenance_ids=[parent_prov_id] if parent_prov_id else [],
            transformation_type="validated_normalization",
            transformation_description="Geocoded from address",
            model_confidence=0.95,
            validation_result={'passed': 1, 'total': 1}  # Range -180 to 180
        )

        tracker.track_field(
            entity_type="property",
            entity_id=prop['id'],
            field_name="address_hash",
            field_value=address_hash,
            source_type="user_input",
            source_name="SHA256 Hash",
            parent_provenance_ids=[parent_prov_id] if parent_prov_id else [],
            transformation_type="lossless",
            transformation_description="16-char SHA256 hash for deduplication",
            transformation_code="hashlib.sha256(address.encode()).hexdigest()[:16]",
            validation_result={'passed': 1, 'total': 1}  # Length = 16
        )

        normalized.append(normalized_prop)

    # Write provenance
    records_written = tracker.write_through(flush_cache=False)

    logger.info(
        f"Normalized {len(normalized)} properties with "
        f"{records_written} new provenance records"
    )

    # Store in XCom
    ti.xcom_push(key='normalized', value=normalized)

    return normalized


def enrich_hazards_with_provenance(**context) -> List[Dict]:
    """Enrich with hazard data and track multi-source provenance."""
    logger.info("Enriching hazards with provenance...")

    ti = context['ti']
    normalized = ti.xcom_pull(task_ids='normalize', key='normalized')
    tenant_id = "550e8400-e29b-41d4-a716-446655440000"

    tracker = ProvenanceTracker(
        tenant_id=tenant_id,
        pipeline_run_id=context['dag_run'].run_id,
        storage_backend=provenance_storage
    )

    enriched = []

    for prop in normalized:
        # Enrich with hazard data (simulated)
        flood_zone = "AE"
        wildfire_risk = 0.08
        heat_risk = 0.22
        composite_risk = (flood_zone == "AE") * 0.15 * 0.5 + wildfire_risk * 0.3 + heat_risk * 0.2

        enriched_prop = {
            **prop,
            "flood_zone": flood_zone,
            "wildfire_risk_score": wildfire_risk,
            "heat_risk_score": heat_risk,
            "composite_risk_score": composite_risk
        }

        # Get parent provenance IDs for lat/lon
        lat_prov = provenance_storage.query_by_field("property", prop['id'], "latitude")
        lon_prov = provenance_storage.query_by_field("property", prop['id'], "longitude")
        parent_ids = []
        if lat_prov:
            parent_ids.append(lat_prov['provenance_id'])
        if lon_prov:
            parent_ids.append(lon_prov['provenance_id'])

        # Track hazard fields
        tracker.track_field(
            entity_type="property",
            entity_id=prop['id'],
            field_name="flood_zone",
            field_value=flood_zone,
            source_type="authoritative_government",
            source_name="FEMA NFHL",
            source_system="https://hazards.fema.gov/gis/nfhl",
            source_version="2024-09-15",
            parent_provenance_ids=parent_ids,
            transformation_type="validated_normalization",
            transformation_description="Flood zone from FEMA NFHL API",
            validation_result={'passed': 1, 'total': 1},
            evidence_url="https://hazards.fema.gov/report/123",
            evidence_metadata={
                "dataset_version": "2024-09-15",
                "query_method": "point_in_polygon",
                "base_flood_elevation": 485
            }
        )

        tracker.track_field(
            entity_type="property",
            entity_id=prop['id'],
            field_name="wildfire_risk_score",
            field_value=wildfire_risk,
            source_type="authoritative_government",
            source_name="USGS WHP",
            source_system="https://wildfire.usgs.gov/whp",
            source_version="2024-08-01",
            parent_provenance_ids=parent_ids,
            transformation_type="validated_normalization",
            model_confidence=0.85,
            validation_result={'passed': 1, 'total': 1}
        )

        tracker.track_field(
            entity_type="property",
            entity_id=prop['id'],
            field_name="heat_risk_score",
            field_value=heat_risk,
            source_type="authoritative_government",
            source_name="NOAA Climate Data",
            source_system="https://www.ncdc.noaa.gov/cdo-web/api/v2",
            source_version="2024-10-01",
            parent_provenance_ids=parent_ids,
            transformation_type="statistical_imputation",
            model_confidence=0.88,
            validation_result={'passed': 1, 'total': 1}
        )

        # Composite risk depends on all three hazard scores
        flood_prov = provenance_storage.query_by_field("property", prop['id'], "flood_zone")
        fire_prov = provenance_storage.query_by_field("property", prop['id'], "wildfire_risk_score")
        heat_prov = provenance_storage.query_by_field("property", prop['id'], "heat_risk_score")

        composite_parent_ids = [
            p['provenance_id'] for p in [flood_prov, fire_prov, heat_prov] if p
        ]

        tracker.track_field(
            entity_type="property",
            entity_id=prop['id'],
            field_name="composite_risk_score",
            field_value=composite_risk,
            source_type="ml_model_validated",
            source_name="Composite Risk Calculator",
            parent_provenance_ids=composite_parent_ids,
            transformation_type="validated_normalization",
            transformation_description="Weighted average: (flood*0.5 + fire*0.3 + heat*0.2)",
            transformation_code="flood*0.5 + wildfire*0.3 + heat*0.2",
            model_confidence=0.88,
            validation_result={'passed': 1, 'total': 1}
        )

        enriched.append(enriched_prop)

    # Write provenance
    records_written = tracker.write_through(flush_cache=False)

    logger.info(
        f"Enriched {len(enriched)} properties with "
        f"{records_written} hazard provenance records"
    )

    ti.xcom_push(key='enriched', value=enriched)

    return enriched


def generate_provenance_report(**context) -> Dict:
    """Generate comprehensive provenance report."""
    logger.info("Generating provenance report...")

    # Query all provenance records from storage
    total_records = len(provenance_storage.records)

    # Calculate statistics
    source_counts = {}
    trust_scores = []

    for record in provenance_storage.records:
        source_type = record['source_type']
        source_counts[source_type] = source_counts.get(source_type, 0) + 1
        trust_scores.append(record['trust_score'])

    avg_trust_score = sum(trust_scores) / len(trust_scores) if trust_scores else 0

    report = {
        "pipeline_run_id": context['dag_run'].run_id,
        "total_provenance_records": total_records,
        "source_distribution": source_counts,
        "average_trust_score": round(avg_trust_score, 4),
        "min_trust_score": round(min(trust_scores), 4) if trust_scores else 0,
        "max_trust_score": round(max(trust_scores), 4) if trust_scores else 0,
        "generated_at": datetime.utcnow().isoformat()
    }

    logger.info(
        f"Provenance Report: {total_records} records tracked, "
        f"avg trust score: {avg_trust_score:.4f}"
    )

    return report


# =============================================================================
# DAG Definition
# =============================================================================

default_args = {
    'owner': 'data_engineering',
    'depends_on_past': False,
    'email_on_failure': True,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'property_pipeline_with_provenance',
    default_args=default_args,
    description='Property pipeline with field-level provenance tracking',
    schedule_interval='@daily',
    start_date=datetime(2024, 11, 1),
    catchup=False,
    tags=['properties', 'provenance', 'trust-score'],
)

# Task definitions
ingest = PythonOperator(
    task_id='ingest',
    python_callable=ingest_with_provenance,
    dag=dag
)

normalize = PythonOperator(
    task_id='normalize',
    python_callable=normalize_with_provenance,
    dag=dag
)

enrich = PythonOperator(
    task_id='enrich_hazards',
    python_callable=enrich_hazards_with_provenance,
    dag=dag
)

report = PythonOperator(
    task_id='generate_provenance_report',
    python_callable=generate_provenance_report,
    dag=dag
)

# Define flow
ingest >> normalize >> enrich >> report
