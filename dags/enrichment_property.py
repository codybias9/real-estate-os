"""Enrich properties with assessor and market data."""

from datetime import datetime
import sys
sys.path.insert(0, '/home/user/real-estate-os')

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from sqlalchemy.orm import Session

from agents.enrichment.service import enrich_property_by_id


def enrich_new_properties(**context):
    """Enrich all properties with 'new' or 'enriched' status that need (re)enrichment."""

    # Get database connection
    hook = PostgresHook(postgres_conn_id="app_db")
    engine = hook.get_sqlalchemy_engine()

    with Session(engine) as db:
        # Import models
        from db.models import Property

        # Get properties that need enrichment
        properties = db.query(Property).filter(
            Property.status.in_(['new', 'enriched'])
        ).limit(100).all()

        enriched_count = 0
        for prop in properties:
            try:
                enrich_property_by_id(prop.id, db)
                enriched_count += 1
                print(f"Enriched property {prop.id}: {prop.address}")
            except Exception as e:
                print(f"Error enriching property {prop.id}: {e}")
                continue

        print(f"Successfully enriched {enriched_count} properties")
        return enriched_count


with DAG(
    dag_id="enrichment_property",
    start_date=datetime(2025, 1, 1),
    schedule_interval="@hourly",
    catchup=False,
    tags=["pipeline"],
    doc_md="""
    # Property Enrichment DAG

    Enriches properties with:
    - Assessor data (APN, tax assessment)
    - Ownership information
    - School district data
    - Location metrics (walkability, transit, crime)
    - Market data (median values, appreciation)
    - Nearby amenities
    """,
):
    enrich_task = PythonOperator(
        task_id="enrich_properties",
        python_callable=enrich_new_properties,
        provide_context=True,
        retries=1,
    )
