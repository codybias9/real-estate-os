"""Score properties for investment potential."""

from datetime import datetime
import sys
sys.path.insert(0, '/home/user/real-estate-os')

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from sqlalchemy.orm import Session

from agents.scoring.scorer import score_property_by_id


def score_enriched_properties(**context):
    """Score all enriched properties that haven't been scored yet."""

    # Get database connection
    hook = PostgresHook(postgres_conn_id="app_db")
    engine = hook.get_sqlalchemy_engine()

    with Session(engine) as db:
        # Import models
        from db.models import Property, PropertyEnrichment, PropertyScore

        # Get enriched properties without scores
        enriched_properties = db.query(Property).join(
            PropertyEnrichment, Property.id == PropertyEnrichment.property_id
        ).filter(
            Property.status.in_(['enriched', 'scored'])
        ).limit(100).all()

        scored_count = 0
        for prop in enriched_properties:
            try:
                score_property_by_id(prop.id, db)
                scored_count += 1
                print(f"Scored property {prop.id}: {prop.address}")
            except Exception as e:
                print(f"Error scoring property {prop.id}: {e}")
                continue

        print(f"Successfully scored {scored_count} properties")
        return scored_count


with DAG(
    dag_id="score_master",
    start_date=datetime(2025, 1, 1),
    schedule_interval="@hourly",
    catchup=False,
    tags=["pipeline"],
    doc_md="""
    # Property Scoring DAG

    Scores properties based on:
    - Price analysis (below/above market)
    - Market timing (appreciation trends)
    - Investment metrics (rental yield, cap rate, ROI)
    - Location quality (walkability, schools, crime)
    - Property condition (age, size, type)

    Generates:
    - Total score (0-100)
    - Component scores
    - Investment recommendation (strong_buy, buy, hold, pass)
    - Risk assessment (low, medium, high)
    """,
):
    score_task = PythonOperator(
        task_id="score_properties",
        python_callable=score_enriched_properties,
        provide_context=True,
        retries=1,
    )
