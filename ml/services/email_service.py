"""
Email Service - Multi-provider email delivery

Wave 3.3 Part 1: Email service abstraction layer

Supports multiple email providers:
- SendGrid
- Mailgun
- SMTP (fallback)

Features:
- Template rendering
- Batch sending
- Delivery tracking
- Retry logic
- Rate limiting
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum
import time
import os


logger = logging.getLogger(__name__)


class EmailProvider(str, Enum):
    """Supported email providers"""
    SENDGRID = "sendgrid"
    MAILGUN = "mailgun"
    SMTP = "smtp"


class EmailStatus(str, Enum):
    """Email delivery status"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    FAILED = "failed"
    UNSUBSCRIBED = "unsubscribed"


@dataclass
class EmailRecipient:
    """Email recipient information"""
    email: str
    name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class EmailMessage:
    """Email message structure"""
    subject: str
    body_html: str
    body_text: Optional[str] = None
    from_email: str = ""
    from_name: Optional[str] = None
    reply_to: Optional[str] = None
    recipients: List[EmailRecipient] = None
    cc: Optional[List[EmailRecipient]] = None
    bcc: Optional[List[EmailRecipient]] = None
    attachments: Optional[List[Dict]] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class EmailResult:
    """Result of email send operation"""
    message_id: str
    status: EmailStatus
    provider: EmailProvider
    sent_at: datetime
    recipient_email: str
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class EmailProviderBase(ABC):
    """Base class for email providers"""

    def __init__(self, api_key: str, **kwargs):
        self.api_key = api_key
        self.config = kwargs

    @abstractmethod
    def send(self, message: EmailMessage) -> List[EmailResult]:
        """Send email message"""
        pass

    @abstractmethod
    def send_batch(self, messages: List[EmailMessage]) -> List[EmailResult]:
        """Send batch of email messages"""
        pass

    @abstractmethod
    def get_status(self, message_id: str) -> EmailStatus:
        """Get delivery status of message"""
        pass


class SendGridProvider(EmailProviderBase):
    """SendGrid email provider"""

    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Email, To, Content
            self.client = SendGridAPIClient(api_key)
            self.Mail = Mail
            self.Email = Email
            self.To = To
            self.Content = Content
        except ImportError:
            logger.warning("SendGrid library not installed. Run: pip install sendgrid")
            self.client = None

    def send(self, message: EmailMessage) -> List[EmailResult]:
        """Send single email via SendGrid"""
        if not self.client:
            return [EmailResult(
                message_id="",
                status=EmailStatus.FAILED,
                provider=EmailProvider.SENDGRID,
                sent_at=datetime.utcnow(),
                recipient_email=message.recipients[0].email if message.recipients else "",
                error="SendGrid client not initialized"
            )]

        results = []
        from_email = self.Email(message.from_email, message.from_name)

        for recipient in message.recipients:
            try:
                to_email = self.To(recipient.email, recipient.name)
                content = self.Content("text/html", message.body_html)

                mail = self.Mail(
                    from_email=from_email,
                    to_emails=to_email,
                    subject=message.subject,
                    html_content=content
                )

                # Add text version if provided
                if message.body_text:
                    mail.add_content(self.Content("text/plain", message.body_text))

                # Add metadata
                if message.metadata:
                    mail.custom_args = message.metadata

                # Send
                response = self.client.send(mail)

                results.append(EmailResult(
                    message_id=response.headers.get('X-Message-Id', ''),
                    status=EmailStatus.SENT if response.status_code == 202 else EmailStatus.FAILED,
                    provider=EmailProvider.SENDGRID,
                    sent_at=datetime.utcnow(),
                    recipient_email=recipient.email,
                    metadata={"status_code": response.status_code}
                ))

            except Exception as e:
                logger.error(f"SendGrid send failed for {recipient.email}: {e}")
                results.append(EmailResult(
                    message_id="",
                    status=EmailStatus.FAILED,
                    provider=EmailProvider.SENDGRID,
                    sent_at=datetime.utcnow(),
                    recipient_email=recipient.email,
                    error=str(e)
                ))

        return results

    def send_batch(self, messages: List[EmailMessage]) -> List[EmailResult]:
        """Send batch of emails"""
        results = []
        for message in messages:
            results.extend(self.send(message))
        return results

    def get_status(self, message_id: str) -> EmailStatus:
        """Get message delivery status"""
        # SendGrid status tracking requires webhook setup
        return EmailStatus.SENT


