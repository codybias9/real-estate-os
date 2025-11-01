"""SendGrid API client for email sending

Handles email composition, sending, and tracking via SendGrid.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import base64

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, Email, To, Content, Attachment,
    FileContent, FileName, FileType, Disposition
)
from python_http_client.exceptions import HTTPError

logger = logging.getLogger(__name__)


class SendGridClient:
    """
    SendGrid client for transactional emails

    Features:
    - Send emails with attachments (PDFs)
    - Track email events (opens, clicks, bounces)
    - Template support
    - Batch sending
    """

    def __init__(self, api_key: str, from_email: str, from_name: str = "Real Estate OS"):
        """
        Initialize SendGrid client

        Args:
            api_key: SendGrid API key
            from_email: Sender email address
            from_name: Sender name
        """
        self.api_key = api_key
        self.from_email = from_email
        self.from_name = from_name

        try:
            self.client = SendGridAPIClient(api_key=api_key)
            logger.info(f"SendGrid client initialized: {from_email}")
        except Exception as e:
            logger.error(f"Failed to initialize SendGrid client: {e}")
            raise

    def send_investor_memo(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_body: str,
        plain_body: str,
        pdf_attachment: Optional[bytes] = None,
        pdf_filename: str = "investor_memo.pdf",
        custom_args: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Send investor memo email with PDF attachment

        Args:
            to_email: Recipient email address
            to_name: Recipient name
            subject: Email subject
            html_body: HTML email body
            plain_body: Plain text email body
            pdf_attachment: PDF content as bytes (optional)
            pdf_filename: Name for PDF attachment
            custom_args: Custom tracking arguments (e.g., prospect_id, campaign_id)

        Returns:
            Dictionary with send results
        """
        logger.info(f"Sending investor memo to: {to_email}")

        try:
            # Create email message
            message = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(to_email, to_name),
                subject=subject,
                plain_text_content=Content("text/plain", plain_body),
                html_content=Content("text/html", html_body)
            )

            # Add PDF attachment if provided
            if pdf_attachment:
                logger.info(f"Attaching PDF: {pdf_filename} ({len(pdf_attachment)} bytes)")

                # Encode PDF to base64
                encoded_pdf = base64.b64encode(pdf_attachment).decode()

                attachment = Attachment(
                    FileContent(encoded_pdf),
                    FileName(pdf_filename),
                    FileType('application/pdf'),
                    Disposition('attachment')
                )
                message.add_attachment(attachment)

            # Add custom tracking arguments
            if custom_args:
                message.custom_arg = custom_args

            # Enable click and open tracking
            message.tracking_settings = {
                "click_tracking": {"enable": True, "enable_text": False},
                "open_tracking": {"enable": True},
                "subscription_tracking": {"enable": False}
            }

            # Send email
            response = self.client.send(message)

            logger.info(f"Email sent successfully: status_code={response.status_code}")

            return {
                'success': True,
                'status_code': response.status_code,
                'message_id': response.headers.get('X-Message-Id'),
                'to_email': to_email
            }

        except HTTPError as e:
            logger.error(f"SendGrid API error: {e.status_code} - {e.body}")
            return {
                'success': False,
                'error': str(e),
                'status_code': e.status_code,
                'to_email': to_email
            }

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return {
                'success': False,
                'error': str(e),
                'to_email': to_email
            }

    def send_batch(
        self,
        emails: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Send multiple emails (batch sending)

        Args:
            emails: List of email dictionaries with recipient info

        Returns:
            List of send results
        """
        logger.info(f"Sending batch of {len(emails)} emails")

        results = []

        for email in emails:
            result = self.send_investor_memo(**email)
            results.append(result)

        successful = sum(1 for r in results if r.get('success'))
        logger.info(f"Batch send complete: {successful}/{len(emails)} successful")

        return results

    def verify_sender(self) -> bool:
        """
        Verify sender email is authenticated in SendGrid

        Returns:
            True if sender is verified
        """
        try:
            response = self.client.client.verified_senders.get()

            verified_senders = response.body.get('results', [])

            for sender in verified_senders:
                if sender.get('from_email') == self.from_email:
                    logger.info(f"Sender verified: {self.from_email}")
                    return True

            logger.warning(f"Sender not verified: {self.from_email}")
            return False

        except Exception as e:
            logger.error(f"Failed to verify sender: {e}")
            return False

    def get_stats(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Get email statistics from SendGrid

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Dictionary with statistics
        """
        try:
            params = {
                'start_date': start_date,
                'end_date': end_date,
                'aggregated_by': 'day'
            }

            response = self.client.client.stats.get(query_params=params)

            stats = response.body

            logger.info(f"Retrieved stats for {start_date} to {end_date}")

            return {
                'success': True,
                'stats': stats
            }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def suppress_email(self, email: str, reason: str = "bounced") -> bool:
        """
        Add email to suppression list

        Args:
            email: Email to suppress
            reason: Suppression reason (bounced, spam, unsubscribe)

        Returns:
            True if suppressed successfully
        """
        try:
            # Map reason to SendGrid suppression group
            suppression_endpoints = {
                'bounced': 'bounces',
                'spam': 'spam_reports',
                'unsubscribe': 'global_unsubscribes'
            }

            endpoint = suppression_endpoints.get(reason, 'bounces')

            data = {
                'emails': [email]
            }

            response = self.client.client.suppression._(endpoint).post(request_body=data)

            logger.info(f"Suppressed email: {email} (reason: {reason})")

            return True

        except Exception as e:
            logger.error(f"Failed to suppress email: {e}")
            return False

    def health_check(self) -> bool:
        """
        Check SendGrid API connectivity

        Returns:
            True if API is accessible
        """
        try:
            # Try to get account info
            response = self.client.client.user.email.get()

            logger.info("SendGrid health check: OK")
            return True

        except Exception as e:
            logger.error(f"SendGrid health check failed: {e}")
            return False
