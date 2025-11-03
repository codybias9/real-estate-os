"""
Webhooks Router
Handle incoming webhooks from SendGrid, Twilio, and other external services
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime
import logging

from api.database import get_db
from db.models import (
    Communication, Property, PropertyTimeline
)
from api.integrations.sendgrid_client import process_webhook_event as process_sendgrid_event
from api.integrations.twilio_client import process_webhook_event as process_twilio_event
from api.sse import (
    emit_property_update,
    emit_timeline_event,
    emit_communication_received
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

# ============================================================================
# SENDGRID WEBHOOKS
# ============================================================================

@router.post("/sendgrid")
async def sendgrid_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle SendGrid webhook events

    Events received:
    - delivered: Email successfully delivered
    - open: Email opened by recipient
    - click: Link clicked in email
    - bounce: Email bounced
    - dropped: Email dropped by SendGrid
    - spam_report: Marked as spam
    - unsubscribe: Recipient unsubscribed

    SendGrid sends events in batches as JSON array
    """
    try:
        events = await request.json()

        if not isinstance(events, list):
            events = [events]

        processed_count = 0

        for event_data in events:
            try:
                # Process event
                processed_event = process_sendgrid_event(event_data)
                event_type = processed_event.get("event_type")

                # Extract custom args (property_id, communication_id)
                property_id = processed_event.get("custom_args", {}).get("property_id")
                communication_id = processed_event.get("custom_args", {}).get("communication_id")

                # Find communication by SendGrid message ID or custom args
                communication = None
                if communication_id:
                    communication = db.query(Communication).filter(
                        Communication.id == int(communication_id)
                    ).first()

                if not communication and property_id:
                    # Try to find by property_id and email
                    email = processed_event.get("email")
                    communication = db.query(Communication).filter(
                        Communication.property_id == int(property_id),
                        Communication.to_address == email
                    ).order_by(Communication.sent_at.desc()).first()

                if communication:
                    # Update communication based on event type
                    if event_type == "delivered":
                        # Email was delivered
                        pass

                    elif event_type == "open":
                        communication.opened_at = datetime.fromtimestamp(processed_event.get("timestamp", 0))

                        # Update property engagement
                        property = db.query(Property).filter(
                            Property.id == communication.property_id
                        ).first()
                        if property:
                            property.email_opens = (property.email_opens or 0) + 1

                            # Emit real-time event
                            await emit_property_update(
                                property_id=property.id,
                                team_id=property.team_id,
                                data={
                                    "event": "email_opened",
                                    "email_opens": property.email_opens,
                                    "communication_id": communication.id
                                }
                            )

                    elif event_type == "click":
                        communication.clicked_at = datetime.fromtimestamp(processed_event.get("timestamp", 0))

                        # Update property engagement
                        property = db.query(Property).filter(
                            Property.id == communication.property_id
                        ).first()
                        if property:
                            property.email_clicks = (property.email_clicks or 0) + 1

                            # Emit real-time event
                            await emit_property_update(
                                property_id=property.id,
                                team_id=property.team_id,
                                data={
                                    "event": "email_clicked",
                                    "email_clicks": property.email_clicks,
                                    "communication_id": communication.id,
                                    "url": processed_event.get("url")
                                }
                            )

                    elif event_type == "bounce":
                        communication.bounced_at = datetime.fromtimestamp(processed_event.get("timestamp", 0))
                        communication.metadata["bounce_reason"] = processed_event.get("bounce_reason")
                        communication.metadata["bounce_type"] = processed_event.get("bounce_type")

                        # Create timeline event
                        if communication.property_id:
                            timeline = PropertyTimeline(
                                property_id=communication.property_id,
                                event_type="email_bounced",
                                event_title="Email Bounced",
                                event_description=f"Email to {communication.to_address} bounced: {processed_event.get('bounce_reason')}",
                                communication_id=communication.id
                            )
                            db.add(timeline)

                    elif event_type == "spam_report":
                        # Mark property owner as opted out
                        property = db.query(Property).filter(
                            Property.id == communication.property_id
                        ).first()
                        if property:
                            property.has_opted_out = True

                            # Create timeline event
                            timeline = PropertyTimeline(
                                property_id=property.id,
                                event_type="spam_report",
                                event_title="Marked as Spam",
                                event_description=f"Email marked as spam by {communication.to_address}",
                                communication_id=communication.id
                            )
                            db.add(timeline)

                    elif event_type == "unsubscribe":
                        # Mark property owner as opted out
                        property = db.query(Property).filter(
                            Property.id == communication.property_id
                        ).first()
                        if property:
                            property.has_opted_out = True
                            property.cadence_paused = True

                            # Create timeline event
                            timeline = PropertyTimeline(
                                property_id=property.id,
                                event_type="unsubscribed",
                                event_title="Unsubscribed",
                                event_description=f"{communication.to_address} unsubscribed from emails",
                                communication_id=communication.id
                            )
                            db.add(timeline)

                    db.commit()
                    processed_count += 1

                else:
                    logger.warning(f"Communication not found for SendGrid event: {event_data}")

            except Exception as e:
                logger.error(f"Failed to process SendGrid event: {str(e)}")
                logger.error(f"Event data: {event_data}")
                continue

        logger.info(f"Processed {processed_count}/{len(events)} SendGrid webhook events")

        return {"success": True, "processed": processed_count, "total": len(events)}

    except Exception as e:
        logger.error(f"Failed to process SendGrid webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


# ============================================================================
# TWILIO WEBHOOKS
# ============================================================================

@router.post("/twilio/sms")
async def twilio_sms_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Twilio SMS status webhooks

    Events received:
    - queued: SMS queued for sending
    - sending: SMS is being sent
    - sent: SMS sent to carrier
    - delivered: SMS delivered to recipient
    - undelivered: SMS failed to deliver
    - failed: SMS send failed
    """
    try:
        # Parse form data (Twilio sends webhooks as form-encoded)
        form_data = await request.form()
        event_data = dict(form_data)

        # Process event
        processed_event = process_twilio_event(event_data)
        message_sid = processed_event.get("message_sid")
        status = processed_event.get("event_type")

        # Find communication by Twilio message SID
        communication = db.query(Communication).filter(
            Communication.metadata["twilio_message_sid"].astext == message_sid
        ).first()

        if communication:
            # Update communication status based on event
            if status in ["delivered"]:
                # SMS was delivered
                pass

            elif status in ["undelivered", "failed"]:
                # SMS failed
                communication.metadata["sms_error_code"] = processed_event.get("error_code")
                communication.bounced_at = datetime.utcnow()

                # Create timeline event
                timeline = PropertyTimeline(
                    property_id=communication.property_id,
                    event_type="sms_failed",
                    event_title="SMS Failed",
                    event_description=f"SMS to {communication.to_address} failed: {processed_event.get('error_code')}",
                    communication_id=communication.id
                )
                db.add(timeline)

            db.commit()

            logger.info(f"Processed Twilio SMS webhook: {message_sid} -> {status}")

            return {"success": True}

        else:
            logger.warning(f"Communication not found for Twilio SMS: {message_sid}")
            return {"success": False, "error": "Communication not found"}

    except Exception as e:
        logger.error(f"Failed to process Twilio SMS webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@router.post("/twilio/voice")
async def twilio_voice_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Twilio voice call status webhooks

    Events received:
    - queued: Call queued
    - ringing: Call ringing
    - in-progress: Call answered
    - completed: Call completed
    - busy: Recipient busy
    - failed: Call failed
    - no-answer: No answer
    """
    try:
        form_data = await request.form()
        event_data = dict(form_data)

        processed_event = process_twilio_event(event_data)
        call_sid = processed_event.get("call_sid")
        status = processed_event.get("event_type")
        duration = processed_event.get("call_duration")

        # Find communication by Twilio call SID
        communication = db.query(Communication).filter(
            Communication.metadata["twilio_call_sid"].astext == call_sid
        ).first()

        if communication:
            # Update communication
            if status == "completed":
                communication.duration_seconds = int(duration) if duration else None

                # If recording URL available, store it
                recording_url = processed_event.get("recording_url")
                if recording_url:
                    communication.metadata["recording_url"] = recording_url

            elif status in ["busy", "failed", "no-answer"]:
                communication.metadata["call_status"] = status

            # Create timeline event
            timeline = PropertyTimeline(
                property_id=communication.property_id,
                event_type=f"call_{status}",
                event_title=f"Call {status.replace('_', ' ').title()}",
                event_description=f"Call to {communication.to_address}: {status}",
                communication_id=communication.id
            )
            db.add(timeline)

            db.commit()

            logger.info(f"Processed Twilio voice webhook: {call_sid} -> {status}")

            return {"success": True}

        else:
            logger.warning(f"Communication not found for Twilio call: {call_sid}")
            return {"success": False, "error": "Communication not found"}

    except Exception as e:
        logger.error(f"Failed to process Twilio voice webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


# ============================================================================
# TWILIO TRANSCRIPTION WEBHOOK
# ============================================================================

@router.post("/twilio/transcription")
async def twilio_transcription_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Twilio transcription completion webhooks
    """
    try:
        form_data = await request.form()
        event_data = dict(form_data)

        recording_sid = event_data.get("RecordingSid")
        transcription_text = event_data.get("TranscriptionText")
        transcription_status = event_data.get("TranscriptionStatus")

        # Find communication by recording SID
        communication = db.query(Communication).filter(
            Communication.metadata["twilio_recording_sid"].astext == recording_sid
        ).first()

        if communication:
            # Store transcription
            communication.call_transcript = transcription_text

            # TODO: Use AI to analyze transcript for:
            # - Sentiment
            # - Key points
            # - Action items
            # For now, just store the raw transcript

            db.commit()

            logger.info(f"Stored transcription for recording: {recording_sid}")

            return {"success": True}

        else:
            logger.warning(f"Communication not found for recording: {recording_sid}")
            return {"success": False, "error": "Communication not found"}

    except Exception as e:
        logger.error(f"Failed to process transcription webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")
