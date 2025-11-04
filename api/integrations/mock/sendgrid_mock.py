"""
Mock SendGrid Email Integration

Simulates SendGrid behavior without requiring API keys.
Perfect for demos, testing, and development.
"""
import uuid
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

# ============================================================================
# MOCK DATA STORAGE (in-memory for demo purposes)
# ============================================================================

# Store sent emails in memory for inspection
_mock_emails = []


def _generate_mock_message_id() -> str:
    """Generate a realistic SendGrid message ID"""
    return f"{uuid.uuid4().hex}.{uuid.uuid4().hex[:8]}@sendgrid.net"


def _email_hash(email: str) -> str:
    """Create deterministic hash from email for engagement simulation"""
    return hashlib.md5(email.encode()).hexdigest()[:8]


def _simulate_email_engagement(to_email: str) -> Dict[str, Any]:
    """
    Simulate realistic email engagement metrics based on email hash

    Returns open rate, click rate, bounce status, etc.
    """
    email_hash_int = int(_email_hash(to_email), 16)

    # Deterministic engagement based on email
    open_rate = (email_hash_int % 100) / 100  # 0-99%
    click_rate = (email_hash_int % 40) / 100  # 0-39%
    bounce_chance = email_hash_int % 100  # 0-99

    # Simulate delivery status
    if bounce_chance < 3:  # 3% bounce rate
        status = "bounced"
        event = "bounce"
    elif bounce_chance < 5:  # 2% spam complaints
        status = "spam"
        event = "spamreport"
    else:
        status = "delivered"
        event = "delivered"

        # Simulate opens and clicks
        if open_rate > 0.3:  # 70% open rate
            event = "open"
        if click_rate > 0.2:  # 20% click rate
            event = "click"

    return {
        "status": status,
        "event": event,
        "open_rate": round(open_rate, 2),
        "click_rate": round(click_rate, 2),
        "bounced": bounce_chance < 3,
        "spam": bounce_chance < 5
    }


# ============================================================================
# EMAIL SENDING
# ============================================================================

def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    from_email: Optional[str] = None,
    from_name: Optional[str] = None,
    reply_to: Optional[str] = None,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    attachments: Optional[List[Dict[str, Any]]] = None,
    custom_args: Optional[Dict[str, str]] = None,
    categories: Optional[List[str]] = None,
    send_at: Optional[int] = None,
    track_opens: bool = True,
    track_clicks: bool = True
) -> Dict[str, Any]:
    """
    Mock send email via SendGrid

    Args:
        to_email: Recipient email address
        subject: Email subject line
        html_content: HTML email body
        from_email: Sender email (defaults to noreply@demo.com)
        from_name: Sender name
        reply_to: Reply-to email
        cc: CC recipients
        bcc: BCC recipients
        attachments: File attachments
        custom_args: Custom tracking arguments
        categories: Email categories for analytics
        send_at: Unix timestamp for scheduled sending
        track_opens: Enable open tracking
        track_clicks: Enable click tracking

    Returns:
        Dict with message_id, status, and delivery info
    """
    if not from_email:
        from_email = "noreply@demo.com"
    if not from_name:
        from_name = "Real Estate OS"

    message_id = _generate_mock_message_id()

    # Simulate engagement
    engagement = _simulate_email_engagement(to_email)

    mock_email = {
        "message_id": message_id,
        "to": to_email,
        "from": from_email,
        "from_name": from_name,
        "subject": subject,
        "html_content": html_content,
        "reply_to": reply_to,
        "cc": cc or [],
        "bcc": bcc or [],
        "attachments": attachments or [],
        "custom_args": custom_args or {},
        "categories": categories or [],
        "send_at": send_at,
        "track_opens": track_opens,
        "track_clicks": track_clicks,
        "status": engagement["status"],
        "event": engagement["event"],
        "sent_at": datetime.utcnow().isoformat(),
        "delivered_at": datetime.utcnow().isoformat() if engagement["status"] == "delivered" else None,
        "opened_at": datetime.utcnow().isoformat() if engagement["event"] == "open" else None,
        "clicked_at": datetime.utcnow().isoformat() if engagement["event"] == "click" else None,
        "bounced": engagement["bounced"],
        "spam": engagement["spam"]
    }

    _mock_emails.append(mock_email)

    logger.info(
        f"[MOCK] Email sent to {to_email}: '{subject}' "
        f"(ID: {message_id}, Status: {engagement['status']}, Event: {engagement['event']})"
    )

    return {
        "success": True,
        "message_id": message_id,
        "status": engagement["status"],
        "to_email": to_email,
        "from_email": from_email,
        "custom_args": custom_args,
        "event": engagement["event"]
    }


