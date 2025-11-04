"""
Outreach.Orchestrator - Property owner outreach via email

Single-Writer Pattern: Only this agent publishes outreach events
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4, UUID

from jinja2 import Environment, FileSystemLoader
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, Attachment, FileContent, FileName, FileType
import base64

from .models import OutreachStatusEnum
from .repository import OutreachRepository


# Re-export for convenience
OutreachStatus = OutreachStatusEnum


class OutreachCampaign:
    """
    Campaign data class for easier access.

    Wraps database model with convenient properties.
    """

    def __init__(self, model):
        self._model = model

    @property
    def id(self) -> str:
        return str(self._model.id)

    @property
    def property_id(self) -> str:
        return str(self._model.property_id)

    @property
    def owner_email(self) -> str:
        return self._model.owner_email

    @property
    def status(self) -> str:
        return self._model.status

    @property
    def sent_at(self) -> Optional[datetime]:
        return self._model.sent_at

    @property
    def opened_at(self) -> Optional[datetime]:
        return self._model.opened_at

    def to_dict(self) -> dict:
        """Serialize to dict"""
        return {
            "id": self.id,
            "property_id": self.property_id,
            "owner_name": self._model.owner_name,
            "owner_email": self.owner_email,
            "status": self.status,
            "subject": self._model.subject,
            "scheduled_at": self._model.scheduled_at.isoformat() if self._model.scheduled_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
        }


class OutreachOrchestrator:
    """
    Orchestrates property owner outreach via email.

    Features:
    - SendGrid email delivery
    - Template-based email rendering (HTML + plain text)
    - Campaign tracking and status updates
    - Event publishing for downstream consumers
    - Idempotent campaign creation
    """

    def __init__(
        self,
        repository: OutreachRepository,
        sendgrid_api_key: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        company_name: str = "Real Estate Investment Co.",
        template_dir: Optional[Path] = None,
    ):
        """
        Initialize outreach orchestrator.

        Args:
            repository: OutreachRepository for persistence
            sendgrid_api_key: SendGrid API key (defaults to SENDGRID_API_KEY env var)
            from_email: Sender email address (defaults to SENDGRID_FROM_EMAIL env var)
            from_name: Sender name (defaults to SENDGRID_FROM_NAME env var)
            company_name: Company name for email templates
            template_dir: Custom template directory (defaults to bundled templates)
        """
        self.repository = repository

        # SendGrid configuration
        self.sendgrid_api_key = sendgrid_api_key or os.getenv("SENDGRID_API_KEY")
        self.from_email = from_email or os.getenv("SENDGRID_FROM_EMAIL", "noreply@example.com")
        self.from_name = from_name or os.getenv("SENDGRID_FROM_NAME", "Real Estate Team")
        self.company_name = company_name

        if not self.sendgrid_api_key:
            raise ValueError("SendGrid API key must be provided or set in SENDGRID_API_KEY env var")

        self.sendgrid = SendGridAPIClient(self.sendgrid_api_key)

        # Initialize Jinja2 template engine
        if template_dir is None:
            # Default to bundled templates
            template_dir = Path(__file__).parent.parent.parent / "templates"

        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True,
        )

    def create_campaign(
        self,
        tenant_id: str,
        property_record: dict,
        score_result: dict,
        memo_url: str,
        scheduled_at: Optional[datetime] = None,
    ) -> OutreachCampaign:
        """
        Create outreach campaign for a property.

        Args:
            tenant_id: Tenant UUID
            property_record: Property data (from PropertyRecord contract)
            score_result: Score data (from ScoreResult contract)
            memo_url: URL to property memo PDF
            scheduled_at: When to send email (default: now)

        Returns:
            OutreachCampaign

        Example:
            >>> orchestrator = OutreachOrchestrator(repository)
            >>> campaign = orchestrator.create_campaign(
            ...     tenant_id="tenant-uuid",
            ...     property_record=property.dict(),
            ...     score_result=score.dict(),
            ...     memo_url="https://s3.../memo.pdf",
            ... )
        """
        # Extract owner information
        owner = property_record.get("owner", {})
        owner_name = owner.get("name", "Property Owner")
        owner_email = owner.get("email")

        if not owner_email:
            raise ValueError("Property owner email is required for outreach")

        # Generate subject line
        address = property_record.get("address", {})
        subject = f"Investment Opportunity - {address.get('line1', 'Your Property')}"

        # Check if campaign already exists for this property
        existing = self.repository.get_campaign_by_property(
            property_id=property_record.get("id"),
            tenant_id=tenant_id,
        )

        if existing:
            # Campaign already exists, return it (idempotent)
            return OutreachCampaign(existing)

        # Create new campaign
        campaign_model = self.repository.create_campaign(
            tenant_id=tenant_id,
            property_id=property_record.get("id"),
            owner_name=owner_name,
            owner_email=owner_email,
            subject=subject,
            memo_url=memo_url,
            scheduled_at=scheduled_at,
            context={
                "property_apn": property_record.get("apn"),
                "score": score_result.get("score"),
            },
        )

        return OutreachCampaign(campaign_model)

    def send_campaign(
        self,
        campaign_id: str,
        tenant_id: str,
        property_record: dict,
        score_result: dict,
    ) -> dict:
        """
        Send campaign email via SendGrid.

        Args:
            campaign_id: Campaign UUID
            tenant_id: Tenant UUID
            property_record: Property data
            score_result: Score data

        Returns:
            Dict with status and message_id

        Raises:
            ValueError: If campaign not found
            Exception: If SendGrid API fails
        """
        # Get campaign
        campaign_model = self.repository.get_campaign(campaign_id, tenant_id)
        if not campaign_model:
            raise ValueError(f"Campaign not found: {campaign_id}")

        # Check if already sent
        if campaign_model.status != OutreachStatusEnum.SCHEDULED.value:
            # Already sent, return existing message ID
            return {
                "status": "already_sent",
                "message_id": campaign_model.sendgrid_message_id,
            }

        # Render email templates
        html_content = self._render_template(
            "memo_delivery_email.html",
            property=property_record,
            score=score_result,
            owner=property_record.get("owner", {}),
            memo_url=campaign_model.memo_url,
            company_name=self.company_name,
            company_email=self.from_email,
        )

        text_content = self._render_template(
            "memo_delivery_email.txt",
            property=property_record,
            score=score_result,
            owner=property_record.get("owner", {}),
            memo_url=campaign_model.memo_url,
            company_name=self.company_name,
            company_email=self.from_email,
        )

        # Create SendGrid email
        message = Mail(
            from_email=Email(self.from_email, self.from_name),
            to_emails=To(campaign_model.owner_email, campaign_model.owner_name),
            subject=campaign_model.subject,
            plain_text_content=Content("text/plain", text_content),
            html_content=Content("text/html", html_content),
        )

        # Add custom args for tracking
        message.custom_arg = {
            "campaign_id": str(campaign_id),
            "tenant_id": str(tenant_id),
            "property_id": str(campaign_model.property_id),
        }

        # Send email
        try:
            response = self.sendgrid.send(message)
            message_id = response.headers.get("X-Message-Id", str(uuid4()))

            # Update campaign status
            self.repository.update_campaign_status(
                campaign_id=campaign_id,
                tenant_id=tenant_id,
                status=OutreachStatusEnum.SENT,
                sendgrid_message_id=message_id,
                sent_at=datetime.now(timezone.utc),
            )

            # Log event
            self.repository.log_event(
                campaign_id=campaign_id,
                tenant_id=tenant_id,
                event_type="sent",
                event_data={
                    "status_code": response.status_code,
                    "message_id": message_id,
                },
            )

            return {
                "status": "sent",
                "message_id": message_id,
                "status_code": response.status_code,
            }

        except Exception as e:
            # Update campaign status to failed
            self.repository.update_campaign_status(
                campaign_id=campaign_id,
                tenant_id=tenant_id,
                status=OutreachStatusEnum.FAILED,
            )

            # Log event
            self.repository.log_event(
                campaign_id=campaign_id,
                tenant_id=tenant_id,
                event_type="failed",
                event_data={"error": str(e)},
            )

            raise

    def handle_webhook(self, webhook_data: dict) -> Optional[dict]:
        """
        Handle SendGrid webhook event.

        Args:
            webhook_data: SendGrid webhook payload

        Returns:
            Dict with campaign info if processed, None if ignored

        Example webhook events:
        - delivered: Email delivered to recipient
        - open: Email opened by recipient
        - click: Link clicked in email
        - bounce: Email bounced
        - unsubscribe: Recipient unsubscribed
        """
        event_type = webhook_data.get("event")
        if not event_type:
            return None

        # Extract campaign ID from custom args
        campaign_id = webhook_data.get("campaign_id")
        tenant_id = webhook_data.get("tenant_id")

        if not campaign_id or not tenant_id:
            # No campaign tracking info, ignore
            return None

        # Get campaign
        campaign_model = self.repository.get_campaign(campaign_id, tenant_id)
        if not campaign_model:
            return None

        # Map webhook event to status update
        status_map = {
            "delivered": (OutreachStatusEnum.DELIVERED, {"delivered_at": datetime.now(timezone.utc)}),
            "open": (OutreachStatusEnum.OPENED, {"opened_at": datetime.now(timezone.utc)}),
            "click": (OutreachStatusEnum.CLICKED, {"clicked_at": datetime.now(timezone.utc)}),
            "bounce": (OutreachStatusEnum.BOUNCED, {}),
            "dropped": (OutreachStatusEnum.FAILED, {}),
            "unsubscribe": (OutreachStatusEnum.UNSUBSCRIBED, {}),
        }

        if event_type in status_map:
            status, timestamp_fields = status_map[event_type]

            # Update campaign status
            self.repository.update_campaign_status(
                campaign_id=campaign_id,
                tenant_id=tenant_id,
                status=status,
                **timestamp_fields,
            )

            # Log event
            self.repository.log_event(
                campaign_id=campaign_id,
                tenant_id=tenant_id,
                event_type=event_type,
                event_data=webhook_data,
            )

            return {
                "campaign_id": campaign_id,
                "event_type": event_type,
                "status": status.value,
            }

        return None

    def get_campaign(self, campaign_id: str, tenant_id: str) -> Optional[OutreachCampaign]:
        """
        Get campaign by ID.

        Args:
            campaign_id: Campaign UUID
            tenant_id: Tenant UUID

        Returns:
            OutreachCampaign if found, None otherwise
        """
        model = self.repository.get_campaign(campaign_id, tenant_id)
        if model:
            return OutreachCampaign(model)
        return None

    def get_campaigns_by_status(
        self,
        status: OutreachStatusEnum,
        tenant_id: str,
        limit: int = 100,
    ) -> list[OutreachCampaign]:
        """
        Get campaigns by status.

        Args:
            status: Target status
            tenant_id: Tenant UUID
            limit: Maximum number of campaigns

        Returns:
            List of OutreachCampaign
        """
        models = self.repository.get_campaigns_by_status(status, tenant_id, limit)
        return [OutreachCampaign(m) for m in models]

    def get_statistics(self, tenant_id: str) -> dict:
        """
        Get campaign statistics.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Dict with counts per status
        """
        return self.repository.count_by_status(tenant_id)

    def _render_template(self, template_name: str, **context) -> str:
        """
        Render email template.

        Args:
            template_name: Template filename
            **context: Template variables

        Returns:
            Rendered template string
        """
        template = self.jinja_env.get_template(template_name)
        return template.render(**context)
