"""
Property Processing Pipeline with OpenLineage Tracking.

This DAG demonstrates complete data lineage tracking using OpenLineage.
Every task emits START/COMPLETE/FAIL events that are sent to Marquez.

Lineage Graph:
  raw_properties_csv → ingest → properties_raw_staging
  properties_raw_staging → normalize → properties_normalized
  properties_normalized → enrich → properties_enriched
  properties_enriched → score → properties_scored
  properties_scored → load → properties_production
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from typing import List, Dict, Any
import logging

from lineage.openlineage_client import (
    OpenLineageDataset,
    airflow_integration
)

logger = logging.getLogger(__name__)


# =============================================================================
# Dataset Definitions
# =============================================================================

# Schema definitions for lineage tracking
PROPERTIES_RAW_SCHEMA = [
    {"name": "id", "type": "STRING"},
    {"name": "tenant_id", "type": "STRING"},
    {"name": "address", "type": "STRING"},
    {"name": "listing_price", "type": "DECIMAL"},
    {"name": "bedrooms", "type": "INTEGER"},
    {"name": "bathrooms", "type": "DECIMAL"},
    {"name": "sqft", "type": "INTEGER"},
]

PROPERTIES_NORMALIZED_SCHEMA = [
    *PROPERTIES_RAW_SCHEMA,
    {"name": "latitude", "type": "DECIMAL"},
    {"name": "longitude", "type": "DECIMAL"},
    {"name": "address_hash", "type": "STRING"},
    {"name": "geocoding_confidence", "type": "DECIMAL"},
]

PROPERTIES_ENRICHED_SCHEMA = [
    *PROPERTIES_NORMALIZED_SCHEMA,
    {"name": "flood_zone", "type": "STRING"},
    {"name": "wildfire_risk_score", "type": "DECIMAL"},
    {"name": "heat_risk_score", "type": "DECIMAL"},
    {"name": "composite_risk_score", "type": "DECIMAL"},
]

PROPERTIES_SCORED_SCHEMA = [
    *PROPERTIES_ENRICHED_SCHEMA,
    {"name": "comp_critic_value", "type": "DECIMAL"},
    {"name": "dcf_value", "type": "DECIMAL"},
    {"name": "ensemble_value", "type": "DECIMAL"},
    {"name": "confidence_score", "type": "DECIMAL"},
]


# =============================================================================
# Lineage Helper Functions
# =============================================================================

def create_dataset_with_schema(
    name: str,
    schema: List[Dict[str, str]],
    documentation: str
) -> OpenLineageDataset:
    """Create dataset with schema facets."""
    facets = airflow_integration.create_dataset_facets(
        schema=schema,
        documentation=documentation
    )

    return OpenLineageDataset(
        namespace="postgres://real_estate_os",
        name=name,
        facets=facets
    )


# =============================================================================
# Pipeline Tasks with Lineage
# =============================================================================

def ingest_properties_with_lineage(**context) -> List[Dict]:
    """
    Ingest raw properties from CSV with lineage tracking.

    Lineage: raw_properties.csv → properties_raw_staging
    """
    logger.info("Starting property ingestion...")

    # Define datasets
    input_dataset = OpenLineageDataset(
        namespace="file://data/raw",
        name="properties.csv",
        facets=airflow_integration.create_dataset_facets(
            schema=PROPERTIES_RAW_SCHEMA,
            documentation="Raw property data from external sources"
        )
    )

    output_dataset = create_dataset_with_schema(
        name="properties_raw_staging",
        schema=PROPERTIES_RAW_SCHEMA,
        documentation="Raw properties loaded into staging table"
    )

    # Emit START event
    airflow_integration.emit_task_lineage(
        context=context,
        inputs=[input_dataset],
        outputs=[output_dataset],
        event_type="START"
    )

    try:
        # Simulate ingestion
        properties = [
            {
                "id": "prop_001",
                "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
                "address": "123 Main St, Austin, TX 78701",
                "listing_price": 450000,
                "bedrooms": 3,
                "bathrooms": 2,
                "sqft": 1500
            },
            {
                "id": "prop_002",
                "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
                "address": "456 Oak Ave, Austin, TX 78704",
                "listing_price": 375000,
                "bedrooms": 2,
                "bathrooms": 2,
                "sqft": 1200
            },
            {
                "id": "prop_003",
                "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
                "address": "789 Elm Rd, Austin, TX 78702",
                "listing_price": 525000,
                "bedrooms": 3,
                "bathrooms": 2.5,
                "sqft": 1800
            }
        ]

        logger.info(f"Ingested {len(properties)} properties")

        # Store in XCom
        context['ti'].xcom_push(key='properties', value=properties)

        # Emit COMPLETE event
        airflow_integration.emit_task_lineage(
            context=context,
            inputs=[input_dataset],
            outputs=[output_dataset],
            event_type="COMPLETE"
        )

        return properties

    except Exception as e:
        logger.error(f"Ingestion failed: {e}")

        # Emit FAIL event
        airflow_integration.emit_task_lineage(
            context=context,
            inputs=[input_dataset],
            outputs=[output_dataset],
            event_type="FAIL",
            error_message=str(e)
        )

        raise


def normalize_addresses_with_lineage(**context) -> List[Dict]:
    """
    Normalize addresses and geocode with lineage tracking.

    Lineage: properties_raw_staging → properties_normalized
    """
    logger.info("Starting address normalization...")

    # Define datasets
    input_dataset = create_dataset_with_schema(
        name="properties_raw_staging",
        schema=PROPERTIES_RAW_SCHEMA,
        documentation="Raw properties from staging"
    )

    output_dataset = create_dataset_with_schema(
        name="properties_normalized",
        schema=PROPERTIES_NORMALIZED_SCHEMA,
        documentation="Properties with normalized addresses and geocoding"
    )

    # Emit START event
    airflow_integration.emit_task_lineage(
        context=context,
        inputs=[input_dataset],
        outputs=[output_dataset],
        event_type="START"
    )

    try:
        # Get input data
        ti = context['ti']
        properties = ti.xcom_pull(task_ids='ingest_properties', key='properties')

        # Normalize
        normalized = []
        for prop in properties:
            normalized_prop = {
                **prop,
                "latitude": 30.2672 + (hash(prop['id']) % 100) / 1000,
                "longitude": -97.7431 - (hash(prop['id']) % 100) / 1000,
                "address_hash": prop['address'][:16],
                "geocoding_confidence": 0.95
            }
            normalized.append(normalized_prop)

        logger.info(f"Normalized {len(normalized)} properties")

        # Store in XCom
        ti.xcom_push(key='normalized', value=normalized)

        # Emit COMPLETE event
        airflow_integration.emit_task_lineage(
            context=context,
            inputs=[input_dataset],
            outputs=[output_dataset],
            event_type="COMPLETE"
        )

        return normalized

    except Exception as e:
        logger.error(f"Normalization failed: {e}")

        airflow_integration.emit_task_lineage(
            context=context,
            inputs=[input_dataset],
            outputs=[output_dataset],
            event_type="FAIL",
            error_message=str(e)
        )

        raise


def enrich_hazards_with_lineage(**context) -> List[Dict]:
    """
    Enrich with hazard data with lineage tracking.

    Lineage: properties_normalized + fema_api + usgs_api + noaa_api → properties_enriched
    """
    logger.info("Starting hazard enrichment...")

    # Define datasets
    input_datasets = [
        create_dataset_with_schema(
            name="properties_normalized",
            schema=PROPERTIES_NORMALIZED_SCHEMA,
            documentation="Normalized properties"
        ),
        OpenLineageDataset(
            namespace="https://api.fema.gov",
            name="nfhl_flood_zones",
            facets=airflow_integration.create_dataset_facets(
                documentation="FEMA National Flood Hazard Layer"
            )
        ),
        OpenLineageDataset(
            namespace="https://api.usgs.gov",
            name="wildfire_hazard_potential",
            facets=airflow_integration.create_dataset_facets(
                documentation="USGS Wildfire Hazard Potential"
            )
        ),
        OpenLineageDataset(
            namespace="https://api.noaa.gov",
            name="climate_data",
            facets=airflow_integration.create_dataset_facets(
                documentation="NOAA Climate Data"
            )
        )
    ]

    output_dataset = create_dataset_with_schema(
        name="properties_enriched",
        schema=PROPERTIES_ENRICHED_SCHEMA,
        documentation="Properties enriched with hazard data"
    )

    # Emit START event
    airflow_integration.emit_task_lineage(
        context=context,
        inputs=input_datasets,
        outputs=[output_dataset],
        event_type="START"
    )

    try:
        # Get input data
        ti = context['ti']
        normalized = ti.xcom_pull(task_ids='normalize_addresses', key='normalized')

        # Enrich with hazards
        enriched = []
        for prop in normalized:
            enriched_prop = {
                **prop,
                "flood_zone": "AE",
                "wildfire_risk_score": 0.08,
                "heat_risk_score": 0.22,
                "composite_risk_score": 0.145
            }
            enriched.append(enriched_prop)

        logger.info(f"Enriched {len(enriched)} properties with hazard data")

        # Store in XCom
        ti.xcom_push(key='enriched', value=enriched)

        # Emit COMPLETE event
        airflow_integration.emit_task_lineage(
            context=context,
            inputs=input_datasets,
            outputs=[output_dataset],
            event_type="COMPLETE"
        )

        return enriched

    except Exception as e:
        logger.error(f"Enrichment failed: {e}")

        airflow_integration.emit_task_lineage(
            context=context,
            inputs=input_datasets,
            outputs=[output_dataset],
            event_type="FAIL",
            error_message=str(e)
        )

        raise


def score_valuations_with_lineage(**context) -> List[Dict]:
    """
    Score property valuations with lineage tracking.

    Lineage: properties_enriched + comp_data + market_data → properties_scored
    """
    logger.info("Starting valuation scoring...")

    # Define datasets
    input_datasets = [
        create_dataset_with_schema(
            name="properties_enriched",
            schema=PROPERTIES_ENRICHED_SCHEMA,
            documentation="Properties with hazard enrichment"
        ),
        OpenLineageDataset(
            namespace="postgres://real_estate_os",
            name="comparable_sales",
            facets=airflow_integration.create_dataset_facets(
                documentation="Historical comparable sales data"
            )
        ),
        OpenLineageDataset(
            namespace="postgres://real_estate_os",
            name="market_indicators",
            facets=airflow_integration.create_dataset_facets(
                documentation="Market trend indicators"
            )
        )
    ]

    output_dataset = create_dataset_with_schema(
        name="properties_scored",
        schema=PROPERTIES_SCORED_SCHEMA,
        documentation="Properties with ML-based valuations"
    )

    # Emit START event
    airflow_integration.emit_task_lineage(
        context=context,
        inputs=input_datasets,
        outputs=[output_dataset],
        event_type="START"
    )

    try:
        # Get input data
        ti = context['ti']
        enriched = ti.xcom_pull(task_ids='enrich_hazards', key='enriched')

        # Score valuations
        scored = []
        for prop in enriched:
            comp_value = prop['listing_price'] * 0.975  # Comp-Critic adjustment
            dcf_value = prop['listing_price'] * 0.99    # DCF valuation
            ensemble_value = (comp_value * 0.5) + (dcf_value * 0.5)

            scored_prop = {
                **prop,
                "comp_critic_value": comp_value,
                "dcf_value": dcf_value,
                "ensemble_value": ensemble_value,
                "confidence_score": 0.82
            }
            scored.append(scored_prop)

        logger.info(f"Scored {len(scored)} properties")

        # Store in XCom
        ti.xcom_push(key='scored', value=scored)

        # Emit COMPLETE event
        airflow_integration.emit_task_lineage(
            context=context,
            inputs=input_datasets,
            outputs=[output_dataset],
            event_type="COMPLETE"
        )

        return scored

    except Exception as e:
        logger.error(f"Scoring failed: {e}")

        airflow_integration.emit_task_lineage(
            context=context,
            inputs=input_datasets,
            outputs=[output_dataset],
            event_type="FAIL",
            error_message=str(e)
        )

        raise


def load_to_production_with_lineage(**context) -> Dict:
    """
    Load to production with lineage tracking.

    Lineage: properties_scored → properties_production
    """
    logger.info("Loading to production...")

    # Define datasets
    input_dataset = create_dataset_with_schema(
        name="properties_scored",
        schema=PROPERTIES_SCORED_SCHEMA,
        documentation="Properties with valuations"
    )

    output_dataset = create_dataset_with_schema(
        name="properties_production",
        schema=PROPERTIES_SCORED_SCHEMA,
        documentation="Production properties table"
    )

    # Emit START event
    airflow_integration.emit_task_lineage(
        context=context,
        inputs=[input_dataset],
        outputs=[output_dataset],
        event_type="START"
    )

    try:
        # Get input data
        ti = context['ti']
        scored = ti.xcom_pull(task_ids='score_valuations', key='scored')

        # Simulate production load
        logger.info(f"Loaded {len(scored)} properties to production")

        result = {
            "status": "success",
            "properties_loaded": len(scored),
            "timestamp": datetime.now().isoformat()
        }

        # Emit COMPLETE event
        airflow_integration.emit_task_lineage(
            context=context,
            inputs=[input_dataset],
            outputs=[output_dataset],
            event_type="COMPLETE"
        )

        return result

    except Exception as e:
        logger.error(f"Production load failed: {e}")

        airflow_integration.emit_task_lineage(
            context=context,
            inputs=[input_dataset],
            outputs=[output_dataset],
            event_type="FAIL",
            error_message=str(e)
        )

        raise


# =============================================================================
# DAG Definition
# =============================================================================

default_args = {
    'owner': 'data_engineering',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'property_pipeline_with_lineage',
    default_args=default_args,
    description='Property processing pipeline with OpenLineage tracking',
    schedule_interval='@daily',
    start_date=datetime(2024, 11, 1),
    catchup=False,
    tags=['properties', 'lineage', 'openlineage', 'marquez'],
)

# Task definitions
ingest = PythonOperator(
    task_id='ingest_properties',
    python_callable=ingest_properties_with_lineage,
    dag=dag
)

normalize = PythonOperator(
    task_id='normalize_addresses',
    python_callable=normalize_addresses_with_lineage,
    dag=dag
)

enrich = PythonOperator(
    task_id='enrich_hazards',
    python_callable=enrich_hazards_with_lineage,
    dag=dag
)

score = PythonOperator(
    task_id='score_valuations',
    python_callable=score_valuations_with_lineage,
    dag=dag
)

load = PythonOperator(
    task_id='load_to_production',
    python_callable=load_to_production_with_lineage,
    dag=dag
)

# Define pipeline flow
ingest >> normalize >> enrich >> score >> load
