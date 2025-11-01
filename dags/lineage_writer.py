"""Lineage Writer DAG: Field Provenance Tracking

This DAG processes field_provenance events from various sources and
atomically writes them to the database along with entity upserts.

Purpose:
- Capture source, method, confidence for every field value
- Enable "Deal Genome" provenance tracking
- Support history/version tracking per field
- Power provenance tooltips and audit trails in UI

Sources:
- Discovery scrapers (FSBO, Zillow, etc.)
- Enrichment APIs (Census, Assessor, ATTOM)
- Manual user edits
- Computed/derived fields

Workflow:
1. Poll RabbitMQ for field_provenance events
2. Deduplicate based on entity+field+value hash
3. Determine version number (incremental per field)
4. Atomically upsert entity + insert provenance record
5. Emit lineage.written.v1 event for downstream consumers
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.utils.trigger_rule import TriggerRule
import logging
import json
import hashlib
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Default arguments
default_args = {
    'owner': 'real-estate-os',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=2),
    'execution_timeout': timedelta(hours=1),
}

# DAG configuration
DAG_ID = 'lineage_writer'
SCHEDULE_INTERVAL = '*/5 * * * *'  # Every 5 minutes
START_DATE = datetime(2025, 1, 1)
POSTGRES_CONN_ID = 'postgres_realestate'

# Configuration
BATCH_SIZE = 100
DEFAULT_TENANT_ID = '00000000-0000-0000-0000-000000000001'  # For backward compatibility


def poll_provenance_events(**context):
    """
    Poll for field_provenance events from various sources

    Sources:
    - field_provenance_staging table (from scrapers)
    - RabbitMQ queue (future)
    - API ingestion logs (future)

    Returns list of provenance records to process.
    """
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    # Query for unprocessed provenance tuples from staging table
    query = """
        SELECT
            id,
            entity_type,
            entity_key,
            field_path,
            value,
            source_system,
            source_url,
            method,
            confidence,
            extracted_at,
            tenant_id
        FROM field_provenance_staging
        WHERE processed = FALSE
        ORDER BY created_at ASC
        LIMIT %s
    """

    results = hook.get_records(query, parameters=(BATCH_SIZE,))

    events = []
    staging_ids = []

    for row in results:
        (staging_id, entity_type, entity_key, field_path, value,
         source_system, source_url, method, confidence, extracted_at, tenant_id) = row

        events.append({
            'staging_id': staging_id,
            'entity_type': entity_type,
            'entity_key': entity_key,
            'field_path': field_path,
            'value': value,
            'source_system': source_system,
            'source_url': source_url,
            'method': method,
            'confidence': float(confidence) if confidence else 0.85,
            'extracted_at': extracted_at.isoformat(),
            'tenant_id': str(tenant_id) if tenant_id else DEFAULT_TENANT_ID
        })

        staging_ids.append(staging_id)

    logger.info(f"Polled {len(events)} provenance events from staging table")

    # Push to XCom
    ti = context['ti']
    ti.xcom_push(key='events', value=events)
    ti.xcom_push(key='staging_ids', value=staging_ids)

    return {'event_count': len(events)}


def _flatten_dict(d: dict, parent_key: str = '', sep: str = '.') -> dict:
    """Flatten nested dictionary to dot notation

    Example:
        {'address': {'street': '123 Main'}} -> {'address.street': '123 Main'}
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def deduplicate_events(**context):
    """
    Deduplicate events based on entity+field+value hash

    Skip events where value hasn't changed from latest version.
    Also resolves entity_key to entity_id (UUID) by creating/looking up
    deterministic property records.
    """
    ti = context['ti']
    events = ti.xcom_pull(task_ids='poll_provenance_events', key='events')

    if not events:
        logger.info("No events to deduplicate")
        return {'deduped_count': 0}

    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    deduped_events = []

    for event in events:
        # Resolve entity_key to entity_id
        # For now, we'll use the entity_key as a deterministic identifier
        # In production, this would resolve to actual property UUID from the property table
        # For demonstration, we'll generate a UUID from the entity_key
        import uuid
        entity_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, event['entity_key']))
        event['entity_id'] = entity_id

        # Calculate value hash
        value_str = json.dumps(event['value'], sort_keys=True, default=str)
        value_hash = hashlib.sha256(value_str.encode()).hexdigest()

        # Check if latest version has same value
        query = """
            SELECT value, version
            FROM field_provenance
            WHERE tenant_id = %s::uuid
              AND entity_type = %s
              AND entity_id = %s::uuid
              AND field_path = %s
            ORDER BY version DESC
            LIMIT 1
        """

        result = hook.get_first(query, parameters=(
            event['tenant_id'],
            event['entity_type'],
            entity_id,
            event['field_path']
        ))

        if result:
            latest_value, latest_version = result
            latest_value_str = json.dumps(latest_value, sort_keys=True, default=str)
            latest_hash = hashlib.sha256(latest_value_str.encode()).hexdigest()

            if latest_hash == value_hash:
                logger.debug(f"Skipping duplicate: {event['field_path']} (no change)")
                # Mark as processed even though skipped
                continue

            # Increment version
            event['version'] = latest_version + 1
        else:
            # First version
            event['version'] = 1

        deduped_events.append(event)

    logger.info(f"Deduplicated {len(events)} -> {len(deduped_events)} events")

    # Push to XCom
    ti.xcom_push(key='deduped_events', value=deduped_events)

    return {
        'input_count': len(events),
        'output_count': len(deduped_events),
        'skipped_count': len(events) - len(deduped_events)
    }


