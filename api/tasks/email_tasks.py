"""
Email Background Tasks
Async email sending and sequence processing
"""
from celery import shared_task, group
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, List, Optional

from api.celery_app import celery_app, get_db_session
from api.integrations import send_email, send_sms
from db.models import (
    Property, Communication, CommunicationType, CommunicationDirection,
    Template, PropertyTimeline, CadenceRule, Team
)

logger = logging.getLogger(__name__)

# ============================================================================
# EMAIL SENDING TASKS
# ============================================================================

@celery_app.task(bind=True, name="api.tasks.email_tasks.send_email_async")
def send_email_async(
    self,
    to_email: str,
    subject: str,
    body: str,
    property_id: Optional[int] = None,
    template_id: Optional[int] = None,
    from_email: Optional[str] = None,
    from_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send email asynchronously

    Args:
        to_email: Recipient email
        subject: Email subject
        body: Email body
        property_id: Related property ID
        template_id: Template used
        from_email: Sender email
        from_name: Sender name

    Returns:
        Dict with send result and communication ID
    """
    logger.info(f"Sending email to {to_email}: {subject}")

    with next(get_db_session()) as db:
        try:
            # Send email via SendGrid
            send_result = send_email(
                to_email=to_email,
                subject=subject,
                body_text=body,
                body_html=body.replace("\n", "<br>"),
                from_email=from_email,
                from_name=from_name,
                custom_args={
                    "property_id": str(property_id) if property_id else None,
                    "task_id": self.request.id
                },
                categories=["async_email"]
            )

            # Create communication record
            communication = Communication(
                property_id=property_id,
                template_id=template_id,
                type=CommunicationType.EMAIL,
                direction=CommunicationDirection.OUTBOUND,
                from_address=from_email or "team@real-estate-os.com",
                to_address=to_email,
                subject=subject,
                body=body,
                sent_at=datetime.utcnow(),
                metadata={
                    "sendgrid_message_id": send_result.get("message_id"),
                    "task_id": self.request.id
                }
            )
            db.add(communication)
            db.flush()

            # Update property if applicable
            if property_id:
                property = db.query(Property).filter(Property.id == property_id).first()
                if property:
                    property.last_contact_date = datetime.utcnow()
                    property.touch_count = (property.touch_count or 0) + 1

                    # Create timeline event
                    timeline = PropertyTimeline(
                        property_id=property_id,
                        event_type="email_sent",
                        event_title="Email Sent",
                        event_description=f"Email sent to {to_email}: {subject}",
                        communication_id=communication.id,
                        metadata={"task_id": self.request.id}
                    )
                    db.add(timeline)

            db.commit()

            logger.info(f"Email sent successfully to {to_email}")

            return {
                "success": True,
                "communication_id": communication.id,
                "message_id": send_result.get("message_id"),
                "to_email": to_email
            }

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            db.rollback()
            raise


@celery_app.task(bind=True, name="api.tasks.email_tasks.send_bulk_emails")
def send_bulk_emails(
    self,
    recipients: List[Dict[str, Any]],
    subject: str,
    body_template: str,
    template_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Send bulk emails with personalization

    Args:
        recipients: List of dicts with to_email, property_id, personalization data
        subject: Email subject (can include {{variables}})
        body_template: Email body template
        template_id: Template ID

    Returns:
        Dict with batch results
    """
    logger.info(f"Sending bulk email to {len(recipients)} recipients")

    # Create a group of parallel email tasks
    email_tasks = []

    for recipient in recipients:
        # Personalize subject and body
        personalized_subject = subject
        personalized_body = body_template

        for key, value in recipient.get("personalization", {}).items():
            personalized_subject = personalized_subject.replace(f"{{{{{key}}}}}", str(value))
            personalized_body = personalized_body.replace(f"{{{{{key}}}}}", str(value))

        # Create async task
        task = send_email_async.s(
            to_email=recipient["to_email"],
            subject=personalized_subject,
            body=personalized_body,
            property_id=recipient.get("property_id"),
            template_id=template_id
        )
        email_tasks.append(task)

    # Execute all email tasks in parallel
    job = group(email_tasks)
    result = job.apply_async()

    logger.info(f"Queued {len(email_tasks)} bulk emails")

    return {
        "success": True,
        "total": len(recipients),
        "group_id": result.id
    }


# ============================================================================
# EMAIL SEQUENCE TASKS
# ============================================================================

@celery_app.task(bind=True, name="api.tasks.email_tasks.process_scheduled_sequences")
def process_scheduled_sequences(self) -> Dict[str, Any]:
    """
    Process scheduled email sequences

    Checks for properties in cadence that are due for outreach

    This runs every 15 minutes via Celery Beat
    """
    logger.info("Processing scheduled email sequences")

    with next(get_db_session()) as db:
        results = {
            "sequences_processed": 0,
            "emails_sent": 0,
            "errors": 0
        }

        # Get all active cadence rules
        cadence_rules = db.query(CadenceRule).filter(CadenceRule.is_active == True).all()

        for rule in cadence_rules:
            try:
                # Find properties that match rule trigger
                properties = _find_properties_for_cadence(db, rule)

                for property in properties:
                    # Check if property cadence is paused
                    if property.cadence_paused:
                        continue

                    # Check if property has opted out
                    if property.has_opted_out:
                        continue

                    # Execute cadence action
                    if rule.action_type == "send_email":
                        _execute_email_cadence(db, property, rule)
                        results["emails_sent"] += 1

                    elif rule.action_type == "send_sms":
                        _execute_sms_cadence(db, property, rule)
                        results["emails_sent"] += 1

                results["sequences_processed"] += 1

            except Exception as e:
                logger.error(f"Failed to process cadence rule {rule.id}: {str(e)}")
                results["errors"] += 1

        db.commit()

        logger.info(f"Sequence processing complete: {results['emails_sent']} emails sent")

        return results


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _find_properties_for_cadence(db, rule: CadenceRule) -> List[Property]:
    """
    Find properties that match cadence rule trigger

    Trigger types:
    - days_since_last_contact
    - stage_changed
    - no_reply_after_x_days
    - new_property
    """
    from sqlalchemy import and_

    trigger_on = rule.trigger_on
    query = db.query(Property)

    if trigger_on == "days_since_last_contact":
        days = rule.action_params.get("days", 7)
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = query.filter(
            and_(
                Property.last_contact_date < cutoff_date,
                Property.cadence_paused == False,
                Property.has_opted_out == False
            )
        )

    elif trigger_on == "no_reply_after_x_days":
        days = rule.action_params.get("days", 14)
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = query.filter(
            and_(
                Property.last_contact_date < cutoff_date,
                Property.reply_count == 0,
                Property.touch_count > 0,
                Property.cadence_paused == False
            )
        )

    elif trigger_on == "new_property":
        hours = rule.action_params.get("hours", 24)
        cutoff_date = datetime.utcnow() - timedelta(hours=hours)

        query = query.filter(
            and_(
                Property.created_at >= cutoff_date,
                Property.touch_count == 0
            )
        )

    # Limit to team if specified
    if rule.team_id:
        query = query.filter(Property.team_id == rule.team_id)

    return query.limit(100).all()  # Process max 100 per rule per run


def _execute_email_cadence(db, property: Property, rule: CadenceRule):
    """
    Execute email cadence action
    """
    template_id = rule.action_params.get("template_id")

    if template_id:
        template = db.query(Template).filter(Template.id == template_id).first()
        if not template:
            logger.error(f"Template {template_id} not found for cadence rule {rule.id}")
            return

        subject = template.subject_template or "Follow-up"
        body = template.body_template

        # Personalize
        subject = subject.replace("{{property.address}}", property.address)
        body = body.replace("{{property.address}}", property.address)
        body = body.replace("{{owner_name}}", property.owner_name or "Property Owner")

        # Send async
        send_email_async.delay(
            to_email=property.owner_mailing_address or "owner@example.com",
            subject=subject,
            body=body,
            property_id=property.id,
            template_id=template_id
        )


def _execute_sms_cadence(db, property: Property, rule: CadenceRule):
    """
    Execute SMS cadence action
    """
    message = rule.action_params.get("message", "Follow-up from Real Estate OS")

    # Personalize
    message = message.replace("{{property.address}}", property.address)
    message = message.replace("{{owner_name}}", property.owner_name or "")

    # Send SMS (if phone number available)
    if property.owner_mailing_address and "+1" in property.owner_mailing_address:
        try:
            send_sms(
                to_phone=property.owner_mailing_address,
                message=message
            )

            # Create communication record
            communication = Communication(
                property_id=property.id,
                type=CommunicationType.SMS,
                direction=CommunicationDirection.OUTBOUND,
                to_address=property.owner_mailing_address,
                body=message,
                sent_at=datetime.utcnow(),
                metadata={"cadence_rule_id": rule.id}
            )
            db.add(communication)

        except Exception as e:
            logger.error(f"Failed to send SMS for cadence: {str(e)}")
