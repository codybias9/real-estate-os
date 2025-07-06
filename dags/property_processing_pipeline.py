from airflow import DAG
from airflow.operators.dummy import DummyOperator
import pendulum

with DAG(
    dag_id='property_processing_pipeline',
    description='Test DAG to verify Airflow startup',
    schedule_interval=None,
    start_date=pendulum.datetime(2024, 1, 1, tz='UTC'),
    catchup=False,
) as dag:
    start = DummyOperator(task_id='start')