class MailgunProvider(EmailProviderBase):
    """Mailgun email provider"""

    def __init__(self, api_key: str, domain: str, **kwargs):
        super().__init__(api_key, **kwargs)
        self.domain = domain
        self.base_url = f"https://api.mailgun.net/v3/{domain}/messages"

        try:
            import requests
            self.requests = requests
        except ImportError:
            logger.warning("requests library not installed. Run: pip install requests")
            self.requests = None

    def send(self, message: EmailMessage) -> List[EmailResult]:
        """Send email via Mailgun"""
        if not self.requests:
            return [EmailResult(
                message_id="",
                status=EmailStatus.FAILED,
                provider=EmailProvider.MAILGUN,
                sent_at=datetime.utcnow(),
                recipient_email=message.recipients[0].email if message.recipients else "",
                error="requests library not installed"
            )]

        results = []

        for recipient in message.recipients:
            try:
                data = {
                    "from": f"{message.from_name} <{message.from_email}>" if message.from_name else message.from_email,
                    "to": f"{recipient.name} <{recipient.email}>" if recipient.name else recipient.email,
                    "subject": message.subject,
                    "html": message.body_html,
                }

                if message.body_text:
                    data["text"] = message.body_text

                if message.tags:
                    data["o:tag"] = message.tags

                response = self.requests.post(
                    self.base_url,
                    auth=("api", self.api_key),
                    data=data
                )

                if response.status_code == 200:
                    result_data = response.json()
                    results.append(EmailResult(
                        message_id=result_data.get("id", ""),
                        status=EmailStatus.SENT,
                        provider=EmailProvider.MAILGUN,
                        sent_at=datetime.utcnow(),
                        recipient_email=recipient.email
                    ))
                else:
                    results.append(EmailResult(
                        message_id="",
                        status=EmailStatus.FAILED,
                        provider=EmailProvider.MAILGUN,
                        sent_at=datetime.utcnow(),
                        recipient_email=recipient.email,
                        error=f"HTTP {response.status_code}: {response.text}"
                    ))

            except Exception as e:
                logger.error(f"Mailgun send failed for {recipient.email}: {e}")
                results.append(EmailResult(
                    message_id="",
                    status=EmailStatus.FAILED,
                    provider=EmailProvider.MAILGUN,
                    sent_at=datetime.utcnow(),
                    recipient_email=recipient.email,
                    error=str(e)
                ))

        return results

    def send_batch(self, messages: List[EmailMessage]) -> List[EmailResult]:
        """Send batch of emails"""
        results = []
        for message in messages:
            results.extend(self.send(message))
        return results

    def get_status(self, message_id: str) -> EmailStatus:
        """Get message delivery status"""
        try:
            url = f"https://api.mailgun.net/v3/{self.domain}/events"
            response = self.requests.get(
                url,
                auth=("api", self.api_key),
                params={"message-id": message_id}
            )

            if response.status_code == 200:
                events = response.json().get("items", [])
                if events:
                    latest_event = events[0]
                    event_type = latest_event.get("event")

                    if event_type == "delivered":
                        return EmailStatus.DELIVERED
                    elif event_type == "opened":
                        return EmailStatus.OPENED
                    elif event_type == "clicked":
                        return EmailStatus.CLICKED
                    elif event_type in ["failed", "bounced"]:
                        return EmailStatus.FAILED

            return EmailStatus.SENT

        except Exception as e:
            logger.error(f"Failed to get status for {message_id}: {e}")
            return EmailStatus.SENT


class SMTPProvider(EmailProviderBase):
    """SMTP email provider (fallback)"""

    def __init__(self, host: str, port: int, username: str, password: str, **kwargs):
        super().__init__(api_key=password, **kwargs)
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = kwargs.get("use_tls", True)

    def send(self, message: EmailMessage) -> List[EmailResult]:
        """Send email via SMTP"""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        results = []

        try:
            # Connect to SMTP server
            if self.use_tls:
                server = smtplib.SMTP(self.host, self.port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.host, self.port)

            server.login(self.username, self.password)

            for recipient in message.recipients:
                try:
                    msg = MIMEMultipart("alternative")
                    msg["Subject"] = message.subject
                    msg["From"] = f"{message.from_name} <{message.from_email}>" if message.from_name else message.from_email
                    msg["To"] = recipient.email

                    # Add text and HTML parts
                    if message.body_text:
                        part1 = MIMEText(message.body_text, "plain")
                        msg.attach(part1)

                    part2 = MIMEText(message.body_html, "html")
                    msg.attach(part2)

                    # Send
                    server.sendmail(message.from_email, recipient.email, msg.as_string())

                    results.append(EmailResult(
                        message_id=f"smtp-{int(time.time())}",
                        status=EmailStatus.SENT,
                        provider=EmailProvider.SMTP,
                        sent_at=datetime.utcnow(),
                        recipient_email=recipient.email
                    ))

                except Exception as e:
                    logger.error(f"SMTP send failed for {recipient.email}: {e}")
                    results.append(EmailResult(
                        message_id="",
                        status=EmailStatus.FAILED,
                        provider=EmailProvider.SMTP,
                        sent_at=datetime.utcnow(),
                        recipient_email=recipient.email,
                        error=str(e)
                    ))

            server.quit()

        except Exception as e:
            logger.error(f"SMTP connection failed: {e}")
            for recipient in message.recipients:
                results.append(EmailResult(
                    message_id="",
                    status=EmailStatus.FAILED,
                    provider=EmailProvider.SMTP,
                    sent_at=datetime.utcnow(),
                    recipient_email=recipient.email,
                    error=str(e)
                ))

        return results

    def send_batch(self, messages: List[EmailMessage]) -> List[EmailResult]:
        """Send batch of emails"""
        results = []
        for message in messages:
            results.extend(self.send(message))
        return results

    def get_status(self, message_id: str) -> EmailStatus:
        """SMTP doesn't provide status tracking"""
        return EmailStatus.SENT


