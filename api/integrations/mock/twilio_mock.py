"""
Mock Twilio SMS and Voice Integration

Simulates Twilio behavior without requiring credentials.
Perfect for demos, testing, and development.
"""
import uuid
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

# ============================================================================
# MOCK DATA STORAGE (in-memory for demo purposes)
# ============================================================================

# Store sent messages in memory for inspection
_mock_messages = []
_mock_calls = []


def _generate_mock_sid(prefix: str = "SM") -> str:
    """Generate a realistic Twilio SID"""
    return f"{prefix}{uuid.uuid4().hex[:32]}"


def _phone_hash(phone: str) -> str:
    """Create a deterministic hash from phone number for transcript consistency"""
    return hashlib.md5(phone.encode()).hexdigest()[:8]


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
    Mock send SMS - simulates Twilio behavior

    Args:
        to_phone: Recipient phone number (E.164 format: +1234567890)
        message: Message body (max 1600 chars)
        from_phone: Sender phone number (defaults to mock number)
        status_callback: Webhook URL for delivery status updates (logged but not called)
        custom_data: Custom metadata to track with the message

    Returns:
        Dict with message SID, status, and success flag
    """
    if not from_phone:
        from_phone = "+15551234567"  # Mock Twilio number

    message_sid = _generate_mock_sid("SM")

    mock_message = {
        "sid": message_sid,
        "to": to_phone,
        "from": from_phone,
        "body": message,
        "status": "delivered",  # Instantly delivered in mock mode
        "sent_at": datetime.utcnow().isoformat(),
        "status_callback": status_callback,
        "custom_data": custom_data,
        "num_segments": (len(message) // 160) + 1,
        "price": -0.0079,  # Mock price per segment
        "price_unit": "USD"
    }

    _mock_messages.append(mock_message)

    logger.info(
        f"[MOCK] SMS sent to {to_phone}: {message[:50]}... (SID: {message_sid})"
    )

    return {
        "success": True,
        "message_sid": message_sid,
        "status": "delivered",
        "to_phone": to_phone,
        "from_phone": from_phone,
        "custom_data": custom_data
    }


def get_sms_status(message_sid: str) -> Dict[str, Any]:
    """
    Mock get SMS delivery status

    Args:
        message_sid: Twilio message SID

    Returns:
        Dict with status, error_code, and delivery info
    """
    # Find message in mock storage
    for msg in _mock_messages:
        if msg["sid"] == message_sid:
            return {
                "sid": message_sid,
                "status": msg["status"],
                "error_code": None,
                "error_message": None,
                "date_sent": msg["sent_at"],
                "date_updated": msg["sent_at"],
                "num_segments": msg["num_segments"],
                "price": msg["price"],
                "price_unit": msg["price_unit"]
            }

    # Message not found - simulate Twilio 404
    logger.warning(f"[MOCK] Message SID {message_sid} not found")
    return {
        "sid": message_sid,
        "status": "unknown",
        "error_code": 20404,
        "error_message": "Message not found",
        "date_sent": None,
        "date_updated": None
    }


# ============================================================================
# VOICE CALLS
# ============================================================================

def make_call(
    to_phone: str,
    from_phone: Optional[str] = None,
    twiml_url: Optional[str] = None,
    twiml: Optional[str] = None,
    status_callback: Optional[str] = None,
    record: bool = False,
    transcribe: bool = False,
    custom_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Mock make outbound call - simulates Twilio behavior

    Args:
        to_phone: Recipient phone number (E.164 format)
        from_phone: Caller ID (defaults to mock number)
        twiml_url: URL to fetch TwiML instructions
        twiml: TwiML instructions directly
        status_callback: Webhook URL for call status updates
        record: Whether to record the call
        transcribe: Whether to transcribe the recording
        custom_data: Custom metadata

    Returns:
        Dict with call SID, status, and details
    """
    if not from_phone:
        from_phone = "+15551234567"

    call_sid = _generate_mock_sid("CA")

    # Simulate realistic call progression
    mock_call = {
        "sid": call_sid,
        "to": to_phone,
        "from": from_phone,
        "status": "completed",  # Instantly completed in mock
        "direction": "outbound-api",
        "duration": 47,  # Deterministic duration based on phone hash
        "price": -0.013,
        "price_unit": "USD",
        "twiml_url": twiml_url,
        "record": record,
        "transcribe": transcribe,
        "status_callback": status_callback,
        "custom_data": custom_data,
        "start_time": datetime.utcnow().isoformat(),
        "end_time": datetime.utcnow().isoformat(),
    }

    # If recording/transcription requested, generate mock recording SID
    if record:
        mock_call["recording_sid"] = _generate_mock_sid("RE")
        mock_call["recording_url"] = f"https://api.twilio.com/mock/recordings/{mock_call['recording_sid']}.mp3"

        if transcribe:
            mock_call["transcription_sid"] = _generate_mock_sid("TR")

    _mock_calls.append(mock_call)

    logger.info(
        f"[MOCK] Call initiated to {to_phone} (SID: {call_sid}, Duration: {mock_call['duration']}s)"
    )

    return {
        "success": True,
        "call_sid": call_sid,
        "status": "completed",
        "to_phone": to_phone,
        "from_phone": from_phone,
        "duration": mock_call["duration"],
        "recording_sid": mock_call.get("recording_sid"),
        "recording_url": mock_call.get("recording_url"),
        "custom_data": custom_data
    }


