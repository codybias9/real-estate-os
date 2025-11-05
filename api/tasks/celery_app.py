"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab
from ..config import settings

# Create Celery app
celery_app = Celery(
    "real_estate_os",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "api.tasks.campaign_tasks",
        "api.tasks.email_tasks",
        "api.tasks.webhook_tasks",
        "api.tasks.cleanup_tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,  # 1 hour
)

# Periodic task schedule
celery_app.conf.beat_schedule = {
    # Cleanup old idempotency keys every hour
    "cleanup-idempotency-keys": {
        "task": "api.tasks.cleanup_tasks.cleanup_idempotency_keys",
        "schedule": crontab(minute=0),  # Every hour
    },
    # Cleanup old audit logs every day
    "cleanup-audit-logs": {
        "task": "api.tasks.cleanup_tasks.cleanup_audit_logs",
        "schedule": crontab(hour=2, minute=0),  # 2 AM daily
    },
    # Retry failed webhooks every 15 minutes
    "retry-failed-webhooks": {
        "task": "api.tasks.webhook_tasks.retry_failed_webhooks",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
    },
    # Generate daily analytics report
    "daily-analytics-report": {
        "task": "api.tasks.email_tasks.send_daily_analytics_report",
        "schedule": crontab(hour=8, minute=0),  # 8 AM daily
    },
}

# Task routes
celery_app.conf.task_routes = {
    "api.tasks.campaign_tasks.*": {"queue": "campaigns"},
    "api.tasks.email_tasks.*": {"queue": "emails"},
    "api.tasks.webhook_tasks.*": {"queue": "webhooks"},
    "api.tasks.cleanup_tasks.*": {"queue": "cleanup"},
}
