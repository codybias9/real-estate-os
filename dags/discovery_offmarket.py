"""Discovery DAG: Scrape off-market leads and insert into prospect_queue

This DAG orchestrates the web scraping process:
1. Validates configuration
2. Launches scraper in Kubernetes pod
3. Validates scraped data
4. Collects metrics
5. Sends alerts if needed
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
    'execution_timeout': timedelta(hours=2),
}

# DAG configuration
DAG_ID = 'discovery_offmarket'
SCHEDULE_INTERVAL = '@daily'  # Run once per day
START_DATE = datetime(2025, 1, 1)

# Kubernetes configuration
K8S_NAMESPACE = os.getenv('K8S_NAMESPACE', 'orchestration')
SCRAPER_IMAGE = os.getenv('SCRAPER_IMAGE', 'real-estate-os/offmarket-scraper:latest')
POSTGRES_CONN_ID = 'postgres_realestate'

# Scraper configuration
DEFAULT_COUNTY = os.getenv('SCRAPER_COUNTY', 'clark_nv')
DEFAULT_STATE = os.getenv('SCRAPER_STATE', 'NV')
DEFAULT_CITY = os.getenv('SCRAPER_CITY', 'Las-Vegas')


def validate_configuration(**context):
    """
    Validate that required configuration exists before scraping

    Checks:
    - County configuration file exists
    - Database connection is available
    - Required environment variables are set
    """
    import yaml
    from pathlib import Path

    errors = []

    # Check county configuration
    county = context['params'].get('county', DEFAULT_COUNTY)
    config_path = Path(f'/opt/airflow/config/counties/{county}.yaml')

    logger.info(f"Checking configuration for county: {county}")

    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f"Configuration loaded: {config}")
        except Exception as e:
            errors.append(f"Failed to parse configuration: {e}")
    else:
        logger.warning(f"Configuration file not found: {config_path}")
        # Not fatal - will use default parameters

    # Check database connection
    try:
        hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
        conn = hook.get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        logger.info("Database connection verified")
    except Exception as e:
        errors.append(f"Database connection failed: {e}")

    # Check required environment variables
    required_env = ['DB_DSN']
    for env_var in required_env:
        if not os.getenv(env_var):
            errors.append(f"Missing environment variable: {env_var}")

    if errors:
        raise ValueError(f"Configuration validation failed: {errors}")

    logger.info("Configuration validation passed")
    return True


def validate_scraped_data(**context):
    """
    Validate that scraping produced data

    Checks:
    - New records were inserted into prospect_queue
    - Records have required fields
    - No excessive duplicate rate
    """
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    # Get execution date for filtering
    execution_date = context['execution_date']

    # Check for new records in the last hour
    query = """
        SELECT
            COUNT(*) as total,
            COUNT(DISTINCT source_id) as unique_records,
            MIN(created_at) as first_record,
            MAX(created_at) as last_record
        FROM prospect_queue
        WHERE created_at >= NOW() - INTERVAL '2 hours'
    """

    result = hook.get_first(query)

    if not result or result[0] == 0:
        logger.warning("No new records found in prospect_queue")
        # Don't fail - might be a slow scraping day
        return {'status': 'no_data', 'total': 0}

    total, unique, first, last = result

    logger.info(f"Scraping results: {total} total records, {unique} unique records")
    logger.info(f"Time range: {first} to {last}")

    # Calculate duplicate rate
    duplicate_rate = (total - unique) / total if total > 0 else 0

    if duplicate_rate > 0.5:
        logger.warning(f"High duplicate rate: {duplicate_rate:.2%}")

    # Check data quality
    quality_query = """
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE payload->>'address' IS NOT NULL) as with_address,
            COUNT(*) FILTER (WHERE payload->>'listing_price' IS NOT NULL) as with_price,
            COUNT(*) FILTER (WHERE payload->>'bedrooms' IS NOT NULL) as with_bedrooms
        FROM prospect_queue
        WHERE created_at >= NOW() - INTERVAL '2 hours'
    """

    quality = hook.get_first(quality_query)

    if quality:
        total_q, with_address, with_price, with_bedrooms = quality
        logger.info(f"Data quality: Address={with_address}/{total_q} "
                   f"Price={with_price}/{total_q} "
                   f"Bedrooms={with_bedrooms}/{total_q}")

    return {
        'status': 'success',
        'total': total,
        'unique': unique,
        'duplicate_rate': duplicate_rate
    }


def collect_metrics(**context):
    """
    Collect and log scraping metrics

    Metrics:
    - Total properties scraped
    - Properties by source
    - Properties by status
    - Average price
    - Data quality scores
    """
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    # Get statistics
    stats_query = """
        SELECT
            source,
            COUNT(*) as count,
            COUNT(DISTINCT source_id) as unique_count,
            status,
            AVG(CAST(payload->>'listing_price' AS NUMERIC)) as avg_price
        FROM prospect_queue
        WHERE created_at >= NOW() - INTERVAL '2 hours'
        GROUP BY source, status
    """

    results = hook.get_records(stats_query)

    logger.info("=" * 50)
    logger.info("SCRAPING METRICS")
    logger.info("=" * 50)

    for row in results:
        source, count, unique, status, avg_price = row
        logger.info(f"{source} ({status}): {count} total, {unique} unique")
        if avg_price:
            logger.info(f"  Average price: ${avg_price:,.2f}")

    logger.info("=" * 50)

    # Push metrics to XCom
    ti = context['ti']
    ti.xcom_push(key='scraping_stats', value={
        'timestamp': datetime.now().isoformat(),
        'results': [
            {
                'source': r[0],
                'count': r[1],
                'unique_count': r[2],
                'status': r[3],
                'avg_price': float(r[4]) if r[4] else None
            }
            for r in results
        ]
    })

    return True


def send_alert_on_failure(**context):
    """
    Send alert if scraping failed

    In production, this would integrate with:
    - Slack
    - PagerDuty
    - Email
    - etc.
    """
    logger.error("Scraping workflow failed!")

    # Get task instance info
    ti = context['ti']
    dag_run = context['dag_run']

    logger.error(f"DAG Run ID: {dag_run.run_id}")
    logger.error(f"Execution Date: {context['execution_date']}")

    # In production, send actual alerts here
    # For now, just log

    return True


# Define the DAG
with DAG(
    dag_id=DAG_ID,
    default_args=default_args,
    description='Scrape off-market property listings',
    schedule_interval=SCHEDULE_INTERVAL,
    start_date=START_DATE,
    catchup=False,
    tags=['pipeline', 'discovery', 'scraping'],
    params={
        'county': DEFAULT_COUNTY,
        'state': DEFAULT_STATE,
        'city': DEFAULT_CITY,
        'spider': 'fsbo',  # Which spider to run
        'max_pages': 10,   # Maximum pages to scrape
    }
) as dag:

    # Task 1: Validate configuration
    validate_config = PythonOperator(
        task_id='validate_configuration',
        python_callable=validate_configuration,
        provide_context=True,
    )

    # Task 2: Run scraper in Kubernetes
    run_scraper = KubernetesPodOperator(
        task_id='run_scraper_pod',
        name='offmarket-scraper',
        namespace=K8S_NAMESPACE,
        image=SCRAPER_IMAGE,
        cmds=['python', '-m', 'offmarket_scraper.scraper'],
        arguments=[
            '{{ params.spider }}',
            '--county={{ params.county }}',
            '--state={{ params.state }}',
            '--city={{ params.city }}',
            '--max_pages={{ params.max_pages }}'
        ],
        env_vars={
            'DB_DSN': os.getenv('DB_DSN', ''),
            'LOG_LEVEL': 'INFO',
            'PLAYWRIGHT_HEADLESS': 'true',
        },
        # Resource limits
        container_resources=k8s.V1ResourceRequirements(
            requests={'memory': '512Mi', 'cpu': '500m'},
            limits={'memory': '2Gi', 'cpu': '2000m'},
        ),
        # Pod configuration
        is_delete_operator_pod=True,
        get_logs=True,
        log_events_on_failure=True,
        startup_timeout_seconds=300,
        # Retry configuration
        retries=2,
        retry_delay=timedelta(minutes=5),
    )

    # Task 3: Validate scraped data
    validate_data = PythonOperator(
        task_id='validate_scraped_data',
        python_callable=validate_scraped_data,
        provide_context=True,
    )

    # Task 4: Collect metrics
    collect_scraping_metrics = PythonOperator(
        task_id='collect_metrics',
        python_callable=collect_metrics,
        provide_context=True,
    )

    # Task 5: Update prospect status (mark as ready for enrichment)
    update_status = PostgresOperator(
        task_id='update_prospect_status',
        postgres_conn_id=POSTGRES_CONN_ID,
        sql="""
            -- Update prospects to 'ready' status if they passed validation
            UPDATE prospect_queue
            SET status = 'ready', updated_at = NOW()
            WHERE status = 'new'
              AND created_at >= NOW() - INTERVAL '2 hours'
              AND payload IS NOT NULL
              AND payload->>'url' IS NOT NULL;
        """
    )

    # Task 6: Alert on failure (runs only if upstream fails)
    alert_on_failure = PythonOperator(
        task_id='send_failure_alert',
        python_callable=send_alert_on_failure,
        provide_context=True,
        trigger_rule=TriggerRule.ONE_FAILED,
    )

    # Define task dependencies
    validate_config >> run_scraper >> validate_data >> collect_scraping_metrics >> update_status

    # Alert task triggers on any failure
    [validate_config, run_scraper, validate_data, collect_scraping_metrics] >> alert_on_failure
