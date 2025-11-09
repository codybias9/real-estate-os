"""
Twilio SMS and Voice Integration
Send SMS, make calls, capture recordings and transcriptions
"""
import os
from typing import Optional, Dict, Any
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
    logger.warning("Twilio credentials not configured - SMS/voice features will fail")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID else None

# ============================================================================
# SMS
# ============================================================================

def send_sms(
    to_phone: str,
    message: str,
    from_phone: Optional[str] = None,
    status_callback: Optional[str] = None,
    custom_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Send an SMS message via Twilio

    Args:
        to_phone: Recipient phone number (E.164 format: +1234567890)
        message: Message body (max 1600 chars)
        from_phone: Sender phone number (defaults to configured Twilio number)
        status_callback: Webhook URL for delivery status updates
        custom_data: Custom metadata to track with the message

    Returns:
        Dict with message SID, status, and success flag

    Raises:
        Exception: If Twilio is not configured or send fails
    """
    if not twilio_client:
        raise Exception("Twilio credentials not configured")

    if not from_phone:
        from_phone = TWILIO_PHONE_NUMBER

    if not from_phone:
        raise Exception("Twilio phone number not configured")

    try:
        # Send SMS
        message_obj = twilio_client.messages.create(
            to=to_phone,
            from_=from_phone,
            body=message,
            status_callback=status_callback
        )

        logger.info(f"SMS sent to {to_phone}: {message[:50]}... (SID: {message_obj.sid})")

        return {
            "success": True,
            "message_sid": message_obj.sid,
            "status": message_obj.status,
            "to_phone": to_phone,
            "from_phone": from_phone,
            "custom_data": custom_data
        }

    except TwilioRestException as e:
        logger.error(f"Failed to send SMS to {to_phone}: {e.msg}")
        raise Exception(f"Twilio error: {e.msg}")


def get_sms_status(message_sid: str) -> Dict[str, Any]:
    """
    Get the delivery status of an SMS message

    Args:
        message_sid: Twilio message SID

    Returns:
        Dict with status, error_code, and delivery info
    """
    if not twilio_client:
        raise Exception("Twilio credentials not configured")

    try:
        message = twilio_client.messages(message_sid).fetch()

        return {
            "message_sid": message.sid,
            "status": message.status,  # queued, sending, sent, delivered, failed, undelivered
            "error_code": message.error_code,
            "error_message": message.error_message,
            "to": message.to,
            "from": message.from_,
            "date_sent": message.date_sent,
            "date_created": message.date_created
        }

    except TwilioRestException as e:
        logger.error(f"Failed to fetch SMS status for {message_sid}: {e.msg}")
        raise


# ============================================================================
# VOICE CALLS
# ============================================================================

def make_call(
    to_phone: str,
    twiml_url: Optional[str] = None,
    twiml: Optional[str] = None,
    from_phone: Optional[str] = None,
    status_callback: Optional[str] = None,
    record: bool = True,
    transcribe: bool = True
) -> Dict[str, Any]:
    """
    Make an outbound call via Twilio

    Args:
        to_phone: Recipient phone number (E.164 format)
        twiml_url: URL that returns TwiML instructions
        twiml: TwiML instructions as string (alternative to twiml_url)
        from_phone: Caller ID (defaults to configured Twilio number)
        status_callback: Webhook URL for call status updates
        record: Whether to record the call
        transcribe: Whether to transcribe recordings

    Returns:
        Dict with call SID, status, and success flag
    """
    if not twilio_client:
        raise Exception("Twilio credentials not configured")

    if not from_phone:
        from_phone = TWILIO_PHONE_NUMBER

    if not from_phone:
        raise Exception("Twilio phone number not configured")

    if not twiml_url and not twiml:
        raise ValueError("Either twiml_url or twiml must be provided")

    try:
        call_params = {
            "to": to_phone,
            "from_": from_phone,
            "status_callback": status_callback,
            "record": record
        }

        if twiml_url:
            call_params["url"] = twiml_url
        else:
            call_params["twiml"] = twiml

        # Make call
        call = twilio_client.calls.create(**call_params)

        logger.info(f"Call initiated to {to_phone} (SID: {call.sid})")

        return {
            "success": True,
            "call_sid": call.sid,
            "status": call.status,  # queued, ringing, in-progress, completed, failed
            "to_phone": to_phone,
            "from_phone": from_phone
        }

    except TwilioRestException as e:
        logger.error(f"Failed to make call to {to_phone}: {e.msg}")
        raise Exception(f"Twilio error: {e.msg}")


def get_call_status(call_sid: str) -> Dict[str, Any]:
    """
    Get the status of a call

    Args:
        call_sid: Twilio call SID

    Returns:
        Dict with status, duration, and call details
    """
    if not twilio_client:
        raise Exception("Twilio credentials not configured")

    try:
        call = twilio_client.calls(call_sid).fetch()

        return {
            "call_sid": call.sid,
            "status": call.status,
            "duration": call.duration,
            "to": call.to,
            "from": call.from_,
            "start_time": call.start_time,
            "end_time": call.end_time,
            "price": call.price,
            "price_unit": call.price_unit
        }

    except TwilioRestException as e:
        logger.error(f"Failed to fetch call status for {call_sid}: {e.msg}")
        raise


def get_call_recording(call_sid: str) -> Optional[Dict[str, Any]]:
    """
    Get the recording URL for a call

    Args:
        call_sid: Twilio call SID

    Returns:
        Dict with recording SID, URL, and duration, or None if no recording
    """
    if not twilio_client:
        raise Exception("Twilio credentials not configured")

    try:
        recordings = twilio_client.recordings.list(call_sid=call_sid, limit=1)

        if not recordings:
            return None

        recording = recordings[0]
        recording_url = f"https://api.twilio.com{recording.uri.replace('.json', '.mp3')}"

        return {
            "recording_sid": recording.sid,
            "recording_url": recording_url,
            "duration": recording.duration,
            "status": recording.status
        }

    except TwilioRestException as e:
        logger.error(f"Failed to fetch recording for call {call_sid}: {e.msg}")
        return None


def get_call_transcript(recording_sid: str) -> Optional[Dict[str, Any]]:
    """
    Get the transcription for a recording

    Args:
        recording_sid: Twilio recording SID

    Returns:
        Dict with transcription text and status, or None if no transcription
    """
    if not twilio_client:
        raise Exception("Twilio credentials not configured")

    try:
        transcriptions = twilio_client.transcriptions.list(recording_sid=recording_sid, limit=1)

        if not transcriptions:
            return None

        transcription = transcriptions[0]

        return {
            "transcription_sid": transcription.sid,
            "transcription_text": transcription.transcription_text,
            "status": transcription.status,
            "duration": transcription.duration
        }

    except TwilioRestException as e:
        logger.error(f"Failed to fetch transcription for recording {recording_sid}: {e.msg}")
        return None


# ============================================================================
# WEBHOOK EVENT PROCESSING
# ============================================================================

def process_webhook_event(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a Twilio webhook event

    Event types (from CallStatus or MessageStatus):
    SMS: queued, sending, sent, delivered, undelivered, failed
    Call: queued, ringing, in-progress, completed, busy, failed, no-answer

    Args:
        event_data: Webhook event payload from Twilio

    Returns:
        Processed event data
    """
    event_type = event_data.get("MessageStatus") or event_data.get("CallStatus")
    message_sid = event_data.get("MessageSid")
    call_sid = event_data.get("CallSid")

    processed = {
        "event_type": event_type,
        "message_sid": message_sid,
        "call_sid": call_sid,
        "from": event_data.get("From"),
        "to": event_data.get("To"),
        "raw_event": event_data
    }

    # SMS-specific fields
    if message_sid:
        processed["sms_status"] = event_data.get("SmsStatus")
        processed["error_code"] = event_data.get("ErrorCode")

    # Call-specific fields
    if call_sid:
        processed["call_duration"] = event_data.get("CallDuration")
        processed["recording_url"] = event_data.get("RecordingUrl")
        processed["recording_sid"] = event_data.get("RecordingSid")

    return processed


# ============================================================================
# NUMBER VALIDATION
# ============================================================================

def validate_phone_number(phone: str) -> Dict[str, Any]:
    """
    Validate and lookup phone number information

    Args:
        phone: Phone number to validate

    Returns:
        Dict with validity, carrier, and number type info
    """
    if not twilio_client:
        raise Exception("Twilio credentials not configured")

    try:
        # Use Twilio Lookup API
        phone_number = twilio_client.lookups.v1.phone_numbers(phone).fetch(type=["carrier"])

        return {
            "valid": True,
            "phone_number": phone_number.phone_number,
            "country_code": phone_number.country_code,
            "carrier": phone_number.carrier.get("name") if phone_number.carrier else None,
            "type": phone_number.carrier.get("type") if phone_number.carrier else None  # mobile, landline, voip
        }

    except TwilioRestException as e:
        logger.warning(f"Phone validation failed for {phone}: {e.msg}")
        return {
            "valid": False,
            "error": e.msg
        }
