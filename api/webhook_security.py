"""
Webhook Security & Verification

Implements signature verification for external webhook endpoints
to prevent unauthorized requests and replay attacks.

Security Requirements:
- SendGrid: Verify signature using public key (Ed25519)
- Twilio: Verify X-Twilio-Signature header (HMAC-SHA1)
- Timestamp validation to prevent replay attacks
"""
import os
import hmac
import hashlib
import base64
import logging
from typing import Dict, Optional
from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# SendGrid webhook public key (get from SendGrid settings)
# Format: Base64-encoded Ed25519 public key
SENDGRID_VERIFICATION_KEY = os.getenv("SENDGRID_VERIFICATION_KEY")

# Twilio auth token (get from Twilio console)
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

# Maximum age for webhook timestamps (5 minutes)
MAX_TIMESTAMP_AGE = 300


# ============================================================================
# SENDGRID SIGNATURE VERIFICATION
# ============================================================================

def verify_sendgrid_signature(
    request: Request,
    payload: bytes,
    signature: str,
    timestamp: str
) -> bool:
    """
    Verify SendGrid webhook signature using Ed25519 public key

    SendGrid signs webhooks with Ed25519 signature.
    See: https://docs.sendgrid.com/for-developers/tracking-events/getting-started-event-webhook-security-features

    Args:
        request: FastAPI Request object
        payload: Raw request body (bytes)
        signature: Signature from X-Twilio-Email-Event-Webhook-Signature header
        timestamp: Timestamp from X-Twilio-Email-Event-Webhook-Timestamp header

    Returns:
        True if signature is valid

    Raises:
        HTTPException: If verification fails
    """
    if not SENDGRID_VERIFICATION_KEY:
        logger.warning("SENDGRID_VERIFICATION_KEY not set - skipping verification")
        # In development, allow without verification if key not set
        # In production, this should FAIL
        if os.getenv("ENVIRONMENT") == "production":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="SendGrid verification key not configured"
            )
        return True

    # Verify timestamp to prevent replay attacks
    try:
        timestamp_int = int(timestamp)
        import time
        current_time = int(time.time())

        if abs(current_time - timestamp_int) > MAX_TIMESTAMP_AGE:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Webhook timestamp too old or invalid"
            )
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook timestamp"
        )

    try:
        # SendGrid uses Ed25519 signature
        # Verification requires nacl (PyNaCl) library
        from nacl.signing import VerifyKey
        from nacl.encoding import Base64Encoder
        from nacl.exceptions import BadSignatureError

        # Decode public key
        verify_key = VerifyKey(
            SENDGRID_VERIFICATION_KEY,
            encoder=Base64Encoder
        )

        # Construct signed payload: timestamp + payload
        signed_payload = timestamp.encode('utf-8') + payload

        # Decode signature
        signature_bytes = base64.b64decode(signature)

        # Verify signature
        try:
            verify_key.verify(signed_payload, signature_bytes)
            return True
        except BadSignatureError:
            logger.error("SendGrid signature verification failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )

    except ImportError:
        logger.error("PyNaCl library not installed. Install with: pip install pynacl")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Signature verification not available"
        )
    except Exception as e:
        logger.error(f"SendGrid signature verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Signature verification failed"
        )


async def verify_sendgrid_webhook(request: Request):
    """
    FastAPI dependency for SendGrid webhook verification

    Usage:
        @router.post("/webhooks/sendgrid", dependencies=[Depends(verify_sendgrid_webhook)])
        async def sendgrid_webhook(request: Request):
            ...
    """
    # Get signature and timestamp from headers
    signature = request.headers.get("X-Twilio-Email-Event-Webhook-Signature")
    timestamp = request.headers.get("X-Twilio-Email-Event-Webhook-Timestamp")

    if not signature or not timestamp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing webhook signature or timestamp"
        )

    # Get raw body
    body = await request.body()

    # Verify signature
    verify_sendgrid_signature(request, body, signature, timestamp)


# ============================================================================
# TWILIO SIGNATURE VERIFICATION
# ============================================================================