def send_templated_email(
    to_email: str,
    template_id: str,
    dynamic_data: Dict[str, Any],
    from_email: Optional[str] = None,
    from_name: Optional[str] = None,
    reply_to: Optional[str] = None,
    custom_args: Optional[Dict[str, str]] = None,
    categories: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Mock send email using SendGrid template

    Args:
        to_email: Recipient email address
        template_id: SendGrid template ID
        dynamic_data: Template substitution data
        from_email: Sender email
        from_name: Sender name
        reply_to: Reply-to email
        custom_args: Custom tracking arguments
        categories: Email categories

    Returns:
        Dict with message_id, status, and delivery info
    """
    if not from_email:
        from_email = "noreply@demo.com"
    if not from_name:
        from_name = "Real Estate OS"

    message_id = _generate_mock_message_id()

    # Simulate engagement
    engagement = _simulate_email_engagement(to_email)

    # Generate subject from dynamic data
    subject = dynamic_data.get("subject", f"Template {template_id}")

    mock_email = {
        "message_id": message_id,
        "to": to_email,
        "from": from_email,
        "from_name": from_name,
        "subject": subject,
        "template_id": template_id,
        "dynamic_data": dynamic_data,
        "reply_to": reply_to,
        "custom_args": custom_args or {},
        "categories": categories or [],
        "status": engagement["status"],
        "event": engagement["event"],
        "sent_at": datetime.utcnow().isoformat(),
        "delivered_at": datetime.utcnow().isoformat() if engagement["status"] == "delivered" else None,
        "opened_at": datetime.utcnow().isoformat() if engagement["event"] == "open" else None,
        "clicked_at": datetime.utcnow().isoformat() if engagement["event"] == "click" else None,
        "bounced": engagement["bounced"],
        "spam": engagement["spam"]
    }

    _mock_emails.append(mock_email)

    logger.info(
        f"[MOCK] Templated email sent to {to_email} using template {template_id} "
        f"(ID: {message_id}, Status: {engagement['status']})"
    )

    return {
        "success": True,
        "message_id": message_id,
        "status": engagement["status"],
        "to_email": to_email,
        "from_email": from_email,
        "template_id": template_id,
        "custom_args": custom_args,
        "event": engagement["event"]
    }


# ============================================================================
# EMAIL STATUS & WEBHOOKS
# ============================================================================

def get_email_status(message_id: str) -> Dict[str, Any]:
    """
    Mock get email delivery status

    Args:
        message_id: SendGrid message ID

    Returns:
        Dict with delivery status and events
    """
    for email in _mock_emails:
        if email["message_id"] == message_id:
            return {
                "message_id": message_id,
                "status": email["status"],
                "event": email["event"],
                "sent_at": email["sent_at"],
                "delivered_at": email.get("delivered_at"),
                "opened_at": email.get("opened_at"),
                "clicked_at": email.get("clicked_at"),
                "bounced": email["bounced"],
                "spam": email["spam"]
            }

    logger.warning(f"[MOCK] Email message ID {message_id} not found")
    return {
        "message_id": message_id,
        "status": "unknown",
        "error": "Message not found"
    }


def simulate_webhook_event(message_id: str, event_type: str) -> Dict[str, Any]:
    """
    Simulate a SendGrid webhook event

    Used for testing webhook handlers without actual SendGrid events.

    Args:
        message_id: SendGrid message ID
        event_type: Event type (delivered, open, click, bounce, etc.)

    Returns:
        Mock webhook payload
    """
    # Find email
    email = None
    for e in _mock_emails:
        if e["message_id"] == message_id:
            email = e
            break

    if not email:
        return {"error": "Message not found"}

    # Generate realistic webhook payload
    webhook_payload = {
        "email": email["to"],
        "timestamp": int(datetime.utcnow().timestamp()),
        "event": event_type,
        "sg_message_id": message_id,
        "sg_event_id": f"evt_{uuid.uuid4().hex[:16]}",
        "category": email.get("categories", []),
        "custom_args": email.get("custom_args", {})
    }

    # Add event-specific fields
    if event_type == "bounce":
        webhook_payload.update({
            "reason": "550 5.1.1 The email account that you tried to reach does not exist",
            "status": "5.1.1",
            "type": "bounce"
        })
    elif event_type == "spamreport":
        webhook_payload.update({
            "type": "spamreport"
        })
    elif event_type == "click":
        webhook_payload.update({
            "url": "https://example.com/property/123",
            "url_offset": {"index": 0, "type": "html"}
        })
    elif event_type == "open":
        webhook_payload.update({
            "useragent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    logger.info(f"[MOCK] Simulated webhook event: {event_type} for {message_id}")

    return webhook_payload


# ============================================================================
# DELIVERABILITY & REPUTATION
# ============================================================================

def check_email_validation(email: str) -> Dict[str, Any]:
    """
    Mock email validation (checks if email is valid format)

    In real SendGrid, this would check:
    - Valid syntax
    - Domain MX records
    - Mailbox existence
    - Spam trap detection
    - Role-based addresses

    Args:
        email: Email address to validate

    Returns:
        Validation results
    """
    import re

    # Basic email regex
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    is_valid = bool(re.match(email_pattern, email))

    # Deterministic quality score based on email
    quality_score = (int(_email_hash(email), 16) % 50 + 50) / 100  # 50-100%

    # Detect role-based addresses
    role_based = any(email.startswith(role) for role in
                    ['admin@', 'info@', 'support@', 'sales@', 'noreply@'])

    return {
        "email": email,
        "is_valid": is_valid,
        "quality_score": round(quality_score, 2),
        "role_based": role_based,
        "disposable": False,  # Mock: no disposable detection
        "spam_trap": False,   # Mock: no spam trap detection
        "mx_found": is_valid,
        "suggestion": None    # Mock: no typo suggestions
    }


def get_deliverability_stats(category: Optional[str] = None) -> Dict[str, Any]:
    """
    Mock get deliverability statistics

    Args:
        category: Filter by email category

    Returns:
        Aggregate stats (delivered, opened, clicked, bounced, etc.)
    """
    # Filter emails by category if provided
    emails = _mock_emails
    if category:
        emails = [e for e in emails if category in e.get("categories", [])]

    if not emails:
        return {
            "total_sent": 0,
            "delivered": 0,
            "opened": 0,
            "clicked": 0,
            "bounced": 0,
            "spam": 0,
            "delivery_rate": 0.0,
            "open_rate": 0.0,
            "click_rate": 0.0,
            "bounce_rate": 0.0
        }

    total = len(emails)
    delivered = sum(1 for e in emails if e["status"] == "delivered")
    opened = sum(1 for e in emails if e.get("opened_at"))
    clicked = sum(1 for e in emails if e.get("clicked_at"))
    bounced = sum(1 for e in emails if e["bounced"])
    spam = sum(1 for e in emails if e["spam"])

    return {
        "total_sent": total,
        "delivered": delivered,
        "opened": opened,
        "clicked": clicked,
        "bounced": bounced,
        "spam": spam,
        "delivery_rate": round(delivered / total, 2) if total > 0 else 0.0,
        "open_rate": round(opened / delivered, 2) if delivered > 0 else 0.0,
        "click_rate": round(clicked / delivered, 2) if delivered > 0 else 0.0,
        "bounce_rate": round(bounced / total, 2) if total > 0 else 0.0
    }


# ============================================================================
# INSPECTION / DEBUG HELPERS
# ============================================================================

def get_all_mock_emails() -> list:
    """Get all mock emails sent (for testing/debugging)"""
    return _mock_emails.copy()


def get_mock_emails_by_recipient(email: str) -> list:
    """Get all emails sent to a specific recipient"""
    return [e for e in _mock_emails if e["to"] == email]


def get_mock_emails_by_category(category: str) -> list:
    """Get all emails in a specific category"""
    return [e for e in _mock_emails if category in e.get("categories", [])]


def clear_mock_data():
    """Clear all mock email data (for testing)"""
    global _mock_emails
    _mock_emails = []
    logger.info("[MOCK] Cleared all mock SendGrid data")
