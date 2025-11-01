"""Drift Monitoring DAG
Nightly drift detection for feature and model drift

Schedule: Daily at 2 AM
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import timedelta
import sys
import pandas as pd
from sqlalchemy import create_engine
import os

sys.path.append('/home/user/real-estate-os')
from ml.monitoring.evidently.drift_detector import detect_drift_and_alert

default_args = {
    'owner': 'ml-team',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'drift_monitoring',
    default_args=default_args,
    description='Monitor feature and model drift using Evidently',
    schedule_interval='0 2 * * *',  # Daily at 2 AM
    start_date=days_ago(1),
    catchup=False,
    tags=['monitoring', 'evidently', 'drift'],
) as dag:

    def load_reference_data(**context):
        """Load reference data (training set)"""

        engine = create_engine(os.getenv("DB_DSN"))

        # Load reference data from database
        # This should be your training set or a stable historical period
        query = """
        SELECT
            sqft,
            lot_size,
            year_built,
            list_price,
            list_price / NULLIF(sqft, 0) AS price_per_sqft,
            dom AS days_on_market,
            cap_rate_estimate AS cap_rate,
            latitude,
            longitude,
            COALESCE(condition_score, 5.0) AS condition_score,
            COALESCE(flood_risk_score, 0.0) AS flood_risk,
            COALESCE(wildfire_risk_score, 0.0) AS wildfire_risk,
            COALESCE(walk_score, 0) AS walk_score,
            asset_type,
            property_type,
            zip_code AS market,
            status
        FROM property
        WHERE created_at BETWEEN '2024-01-01' AND '2024-03-31'
          AND status IN ('sold', 'closed')
        LIMIT 10000
        """

        df = pd.read_sql(query, engine)
        engine.dispose()

        # Save to XCom (or to file for large datasets)
        context['task_instance'].xcom_push(key='reference_data', value=df.to_json())

    def load_current_data(**context):
        """Load current production data (last 7 days)"""

        engine = create_engine(os.getenv("DB_DSN"))

        # Load recent data
        query = """
        SELECT
            sqft,
            lot_size,
            year_built,
            list_price,
            list_price / NULLIF(sqft, 0) AS price_per_sqft,
            dom AS days_on_market,
            cap_rate_estimate AS cap_rate,
            latitude,
            longitude,
            COALESCE(condition_score, 5.0) AS condition_score,
            COALESCE(flood_risk_score, 0.0) AS flood_risk,
            COALESCE(wildfire_risk_score, 0.0) AS wildfire_risk,
            COALESCE(walk_score, 0) AS walk_score,
            asset_type,
            property_type,
            zip_code AS market,
            status
        FROM property
        WHERE created_at >= NOW() - INTERVAL '7 days'
        LIMIT 10000
        """

        df = pd.read_sql(query, engine)
        engine.dispose()

        context['task_instance'].xcom_push(key='current_data', value=df.to_json())

    def detect_drift(**context):
        """Run drift detection"""

        # Load data from XCom
        ti = context['task_instance']
        reference_json = ti.xcom_pull(key='reference_data', task_ids='load_reference_data')
        current_json = ti.xcom_pull(key='current_data', task_ids='load_current_data')

        reference_data = pd.read_json(reference_json)
        current_data = pd.read_json(current_json)

        # Run drift detection
        report_path = f"/tmp/drift_report_{context['ds']}.html"

        result = detect_drift_and_alert(
            reference_data=reference_data,
            current_data=current_data,
            report_path=report_path
        )

        # Push result to XCom
        ti.xcom_push(key='drift_result', value=result)

        return result

    def send_alerts(**context):
        """Send alerts if drift detected"""

        ti = context['task_instance']
        result = ti.xcom_pull(key='drift_result', task_ids='detect_drift')

        severity = result.get('severity')
        block_deployment = result.get('block_deployment')

        if severity in ['WARNING', 'CRITICAL']:
            # Send Slack alert
            message = f"""
🚨 Data Drift Alert - {severity}

Drifted columns: {result['drift_summary']['number_of_drifted_columns']}
Share of drift: {result['drift_summary']['share_of_drifted_columns']:.1%}
Block deployment: {block_deployment}

Report: {result['report_path']}
"""

            print(f"ALERT: {message}")

            # TODO: Send to Slack webhook
            # requests.post(os.getenv("SLACK_WEBHOOK_URL"), json={"text": message})

        if block_deployment:
            raise Exception("CRITICAL drift detected - blocking deployment!")

    def upload_report_to_s3(**context):
        """Upload drift report to S3 for archival"""

        ti = context['task_instance']
        result = ti.xcom_pull(key='drift_result', task_ids='detect_drift')

        report_path = result.get('report_path')

        # TODO: Upload to S3
        # boto3.client('s3').upload_file(report_path, bucket, key)

        print(f"Report would be uploaded: {report_path}")

    # Task definitions
    load_ref = PythonOperator(
        task_id='load_reference_data',
        python_callable=load_reference_data,
    )

    load_curr = PythonOperator(
        task_id='load_current_data',
        python_callable=load_current_data,
    )

    detect = PythonOperator(
        task_id='detect_drift',
        python_callable=detect_drift,
    )

    alert = PythonOperator(
        task_id='send_alerts',
        python_callable=send_alerts,
    )

    upload = PythonOperator(
        task_id='upload_report_to_s3',
        python_callable=upload_report_to_s3,
    )

    # Dependencies
    [load_ref, load_curr] >> detect >> alert >> upload
