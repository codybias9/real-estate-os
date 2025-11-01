"""
Embedding Indexing DAG

Airflow DAG for syncing property embeddings to Qdrant.

Schedule: Daily at 3 AM
Triggers: After Portfolio Twin training completes

Part of Wave 2.2 - Qdrant indexing automation.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.sensors.external_task import ExternalTaskSensor
from airflow.utils.dates import days_ago
import logging


logger = logging.getLogger(__name__)


# Default arguments
default_args = {
    'owner': 'realestate-ml',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# DAG definition
dag = DAG(
    'embedding_indexing',
    default_args=default_args,
    description='Sync property embeddings to Qdrant vector database',
    schedule_interval='0 3 * * *',  # Daily at 3 AM
    start_date=days_ago(1),
    catchup=False,
    tags=['ml', 'embeddings', 'qdrant'],
)


def check_qdrant_health(**context):
    """
    Check if Qdrant server is healthy

    Verifies connectivity before starting indexing.
    """
    from ml.embeddings.qdrant_client import QdrantVectorDB

    qdrant_host = context['params'].get('qdrant_host', 'localhost')
    qdrant_port = context['params'].get('qdrant_port', 6333)

    try:
        qdrant = QdrantVectorDB(host=qdrant_host, port=qdrant_port)

        # Try to get collection info (if exists)
        try:
            info = qdrant.get_collection_info("property_embeddings")
            logger.info(f"Qdrant health check passed. Collections: {info}")
        except Exception:
            # Collection doesn't exist yet, but Qdrant is reachable
            logger.info("Qdrant reachable, collections will be created")

        logger.info("Qdrant health check passed!")

    except Exception as e:
        raise ValueError(f"Qdrant health check failed: {e}")


def check_model_exists(**context):
    """
    Check if trained Portfolio Twin model exists

    Ensures we have a model before trying to generate embeddings.
    """
    from pathlib import Path

    model_path = Path(context['params'].get('model_path', 'ml/serving/models/portfolio_twin.pt'))

    if not model_path.exists():
        raise ValueError(f"Model not found at {model_path}. Run portfolio_twin_training DAG first.")

    logger.info(f"Model found at {model_path}")


def count_properties(**context):
    """
    Count properties that need indexing

    Compares database count with Qdrant count to determine if full reindex needed.
    """
    from sqlalchemy import create_engine, func
    from sqlalchemy.orm import sessionmaker
    from db.models import Property
    from ml.embeddings.qdrant_client import QdrantVectorDB

    tenant_id = context['params']['tenant_id']
    db_url = context['params']['db_url']
    qdrant_host = context['params'].get('qdrant_host', 'localhost')
    qdrant_port = context['params'].get('qdrant_port', 6333)

    # Connect to database
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    # Set tenant context
    db.execute(f"SET LOCAL app.current_tenant_id = '{tenant_id}'")

    # Count properties in database
    db_count = db.query(func.count(Property.id)).scalar()

    # Count properties in Qdrant
    qdrant = QdrantVectorDB(host=qdrant_host, port=qdrant_port)
    try:
        info = qdrant.get_collection_info("property_embeddings")
        qdrant_count = info['points_count']
    except Exception:
        qdrant_count = 0

    db.close()

    logger.info(f"Properties: DB={db_count}, Qdrant={qdrant_count}")

    # Store counts in XCom
    context['task_instance'].xcom_push(key='db_count', value=db_count)
    context['task_instance'].xcom_push(key='qdrant_count', value=qdrant_count)

    # Decide if full reindex needed
    needs_full_reindex = (qdrant_count < db_count * 0.9)  # If >10% missing
    context['task_instance'].xcom_push(key='needs_full_reindex', value=needs_full_reindex)

    if needs_full_reindex:
        logger.info("Full reindex needed (too many missing)")
    else:
        logger.info("Incremental update sufficient")


def index_embeddings(**context):
    """
    Index embeddings into Qdrant

    Uses BashOperator to call the indexer CLI script.
    This is a placeholder for the Python-based orchestration.
    """
    logger.info("Indexing started via BashOperator")


def verify_indexing(**context):
    """
    Verify indexing completed successfully

    Checks that all properties are indexed and searchable.
    """
    from ml.embeddings.qdrant_client import QdrantVectorDB

    qdrant_host = context['params'].get('qdrant_host', 'localhost')
    qdrant_port = context['params'].get('qdrant_port', 6333)
    tenant_id = context['params']['tenant_id']

    # Get expected count from XCom
    db_count = context['task_instance'].xcom_pull(task_ids='count_properties', key='db_count')

    # Get actual count from Qdrant
    qdrant = QdrantVectorDB(host=qdrant_host, port=qdrant_port)
    info = qdrant.get_collection_info("property_embeddings")
    qdrant_count = info['points_count']

    logger.info(f"Indexing verification: Expected={db_count}, Actual={qdrant_count}")

    # Allow 5% tolerance
    if qdrant_count < db_count * 0.95:
        raise ValueError(f"Indexing incomplete: {qdrant_count}/{db_count} properties")

    logger.info("Indexing verification passed!")

    # Store final count
    context['task_instance'].xcom_push(key='final_count', value=qdrant_count)


def test_similarity_search(**context):
    """
    Test similarity search functionality

    Picks a random property and finds similar ones to verify search works.
    """
    from ml.embeddings.qdrant_client import QdrantVectorDB
    import random

    tenant_id = context['params']['tenant_id']
    qdrant_host = context['params'].get('qdrant_host', 'localhost')
    qdrant_port = context['params'].get('qdrant_port', 6333)

    qdrant = QdrantVectorDB(host=qdrant_host, port=qdrant_port)

    # Get a random property
    properties, _ = qdrant.scroll_properties(tenant_id=tenant_id, batch_size=10)

    if not properties:
        logger.warning("No properties found for testing")
        return

    test_property = random.choice(properties)
    property_id = test_property['property_id']

    logger.info(f"Testing similarity search with property {property_id}")

    # Find similar properties
    similar = qdrant.find_look_alikes(
        property_id=property_id,
        tenant_id=tenant_id,
        top_k=5
    )

    if not similar:
        raise ValueError("Similarity search returned no results")

    logger.info(f"Found {len(similar)} similar properties:")
    for i, prop in enumerate(similar, 1):
        logger.info(f"  {i}. {prop.property_id} (score: {prop.similarity_score:.3f})")

    logger.info("Similarity search test passed!")


# Task 1: Check Qdrant health
health_check_task = PythonOperator(
    task_id='check_qdrant_health',
    python_callable=check_qdrant_health,
    provide_context=True,
    dag=dag,
)

# Task 2: Check model exists
model_check_task = PythonOperator(
    task_id='check_model_exists',
    python_callable=check_model_exists,
    provide_context=True,
    dag=dag,
)

# Task 3: Count properties
count_task = PythonOperator(
    task_id='count_properties',
    python_callable=count_properties,
    provide_context=True,
    dag=dag,
)

# Task 4: Index embeddings (via Bash)
index_task = BashOperator(
    task_id='index_embeddings',
    bash_command="""
    python ml/embeddings/indexer.py \
        --tenant-id {{ params.tenant_id }} \
        --model-path {{ params.model_path }} \
        --db-url {{ params.db_url }} \
        --qdrant-host {{ params.qdrant_host }} \
        --qdrant-port {{ params.qdrant_port }} \
        --batch-size {{ params.batch_size }} \
        {% if task_instance.xcom_pull(task_ids='count_properties', key='needs_full_reindex') %}--recreate{% endif %}
    """,
    dag=dag,
)

# Task 5: Verify indexing
verify_task = PythonOperator(
    task_id='verify_indexing',
    python_callable=verify_indexing,
    provide_context=True,
    dag=dag,
)

# Task 6: Test similarity search
test_task = PythonOperator(
    task_id='test_similarity_search',
    python_callable=test_similarity_search,
    provide_context=True,
    dag=dag,
)

# Define task dependencies
health_check_task >> model_check_task >> count_task >> index_task >> verify_task >> test_task


# Example params for manual trigger:
"""
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "db_url": "postgresql://user:pass@localhost/realestate",
  "model_path": "ml/serving/models/portfolio_twin.pt",
  "qdrant_host": "localhost",
  "qdrant_port": 6333,
  "batch_size": 100
}
"""
