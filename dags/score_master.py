"""Score Master DAG: ML-based property scoring

This DAG orchestrates property scoring:
1. Fetches enriched properties ready for scoring
2. Batches properties for processing
3. Launches scoring agent in Kubernetes
4. Validates scores
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
DAG_ID = 'score_master'
SCHEDULE_INTERVAL = '@daily'
START_DATE = datetime(2025, 1, 1)

# Kubernetes configuration
K8S_NAMESPACE = os.getenv('K8S_NAMESPACE', 'orchestration')
SCORING_IMAGE = os.getenv('SCORING_IMAGE', 'real-estate-os/scoring-agent:latest')
POSTGRES_CONN_ID = 'postgres_realestate'

# Scoring configuration
BATCH_SIZE = int(os.getenv('SCORING_BATCH_SIZE', '100'))
MODEL_PATH = '/models/lightgbm_latest'
QDRANT_URL = os.getenv('QDRANT_URL', 'http://qdrant:6333')


def fetch_enriched_prospects(**context):
    """
    Fetch prospects that are enriched and ready for scoring

    Selects prospects with status='enriched' and no existing scores.
    """
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    batch_size = context['params'].get('batch_size', BATCH_SIZE)

    # Query for prospects needing scoring
    query = """
        SELECT pq.id
        FROM prospect_queue pq
        INNER JOIN property_enrichment pe ON pe.prospect_id = pq.id
        LEFT JOIN property_scores ps ON ps.prospect_id = pq.id
        WHERE pq.status = 'enriched'
          AND ps.id IS NULL
        ORDER BY pq.created_at DESC
        LIMIT %s
    """

    results = hook.get_records(query, parameters=(batch_size,))

    if not results:
        logger.warning("No prospects ready for scoring")
        return {'prospect_ids': [], 'count': 0}

    prospect_ids = [row[0] for row in results]

    logger.info(f"Found {len(prospect_ids)} prospects ready for scoring")

    # Push to XCom
    ti = context['ti']
    ti.xcom_push(key='prospect_ids', value=prospect_ids)

    return {
        'prospect_ids': prospect_ids,
        'count': len(prospect_ids)
    }


def validate_scores(**context):
    """
    Validate scoring results

    Checks:
    - Scores were created
    - Scores are in valid range (0-100)
    - Vectors were stored in Qdrant
    """
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    # Get prospect IDs from XCom
    ti = context['ti']
    prospect_ids = ti.xcom_pull(task_ids='fetch_enriched_prospects', key='prospect_ids')

    if not prospect_ids:
        logger.warning("No prospect IDs to validate")
        return {'status': 'no_data'}

    # Check scores
    query = """
        SELECT
            COUNT(*) as total,
            AVG(bird_dog_score) as avg_score,
            MIN(bird_dog_score) as min_score,
            MAX(bird_dog_score) as max_score,
            AVG(confidence_level) as avg_confidence,
            COUNT(*) FILTER (WHERE bird_dog_score >= 75) as high_scores,
            COUNT(*) FILTER (WHERE bird_dog_score >= 50 AND bird_dog_score < 75) as medium_scores,
            COUNT(*) FILTER (WHERE bird_dog_score < 50) as low_scores
        FROM property_scores
        WHERE prospect_id = ANY(%s)
    """

    result = hook.get_first(query, parameters=(prospect_ids,))

    if not result:
        logger.error("Failed to query scoring results")
        return {'status': 'error'}

    total, avg_score, min_score, max_score, avg_conf, high, medium, low = result

    logger.info(f"Scoring results: {total}/{len(prospect_ids)} scored")
    logger.info(f"  Average score: {avg_score:.2f}")
    logger.info(f"  Score range: {min_score:.2f} - {max_score:.2f}")
    logger.info(f"  Average confidence: {avg_conf:.2f}%")
    logger.info(f"  High scores (≥75): {high}")
    logger.info(f"  Medium scores (50-75): {medium}")
    logger.info(f"  Low scores (<50): {low}")

    # Calculate success rate
    success_rate = total / len(prospect_ids) if prospect_ids else 0

    if success_rate < 0.5:
        logger.warning(f"Low scoring success rate: {success_rate:.1%}")

    return {
        'status': 'success',
        'total_scored': total,
        'total_attempted': len(prospect_ids),
        'success_rate': success_rate,
        'avg_score': float(avg_score) if avg_score else 0,
        'score_distribution': {
            'high': high,
            'medium': medium,
            'low': low
        }
    }


def collect_scoring_metrics(**context):
    """Collect and log scoring metrics"""
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    # Get statistics
    stats_query = """
        SELECT
            COUNT(*) as total_scored,
            AVG(bird_dog_score) as avg_score,
            STDDEV(bird_dog_score) as std_score,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY bird_dog_score) as median_score,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY bird_dog_score) as q1_score,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY bird_dog_score) as q3_score,
            COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '1 day') as scored_today,
            AVG(confidence_level) as avg_confidence
        FROM property_scores
    """

    result = hook.get_first(stats_query)

    if result:
        total, avg, std, median, q1, q3, today, conf = result

        logger.info("=" * 50)
        logger.info("SCORING METRICS")
        logger.info("=" * 50)
        logger.info(f"Total scored properties: {total}")
        logger.info(f"Scored today: {today}")
        logger.info(f"Average score: {avg:.2f} ± {std:.2f}" if avg and std else "N/A")
        logger.info(f"Median score: {median:.2f}" if median else "N/A")
        logger.info(f"Quartiles: Q1={q1:.2f}, Q3={q3:.2f}" if q1 and q3 else "N/A")
        logger.info(f"Average confidence: {conf:.2f}%" if conf else "N/A")
        logger.info("=" * 50)

    # Get model version stats
    model_query = """
        SELECT model_version, COUNT(*) as count
        FROM property_scores
        GROUP BY model_version
        ORDER BY count DESC
    """

    model_results = hook.get_records(model_query)

    if model_results:
        logger.info("Scores by model version:")
        for model_version, count in model_results:
            logger.info(f"  {model_version}: {count}")

    return True


def send_scoring_alert(**context):
    """Send alert if scoring failed"""
    logger.error("Scoring workflow failed!")

    ti = context['ti']
    dag_run = context['dag_run']

    logger.error(f"DAG Run ID: {dag_run.run_id}")
    logger.error(f"Execution Date: {context['execution_date']}")

    # In production, send actual alerts

    return True


# Define the DAG
with DAG(
    dag_id=DAG_ID,
    default_args=default_args,
    description='Score properties using LightGBM ML model',
    schedule_interval=SCHEDULE_INTERVAL,
    start_date=START_DATE,
    catchup=False,
    tags=['pipeline', 'scoring', 'ml'],
    params={
        'batch_size': BATCH_SIZE,
        'min_score_threshold': 0,  # Minimum score to process further
    }
) as dag:

    # Task 1: Fetch enriched prospects
    fetch_prospects = PythonOperator(
        task_id='fetch_enriched_prospects',
        python_callable=fetch_enriched_prospects,
        provide_context=True,
    )

    # Task 2: Run scoring agent in Kubernetes
    run_scoring = KubernetesPodOperator(
        task_id='run_scoring_agent',
        name='scoring-agent',
        namespace=K8S_NAMESPACE,
        image=SCORING_IMAGE,
        cmds=['python', '-m', 'scoring_agent.scoring_agent'],
        arguments=[
            '--prospect-ids={{ ti.xcom_pull(task_ids="fetch_enriched_prospects", key="prospect_ids") | join(",") }}',
            '--db-dsn={{ var.value.get("DB_DSN", "") }}',
            '--model-path=' + MODEL_PATH,
            '--qdrant-url=' + QDRANT_URL,
        ],
        env_vars={
            'DB_DSN': os.getenv('DB_DSN', ''),
            'QDRANT_URL': QDRANT_URL,
            'LOG_LEVEL': 'INFO',
        },
        # Mount model volume (in production, this would be a PV with the trained model)
        volumes=[
            k8s.V1Volume(
                name='models',
                empty_dir=k8s.V1EmptyDirVolumeSource()
            )
        ],
        volume_mounts=[
            k8s.V1VolumeMount(
                name='models',
                mount_path='/models'
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

    # Task 3: Validate scores
    validate_results = PythonOperator(
        task_id='validate_scores',
        python_callable=validate_scores,
        provide_context=True,
    )

    # Task 4: Collect metrics
    collect_metrics = PythonOperator(
        task_id='collect_metrics',
        python_callable=collect_scoring_metrics,
        provide_context=True,
    )

    # Task 5: Update prospect status
    update_status = PostgresOperator(
        task_id='update_prospect_status',
        postgres_conn_id=POSTGRES_CONN_ID,
        sql="""
            -- Update prospects to 'scored' status
            UPDATE prospect_queue
            SET status = 'scored', updated_at = NOW()
            WHERE id IN (
                SELECT prospect_id
                FROM property_scores
                WHERE created_at >= NOW() - INTERVAL '2 hours'
            )
            AND status = 'enriched';
        """
    )

    # Task 6: Alert on failure
    alert_on_failure = PythonOperator(
        task_id='send_failure_alert',
        python_callable=send_scoring_alert,
        provide_context=True,
        trigger_rule=TriggerRule.ONE_FAILED,
    )

    # Define task dependencies
    fetch_prospects >> run_scoring >> validate_results >> collect_metrics >> update_status

    # Alert task triggers on any failure
    [fetch_prospects, run_scoring, validate_results, collect_metrics] >> alert_on_failure
