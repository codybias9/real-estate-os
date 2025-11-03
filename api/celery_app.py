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
        }
    }
)

# ============================================================================
# TASK BASE CLASSES
# ============================================================================

class BaseTask(celery_app.Task):
    """
    Base task class with common functionality
    """

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        Handle task failure - log to database and send alerts
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Task {self.name} failed: {exc}", exc_info=einfo)

        # TODO: Send alert to Sentry or monitoring system
        # TODO: Record failure in database

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """
        Handle task retry
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Task {self.name} retrying: {exc}")

    def on_success(self, retval, task_id, args, kwargs):
        """
        Handle task success
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Task {self.name} completed successfully")


# Set default base class for all tasks
celery_app.Task = BaseTask

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
