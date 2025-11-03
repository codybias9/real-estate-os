"""
SendGrid Email Integration
Send transactional emails and track delivery events
"""
import os
from typing import Optional, List, Dict, Any
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, Email, To, Content, Personalization,
    CustomArg, Category, Attachment
)
import base64
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "no-reply@real-estate-os.com")
SENDGRID_FROM_NAME = os.getenv("SENDGRID_FROM_NAME", "Real Estate OS")

if not SENDGRID_API_KEY:
    logger.warning("SENDGRID_API_KEY not configured - email sending will fail")

sg = SendGridAPIClient(SENDGRID_API_KEY) if SENDGRID_API_KEY else None

# ============================================================================
# EMAIL SENDING
# ============================================================================

def send_email(
    to_email: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    from_email: Optional[str] = None,
    from_name: Optional[str] = None,
    reply_to: Optional[str] = None,
    attachments: Optional[List[Dict[str, Any]]] = None,
    custom_args: Optional[Dict[str, str]] = None,
    categories: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Send an email via SendGrid

    Args:
        to_email: Recipient email address
        subject: Email subject line
        body_text: Plain text body
        body_html: HTML body (optional)
        from_email: Sender email (defaults to configured sender)
        from_name: Sender name (defaults to configured name)
        reply_to: Reply-to email address
        attachments: List of attachments with filename, content, type
        custom_args: Custom arguments for tracking (e.g., property_id, communication_id)
        categories: Categories for organizing emails in SendGrid

    Returns:
        Dict with status_code, message_id, and success flag

    Raises:
        Exception: If SendGrid is not configured or send fails
    """
    if not sg:
        raise Exception("SendGrid API key not configured")

    try:
        # Create message
        message = Mail(
            from_email=Email(from_email or SENDGRID_FROM_EMAIL, from_name or SENDGRID_FROM_NAME),
            to_emails=To(to_email),
            subject=subject,
            plain_text_content=Content("text/plain", body_text),
            html_content=Content("text/html", body_html) if body_html else None
        )

        # Add reply-to
        if reply_to:
            message.reply_to = Email(reply_to)

        # Add custom arguments for tracking
        if custom_args:
            for key, value in custom_args.items():
                message.custom_arg = CustomArg(key, str(value))

        # Add categories
        if categories:
            for category in categories:
                message.category = Category(category)

        # Add attachments
        if attachments:
            for attachment_data in attachments:
                attachment = Attachment()
                attachment.file_content = base64.b64encode(attachment_data["content"]).decode()
                attachment.file_type = attachment_data.get("type", "application/pdf")
                attachment.file_name = attachment_data["filename"]
                attachment.disposition = "attachment"
                message.attachment = attachment

        # Enable tracking
        message.tracking_settings = {
            "click_tracking": {"enable": True},
            "open_tracking": {"enable": True},
            "subscription_tracking": {"enable": False}
        }

        # Send email
        response = sg.send(message)

        logger.info(f"Email sent to {to_email}: {subject} (status: {response.status_code})")

        return {
            "success": response.status_code in [200, 201, 202],
            "status_code": response.status_code,
            "message_id": response.headers.get("X-Message-Id"),
            "to_email": to_email
        }

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        raise


def send_templated_email(
    to_email: str,
    template_id: str,
    dynamic_data: Dict[str, Any],
    from_email: Optional[str] = None,
    from_name: Optional[str] = None,
    custom_args: Optional[Dict[str, str]] = None,
    categories: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Send an email using a SendGrid dynamic template

    Args:
        to_email: Recipient email address
        template_id: SendGrid template ID
        dynamic_data: Template variable substitutions
        from_email: Sender email (defaults to configured sender)
        from_name: Sender name (defaults to configured name)
        custom_args: Custom arguments for tracking
        categories: Categories for organizing emails

    Returns:
        Dict with status_code, message_id, and success flag
    """
    if not sg:
        raise Exception("SendGrid API key not configured")

    try:
        message = Mail(
            from_email=Email(from_email or SENDGRID_FROM_EMAIL, from_name or SENDGRID_FROM_NAME),
            to_emails=To(to_email)
        )

        # Set template ID
        message.template_id = template_id

        # Add dynamic template data
        personalization = Personalization()
        personalization.add_to(To(to_email))
        personalization.dynamic_template_data = dynamic_data
        message.add_personalization(personalization)

        # Add custom arguments
        if custom_args:
            for key, value in custom_args.items():
                message.custom_arg = CustomArg(key, str(value))

        # Add categories
        if categories:
            for category in categories:
                message.category = Category(category)

        # Send email
        response = sg.send(message)

        logger.info(f"Templated email sent to {to_email} using template {template_id} (status: {response.status_code})")

        return {
            "success": response.status_code in [200, 201, 202],
            "status_code": response.status_code,
            "message_id": response.headers.get("X-Message-Id"),
            "to_email": to_email
        }

    except Exception as e:
        logger.error(f"Failed to send templated email to {to_email}: {str(e)}")
        raise


# ============================================================================
# WEBHOOK EVENT PROCESSING
# ============================================================================

def process_webhook_event(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a SendGrid webhook event

    Event types:
    - delivered: Email successfully delivered
    - open: Email opened by recipient
    - click: Link clicked in email
    - bounce: Email bounced
    - dropped: Email dropped by SendGrid
    - spam_report: Marked as spam
    - unsubscribe: Recipient unsubscribed

    Args:
        event_data: Webhook event payload from SendGrid

    Returns:
        Processed event data with extracted fields
    """
    event_type = event_data.get("event")
    email = event_data.get("email")
    timestamp = event_data.get("timestamp")

    # Extract custom args (property_id, communication_id, etc.)
    custom_args = {}
    for key, value in event_data.items():
        if key.startswith("property_id") or key.startswith("communication_id"):
            custom_args[key] = value

    processed = {
        "event_type": event_type,
        "email": email,
        "timestamp": timestamp,
        "custom_args": custom_args,
        "raw_event": event_data
    }

    # Extract event-specific data
    if event_type == "bounce":
        processed["bounce_reason"] = event_data.get("reason")
        processed["bounce_type"] = event_data.get("type")  # "blocked" or "bounce"

    elif event_type == "click":
        processed["url"] = event_data.get("url")

    elif event_type == "spam_report":
        processed["spam_reason"] = event_data.get("reason")

    return processed


# ============================================================================
# SUPPRESSION LIST MANAGEMENT
# ============================================================================

def add_to_suppression_list(email: str, reason: str = "bounced") -> bool:
    """
    Add email to suppression list to prevent future sends

    Args:
        email: Email address to suppress
        reason: Reason for suppression (bounced, spam, unsubscribe)

    Returns:
        True if successfully added
    """
    if not sg:
        logger.warning("SendGrid not configured - cannot add to suppression list")
        return False

    try:
        # In production, call SendGrid's suppression API
        # For now, just log
        logger.info(f"Would add {email} to suppression list (reason: {reason})")
        return True
    except Exception as e:
        logger.error(f"Failed to add {email} to suppression list: {str(e)}")
        return False


def check_suppression_list(email: str) -> bool:
    """
    Check if email is on suppression list

    Args:
        email: Email address to check

    Returns:
        True if email is suppressed, False otherwise
    """
    if not sg:
        return False

    try:
        # In production, call SendGrid's suppression API
        # For now, return False
        return False
    except Exception as e:
        logger.error(f"Failed to check suppression list for {email}: {str(e)}")
        return False
