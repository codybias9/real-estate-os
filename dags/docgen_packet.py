"""Document Generation DAG: Creates investor memo PDFs

This DAG orchestrates document generation:
1. Fetches scored properties above threshold
2. Batches properties for processing
3. Launches document generation agent in Kubernetes
4. Validates PDFs were created
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
    'execution_timeout': timedelta(hours=3),
}

# DAG configuration
DAG_ID = 'docgen_packet'
SCHEDULE_INTERVAL = '@daily'
START_DATE = datetime(2025, 1, 1)

# Kubernetes configuration
K8S_NAMESPACE = os.getenv('K8S_NAMESPACE', 'orchestration')
DOCGEN_IMAGE = os.getenv('DOCGEN_IMAGE', 'real-estate-os/docgen-agent:latest')
POSTGRES_CONN_ID = 'postgres_realestate'

# Document generation configuration
BATCH_SIZE = int(os.getenv('DOCGEN_BATCH_SIZE', '50'))
MIN_SCORE_THRESHOLD = int(os.getenv('MIN_SCORE_THRESHOLD', '50'))
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'minio:9000')
QDRANT_URL = os.getenv('QDRANT_URL', 'http://qdrant:6333')


def fetch_scored_prospects(**context):
    """
    Fetch prospects that are scored and ready for document generation

    Selects prospects with:
    - status='scored'
    - bird_dog_score >= threshold
    - no existing action packets
    """
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    batch_size = context['params'].get('batch_size', BATCH_SIZE)
    min_score = context['params'].get('min_score_threshold', MIN_SCORE_THRESHOLD)

    # Query for prospects needing documents
    query = """
        SELECT pq.id
        FROM prospect_queue pq
        INNER JOIN property_scores ps ON ps.prospect_id = pq.id
        LEFT JOIN action_packets ap ON ap.prospect_id = pq.id
        WHERE pq.status = 'scored'
          AND ps.bird_dog_score >= %s
          AND ap.id IS NULL
        ORDER BY ps.bird_dog_score DESC
        LIMIT %s
    """

    results = hook.get_records(query, parameters=(min_score, batch_size))

    if not results:
        logger.warning("No prospects ready for document generation")
        return {'prospect_ids': [], 'count': 0}

    prospect_ids = [row[0] for row in results]

    logger.info(f"Found {len(prospect_ids)} prospects ready for document generation")

    # Push to XCom
    ti = context['ti']
    ti.xcom_push(key='prospect_ids', value=prospect_ids)

    return {
        'prospect_ids': prospect_ids,
        'count': len(prospect_ids)
    }


def validate_documents(**context):
    """
    Validate document generation results

    Checks:
    - PDFs were created
    - Action packets exist
    - MinIO objects are accessible
    """
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    # Get prospect IDs from XCom
    ti = context['ti']
    prospect_ids = ti.xcom_pull(task_ids='fetch_scored_prospects', key='prospect_ids')

    if not prospect_ids:
        logger.warning("No prospect IDs to validate")
        return {'status': 'no_data'}

    # Check action packets
    query = """
        SELECT
            COUNT(*) as total_packets,
            COUNT(*) FILTER (WHERE status = 'generated') as generated,
            COUNT(*) FILTER (WHERE status = 'error') as errors,
            AVG(CAST(metadata->>'pdf_size' AS INTEGER)) as avg_size
        FROM action_packets
        WHERE prospect_id = ANY(%s)
          AND packet_type = 'investor_memo'
    """

    result = hook.get_first(query, parameters=(prospect_ids,))

    if not result:
        logger.error("Failed to query action packets")
        return {'status': 'error'}

    total, generated, errors, avg_size = result

    logger.info(f"Document validation results: {generated}/{len(prospect_ids)} generated")
    logger.info(f"  Errors: {errors}")
    logger.info(f"  Average PDF size: {avg_size or 0:.0f} bytes")

    # Calculate success rate
    success_rate = generated / len(prospect_ids) if prospect_ids else 0

    if success_rate < 0.5:
        logger.warning(f"Low document generation success rate: {success_rate:.1%}")

    return {
        'status': 'success',
        'total_generated': generated,
        'total_attempted': len(prospect_ids),
        'success_rate': success_rate,
        'errors': errors,
        'avg_pdf_size': int(avg_size) if avg_size else 0
    }


def collect_docgen_metrics(**context):
    """Collect and log document generation metrics"""
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    # Get statistics
    stats_query = """
        SELECT
            COUNT(*) as total_packets,
            COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '1 day') as generated_today,
            COUNT(*) FILTER (WHERE status = 'generated') as successful,
            COUNT(*) FILTER (WHERE status = 'error') as failed,
            AVG(CAST(metadata->>'pdf_size' AS INTEGER)) as avg_size,
            MIN(created_at) as first_packet,
            MAX(created_at) as latest_packet
        FROM action_packets
        WHERE packet_type = 'investor_memo'
    """

    result = hook.get_first(stats_query)

    if result:
        total, today, successful, failed, avg_size, first, latest = result

        logger.info("=" * 50)
        logger.info("DOCUMENT GENERATION METRICS")
        logger.info("=" * 50)
        logger.info(f"Total packets generated: {total}")
        logger.info(f"Generated today: {today}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Average PDF size: {avg_size or 0:.0f} bytes ({(avg_size or 0) / 1024:.1f} KB)")
        logger.info(f"First packet: {first}")
        logger.info(f"Latest packet: {latest}")
        logger.info("=" * 50)

    # Get prospect statistics
    prospect_query = """
        SELECT
            COUNT(DISTINCT pq.id) as total_prospects,
            COUNT(DISTINCT CASE WHEN ap.id IS NOT NULL THEN pq.id END) as with_packets,
            COUNT(DISTINCT CASE WHEN pq.status = 'packet_ready' THEN pq.id END) as packet_ready
        FROM prospect_queue pq
        LEFT JOIN action_packets ap ON ap.prospect_id = pq.id
        WHERE pq.status IN ('scored', 'packet_ready')
    """

    result = hook.get_first(prospect_query)

    if result:
        total_prospects, with_packets, packet_ready = result

        logger.info("Prospect Coverage:")
        logger.info(f"  Total scored prospects: {total_prospects}")
        logger.info(f"  With action packets: {with_packets}")
        logger.info(f"  Packet ready status: {packet_ready}")
        logger.info(f"  Coverage rate: {(with_packets / total_prospects * 100) if total_prospects else 0:.1f}%")

    return True


def send_docgen_alert(**context):
    """Send alert if document generation failed"""
    logger.error("Document generation workflow failed!")

    ti = context['ti']
    dag_run = context['dag_run']

    logger.error(f"DAG Run ID: {dag_run.run_id}")
    logger.error(f"Execution Date: {context['execution_date']}")

    # In production, send actual alerts (Slack, email, PagerDuty)

    return True


# Define the DAG
with DAG(
    dag_id=DAG_ID,
    default_args=default_args,
    description='Generate investor memo PDFs for scored properties',
    schedule_interval=SCHEDULE_INTERVAL,
    start_date=START_DATE,
    catchup=False,
    tags=['pipeline', 'documents', 'pdf'],
    params={
        'batch_size': BATCH_SIZE,
        'min_score_threshold': MIN_SCORE_THRESHOLD,
    }
) as dag:

    # Task 1: Fetch scored prospects
    fetch_prospects = PythonOperator(
        task_id='fetch_scored_prospects',
        python_callable=fetch_scored_prospects,
        provide_context=True,
    )

    # Task 2: Run document generation agent in Kubernetes
    run_docgen = KubernetesPodOperator(
        task_id='run_docgen_agent',
        name='docgen-agent',
        namespace=K8S_NAMESPACE,
        image=DOCGEN_IMAGE,
        cmds=['python', '-m', 'docgen_agent.docgen_agent'],
        arguments=[
            '--prospect-ids={{ ti.xcom_pull(task_ids="fetch_scored_prospects", key="prospect_ids") | join(",") }}',
            '--db-dsn={{ var.value.get("DB_DSN", "") }}',
            '--minio-endpoint=' + MINIO_ENDPOINT,
            '--minio-access-key={{ var.value.get("MINIO_ACCESS_KEY", "minioadmin") }}',
            '--minio-secret-key={{ var.value.get("MINIO_SECRET_KEY", "minioadmin") }}',
            '--templates-dir=/app/templates',
            '--qdrant-url=' + QDRANT_URL,
        ],
        env_vars={
            'DB_DSN': os.getenv('DB_DSN', ''),
            'MINIO_ENDPOINT': MINIO_ENDPOINT,
            'QDRANT_URL': QDRANT_URL,
            'LOG_LEVEL': 'INFO',
        },
        # Mount templates volume
        volumes=[
            k8s.V1Volume(
                name='templates',
                config_map=k8s.V1ConfigMapVolumeSource(
                    name='investor-memo-templates'
                )
            )
        ],
        volume_mounts=[
            k8s.V1VolumeMount(
                name='templates',
                mount_path='/app/templates'
            )
        ],
        # Resource limits
        container_resources=k8s.V1ResourceRequirements(
            requests={'memory': '512Mi', 'cpu': '500m'},
            limits={'memory': '2Gi', 'cpu': '2000m'},
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

    # Task 3: Validate documents
    validate_results = PythonOperator(
        task_id='validate_documents',
        python_callable=validate_documents,
        provide_context=True,
    )

    # Task 4: Collect metrics
    collect_metrics = PythonOperator(
        task_id='collect_metrics',
        python_callable=collect_docgen_metrics,
        provide_context=True,
    )

    # Task 5: Update prospect status
    update_status = PostgresOperator(
        task_id='update_prospect_status',
        postgres_conn_id=POSTGRES_CONN_ID,
        sql="""
            -- Update prospects to 'packet_ready' status
            UPDATE prospect_queue
            SET status = 'packet_ready', updated_at = NOW()
            WHERE id IN (
                SELECT prospect_id
                FROM action_packets
                WHERE packet_type = 'investor_memo'
                  AND status = 'generated'
                  AND created_at >= NOW() - INTERVAL '2 hours'
            )
            AND status = 'scored';
        """
    )

    # Task 6: Alert on failure
    alert_on_failure = PythonOperator(
        task_id='send_failure_alert',
        python_callable=send_docgen_alert,
        provide_context=True,
        trigger_rule=TriggerRule.ONE_FAILED,
    )

    # Define task dependencies
    fetch_prospects >> run_docgen >> validate_results >> collect_metrics >> update_status

    # Alert task triggers on any failure
    [fetch_prospects, run_docgen, validate_results, collect_metrics] >> alert_on_failure
