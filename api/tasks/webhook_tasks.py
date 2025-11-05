"""Webhook delivery Celery tasks."""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from celery import Task
import asyncio

from .celery_app import celery_app
from ..database import SessionLocal
from ..models import WebhookLog
from ..services.webhook import webhook_service


class DatabaseTask(Task):
    """Base task that provides database session."""

    _db = None

    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(bind=True, max_retries=3)
def send_webhook(self, url: str, event_type: str, payload: dict, organization_id: int):
    """
    Send webhook to external URL.

    Args:
        url: Webhook endpoint URL
        event_type: Event type (e.g., 'property.created')
        payload: Event payload
        organization_id: Organization ID
    """
    try:
        success = asyncio.run(
            webhook_service.send_webhook(url, event_type, payload, organization_id)
        )

        if not success:
            # Retry on failure
            raise self.retry(countdown=60 * (self.request.retries + 1))

        return {"url": url, "event_type": event_type, "success": True}

    except Exception as e:
        if self.request.retries >= self.max_retries:
            return {"url": url, "event_type": event_type, "success": False, "error": str(e)}
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))


@celery_app.task(base=DatabaseTask, bind=True)
def retry_failed_webhooks(self):
    """Retry failed webhooks that are within retry limits."""
    db = self.db

    try:
        # Get failed webhooks from the last 24 hours that haven't exceeded max retries
        one_day_ago = datetime.utcnow() - timedelta(days=1)

        failed_webhooks = db.query(WebhookLog).filter(
            WebhookLog.success == False,
            WebhookLog.created_at >= one_day_ago,
            WebhookLog.retry_count < 5,  # Max 5 retries
        ).all()

        results = []

        for webhook in failed_webhooks:
            try:
                # Parse payload back to dict
                import json
                payload = json.loads(webhook.payload)

                # Increment retry count
                webhook.retry_count += 1
                db.commit()

                # Retry sending
                success = asyncio.run(
                    webhook_service.send_webhook(
                        url=webhook.url,
                        event_type=webhook.event_type,
                        payload=payload.get("data", {}),
                        organization_id=webhook.organization_id,
                        retry_count=webhook.retry_count,
                    )
                )

                results.append({
                    "webhook_id": webhook.id,
                    "url": webhook.url,
                    "success": success,
                    "retry_count": webhook.retry_count,
                })

            except Exception as e:
                results.append({
                    "webhook_id": webhook.id,
                    "url": webhook.url,
                    "success": False,
                    "error": str(e),
                })

        return {
            "total_retried": len(failed_webhooks),
            "results": results,
        }

    except Exception as e:
        return {"error": str(e)}


@celery_app.task
def send_property_created_webhook(url: str, property_data: dict, organization_id: int):
    """
    Send property.created webhook.

    Args:
        url: Webhook URL
        property_data: Property data
        organization_id: Organization ID
    """
    return send_webhook.delay(url, "property.created", property_data, organization_id)


@celery_app.task
def send_lead_created_webhook(url: str, lead_data: dict, organization_id: int):
    """
    Send lead.created webhook.

    Args:
        url: Webhook URL
        lead_data: Lead data
        organization_id: Organization ID
    """
    return send_webhook.delay(url, "lead.created", lead_data, organization_id)


@celery_app.task
def send_deal_closed_webhook(url: str, deal_data: dict, organization_id: int):
    """
    Send deal.closed webhook.

    Args:
        url: Webhook URL
        deal_data: Deal data
        organization_id: Organization ID
    """
    return send_webhook.delay(url, "deal.closed", deal_data, organization_id)


@celery_app.task
def send_campaign_completed_webhook(url: str, campaign_data: dict, organization_id: int):
    """
    Send campaign.completed webhook.

    Args:
        url: Webhook URL
        campaign_data: Campaign data
        organization_id: Organization ID
    """
    return send_webhook.delay(url, "campaign.completed", campaign_data, organization_id)


@celery_app.task(base=DatabaseTask, bind=True)
def cleanup_old_webhook_logs(self, days: int = 30):
    """
    Clean up old webhook logs.

    Args:
        days: Number of days to keep logs (default: 30)
    """
    db = self.db

    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Delete old successful webhooks
        deleted_count = db.query(WebhookLog).filter(
            WebhookLog.created_at < cutoff_date,
            WebhookLog.success == True,
        ).delete()

        db.commit()

        return {
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
        }

    except Exception as e:
        db.rollback()
        return {"error": str(e)}
