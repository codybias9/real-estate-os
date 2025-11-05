"""Celery tasks package."""

from .celery_app import celery_app
from .campaign_tasks import (
    send_campaign,
    process_campaign_recipient,
    update_campaign_metrics,
    schedule_campaign_send,
)
from .email_tasks import (
    send_welcome_email,
    send_lead_assignment_notification,
    send_deal_update_notification,
    send_daily_analytics_report,
    send_password_reset_email,
    send_verification_email,
    send_bulk_notification,
)
from .webhook_tasks import (
    send_webhook,
    retry_failed_webhooks,
    send_property_created_webhook,
    send_lead_created_webhook,
    send_deal_closed_webhook,
    send_campaign_completed_webhook,
)
from .cleanup_tasks import (
    cleanup_idempotency_keys,
    cleanup_audit_logs,
    cleanup_old_webhook_logs,
    cleanup_soft_deleted_records,
    vacuum_database,
    generate_backup_metadata,
)

__all__ = [
    "celery_app",
    # Campaign tasks
    "send_campaign",
    "process_campaign_recipient",
    "update_campaign_metrics",
    "schedule_campaign_send",
    # Email tasks
    "send_welcome_email",
    "send_lead_assignment_notification",
    "send_deal_update_notification",
    "send_daily_analytics_report",
    "send_password_reset_email",
    "send_verification_email",
    "send_bulk_notification",
    # Webhook tasks
    "send_webhook",
    "retry_failed_webhooks",
    "send_property_created_webhook",
    "send_lead_created_webhook",
    "send_deal_closed_webhook",
    "send_campaign_completed_webhook",
    # Cleanup tasks
    "cleanup_idempotency_keys",
    "cleanup_audit_logs",
    "cleanup_old_webhook_logs",
    "cleanup_soft_deleted_records",
    "vacuum_database",
    "generate_backup_metadata",
]
