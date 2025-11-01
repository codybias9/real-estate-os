"""Enrichment DAG: Enrich properties with assessor and census data

This DAG orchestrates property enrichment:
1. Fetches prospects ready for enrichment
2. Batches prospects for processing
3. Launches enrichment agent in Kubernetes
4. Validates enrichment data quality
5. Updates prospect status
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.utils.trigger_rule import TriggerRule
from kubernetes.client import models as k8s
import logging
import os

logger = logging.getLogger(__name__)

# Default arguments
default_args = {
    'owner': 'real-estate-os',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=4),
}

# DAG configuration
DAG_ID = 'enrichment_property'
SCHEDULE_INTERVAL = '@daily'
START_DATE = datetime(2025, 1, 1)

# Kubernetes configuration
K8S_NAMESPACE = os.getenv('K8S_NAMESPACE', 'orchestration')
ENRICHMENT_IMAGE = os.getenv('ENRICHMENT_IMAGE', 'real-estate-os/enrichment-agent:latest')
POSTGRES_CONN_ID = 'postgres_realestate'

# Enrichment configuration
BATCH_SIZE = int(os.getenv('ENRICHMENT_BATCH_SIZE', '100'))
CENSUS_API_KEY = os.getenv('CENSUS_API_KEY', '')


def fetch_ready_prospects(**context):
    """
    Fetch prospects that are ready for enrichment

    Selects prospects with status='ready' and no existing enrichment.
    """
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    batch_size = context['params'].get('batch_size', BATCH_SIZE)

    # Query for prospects needing enrichment
    query = """
        SELECT pq.id, pq.payload->>'zip_code' as zip_code
        FROM prospect_queue pq
        LEFT JOIN property_enrichment pe ON pe.prospect_id = pq.id
        WHERE pq.status = 'ready'
          AND pe.id IS NULL
        ORDER BY pq.created_at DESC
        LIMIT %s
    """

    results = hook.get_records(query, parameters=(batch_size,))

    if not results:
        logger.warning("No prospects ready for enrichment")
        return {'prospect_ids': [], 'count': 0}

    prospect_ids = [row[0] for row in results]

    logger.info(f"Found {len(prospect_ids)} prospects ready for enrichment")

    # Push to XCom for downstream tasks
    ti = context['ti']
    ti.xcom_push(key='prospect_ids', value=prospect_ids)

    return {
        'prospect_ids': prospect_ids,
        'count': len(prospect_ids)
    }


def validate_enrichment(**context):
    """
    Validate enrichment data quality

    Checks:
    - Enrichment records were created
    - Data completeness
    - No excessive errors
    """
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    # Get prospect IDs from XCom
    ti = context['ti']
    prospect_ids = ti.xcom_pull(task_ids='fetch_ready_prospects', key='prospect_ids')

    if not prospect_ids:
        logger.warning("No prospect IDs to validate")
        return {'status': 'no_data'}

    # Check how many were enriched
    query = """
        SELECT COUNT(*) as total,
               COUNT(*) FILTER (WHERE square_footage IS NOT NULL) as with_sqft,
               COUNT(*) FILTER (WHERE bedrooms IS NOT NULL) as with_beds,
               COUNT(*) FILTER (WHERE assessed_value IS NOT NULL) as with_value
        FROM property_enrichment
        WHERE prospect_id = ANY(%s)
    """

    result = hook.get_first(query, parameters=(prospect_ids,))

    if not result:
        logger.error("Failed to query enrichment results")
        return {'status': 'error'}

    total, with_sqft, with_beds, with_value = result

    logger.info(f"Enrichment results: {total}/{len(prospect_ids)} enriched")
    logger.info(f"  With square footage: {with_sqft}/{total}")
    logger.info(f"  With bedrooms: {with_beds}/{total}")
    logger.info(f"  With assessed value: {with_value}/{total}")

    # Calculate success rate
    success_rate = total / len(prospect_ids) if prospect_ids else 0

    if success_rate < 0.5:
        logger.warning(f"Low enrichment success rate: {success_rate:.1%}")

    return {
        'status': 'success',
        'total_enriched': total,
        'total_attempted': len(prospect_ids),
        'success_rate': success_rate,
        'completeness': {
            'square_footage': with_sqft / total if total > 0 else 0,
            'bedrooms': with_beds / total if total > 0 else 0,
            'assessed_value': with_value / total if total > 0 else 0
        }
    }


def collect_enrichment_metrics(**context):
    """Collect and log enrichment metrics"""
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    # Get statistics
    stats_query = """
        SELECT
            COUNT(*) as total_enriched,
            AVG(square_footage) as avg_sqft,
            AVG(bedrooms) as avg_beds,
            AVG(CAST(assessed_value AS NUMERIC)) as avg_value,
            COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '1 day') as enriched_today
        FROM property_enrichment
    """

    result = hook.get_first(stats_query)

    if result:
        total, avg_sqft, avg_beds, avg_value, today = result

        logger.info("=" * 50)
        logger.info("ENRICHMENT METRICS")
        logger.info("=" * 50)
        logger.info(f"Total enriched properties: {total}")
        logger.info(f"Enriched today: {today}")
        logger.info(f"Average square footage: {avg_sqft:.0f}" if avg_sqft else "N/A")
        logger.info(f"Average bedrooms: {avg_beds:.1f}" if avg_beds else "N/A")
        logger.info(f"Average assessed value: ${avg_value:,.2f}" if avg_value else "N/A")
        logger.info("=" * 50)

    return True


def send_enrichment_alert(**context):
    """Send alert if enrichment failed"""
    logger.error("Enrichment workflow failed!")

    ti = context['ti']
    dag_run = context['dag_run']

    logger.error(f"DAG Run ID: {dag_run.run_id}")
    logger.error(f"Execution Date: {context['execution_date']}")

    # In production, send actual alerts (Slack, PagerDuty, etc.)

    return True


# Define the DAG
with DAG(
    dag_id=DAG_ID,
    default_args=default_args,
    description='Enrich property data with assessor and census information',
    schedule_interval=SCHEDULE_INTERVAL,
    start_date=START_DATE,
    catchup=False,
    tags=['pipeline', 'enrichment'],
    params={
        'batch_size': BATCH_SIZE,
        'county': 'clark_nv',
    }
) as dag:

    # Task 1: Fetch prospects ready for enrichment
    fetch_prospects = PythonOperator(
        task_id='fetch_ready_prospects',
        python_callable=fetch_ready_prospects,
        provide_context=True,
    )

    # Task 2: Run enrichment agent in Kubernetes
    run_enrichment = KubernetesPodOperator(
        task_id='run_enrichment_agent',
        name='enrichment-agent',
        namespace=K8S_NAMESPACE,
        image=ENRICHMENT_IMAGE,
        cmds=['python', '-m', 'enrichment_agent.enrichment_agent'],
        arguments=[
            '--prospect-ids={{ ti.xcom_pull(task_ids="fetch_ready_prospects", key="prospect_ids") | join(",") }}',
            '--db-dsn={{ var.value.get("DB_DSN", "") }}',
            '--census-api-key={{ var.value.get("CENSUS_API_KEY", "") }}',
            '--county-config=/opt/airflow/config/counties/{{ params.county }}.yaml',
        ],
        env_vars={
            'DB_DSN': os.getenv('DB_DSN', ''),
            'CENSUS_API_KEY': CENSUS_API_KEY,
            'LOG_LEVEL': 'INFO',
        },
        # Resource limits
        container_resources=k8s.V1ResourceRequirements(
            requests={'memory': '256Mi', 'cpu': '250m'},
            limits={'memory': '1Gi', 'cpu': '1000m'},
        ),
        # Pod configuration
        is_delete_operator_pod=True,
        get_logs=True,
        log_events_on_failure=True,
        startup_timeout_seconds=180,
        # Retry configuration
        retries=2,
        retry_delay=timedelta(minutes=5),
    )

    # Task 3: Validate enrichment results
    validate_results = PythonOperator(
        task_id='validate_enrichment',
        python_callable=validate_enrichment,
        provide_context=True,
    )

    # Task 4: Collect metrics
    collect_metrics = PythonOperator(
        task_id='collect_metrics',
        python_callable=collect_enrichment_metrics,
        provide_context=True,
    )

    # Task 5: Update prospect status
    update_status = PostgresOperator(
        task_id='update_prospect_status',
        postgres_conn_id=POSTGRES_CONN_ID,
        sql="""
            -- Update prospects to 'enriched' status
            UPDATE prospect_queue
            SET status = 'enriched', updated_at = NOW()
            WHERE id IN (
                SELECT prospect_id
                FROM property_enrichment
                WHERE created_at >= NOW() - INTERVAL '2 hours'
            )
            AND status = 'ready';
        """
    )

    # Task 6: Alert on failure
    alert_on_failure = PythonOperator(
        task_id='send_failure_alert',
        python_callable=send_enrichment_alert,
        provide_context=True,
        trigger_rule=TriggerRule.ONE_FAILED,
    )

    # Define task dependencies
    fetch_prospects >> run_enrichment >> validate_results >> collect_metrics >> update_status

    # Alert task triggers on any failure
    [fetch_prospects, run_enrichment, validate_results, collect_metrics] >> alert_on_failure
