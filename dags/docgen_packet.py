"""Generate Investor Memo PDFs for scored properties."""

from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
sys.path.insert(0, '/home/user/real-estate-os')

from db.models import Property, PropertyScore, GeneratedDocument
from agents.docgen.service import generate_document_for_property


# Database configuration
DATABASE_URL = "postgresql://airflow:airflow@postgres:5432/airflow"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def generate_investor_memos(**context):
    """Generate investor memos for properties that have been scored but not documented."""
    db = SessionLocal()

    try:
        # Find properties that have scores but no documents
        scored_properties = (
            db.query(Property)
            .join(PropertyScore, Property.id == PropertyScore.property_id)
            .outerjoin(GeneratedDocument, Property.id == GeneratedDocument.property_id)
            .filter(
                Property.status.in_(['scored']),
                GeneratedDocument.id.is_(None)  # No document exists
            )
            .limit(50)  # Process 50 at a time
            .all()
        )

        context['task_instance'].xcom_push(key='found_properties', value=len(scored_properties))

        generated_count = 0
        error_count = 0

        for prop in scored_properties:
            try:
                print(f"Generating memo for property {prop.id}: {prop.address}")
                document = generate_document_for_property(prop.id, db)
                generated_count += 1
                print(f"✓ Successfully generated memo: {document.file_path}")

            except Exception as e:
                error_count += 1
                print(f"✗ Error generating memo for property {prop.id}: {str(e)}")
                continue

        context['task_instance'].xcom_push(key='generated_count', value=generated_count)
        context['task_instance'].xcom_push(key='error_count', value=error_count)

        print(f"\nDocument Generation Summary:")
        print(f"  Found: {len(scored_properties)} properties")
        print(f"  Generated: {generated_count} memos")
        print(f"  Errors: {error_count}")

    finally:
        db.close()


def regenerate_all_memos(**context):
    """Regenerate memos for all scored properties (for testing/demo purposes)."""
    db = SessionLocal()

    try:
        # Get all scored properties
        scored_properties = (
            db.query(Property)
            .join(PropertyScore, Property.id == PropertyScore.property_id)
            .filter(Property.status.in_(['scored', 'documented']))
            .limit(100)  # Limit for demo
            .all()
        )

        context['task_instance'].xcom_push(key='total_properties', value=len(scored_properties))

        generated_count = 0
        error_count = 0

        for prop in scored_properties:
            try:
                print(f"Regenerating memo for property {prop.id}: {prop.address}")
                document = generate_document_for_property(prop.id, db)
                generated_count += 1

            except Exception as e:
                error_count += 1
                print(f"Error regenerating memo for property {prop.id}: {str(e)}")
                continue

        context['task_instance'].xcom_push(key='generated_count', value=generated_count)
        context['task_instance'].xcom_push(key='error_count', value=error_count)

        print(f"\nRegeneration Summary:")
        print(f"  Total: {len(scored_properties)} properties")
        print(f"  Generated: {generated_count} memos")
        print(f"  Errors: {error_count}")

    finally:
        db.close()


# Define the DAG
with DAG(
    dag_id="docgen_packet",
    description="Generate investor memo PDFs for scored properties",
    start_date=datetime(2025, 1, 1),
    schedule_interval="0 */2 * * *",  # Every 2 hours
    catchup=False,
    tags=["pipeline", "documents"],
    default_args={
        'retries': 1,
        'retry_delay': 300,  # 5 minutes
    }
) as dag:

    # Main task: Generate memos for new scored properties
    generate_memos_task = PythonOperator(
        task_id="generate_investor_memos",
        python_callable=generate_investor_memos,
        provide_context=True,
    )

    # Optional: Task to regenerate all memos (manual trigger only)
    regenerate_all_task = PythonOperator(
        task_id="regenerate_all_memos",
        python_callable=regenerate_all_memos,
        provide_context=True,
    )

    # Task dependencies
    generate_memos_task
