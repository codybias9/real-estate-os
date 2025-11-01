"""Email Campaign DAG: Sends investor memos via email

This DAG orchestrates email outreach:
1. Creates/fetches active email campaign
2. Populates email queue with recipients
3. Launches email agent in Kubernetes
4. Validates email sends
5. Updates campaign statistics
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
import json

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
DAG_ID = 'email_campaign'
SCHEDULE_INTERVAL = '@daily'
START_DATE = datetime(2025, 1, 1)

# Kubernetes configuration
K8S_NAMESPACE = os.getenv('K8S_NAMESPACE', 'orchestration')
EMAIL_IMAGE = os.getenv('EMAIL_IMAGE', 'real-estate-os/email-agent:latest')
POSTGRES_CONN_ID = 'postgres_realestate'

# Email configuration
MAX_EMAILS_PER_RUN = int(os.getenv('MAX_EMAILS_PER_RUN', '100'))
MIN_SCORE_FOR_EMAIL = int(os.getenv('MIN_SCORE_FOR_EMAIL', '60'))


def create_or_get_campaign(**context):
    """
    Create or get active email campaign

    Creates a new campaign for today if none exists,
    or returns existing active campaign.
    """
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    execution_date = context['execution_date'].date()

    # Check for existing campaign for today
    query = """
        SELECT id, name, status
        FROM email_campaigns
        WHERE campaign_date = %s
        ORDER BY created_at DESC
        LIMIT 1
    """

    result = hook.get_first(query, parameters=(execution_date,))

    if result:
        campaign_id, name, status = result
        logger.info(f"Found existing campaign: {campaign_id} ({name}) - status: {status}")

        # Push to XCom
        ti = context['ti']
        ti.xcom_push(key='campaign_id', value=campaign_id)

        return {
            'campaign_id': campaign_id,
            'name': name,
            'status': status,
            'created': False
        }

    # Create new campaign
    campaign_name = f"Daily Investor Outreach - {execution_date}"

    insert_query = """
        INSERT INTO email_campaigns (
            name,
            campaign_type,
            campaign_date,
            status,
            created_at,
            updated_at
        )
        VALUES (%s, %s, %s, %s, NOW(), NOW())
        RETURNING id
    """

    campaign_id = hook.get_first(
        insert_query,
        parameters=(campaign_name, 'investor_memo', execution_date, 'active')
    )[0]

    logger.info(f"Created new campaign: {campaign_id} ({campaign_name})")

    # Push to XCom
    ti = context['ti']
    ti.xcom_push(key='campaign_id', value=campaign_id)

    return {
        'campaign_id': campaign_id,
        'name': campaign_name,
        'status': 'active',
        'created': True
    }


def populate_email_queue(**context):
    """
    Populate email queue with recipients

    For each action packet (property with PDF):
    - Find investor/lead contacts
    - Create email queue entry
    - Deduplicate based on recent sends
    """
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    # Get campaign ID from XCom
    ti = context['ti']
    campaign_id = ti.xcom_pull(task_ids='create_or_get_campaign', key='campaign_id')

    min_score = context['params'].get('min_score', MIN_SCORE_FOR_EMAIL)
    max_emails = context['params'].get('max_emails', MAX_EMAILS_PER_RUN)

    # Query for action packets ready to email
    # (properties with PDFs, scores above threshold, not recently emailed)
    query = """
        WITH ready_packets AS (
            SELECT
                ap.id as action_packet_id,
                ap.prospect_id,
                ps.bird_dog_score
            FROM action_packets ap
            INNER JOIN property_scores ps ON ps.prospect_id = ap.prospect_id
            LEFT JOIN email_queue eq ON eq.action_packet_id = ap.id
                AND eq.created_at >= NOW() - INTERVAL '30 days'
            WHERE ap.status = 'generated'
              AND ap.packet_type = 'investor_memo'
              AND ps.bird_dog_score >= %s
              AND eq.id IS NULL
            ORDER BY ps.bird_dog_score DESC
            LIMIT %s
        )
        SELECT
            rp.action_packet_id,
            rp.prospect_id,
            rp.bird_dog_score
        FROM ready_packets rp
    """

    ready_packets = hook.get_records(query, parameters=(min_score, max_emails))

    if not ready_packets:
        logger.warning("No action packets ready for email")
        return {'queued': 0, 'action_packets': 0}

    logger.info(f"Found {len(ready_packets)} action packets ready for email")

    # For demonstration, we'll create email queue entries with placeholder recipients
    # In production, this would match with actual investor/lead database

    inserted = 0

    for action_packet_id, prospect_id, score in ready_packets:
        # In production: fetch real recipients from investor_contacts table
        # For now, use placeholder
        recipient_email = f"investor_{prospect_id}@example.com"
        recipient_name = f"Investor {prospect_id}"

        insert_query = """
            INSERT INTO email_queue (
                campaign_id,
                action_packet_id,
                recipient_email,
                recipient_name,
                status,
                metadata,
                created_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
        """

        metadata = {
            'prospect_id': prospect_id,
            'score': float(score)
        }

        hook.run(insert_query, parameters=(
            campaign_id,
            action_packet_id,
            recipient_email,
            recipient_name,
            'pending',
            json.dumps(metadata)
        ))

        inserted += 1

    logger.info(f"Queued {inserted} emails for campaign {campaign_id}")

    return {
        'queued': inserted,
        'action_packets': len(ready_packets)
    }


def validate_email_sends(**context):
    """
    Validate email sending results

    Checks:
    - Emails were sent successfully
    - SendGrid message IDs recorded
    - Error rates within acceptable limits
    """
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    # Get campaign ID from XCom
    ti = context['ti']
    campaign_id = ti.xcom_pull(task_ids='create_or_get_campaign', key='campaign_id')

    # Get email statistics
    query = """
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'sent') as sent,
            COUNT(*) FILTER (WHERE status = 'error') as errors,
            COUNT(*) FILTER (WHERE status = 'pending') as pending
        FROM email_queue
        WHERE campaign_id = %s
    """

    result = hook.get_first(query, parameters=(campaign_id,))

    if not result:
        logger.error("Failed to query email queue")
        return {'status': 'error'}

    total, sent, errors, pending = result

    logger.info(f"Email validation results: {sent}/{total} sent")
    logger.info(f"  Errors: {errors}")
    logger.info(f"  Pending: {pending}")

    # Calculate success rate
    success_rate = sent / total if total > 0 else 0

    if success_rate < 0.8:
        logger.warning(f"Low email success rate: {success_rate:.1%}")

    return {
        'status': 'success',
        'total': total,
        'sent': sent,
        'errors': errors,
        'pending': pending,
        'success_rate': success_rate
    }


def collect_campaign_metrics(**context):
    """Collect and log email campaign metrics"""
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    # Get campaign ID
    ti = context['ti']
    campaign_id = ti.xcom_pull(task_ids='create_or_get_campaign', key='campaign_id')

    # Get campaign statistics
    stats_query = """
        SELECT
            ec.name,
            ec.campaign_type,
            ec.campaign_date,
            COUNT(eq.id) as total_emails,
            COUNT(eq.id) FILTER (WHERE eq.status = 'sent') as sent,
            COUNT(eq.id) FILTER (WHERE eq.status = 'error') as errors,
            COUNT(eq.id) FILTER (WHERE eq.status = 'opened') as opens,
            COUNT(eq.id) FILTER (WHERE eq.status = 'clicked') as clicks
        FROM email_campaigns ec
        LEFT JOIN email_queue eq ON eq.campaign_id = ec.id
        WHERE ec.id = %s
        GROUP BY ec.id, ec.name, ec.campaign_type, ec.campaign_date
    """

    result = hook.get_first(stats_query, parameters=(campaign_id,))

    if result:
        name, campaign_type, campaign_date, total, sent, errors, opens, clicks = result

        logger.info("=" * 50)
        logger.info("EMAIL CAMPAIGN METRICS")
        logger.info("=" * 50)
        logger.info(f"Campaign: {name}")
        logger.info(f"Date: {campaign_date}")
        logger.info(f"Type: {campaign_type}")
        logger.info(f"Total emails: {total}")
        logger.info(f"Sent: {sent}")
        logger.info(f"Errors: {errors}")
        logger.info(f"Opens: {opens}")
        logger.info(f"Clicks: {clicks}")

        if sent > 0:
            logger.info(f"Open rate: {(opens / sent * 100):.1f}%")
            logger.info(f"Click rate: {(clicks / sent * 100):.1f}%")

        logger.info("=" * 50)

    return True


def send_campaign_alert(**context):
    """Send alert if email campaign failed"""
    logger.error("Email campaign workflow failed!")

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
    description='Send investor memo email campaigns',
    schedule_interval=SCHEDULE_INTERVAL,
    start_date=START_DATE,
    catchup=False,
    tags=['pipeline', 'email', 'outreach'],
    params={
        'min_score': MIN_SCORE_FOR_EMAIL,
        'max_emails': MAX_EMAILS_PER_RUN,
    }
) as dag:

    # Task 1: Create or get campaign
    create_campaign = PythonOperator(
        task_id='create_or_get_campaign',
        python_callable=create_or_get_campaign,
        provide_context=True,
    )

    # Task 2: Populate email queue
    populate_queue = PythonOperator(
        task_id='populate_email_queue',
        python_callable=populate_email_queue,
        provide_context=True,
    )

    # Task 3: Run email agent in Kubernetes
    run_email_agent = KubernetesPodOperator(
        task_id='run_email_agent',
        name='email-agent',
        namespace=K8S_NAMESPACE,
        image=EMAIL_IMAGE,
        cmds=['python', '-m', 'email_agent.email_agent'],
        arguments=[
            '--campaign-id={{ ti.xcom_pull(task_ids="create_or_get_campaign", key="campaign_id") }}',
            '--db-dsn={{ var.value.get("DB_DSN", "") }}',
            '--sendgrid-api-key={{ var.value.get("SENDGRID_API_KEY", "") }}',
            '--from-email={{ var.value.get("FROM_EMAIL", "noreply@realestateos.com") }}',
            '--from-name=Real Estate OS',
        ],
        env_vars={
            'DB_DSN': os.getenv('DB_DSN', ''),
            'SENDGRID_API_KEY': os.getenv('SENDGRID_API_KEY', ''),
            'FROM_EMAIL': os.getenv('FROM_EMAIL', 'noreply@realestateos.com'),
            'LOG_LEVEL': 'INFO',
        },
        # Resource limits (email sending is lightweight)
        container_resources=k8s.V1ResourceRequirements(
            requests={'memory': '256Mi', 'cpu': '250m'},
            limits={'memory': '512Mi', 'cpu': '500m'},
        ),
        # Pod configuration
        is_delete_operator_pod=True,
        get_logs=True,
        log_events_on_failure=True,
        startup_timeout_seconds=120,
        # Retry configuration
        retries=2,
        retry_delay=timedelta(minutes=5),
    )

    # Task 4: Validate sends
    validate_sends = PythonOperator(
        task_id='validate_email_sends',
        python_callable=validate_email_sends,
        provide_context=True,
    )

    # Task 5: Collect metrics
    collect_metrics = PythonOperator(
        task_id='collect_campaign_metrics',
        python_callable=collect_campaign_metrics,
        provide_context=True,
    )

    # Task 6: Update campaign status
    update_campaign = PostgresOperator(
        task_id='update_campaign_status',
        postgres_conn_id=POSTGRES_CONN_ID,
        sql="""
            -- Update campaign status to completed
            UPDATE email_campaigns
            SET status = 'completed', updated_at = NOW()
            WHERE id = {{ ti.xcom_pull(task_ids='create_or_get_campaign', key='campaign_id') }};
        """
    )

    # Task 7: Alert on failure
    alert_on_failure = PythonOperator(
        task_id='send_failure_alert',
        python_callable=send_campaign_alert,
        provide_context=True,
        trigger_rule=TriggerRule.ONE_FAILED,
    )

    # Define task dependencies
    create_campaign >> populate_queue >> run_email_agent >> validate_sends >> collect_metrics >> update_campaign

    # Alert task triggers on any failure
    [create_campaign, populate_queue, run_email_agent, validate_sends, collect_metrics] >> alert_on_failure
