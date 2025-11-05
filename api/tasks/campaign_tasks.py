"""Campaign-related Celery tasks."""

from datetime import datetime
from sqlalchemy.orm import Session
from celery import Task
import asyncio

from .celery_app import celery_app
from ..database import SessionLocal
from ..models import Campaign, CampaignRecipient, Lead
from ..models.campaign import CampaignType, CampaignStatus
from ..services.email import email_service
from ..services.sms import sms_service


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


@celery_app.task(base=DatabaseTask, bind=True, max_retries=3)
def send_campaign(self, campaign_id: int):
    """
    Send campaign messages to all pending recipients.

    Args:
        campaign_id: Campaign ID to send
    """
    db = self.db

    try:
        # Get campaign
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return {"error": "Campaign not found"}

        # Update campaign status
        campaign.status = CampaignStatus.IN_PROGRESS
        campaign.started_at = datetime.utcnow()
        db.commit()

        # Get pending recipients
        recipients = db.query(CampaignRecipient).filter(
            CampaignRecipient.campaign_id == campaign_id,
            CampaignRecipient.status == "pending",
        ).all()

        sent_count = 0
        failed_count = 0

        # Send to each recipient
        for recipient in recipients:
            try:
                success = False

                if campaign.campaign_type == CampaignType.EMAIL:
                    # Send email
                    success = asyncio.run(
                        email_service.send_campaign_email(
                            to_email=recipient.email,
                            subject=campaign.subject,
                            content=campaign.content,
                            first_name=recipient.first_name,
                        )
                    )
                elif campaign.campaign_type == CampaignType.SMS:
                    # Send SMS
                    success = asyncio.run(
                        sms_service.send_campaign_sms(
                            to_number=recipient.phone,
                            content=campaign.content,
                            first_name=recipient.first_name,
                        )
                    )

                if success:
                    recipient.status = "sent"
                    recipient.sent_at = datetime.utcnow()
                    # Simulate delivery
                    recipient.status = "delivered"
                    recipient.delivered_at = datetime.utcnow()
                    campaign.sent_count += 1
                    campaign.delivered_count += 1
                    sent_count += 1
                else:
                    recipient.status = "failed"
                    recipient.error_message = "Failed to send"
                    failed_count += 1

            except Exception as e:
                recipient.status = "failed"
                recipient.error_message = str(e)
                failed_count += 1

            db.commit()

        # Update campaign status
        campaign.status = CampaignStatus.COMPLETED
        campaign.completed_at = datetime.utcnow()
        db.commit()

        return {
            "campaign_id": campaign_id,
            "sent": sent_count,
            "failed": failed_count,
            "total": len(recipients),
        }

    except Exception as e:
        # Mark campaign as failed
        if campaign:
            campaign.status = CampaignStatus.PAUSED
            db.commit()

        raise self.retry(exc=e, countdown=60)


@celery_app.task(base=DatabaseTask, bind=True)
def process_campaign_recipient(self, recipient_id: int):
    """
    Process a single campaign recipient.

    Args:
        recipient_id: Recipient ID to process
    """
    db = self.db

    try:
        recipient = db.query(CampaignRecipient).filter(
            CampaignRecipient.id == recipient_id
        ).first()

        if not recipient:
            return {"error": "Recipient not found"}

        campaign = db.query(Campaign).filter(
            Campaign.id == recipient.campaign_id
        ).first()

        if not campaign:
            return {"error": "Campaign not found"}

        # Send message
        success = False

        if campaign.campaign_type == CampaignType.EMAIL:
            success = asyncio.run(
                email_service.send_campaign_email(
                    to_email=recipient.email,
                    subject=campaign.subject,
                    content=campaign.content,
                    first_name=recipient.first_name,
                )
            )
        elif campaign.campaign_type == CampaignType.SMS:
            success = asyncio.run(
                sms_service.send_campaign_sms(
                    to_number=recipient.phone,
                    content=campaign.content,
                    first_name=recipient.first_name,
                )
            )

        if success:
            recipient.status = "sent"
            recipient.sent_at = datetime.utcnow()
            recipient.status = "delivered"
            recipient.delivered_at = datetime.utcnow()
            campaign.sent_count += 1
            campaign.delivered_count += 1
        else:
            recipient.status = "failed"
            recipient.error_message = "Failed to send"

        db.commit()

        return {"recipient_id": recipient_id, "success": success}

    except Exception as e:
        recipient.status = "failed"
        recipient.error_message = str(e)
        db.commit()
        raise


@celery_app.task(base=DatabaseTask)
def update_campaign_metrics(campaign_id: int):
    """
    Update campaign metrics and statistics.

    Args:
        campaign_id: Campaign ID to update
    """
    db = SessionLocal()

    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return {"error": "Campaign not found"}

        # Count recipients by status
        recipients = db.query(CampaignRecipient).filter(
            CampaignRecipient.campaign_id == campaign_id
        ).all()

        campaign.total_recipients = len(recipients)
        campaign.sent_count = sum(1 for r in recipients if r.sent_at is not None)
        campaign.delivered_count = sum(1 for r in recipients if r.delivered_at is not None)
        campaign.opened_count = sum(1 for r in recipients if r.opened_at is not None)
        campaign.clicked_count = sum(1 for r in recipients if r.clicked_at is not None)
        campaign.bounced_count = sum(1 for r in recipients if r.bounced_at is not None)
        campaign.unsubscribed_count = sum(1 for r in recipients if r.unsubscribed_at is not None)

        db.commit()

        return {
            "campaign_id": campaign_id,
            "total": campaign.total_recipients,
            "sent": campaign.sent_count,
            "delivered": campaign.delivered_count,
        }

    finally:
        db.close()


@celery_app.task
def schedule_campaign_send(campaign_id: int, send_at: datetime):
    """
    Schedule a campaign to be sent at a specific time.

    Args:
        campaign_id: Campaign ID to send
        send_at: When to send the campaign
    """
    # Calculate delay
    now = datetime.utcnow()
    delay_seconds = (send_at - now).total_seconds()

    if delay_seconds > 0:
        # Schedule the task
        send_campaign.apply_async(args=[campaign_id], countdown=delay_seconds)
    else:
        # Send immediately
        send_campaign.delay(campaign_id)

    return {"campaign_id": campaign_id, "scheduled_at": send_at.isoformat()}
