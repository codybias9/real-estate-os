from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from offmarket_scraper.scraper import run as scrape_offmarket

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='discovery_offmarket',
    default_args=default_args,
    description='Off-Market Property Discovery',
    schedule_interval='*/15 * * * *',
    start_date=days_ago(1),
    catchup=False,
    tags=['discovery'],
) as dag:

    t1 = PythonOperator(
        task_id='run_offmarket_scraper',
        python_callable=scrape_offmarket
    )

    t1
