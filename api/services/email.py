"""Email service for sending emails."""

import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from jinja2 import Template
import asyncio

from ..config import settings


class EmailService:
    """Email service for sending emails via SMTP."""

    def __init__(self):
        """Initialize email service."""
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL
        self.from_name = settings.SMTP_FROM_NAME

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html: bool = False,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
    ) -> bool:
        """
        Send an email.

        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body (plain text or HTML)
            html: Whether body is HTML
            cc: CC recipients
            bcc: BCC recipients

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            message["Subject"] = subject

            if cc:
                message["Cc"] = ", ".join(cc)

            # Attach body
            mime_type = "html" if html else "plain"
            part = MIMEText(body, mime_type)
            message.attach(part)

            # For development/testing, just print the email
            if settings.DEBUG:
                print(f"\n{'='*50}")
                print(f"EMAIL: {to_email}")
                print(f"SUBJECT: {subject}")
                print(f"{'='*50}")
                print(body)
                print(f"{'='*50}\n")
                return True

            # Send via SMTP
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                start_tls=False,
            )

            return True

        except Exception as e:
            print(f"Error sending email: {e}")
            return False

    async def send_template_email(
        self,
        to_email: str,
        subject: str,
        template: str,
        context: dict,
    ) -> bool:
        """
        Send an email using a Jinja2 template.

        Args:
            to_email: Recipient email address
            subject: Email subject
            template: Jinja2 template string
            context: Template context variables

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Render template
            jinja_template = Template(template)
            body = jinja_template.render(**context)

            # Send email
            return await self.send_email(to_email, subject, body, html=True)

        except Exception as e:
            print(f"Error sending template email: {e}")
            return False

    async def send_verification_email(self, to_email: str, token: str) -> bool:
        """Send email verification email."""
        subject = "Verify your email address"
        body = f"""
        <h2>Welcome to Real Estate OS!</h2>
        <p>Please verify your email address by clicking the link below:</p>
        <p><a href="http://localhost:3000/verify-email?token={token}">Verify Email</a></p>
        <p>If you didn't create an account, you can safely ignore this email.</p>
        """
        return await self.send_email(to_email, subject, body, html=True)

    async def send_password_reset_email(self, to_email: str, token: str) -> bool:
        """Send password reset email."""
        subject = "Reset your password"
        body = f"""
        <h2>Password Reset Request</h2>
        <p>You requested to reset your password. Click the link below to proceed:</p>
        <p><a href="http://localhost:3000/reset-password?token={token}">Reset Password</a></p>
        <p>This link will expire in 1 hour.</p>
        <p>If you didn't request this, you can safely ignore this email.</p>
        """
        return await self.send_email(to_email, subject, body, html=True)

    async def send_campaign_email(
        self,
        to_email: str,
        subject: str,
        content: str,
        first_name: Optional[str] = None,
    ) -> bool:
        """Send campaign email with personalization."""
        # Replace placeholders
        personalized_content = content.replace("{{first_name}}", first_name or "there")

        return await self.send_email(to_email, subject, personalized_content, html=True)


# Singleton instance
email_service = EmailService()