def get_call_status(call_sid: str) -> Dict[str, Any]:
    """
    Mock get call status

    Args:
        call_sid: Twilio call SID

    Returns:
        Dict with status and call details
    """
    for call in _mock_calls:
        if call["sid"] == call_sid:
            return {
                "sid": call_sid,
                "status": call["status"],
                "duration": call["duration"],
                "price": call["price"],
                "price_unit": call["price_unit"],
                "start_time": call["start_time"],
                "end_time": call["end_time"]
            }

    logger.warning(f"[MOCK] Call SID {call_sid} not found")
    return {
        "sid": call_sid,
        "status": "unknown",
        "error": "Call not found"
    }


def get_call_transcript(call_sid: str) -> Dict[str, Any]:
    """
    Mock get call transcription

    Returns a realistic fake transcript based on the call SID.
    In real Twilio, this would return the actual speech-to-text.

    Args:
        call_sid: Twilio call SID

    Returns:
        Dict with transcription text, confidence, and metadata
    """
    # Find call
    call = None
    for c in _mock_calls:
        if c["sid"] == call_sid:
            call = c
            break

    if not call:
        logger.warning(f"[MOCK] Call SID {call_sid} not found for transcription")
        return {
            "error": "Call not found",
            "transcription_text": None,
            "confidence": 0.0
        }

    if not call.get("transcribe"):
        return {
            "error": "Call was not set to transcribe",
            "transcription_text": None,
            "confidence": 0.0
        }

    # Generate deterministic mock transcript based on phone number
    phone_hash = _phone_hash(call["to"])

    # Realistic mock transcripts for property outreach
    mock_transcripts = [
        "Hi, this is calling about the property at 123 Main Street. I'm interested in making an offer. Can you give me a call back?",
        "Hello, I received your letter about my house. I'm not ready to sell right now, but maybe in six months. Thanks.",
        "Yes, I'm the owner. I might be interested in selling. What kind of offer are you thinking?",
        "Not interested, please remove me from your list. Thank you.",
        "Hi, this is the property owner. Can you tell me more about how this works? I've never sold a house directly before.",
        "I'm interested, but I need to talk to my spouse first. Can you send me some more information?",
        "The property needs a lot of work. I'm open to offers but it would have to be cash.",
        "I already have a realtor, but if your offer is better I'd consider it. What are you offering?",
    ]

    # Use hash to deterministically select transcript
    transcript_index = int(phone_hash, 16) % len(mock_transcripts)
    transcript_text = mock_transcripts[transcript_index]

    # Confidence based on hash
    confidence = 0.85 + (int(phone_hash[:4], 16) % 15) / 100

    logger.info(f"[MOCK] Generated transcript for call {call_sid}: {transcript_text[:50]}...")

    return {
        "transcription_sid": call.get("transcription_sid", _generate_mock_sid("TR")),
        "transcription_text": transcript_text,
        "transcription_status": "completed",
        "confidence": round(confidence, 2),
        "duration": call["duration"],
        "price": -0.05,  # Mock transcription price
        "price_unit": "USD"
    }


def get_recording_url(recording_sid: str) -> str:
    """
    Mock get recording URL

    Returns a mock URL for the recording audio file.

    Args:
        recording_sid: Twilio recording SID

    Returns:
        Mock URL to recording file
    """
    return f"https://api.twilio.com/mock/recordings/{recording_sid}.mp3"


# ============================================================================
# INSPECTION / DEBUG HELPERS
# ============================================================================

def get_all_mock_messages() -> list:
    """Get all mock messages sent (for testing/debugging)"""
    return _mock_messages.copy()


def get_all_mock_calls() -> list:
    """Get all mock calls made (for testing/debugging)"""
    return _mock_calls.copy()


def clear_mock_data():
    """Clear all mock data (for testing)"""
    global _mock_messages, _mock_calls
    _mock_messages = []
    _mock_calls = []
    logger.info("[MOCK] Cleared all mock Twilio data")