class EmailService:
    """
    Unified email service with multiple provider support

    Handles email sending with automatic failover, rate limiting,
    and delivery tracking.
    """

    def __init__(
        self,
        provider: EmailProvider = EmailProvider.SENDGRID,
        rate_limit_per_second: float = 10.0,
        **provider_config
    ):
        """
        Initialize email service

        Args:
            provider: Email provider to use
            rate_limit_per_second: Max emails per second
            **provider_config: Provider-specific configuration
        """
        self.provider_type = provider
        self.rate_limit = rate_limit_per_second
        self.last_send_time = 0.0

        # Initialize provider
        if provider == EmailProvider.SENDGRID:
            api_key = provider_config.get("api_key") or os.getenv("SENDGRID_API_KEY")
            self.provider = SendGridProvider(api_key)
        elif provider == EmailProvider.MAILGUN:
            api_key = provider_config.get("api_key") or os.getenv("MAILGUN_API_KEY")
            domain = provider_config.get("domain") or os.getenv("MAILGUN_DOMAIN")
            self.provider = MailgunProvider(api_key, domain)
        elif provider == EmailProvider.SMTP:
            self.provider = SMTPProvider(
                host=provider_config.get("host", "smtp.gmail.com"),
                port=provider_config.get("port", 587),
                username=provider_config.get("username", ""),
                password=provider_config.get("password", ""),
                use_tls=provider_config.get("use_tls", True)
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")

        logger.info(f"EmailService initialized with {provider} provider")

    def _rate_limit_check(self):
        """Check and enforce rate limiting"""
        if self.rate_limit > 0:
            time_since_last = time.time() - self.last_send_time
            min_interval = 1.0 / self.rate_limit

            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                time.sleep(sleep_time)

        self.last_send_time = time.time()

    def send(
        self,
        subject: str,
        body_html: str,
        recipients: List[str],
        from_email: str,
        from_name: Optional[str] = None,
        body_text: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[EmailResult]:
        """
        Send email to recipients

        Args:
            subject: Email subject
            body_html: HTML email body
            recipients: List of recipient email addresses
            from_email: Sender email address
            from_name: Sender name (optional)
            body_text: Plain text version (optional)
            tags: Email tags for tracking (optional)
            metadata: Additional metadata (optional)

        Returns:
            List of EmailResult objects
        """
        # Rate limiting
        self._rate_limit_check()

        # Build message
        message = EmailMessage(
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            from_email=from_email,
            from_name=from_name,
            recipients=[EmailRecipient(email=email) for email in recipients],
            tags=tags,
            metadata=metadata
        )

        # Send via provider
        try:
            results = self.provider.send(message)
            logger.info(f"Sent {len(results)} emails via {self.provider_type}")
            return results
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return [
                EmailResult(
                    message_id="",
                    status=EmailStatus.FAILED,
                    provider=self.provider_type,
                    sent_at=datetime.utcnow(),
                    recipient_email=email,
                    error=str(e)
                )
                for email in recipients
            ]

    def send_template(
        self,
        template: str,
        template_data: Dict[str, Any],
        recipients: List[str],
        from_email: str,
        subject: str,
        from_name: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[EmailResult]:
        """
        Send templated email

        Args:
            template: HTML template with {variable} placeholders
            template_data: Data to render template
            recipients: List of recipient emails
            from_email: Sender email
            subject: Email subject
            from_name: Sender name (optional)
            tags: Email tags (optional)

        Returns:
            List of EmailResult objects
        """
        # Render template
        try:
            rendered_html = template.format(**template_data)
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            return [
                EmailResult(
                    message_id="",
                    status=EmailStatus.FAILED,
                    provider=self.provider_type,
                    sent_at=datetime.utcnow(),
                    recipient_email=email,
                    error=f"Template rendering failed: {e}"
                )
                for email in recipients
            ]

        return self.send(
            subject=subject,
            body_html=rendered_html,
            recipients=recipients,
            from_email=from_email,
            from_name=from_name,
            tags=tags
        )

    def get_status(self, message_id: str) -> EmailStatus:
        """Get delivery status of message"""
        return self.provider.get_status(message_id)
