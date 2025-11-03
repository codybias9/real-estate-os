"""
Celery Application Configuration
Background task processing for Real Estate OS
"""
import os
from celery import Celery
from celery.schedules import crontab

# ============================================================================
# CELERY APP CONFIGURATION
# ============================================================================

# Get broker and backend URLs from environment
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "amqp://admin:admin@localhost:5672/")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

# Create Celery app
celery_app = Celery(
    "real_estate_os",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "api.tasks.memo_tasks",
        "api.tasks.enrichment_tasks",
        "api.tasks.email_tasks",
        "api.tasks.maintenance_tasks"
    ]
)

# ============================================================================
# CELERY CONFIGURATION
# ============================================================================

celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task routing
    task_routes={
        "api.tasks.memo_tasks.*": {"queue": "memos"},
        "api.tasks.enrichment_tasks.*": {"queue": "enrichment"},
        "api.tasks.email_tasks.*": {"queue": "emails"},
        "api.tasks.maintenance_tasks.*": {"queue": "maintenance"}
    },

    # Task execution settings
    task_acks_late=True,  # Acknowledge task after completion
    task_reject_on_worker_lost=True,  # Reject if worker crashes
    worker_prefetch_multiplier=1,  # Fetch one task at a time for fair distribution

    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,  # Persist results

    # Retry settings
    task_default_retry_delay=60,  # Wait 60 seconds before retry
    task_max_retries=3,  # Max 3 retries

    # Worker settings
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks (prevent memory leaks)
    worker_disable_rate_limits=False,

    # Dead Letter Queue (DLQ) settings
    task_annotations={
        "*": {
            "rate_limit": "100/m",  # Max 100 tasks per minute
            "time_limit": 300,  # Hard time limit: 5 minutes
            "soft_time_limit": 240,  # Soft time limit: 4 minutes (raises exception)
        }
    },

    # RabbitMQ queue configuration with Dead Letter Exchange (DLX)
    task_queues={
        "memos": {
            "exchange": "default",
            "routing_key": "memos",
            "queue_arguments": {
                "x-dead-letter-exchange": "dlx",
                "x-dead-letter-routing-key": "dlq.memos",
                "x-message-ttl": 86400000,  # 24 hours
            }
        },
        "enrichment": {
            "exchange": "default",
            "routing_key": "enrichment",
            "queue_arguments": {
                "x-dead-letter-exchange": "dlx",
                "x-dead-letter-routing-key": "dlq.enrichment",
                "x-message-ttl": 86400000,
            }
        },
        "emails": {
            "exchange": "default",
            "routing_key": "emails",
            "queue_arguments": {
                "x-dead-letter-exchange": "dlx",
                "x-dead-letter-routing-key": "dlq.emails",
                "x-message-ttl": 86400000,
            }
        },
        "maintenance": {
            "exchange": "default",
            "routing_key": "maintenance",
            "queue_arguments": {
                "x-dead-letter-exchange": "dlx",
                "x-dead-letter-routing-key": "dlq.maintenance",
                "x-message-ttl": 86400000,
            }
        },
    },

    # Beat schedule (periodic tasks)
    beat_schedule={
        # Update deliverability metrics daily
        "update-deliverability-metrics": {
            "task": "api.tasks.maintenance_tasks.update_deliverability_metrics",
            "schedule": crontab(hour=2, minute=0),  # 2:00 AM daily
        },

        # Refresh portfolio metrics daily
        "refresh-portfolio-metrics": {
            "task": "api.tasks.maintenance_tasks.refresh_portfolio_metrics",
            "schedule": crontab(hour=3, minute=0),  # 3:00 AM daily
        },

        # Check budget alerts every hour
        "check-budget-alerts": {
            "task": "api.tasks.maintenance_tasks.check_budget_alerts",
            "schedule": crontab(minute=0),  # Every hour
        },

        # Clean up expired share links every 6 hours
        "cleanup-expired-share-links": {
            "task": "api.tasks.maintenance_tasks.cleanup_expired_share_links",
            "schedule": crontab(hour="*/6", minute=0),  # Every 6 hours
        },

        # Process scheduled email sequences every 15 minutes
        "process-email-sequences": {
            "task": "api.tasks.email_tasks.process_scheduled_sequences",
            "schedule": crontab(minute="*/15"),  # Every 15 minutes
        },

        # Check DLQ alerts every 5 minutes
        "check-dlq-alerts": {
            "task": "api.tasks.maintenance_tasks.check_dlq_alerts",
            "schedule": crontab(minute="*/5"),  # Every 5 minutes
        },

        # Clean up expired idempotency keys daily
        "cleanup-idempotency-keys": {
            "task": "api.tasks.maintenance_tasks.cleanup_idempotency_keys",
            "schedule": crontab(hour=4, minute=0),  # 4:00 AM daily
        }
    }
)

# ============================================================================
# TASK BASE CLASSES WITH DLQ SUPPORT
# ============================================================================

# Import DLQ task base class
from api.dlq import DLQTask

# Set default base class for all tasks (includes automatic DLQ recording)
celery_app.Task = DLQTask

# ============================================================================
# UTILITIES
# ============================================================================

def get_db_session():
    """
    Get database session for use in Celery tasks

    IMPORTANT: Always use this in a context manager to ensure proper cleanup

    Example:
        with get_db_session() as db:
            property = db.query(Property).first()
    """
    from api.database import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    # For testing - start worker directly
    celery_app.start()