def verify_twilio_signature(
    url: str,
    params: Dict[str, str],
    signature: str
) -> bool:
    """
    Verify Twilio webhook signature

    Twilio signs requests with HMAC-SHA1 using your auth token.
    See: https://www.twilio.com/docs/usage/webhooks/webhooks-security

    Args:
        url: Full URL of webhook endpoint (including https://)
        params: POST parameters (form data)
        signature: X-Twilio-Signature header value

    Returns:
        True if signature is valid

    Raises:
        HTTPException: If verification fails
    """
    if not TWILIO_AUTH_TOKEN:
        logger.warning("TWILIO_AUTH_TOKEN not set - skipping verification")
        # In development, allow without verification if token not set
        # In production, this should FAIL
        if os.getenv("ENVIRONMENT") == "production":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Twilio auth token not configured"
            )
        return True

    try:
        # Construct data string: URL + sorted params
        # Twilio's algorithm:
        # 1. Take the full URL (e.g., https://mycompany.com/webhook)
        # 2. Sort parameters alphabetically
        # 3. Append each parameter name=value to the URL
        # 4. Sign with HMAC-SHA1 using auth token
        # 5. Base64 encode the result

        data_string = url

        # Sort parameters by key
        for key in sorted(params.keys()):
            data_string += key + params[key]

        # Create HMAC-SHA1 signature
        computed_signature = base64.b64encode(
            hmac.new(
                TWILIO_AUTH_TOKEN.encode('utf-8'),
                data_string.encode('utf-8'),
                hashlib.sha1
            ).digest()
        ).decode('utf-8')

        # Compare signatures (constant-time comparison to prevent timing attacks)
        if not hmac.compare_digest(computed_signature, signature):
            logger.error("Twilio signature verification failed")
            logger.debug(f"Expected: {computed_signature}")
            logger.debug(f"Received: {signature}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )

        return True

    except Exception as e:
        logger.error(f"Twilio signature verification error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Signature verification failed"
        )


async def verify_twilio_webhook(request: Request):
    """
    FastAPI dependency for Twilio webhook verification

    Usage:
        @router.post("/webhooks/twilio/sms", dependencies=[Depends(verify_twilio_webhook)])
        async def twilio_sms_webhook(request: Request):
            ...
    """
    # Get signature from header
    signature = request.headers.get("X-Twilio-Signature")

    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Twilio signature"
        )

    # Get full URL (Twilio needs the exact URL including protocol)
    url = str(request.url)

    # Get form parameters
    form_data = await request.form()
    params = dict(form_data)

    # Verify signature
    verify_twilio_signature(url, params, signature)


# ============================================================================
# WEBHOOK DEDUPLICATION & ORDERING
# ============================================================================

class WebhookDeduplicator:
    """
    Prevent duplicate webhook processing using in-memory cache

    In production, use Redis for distributed deduplication

    Prevents:
    - Duplicate webhook delivery
    - Out-of-order processing (e.g., 'opened' before 'delivered')
    """

    def __init__(self):
        # Simple in-memory cache (use Redis in production)
        self._processed_webhooks: Dict[str, float] = {}

    def is_duplicate(self, webhook_id: str, retention_seconds: int = 3600) -> bool:
        """
        Check if webhook was already processed

        Args:
            webhook_id: Unique webhook identifier (e.g., message_id + event_type)
            retention_seconds: How long to remember processed webhooks

        Returns:
            True if duplicate (already processed)
        """
        import time
        now = time.time()

        # Clean up old entries
        expired_keys = [
            k for k, v in self._processed_webhooks.items()
            if now - v > retention_seconds
        ]
        for key in expired_keys:
            del self._processed_webhooks[key]

        # Check if already processed
        if webhook_id in self._processed_webhooks:
            logger.warning(f"Duplicate webhook detected: {webhook_id}")
            return True

        # Mark as processed
        self._processed_webhooks[webhook_id] = now
        return False


# Global deduplicator instance (use Redis in production)
webhook_deduplicator = WebhookDeduplicator()


def check_webhook_ordering(
    communication_id: int,
    new_event: str,
    current_status: Optional[str] = None
) -> bool:
    """
    Check if webhook event ordering is valid

    Prevents invalid transitions like:
    - 'opened' before 'delivered'
    - 'clicked' before 'opened'

    Args:
        communication_id: Communication ID
        new_event: New event type (e.g., 'opened', 'delivered')
        current_status: Current communication status

    Returns:
        True if transition is valid

    Email event order:
    queued → sending → sent → delivered → opened → clicked

    Invalid:
    - opened before delivered
    - clicked before delivered
    """
    # Define valid state transitions
    valid_transitions = {
        "queued": ["sending", "sent", "delivered", "bounced", "failed"],
        "sending": ["sent", "delivered", "bounced", "failed"],
        "sent": ["delivered", "bounced", "failed"],
        "delivered": ["opened", "clicked", "bounced"],  # Can still bounce after delivery attempt
        "opened": ["clicked"],
        "clicked": [],  # Terminal state (for success)
        "bounced": [],  # Terminal state (for failure)
        "failed": [],   # Terminal state (for failure)
    }

    if not current_status:
        # No current status, allow any event
        return True

    allowed = valid_transitions.get(current_status, [])

    if new_event not in allowed:
        logger.warning(
            f"Invalid webhook event order for communication {communication_id}: "
            f"{current_status} → {new_event}"
        )
        # Don't reject, but log and potentially query provider API to reconcile
        return False

    return True


# ============================================================================
# WEBHOOK RETRY & DLQ
# ============================================================================

async def handle_webhook_failure(
    webhook_type: str,
    event_data: Dict,
    error: Exception
):
    """
    Handle webhook processing failure

    On failure:
    1. Log error with full context
    2. Send to DLQ for manual review
    3. Alert monitoring system

    Args:
        webhook_type: Type of webhook (e.g., 'sendgrid', 'twilio')
        event_data: Raw event data
        error: Exception that occurred
    """
    logger.error(
        f"Webhook processing failed: {webhook_type}",
        extra={
            "webhook_type": webhook_type,
            "event_data": event_data,
            "error": str(error),
            "error_type": type(error).__name__
        }
    )

    # TODO: Send to DLQ (Dead Letter Queue)
    # In production, use:
    # - RabbitMQ DLQ
    # - AWS SQS DLQ
    # - Redis Streams

    # TODO: Alert monitoring
    # - Send to Sentry
    # - Trigger PagerDuty alert
    # - Log to monitoring system
