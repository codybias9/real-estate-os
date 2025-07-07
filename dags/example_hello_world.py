from __future__ import annotations

import pendulum

from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator

with DAG(
    dag_id="example_hello_world",
    schedule=None,
    start_date=pendulum.datetime(2024, 1, 1, tz="UTC"),
    catchup=False,
    tags=["example"],
) as dag:
    hello_task = BashOperator(
        task_id="hello",
        bash_command="echo 'Hello from Airflow! The orchestration layer is working.'",
    )
