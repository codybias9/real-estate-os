"""
Email Provider Implementations

MockEmailProvider: Uses MailHog SMTP for local development
SendGridProvider: Uses SendGrid API for production
"""
import json
import logging
import smtplib
from abc import ABC, abstractmethod
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from api.config import get_config

logger = logging.getLogger(__name__)


class EmailProvider(ABC):
    """Abstract email provider interface"""

    @abstractmethod
    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        from_email: Optional[str] = None,
        html: bool = False,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[Dict]] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Send an email

        Returns:
            Dict with message_id, status, and provider-specific data
        """
        pass


class MockEmailProvider(EmailProvider):
    """
    Mock email provider using MailHog SMTP

    Sends emails to MailHog (localhost:1025) for capture and inspection.
    Records sent emails to audit artifacts for deterministic testing.
    """

    def __init__(self):
        self.config = get_config()
        self.smtp_host = self.config.SMTP_HOST
        self.smtp_port = self.config.SMTP_PORT
        self.from_email = self.config.SMTP_FROM
        self.artifacts_dir = Path(self.config.AUDIT_ARTIFACTS_DIR) / "sent_emails"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"MockEmailProvider initialized: {self.smtp_host}:{self.smtp_port}")

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        from_email: Optional[str] = None,
        html: bool = False,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[Dict]] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """Send email via MailHog SMTP"""

        from_email = from_email or self.from_email
        message_id = f"<mock-{datetime.utcnow().timestamp()}@realtor-demo.com>"

        # Build MIME message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to
        msg['Message-ID'] = message_id

        if cc:
            msg['Cc'] = ', '.join(cc)

        # Add body
        if html:
            msg.attach(MIMEText(body, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))

        # Send via SMTP
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                recipients = [to] + (cc or []) + (bcc or [])
                server.send_message(msg, from_addr=from_email, to_addrs=recipients)

            logger.info(f"Email sent via MailHog: {to} - {subject}")

            # Record to artifacts
            artifact = {
                "message_id": message_id,
                "timestamp": datetime.utcnow().isoformat(),
                "from": from_email,
                "to": to,
                "cc": cc,
                "bcc": bcc,
                "subject": subject,
                "body": body,
                "html": html,
                "metadata": metadata,
                "status": "sent"
            }

            artifact_file = self.artifacts_dir / f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{to.replace('@', '_at_')}.json"
            with open(artifact_file, 'w') as f:
                json.dump(artifact, f, indent=2)

            return {
                "message_id": message_id,
                "status": "sent",
                "provider": "mock_smtp",
                "artifact_path": str(artifact_file)
            }

        except Exception as e:
            logger.error(f"Failed to send email via MailHog: {str(e)}")
            return {
                "message_id": message_id,
                "status": "failed",
                "provider": "mock_smtp",
                "error": str(e)
            }


class SendGridProvider(EmailProvider):
    """
    Production email provider using SendGrid API

    Requires SENDGRID_API_KEY in configuration.
    """

    def __init__(self):
        self.config = get_config()
        self.api_key = self.config.SENDGRID_API_KEY
        self.from_email = self.config.SMTP_FROM

        if not self.api_key:
            logger.warning("SendGrid API key not configured - emails will fail")

        logger.info("SendGridProvider initialized")

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        from_email: Optional[str] = None,
        html: bool = False,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[Dict]] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """Send email via SendGrid API"""

        if not self.api_key:
            logger.error("SendGrid API key not configured")
            return {
                "message_id": None,
                "status": "failed",
                "provider": "sendgrid",
                "error": "API key not configured"
            }

        # TODO: Implement actual SendGrid API call
        # from sendgrid import SendGridAPIClient
        # from sendgrid.helpers.mail import Mail

        logger.warning("SendGrid implementation pending - returning mock success")

        message_id = f"<sendgrid-{datetime.utcnow().timestamp()}@realtor-demo.com>"

        return {
            "message_id": message_id,
            "status": "sent",
            "provider": "sendgrid",
            "note": "Implementation pending"
        }
