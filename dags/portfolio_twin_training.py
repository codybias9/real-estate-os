"""
Portfolio Twin Training DAG

Airflow DAG for automated Portfolio Twin model training.

Schedule: Weekly (every Sunday at 2 AM)
Triggers: Manual or when user interaction data reaches threshold

Part of Wave 2.1 - Portfolio Twin training pipeline.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
import os
import logging

from db.models import Deal, Property
from ml.training.train_portfolio_twin import main as train_main
from ml.training.data_loader import create_negative_samples


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
    'portfolio_twin_training',
    default_args=default_args,
    description='Train Portfolio Twin model on user interaction data',
    schedule_interval='0 2 * * 0',  # Weekly on Sunday at 2 AM
    start_date=days_ago(1),
    catchup=False,
    tags=['ml', 'training', 'portfolio-twin'],
)


def check_data_threshold(**context):
    """
    Check if we have enough interaction data to train

    Minimum requirements:
    - At least 100 user interactions (deals)
    - At least 50 unique properties
    - At least 2 users with interactions
    """
    tenant_id = context['params']['tenant_id']
    db_url = context['params']['db_url']

    # Connect to database
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    # Set tenant context
    db.execute(f"SET LOCAL app.current_tenant_id = '{tenant_id}'")

    # Count interactions
    num_deals = db.query(func.count(Deal.id)).scalar()
    num_properties = db.query(func.count(func.distinct(Deal.property_id))).scalar()
    num_users = db.query(func.count(func.distinct(Deal.user_id))).scalar()

    db.close()

    logger.info(f"Data check: {num_deals} deals, {num_properties} properties, {num_users} users")

    # Check thresholds
    if num_deals < 100:
        raise ValueError(f"Not enough deals: {num_deals} < 100")
    if num_properties < 50:
        raise ValueError(f"Not enough properties: {num_properties} < 50")
    if num_users < 2:
        raise ValueError(f"Not enough users: {num_users} < 2")

    logger.info("Data threshold check passed!")

    # Store stats in XCom
    context['task_instance'].xcom_push(key='num_deals', value=num_deals)
    context['task_instance'].xcom_push(key='num_properties', value=num_properties)
    context['task_instance'].xcom_push(key='num_users', value=num_users)


def prepare_training_data(**context):
    """
    Prepare training data:
    - Create negative samples
    - Split train/val sets
    - Log data statistics
    """
    tenant_id = context['params']['tenant_id']
    db_url = context['params']['db_url']

    # Connect to database
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    # Set tenant context
    db.execute(f"SET LOCAL app.current_tenant_id = '{tenant_id}'")

    # Create negative samples
    logger.info("Creating negative samples...")
    negative_samples = create_negative_samples(
        db_session=db,
        tenant_id=tenant_id,
        num_samples=1000
    )

    logger.info(f"Created {len(negative_samples)} negative samples")

    db.close()

    # Store in XCom
    context['task_instance'].xcom_push(key='num_negative_samples', value=len(negative_samples))


def train_model(**context):
    """
    Train the Portfolio Twin model

    Calls the main training script with configured parameters.
    """
    tenant_id = context['params']['tenant_id']
    db_url = context['params']['db_url']
    epochs = context['params'].get('epochs', 100)
    batch_size = context['params'].get('batch_size', 32)
    learning_rate = context['params'].get('learning_rate', 0.001)

    logger.info(f"Starting training with epochs={epochs}, batch_size={batch_size}, lr={learning_rate}")

    # Training is handled by BashOperator calling the CLI script
    # This function is for Python-based orchestration if needed

    logger.info("Training completed (via BashOperator)")


def evaluate_model_quality(**context):
    """
    Evaluate trained model and check quality gates

    Quality gates:
    - Validation F1 > 0.6
    - Validation accuracy > 0.7
    - No NaN embeddings
    """
    import torch
    import json
    from pathlib import Path

    output_dir = Path(context['params'].get('output_dir', 'ml/checkpoints'))

    # Load training history
    history_path = output_dir / 'training_history.json'
    if not history_path.exists():
        raise ValueError(f"Training history not found: {history_path}")

    with open(history_path, 'r') as f:
        history = json.load(f)

    # Get final metrics
    final_metrics = history[-1]
    val_f1 = final_metrics.get('f1', 0.0)
    val_accuracy = final_metrics.get('accuracy', 0.0)

    logger.info(f"Final metrics: F1={val_f1:.4f}, Accuracy={val_accuracy:.4f}")

    # Check quality gates
    if val_f1 < 0.6:
        raise ValueError(f"F1 score too low: {val_f1:.4f} < 0.6")
    if val_accuracy < 0.7:
        raise ValueError(f"Accuracy too low: {val_accuracy:.4f} < 0.7")

    # Load model and check for NaN
    model_path = output_dir / 'portfolio_twin_best.pt'
    if not model_path.exists():
        raise ValueError(f"Model checkpoint not found: {model_path}")

    checkpoint = torch.load(model_path)
    model_state = checkpoint['model_state_dict']

    for name, param in model_state.items():
        if torch.isnan(param).any():
            raise ValueError(f"NaN detected in parameter: {name}")

    logger.info("Quality gates passed!")

    # Store in XCom
    context['task_instance'].xcom_push(key='final_f1', value=val_f1)
    context['task_instance'].xcom_push(key='final_accuracy', value=val_accuracy)


def deploy_model(**context):
    """
    Deploy trained model to production

    - Copy best model to serving directory
    - Update model metadata
    - Trigger model serving reload
    """
    from pathlib import Path
    import shutil

    output_dir = Path(context['params'].get('output_dir', 'ml/checkpoints'))
    serving_dir = Path(context['params'].get('serving_dir', 'ml/serving/models'))

    serving_dir.mkdir(parents=True, exist_ok=True)

    # Copy best model
    best_model = output_dir / 'portfolio_twin_best.pt'
    deployed_model = serving_dir / 'portfolio_twin.pt'

    shutil.copy(best_model, deployed_model)
    logger.info(f"Deployed model: {deployed_model}")

    # Update metadata
    metadata = {
        'model_name': 'portfolio_twin',
        'version': context['execution_date'].strftime('%Y%m%d_%H%M%S'),
        'deployed_at': datetime.utcnow().isoformat(),
        'metrics': {
            'f1': float(context['task_instance'].xcom_pull(task_ids='evaluate_model', key='final_f1')),
            'accuracy': float(context['task_instance'].xcom_pull(task_ids='evaluate_model', key='final_accuracy')),
        }
    }

    import json
    metadata_path = serving_dir / 'portfolio_twin_metadata.json'
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Updated metadata: {metadata_path}")

    # TODO: Trigger model serving reload (e.g., via API call or file watcher)
    logger.info("Model deployment complete!")


# Task 1: Check data threshold
check_data_task = PythonOperator(
    task_id='check_data_threshold',
    python_callable=check_data_threshold,
    provide_context=True,
    dag=dag,
)

# Task 2: Prepare training data
prepare_data_task = PythonOperator(
    task_id='prepare_training_data',
    python_callable=prepare_training_data,
    provide_context=True,
    dag=dag,
)

# Task 3: Train model (via Bash)
train_task = BashOperator(
    task_id='train_model',
    bash_command="""
    python ml/training/train_portfolio_twin.py \
        --tenant-id {{ params.tenant_id }} \
        --db-url {{ params.db_url }} \
        --epochs {{ params.epochs }} \
        --batch-size {{ params.batch_size }} \
        --learning-rate {{ params.learning_rate }} \
        --output-dir {{ params.output_dir }}
    """,
    dag=dag,
)

# Task 4: Evaluate model quality
evaluate_task = PythonOperator(
    task_id='evaluate_model',
    python_callable=evaluate_model_quality,
    provide_context=True,
    dag=dag,
)

# Task 5: Deploy model
deploy_task = PythonOperator(
    task_id='deploy_model',
    python_callable=deploy_model,
    provide_context=True,
    dag=dag,
)

# Define task dependencies
check_data_task >> prepare_data_task >> train_task >> evaluate_task >> deploy_task


# Example params for manual trigger:
"""
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "db_url": "postgresql://user:pass@localhost/realestate",
  "epochs": 100,
  "batch_size": 32,
  "learning_rate": 0.001,
  "output_dir": "ml/checkpoints",
  "serving_dir": "ml/serving/models"
}
"""
