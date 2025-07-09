from __future__ import annotations

import pendulum

from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator

with DAG(
    dag_id="example_test_dag",
    schedule=None,
    start_date=pendulum.datetime(2023, 1, 1, tz="UTC"),
    catchup=False,
    tags=["example"],
) as dag:
    test_task = BashOperator(
        task_id="test_task",
        bash_command="echo 'Hello from the test DAG! The mount is working!'",
    )
