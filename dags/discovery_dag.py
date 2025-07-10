from __future__ import annotations

import pendulum

from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator

with DAG(
    dag_id="offmarket_scrape_dag",
    schedule=None,
    start_date=pendulum.datetime(2023, 1, 1, tz="UTC"),
    catchup=False,
    tags=["discovery"],
) as dag:
    # This task runs the Scrapy spider.
    # We navigate into the project directory inside the container and execute the crawl.
    run_scraper_task = BashOperator(
        task_id="run_offmarket_scraper",
        bash_command="cd /opt/airflow/src/scraper && poetry run scrapy crawl listings",
    )