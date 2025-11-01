"""Data Quality DAG
Runs Great Expectations validations at phase boundaries

Schedule: Daily at 6 AM
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import timedelta
import sys

sys.path.append('/home/user/real-estate-os')
from libs.data_quality.gx.checkpoints.daily_validation import (
    validate_after_ingest,
    validate_after_enrich,
    validate_after_score,
    check_freshness,
    check_schema_drift
)

default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'data_quality_validation',
    default_args=default_args,
    description='Great Expectations data quality validation',
    schedule_interval='0 6 * * *',  # Daily at 6 AM
    start_date=days_ago(1),
    catchup=False,
    tags=['data-quality', 'great-expectations'],
) as dag:

    # Freshness check
    freshness = PythonOperator(
        task_id='check_data_freshness',
        python_callable=check_freshness,
    )

    # Schema drift check
    schema_drift = PythonOperator(
        task_id='check_schema_drift',
        python_callable=check_schema_drift,
    )

    # Validate after ingest
    validate_ingest = PythonOperator(
        task_id='validate_after_ingest',
        python_callable=validate_after_ingest,
    )

    # Validate after enrich
    validate_enriched = PythonOperator(
        task_id='validate_after_enrich',
        python_callable=validate_after_enrich,
    )

    # Validate after score
    validate_scored = PythonOperator(
        task_id='validate_after_score',
        python_callable=validate_after_score,
    )

    # Dependencies
    [freshness, schema_drift] >> validate_ingest >> validate_enriched >> validate_scored
