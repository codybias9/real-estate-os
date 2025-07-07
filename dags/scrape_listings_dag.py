from __future__ import annotations

import pendulum

from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator

with DAG(
    dag_id="scrape_book_listings",
    # Run daily at midnight UTC. You can adjust this as needed.
    schedule="0 0 * * *",
    start_date=pendulum.datetime(2024, 7, 7, tz="UTC"),
    catchup=False,
    tags=["scraping", "data-ingestion"],
    doc_md="""
    ### Scrape Book Listings DAG

    This DAG runs the Scrapy spider to collect book listings from books.toscrape.com.
    It executes the scrapy crawl listings command from within the project's
    source directory inside the Airflow worker.
    """,
) as dag:
    # This task executes the scrapy crawl command.
    # It's crucial to first cd into the directory containing scrapy.cfg
    # so that Scrapy can find the project settings.
    scrape_task = BashOperator(
        task_id="run_scrapy_spider",
        bash_command="cd /opt/airflow/src && poetry run scrapy crawl listings",
    )