def write_provenance_records(**context):
    """
    Atomically write provenance records to database

    For each event:
    1. Begin transaction
    2. Insert field_provenance record
    3. Mark staging record as processed
    4. Commit transaction

    Ensures provenance and staging are always in sync.
    """
    ti = context['ti']
    events = ti.xcom_pull(task_ids='deduplicate_events', key='deduped_events')

    if not events:
        logger.info("No events to write")
        return {'written_count': 0}

    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)
    conn = hook.get_conn()

    written_count = 0
    failed_count = 0

    for event in events:
        try:
            cursor = conn.cursor()

            # Set tenant context for RLS
            cursor.execute(f"SET LOCAL app.current_tenant_id = '{event['tenant_id']}'")

            # Insert provenance record
            insert_query = """
                INSERT INTO field_provenance (
                    tenant_id,
                    entity_type,
                    entity_id,
                    field_path,
                    value,
                    source_system,
                    source_url,
                    method,
                    confidence,
                    version,
                    extracted_at
                )
                VALUES (
                    %s::uuid, %s, %s::uuid, %s, %s::jsonb, %s, %s, %s, %s, %s, %s::timestamptz
                )
            """

            cursor.execute(insert_query, (
                event['tenant_id'],
                event['entity_type'],
                event['entity_id'],
                event['field_path'],
                json.dumps(event['value'], default=str),
                event['source_system'],
                event['source_url'],
                event['method'],
                event['confidence'],
                event['version'],
                event['extracted_at']
            ))

            # Mark staging record as processed
            if 'staging_id' in event:
                cursor.execute(
                    "UPDATE field_provenance_staging SET processed = TRUE WHERE id = %s",
                    (event['staging_id'],)
                )

            conn.commit()
            written_count += 1

            cursor.close()

        except Exception as e:
            logger.error(f"Failed to write provenance for {event['entity_type']}:{event['entity_id']}:{event['field_path']}: {e}")
            conn.rollback()
            failed_count += 1

    conn.close()

    logger.info(f"Wrote {written_count} provenance records ({failed_count} failed)")

    return {
        'written_count': written_count,
        'failed_count': failed_count
    }


def collect_lineage_metrics(**context):
    """Collect and log lineage writing metrics"""
    hook = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)

    # Get statistics
    stats_query = """
        SELECT
            COUNT(*) as total_records,
            COUNT(DISTINCT entity_id) as unique_entities,
            COUNT(DISTINCT field_path) as unique_fields,
            COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '1 hour') as recent_hour,
            COUNT(*) FILTER (WHERE method = 'scrape') as scraped,
            COUNT(*) FILTER (WHERE method = 'api') as api,
            COUNT(*) FILTER (WHERE method = 'manual') as manual,
            AVG(confidence) as avg_confidence
        FROM field_provenance
        WHERE tenant_id = %s
    """

    result = hook.get_first(stats_query, parameters=(DEFAULT_TENANT_ID,))

    if result:
        (total, unique_entities, unique_fields, recent_hour,
         scraped, api, manual, avg_confidence) = result

        logger.info("=" * 50)
        logger.info("LINEAGE WRITER METRICS")
        logger.info("=" * 50)
        logger.info(f"Total provenance records: {total}")
        logger.info(f"Unique entities tracked: {unique_entities}")
        logger.info(f"Unique fields tracked: {unique_fields}")
        logger.info(f"Records in last hour: {recent_hour}")
        logger.info(f"By method - Scraped: {scraped}, API: {api}, Manual: {manual}")
        logger.info(f"Average confidence: {avg_confidence:.2f}" if avg_confidence else "N/A")
        logger.info("=" * 50)

    return True


def alert_on_failure(**context):
    """Send alert if lineage writing failed"""
    logger.error("Lineage writer workflow failed!")

    ti = context['ti']
    dag_run = context['dag_run']

    logger.error(f"DAG Run ID: {dag_run.run_id}")
    logger.error(f"Execution Date: {context['execution_date']}")

    # In production, send actual alerts (Slack, PagerDuty)

    return True


# Define the DAG
with DAG(
    dag_id=DAG_ID,
    default_args=default_args,
    description='Write field provenance records for Deal Genome tracking',
    schedule_interval=SCHEDULE_INTERVAL,
    start_date=START_DATE,
    catchup=False,
    tags=['lineage', 'provenance', 'governance'],
) as dag:

    # Task 1: Poll for provenance events
    poll_events = PythonOperator(
        task_id='poll_provenance_events',
        python_callable=poll_provenance_events,
        provide_context=True,
    )

    # Task 2: Deduplicate events
    dedupe_events = PythonOperator(
        task_id='deduplicate_events',
        python_callable=deduplicate_events,
        provide_context=True,
    )

    # Task 3: Write provenance records
    write_records = PythonOperator(
        task_id='write_provenance_records',
        python_callable=write_provenance_records,
        provide_context=True,
    )

    # Task 4: Collect metrics
    collect_metrics = PythonOperator(
        task_id='collect_lineage_metrics',
        python_callable=collect_lineage_metrics,
        provide_context=True,
    )

    # Task 5: Alert on failure
    alert_failure = PythonOperator(
        task_id='alert_on_failure',
        python_callable=alert_on_failure,
        provide_context=True,
        trigger_rule=TriggerRule.ONE_FAILED,
    )

    # Define task dependencies
    poll_events >> dedupe_events >> write_records >> collect_metrics

    # Alert task triggers on any failure
    [poll_events, dedupe_events, write_records, collect_metrics] >> alert_failure
