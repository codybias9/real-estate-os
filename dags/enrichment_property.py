\"\"\"Join assessor API data onto prospect_queue\"\"\"
from datetime import datetime
from airflow import DAG
from airflow.operators.empty import EmptyOperator

with DAG(
    dag_id="enrichment_property",
    start_date=datetime(2025, 1, 1),
    schedule_interval="@hourly",
    catchup=False,
    tags=["pipeline"],
):
    EmptyOperator(task_id="placeholder")
