"""
Property Processing Pipeline DAG

This DAG orchestrates the end-to-end property data processing pipeline:
1. Ingest raw property data
2. Validate with Great Expectations (ingestion checkpoint)
3. Normalize addresses with libpostal
4. Enrich with external data (hazards, market data)
5. Validate with Great Expectations (pre-ML checkpoint)
6. Run ML models (Comp-Critic, motivation scoring)
7. Generate prospects list
8. Update vector embeddings in Qdrant
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.dates import days_ago

# Import GX validation functions
import sys
sys.path.insert(0, '/home/user/real-estate-os')

from data_quality.gx_integration import (
    validate_properties_ingestion,
    validate_prospects_pre_ml,
    GXValidationError
)

default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email': ['alerts@real-estate-os.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),
}

with DAG(
    dag_id='property_processing_pipeline',
    default_args=default_args,
    description='End-to-end property data processing with GX gates',
    schedule_interval='0 2 * * *',  # Daily at 2 AM
    start_date=days_ago(1),
    catchup=False,
    tags=['pipeline', 'properties', 'data-quality'],
    doc_md=__doc__,
) as dag:

    # Start
    start = EmptyOperator(task_id='start')

    # Task 1: Ingest raw property data
    def ingest_properties(**context):
        """
        Ingest raw property data from external sources

        In production, this would:
        - Fetch data from MLS feeds, public records, web scraping
        - Parse and standardize formats
        - Insert into properties table
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info("Ingesting property data...")
        # Simulate ingestion
        properties_ingested = 1250

        logger.info(f"Ingested {properties_ingested} properties")
        return {"properties_count": properties_ingested}

    ingest_task = PythonOperator(
        task_id='ingest_properties',
        python_callable=ingest_properties,
    )

    # Task 2: Validate ingested properties (GX Gate #1)
    validate_ingestion = PythonOperator(
        task_id='validate_properties_ingestion',
        python_callable=validate_properties_ingestion,
        doc_md="""
        ## Great Expectations: Ingestion Checkpoint

        Validates properties data immediately after ingestion.

        **Expectations:**
        - Schema compliance (required columns present)
        - Primary key constraints (id not null, unique)
        - Tenant isolation (tenant_id not null, valid UUID)
        - Data type constraints (price, bedrooms, sqft in range)
        - Format validation (ZIP code, state code, property_type)
        - Audit fields (created_at, updated_at not null)

        **Failure handling:**
        - Task fails if validation fails
        - Email alert sent to data-engineering
        - Slack notification via GX action
        - Pipeline stops (downstream tasks not executed)
        """
    )

    # Task 3: Normalize addresses
    def normalize_addresses(**context):
        """
        Normalize addresses using libpostal

        Standardizes address components for accurate geocoding and matching
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info("Normalizing addresses with libpostal...")
        # In production: call libpostal service
        addresses_normalized = context['ti'].xcom_pull(
            task_ids='ingest_properties'
        )['properties_count']

        logger.info(f"Normalized {addresses_normalized} addresses")
        return {"addresses_normalized": addresses_normalized}

    normalize_task = PythonOperator(
        task_id='normalize_addresses',
        python_callable=normalize_addresses,
    )

    # Task 4: Enrich with external data
    def enrich_properties(**context):
        """
        Enrich properties with external data:
        - Hazard layers (FEMA flood, wildfire, earthquake)
        - Market data (median price, days on market, inventory)
        - Demographics (population, income, employment)
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info("Enriching properties with external data...")
        # In production: spatial joins, API calls
        properties_enriched = context['ti'].xcom_pull(
            task_ids='normalize_addresses'
        )['addresses_normalized']

        logger.info(f"Enriched {properties_enriched} properties")
        return {"properties_enriched": properties_enriched}

    enrich_task = PythonOperator(
        task_id='enrich_properties',
        python_callable=enrich_properties,
    )

    # Task 5: Run Comp-Critic valuation
    def run_comp_critic(**context):
        """
        Run Comp-Critic valuation model

        3-stage valuation:
        1. Retrieval: Find comparable properties
        2. Ranking: Rank by relevance
        3. Hedonic adjustment: Adjust for differences
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info("Running Comp-Critic valuation...")
        properties_count = context['ti'].xcom_pull(
            task_ids='enrich_properties'
        )['properties_enriched']

        # In production: call ml/models/comp_critic.py
        logger.info(f"Valued {properties_count} properties")
        return {"properties_valued": properties_count}

    comp_critic_task = PythonOperator(
        task_id='run_comp_critic_valuation',
        python_callable=run_comp_critic,
    )

    # Task 6: Score prospects motivation
    def score_motivation(**context):
        """
        Score prospect motivation using ML model

        Features:
        - Equity position
        - Property condition
        - Owner demographics
        - Market regime
        - Time in ownership
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info("Scoring prospect motivation...")
        # In production: call ML scoring service
        prospects_scored = 450

        logger.info(f"Scored {prospects_scored} prospects")
        return {"prospects_count": prospects_scored}

    score_task = PythonOperator(
        task_id='score_prospect_motivation',
        python_callable=score_motivation,
    )

    # Task 7: Validate prospects (GX Gate #2)
    validate_prospects = PythonOperator(
        task_id='validate_prospects_pre_ml',
        python_callable=validate_prospects_pre_ml,
        doc_md="""
        ## Great Expectations: Pre-ML Checkpoint

        Validates prospects data before downstream ML pipeline.

        **Expectations:**
        - Schema compliance
        - Foreign key integrity (property_id references valid property)
        - Tenant isolation
        - Score bounds (motivation_score between 0 and 1)
        - Contact data format (phone, email regex)
        - Status values (contact_status in valid set)

        **Failure handling:**
        - Task fails if validation fails
        - Email alert sent
        - Slack notification
        - Prevents invalid data from reaching ML pipeline
        """
    )

    # Task 8: Update vector embeddings
    def update_embeddings(**context):
        """
        Update property embeddings in Qdrant

        Generate embeddings from property features and update vector store
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info("Updating vector embeddings in Qdrant...")
        properties_count = context['ti'].xcom_pull(
            task_ids='run_comp_critic_valuation'
        )['properties_valued']

        # In production: call embedding service, upsert to Qdrant
        logger.info(f"Updated {properties_count} embeddings")
        return {"embeddings_updated": properties_count}

    embeddings_task = PythonOperator(
        task_id='update_vector_embeddings',
        python_callable=update_embeddings,
    )

    # Task 9: Generate daily report
    def generate_report(**context):
        """
        Generate daily pipeline report

        Includes:
        - Properties ingested/validated
        - Prospects identified
        - GX validation results
        - Model performance metrics
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info("Generating daily report...")

        # Pull stats from XCom
        stats = {
            "properties_ingested": context['ti'].xcom_pull(
                task_ids='ingest_properties'
            )['properties_count'],
            "prospects_scored": context['ti'].xcom_pull(
                task_ids='score_prospect_motivation'
            )['prospects_count'],
            "embeddings_updated": context['ti'].xcom_pull(
                task_ids='update_vector_embeddings'
            )['embeddings_updated'],
        }

        logger.info(f"Pipeline stats: {stats}")
        return stats

    report_task = PythonOperator(
        task_id='generate_daily_report',
        python_callable=generate_report,
    )

    # End
    end = EmptyOperator(task_id='end')

    # Define task dependencies
    start >> ingest_task >> validate_ingestion >> normalize_task >> enrich_task
    enrich_task >> comp_critic_task >> score_task >> validate_prospects
    validate_prospects >> embeddings_task >> report_task >> end
