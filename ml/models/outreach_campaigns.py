"""
Outreach Campaign System

Wave 3.3 Part 2: Multi-step email campaign management

Features:
- Campaign sequencing with delays
- Template management
- Recipient tracking
- A/B testing
- Unsubscribe handling
- Analytics and reporting
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
from uuid import UUID, uuid4
import logging

logger = logging.getLogger(__name__)


class CampaignStatus(str, Enum):
    """Campaign lifecycle status"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class CampaignType(str, Enum):
    """Types of outreach campaigns"""
    SELLER_OUTREACH = "seller_outreach"  # Direct to property owners
    AGENT_NETWORKING = "agent_networking"  # To other agents
    BUYER_NURTURE = "buyer_nurture"  # To prospective buyers
    REFERRAL_REQUEST = "referral_request"  # Ask for referrals
    FOLLOW_UP = "follow_up"  # General follow-up


class RecipientStatus(str, Enum):
    """Recipient engagement status"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    REPLIED = "replied"
    UNSUBSCRIBED = "unsubscribed"
    BOUNCED = "bounced"
    COMPLETED = "completed"  # Completed all steps


@dataclass
class EmailTemplate:
    """Email template with variables"""
    id: str
    name: str
    subject: str
    body_html: str
    body_text: Optional[str] = None
    variables: List[str] = field(default_factory=list)  # e.g., ['property_address', 'owner_name']
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CampaignStep:
    """Single step in campaign sequence"""
    id: str
    step_number: int
    template_id: str
    delay_days: int  # Days to wait after previous step (0 for first step)
    delay_hours: int = 0  # Additional hours for fine-grained control
    send_time_hour: Optional[int] = None  # Preferred send hour (0-23)
    conditions: Optional[Dict[str, Any]] = None  # Conditional logic (e.g., only if previous opened)


@dataclass
class CampaignRecipient:
    """Recipient in a campaign"""
    id: str
    campaign_id: str
    email: str
    name: Optional[str] = None

    # Property/entity association
    property_id: Optional[str] = None
    entity_id: Optional[str] = None

    # Template variables for personalization
    template_data: Dict[str, Any] = field(default_factory=dict)

    # Tracking
    status: RecipientStatus = RecipientStatus.PENDING
    current_step: int = 0
    last_email_sent_at: Optional[datetime] = None
    last_opened_at: Optional[datetime] = None
    last_clicked_at: Optional[datetime] = None
    bounced_at: Optional[datetime] = None
    unsubscribed_at: Optional[datetime] = None

    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Campaign:
    """Email outreach campaign"""
    id: str
    name: str
    campaign_type: CampaignType
    status: CampaignStatus

    # Sequence
    steps: List[CampaignStep] = field(default_factory=list)

    # Settings
    from_email: str = ""
    from_name: str = ""
    reply_to: Optional[str] = None

    # Scheduling
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    # Recipients
    total_recipients: int = 0

    # Analytics
    emails_sent: int = 0
    emails_delivered: int = 0
    emails_opened: int = 0
    emails_clicked: int = 0
    replies_received: int = 0
    unsubscribes: int = 0

    # Metadata
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class CampaignBuilder:
    """Builder for creating campaigns"""

    def __init__(self, name: str, campaign_type: CampaignType):
        self.campaign = Campaign(
            id=str(uuid4()),
            name=name,
            campaign_type=campaign_type,
            status=CampaignStatus.DRAFT
        )

    def set_sender(
        self,
        from_email: str,
        from_name: str,
        reply_to: Optional[str] = None
    ) -> 'CampaignBuilder':
        """Set sender information"""
        self.campaign.from_email = from_email
        self.campaign.from_name = from_name
        self.campaign.reply_to = reply_to or from_email
        return self

    def add_step(
        self,
        template_id: str,
        delay_days: int = 0,
        delay_hours: int = 0,
        send_time_hour: Optional[int] = None,
        conditions: Optional[Dict[str, Any]] = None
    ) -> 'CampaignBuilder':
        """Add step to campaign sequence"""
        step_number = len(self.campaign.steps) + 1

        step = CampaignStep(
            id=str(uuid4()),
            step_number=step_number,
            template_id=template_id,
            delay_days=delay_days,
            delay_hours=delay_hours,
            send_time_hour=send_time_hour,
            conditions=conditions
        )

        self.campaign.steps.append(step)
        return self

    def set_schedule(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> 'CampaignBuilder':
        """Set campaign schedule"""
        self.campaign.start_date = start_date
        self.campaign.end_date = end_date
        return self

    def set_metadata(
        self,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        created_by: Optional[str] = None
    ) -> 'CampaignBuilder':
        """Set campaign metadata"""
        if description:
            self.campaign.description = description
        if tags:
            self.campaign.tags = tags
        if created_by:
            self.campaign.created_by = created_by
        return self

    def build(self) -> Campaign:
        """Build and return campaign"""
        if not self.campaign.steps:
            raise ValueError("Campaign must have at least one step")
        if not self.campaign.from_email:
            raise ValueError("Campaign must have sender email")

        return self.campaign


class CampaignSequencer:
    """
    Manages campaign execution and sequencing

    Determines which emails to send based on:
    - Campaign schedule
    - Step delays
    - Recipient status
    - Conditional logic
    """

    def __init__(self):
        pass

    def get_next_sends(
        self,
        campaign: Campaign,
        recipients: List[CampaignRecipient],
        now: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Determine which emails should be sent now

        Returns list of send instructions:
        [
            {
                'recipient_id': str,
                'step_number': int,
                'template_id': str,
                'recipient': CampaignRecipient
            },
            ...
        ]
        """
        if now is None:
            now = datetime.utcnow()

        # Check campaign status
        if campaign.status != CampaignStatus.ACTIVE:
            logger.debug(f"Campaign {campaign.id} not active")
            return []

        # Check campaign schedule
        if campaign.start_date and now < campaign.start_date:
            logger.debug(f"Campaign {campaign.id} not started yet")
            return []

        if campaign.end_date and now > campaign.end_date:
            logger.debug(f"Campaign {campaign.id} has ended")
            return []

        sends = []

        for recipient in recipients:
            # Skip if completed or unsubscribed
            if recipient.status in [RecipientStatus.COMPLETED, RecipientStatus.UNSUBSCRIBED]:
                continue

            # Determine next step for this recipient
            next_step_number = recipient.current_step + 1

            # Check if there's a next step
            if next_step_number > len(campaign.steps):
                # Recipient completed all steps
                continue

            step = campaign.steps[next_step_number - 1]

            # Calculate when this step should be sent
            if next_step_number == 1:
                # First step - send immediately (respecting send_time_hour)
                send_time = now
            else:
                # Subsequent steps - calculate based on last send + delay
                if not recipient.last_email_sent_at:
                    continue  # Can't proceed without previous send time

                send_time = recipient.last_email_sent_at + timedelta(
                    days=step.delay_days,
                    hours=step.delay_hours
                )

            # Check if it's time to send
            if now < send_time:
                continue

            # Check send_time_hour preference
            if step.send_time_hour is not None:
                if now.hour != step.send_time_hour:
                    # Wait for preferred hour
                    continue

            # Check conditional logic
            if step.conditions:
                if not self._check_conditions(step.conditions, recipient):
                    # Conditions not met - skip step
                    logger.debug(f"Step {step.step_number} conditions not met for {recipient.email}")
                    continue

            # This email should be sent
            sends.append({
                'recipient_id': recipient.id,
                'step_number': next_step_number,
                'template_id': step.template_id,
                'recipient': recipient
            })

        return sends

    def _check_conditions(
        self,
        conditions: Dict[str, Any],
        recipient: CampaignRecipient
    ) -> bool:
        """Check if conditional logic is satisfied"""

        # Example conditions:
        # {'previous_opened': True} - only send if previous email was opened
        # {'previous_clicked': True} - only send if previous email was clicked
        # {'days_since_last': 7} - only send if 7+ days since last email

        if 'previous_opened' in conditions:
            if conditions['previous_opened'] and not recipient.last_opened_at:
                return False

        if 'previous_clicked' in conditions:
            if conditions['previous_clicked'] and not recipient.last_clicked_at:
                return False

        if 'days_since_last' in conditions:
            if recipient.last_email_sent_at:
                days_since = (datetime.utcnow() - recipient.last_email_sent_at).days
                if days_since < conditions['days_since_last']:
                    return False

        return True

    def mark_sent(
        self,
        recipient: CampaignRecipient,
        step_number: int,
        message_id: str,
        sent_at: Optional[datetime] = None
    ) -> CampaignRecipient:
        """Mark email as sent and update recipient status"""
        if sent_at is None:
            sent_at = datetime.utcnow()

        recipient.current_step = step_number
        recipient.last_email_sent_at = sent_at
        recipient.status = RecipientStatus.SENT

        return recipient

    def mark_delivered(
        self,
        recipient: CampaignRecipient,
        delivered_at: Optional[datetime] = None
    ) -> CampaignRecipient:
        """Mark email as delivered"""
        if recipient.status == RecipientStatus.SENT:
            recipient.status = RecipientStatus.DELIVERED
        return recipient

    def mark_opened(
        self,
        recipient: CampaignRecipient,
        opened_at: Optional[datetime] = None
    ) -> CampaignRecipient:
        """Mark email as opened"""
        if opened_at is None:
            opened_at = datetime.utcnow()

        recipient.last_opened_at = opened_at
        if recipient.status in [RecipientStatus.SENT, RecipientStatus.DELIVERED]:
            recipient.status = RecipientStatus.OPENED
        return recipient

    def mark_clicked(
        self,
        recipient: CampaignRecipient,
        clicked_at: Optional[datetime] = None
    ) -> CampaignRecipient:
        """Mark email link as clicked"""
        if clicked_at is None:
            clicked_at = datetime.utcnow()

        recipient.last_clicked_at = clicked_at
        if recipient.status != RecipientStatus.REPLIED:
            recipient.status = RecipientStatus.CLICKED
        return recipient

    def mark_replied(
        self,
        recipient: CampaignRecipient
    ) -> CampaignRecipient:
        """Mark recipient as replied"""
        recipient.status = RecipientStatus.REPLIED
        return recipient

    def mark_unsubscribed(
        self,
        recipient: CampaignRecipient,
        unsubscribed_at: Optional[datetime] = None
    ) -> CampaignRecipient:
        """Mark recipient as unsubscribed"""
        if unsubscribed_at is None:
            unsubscribed_at = datetime.utcnow()

        recipient.unsubscribed_at = unsubscribed_at
        recipient.status = RecipientStatus.UNSUBSCRIBED
        return recipient

    def mark_bounced(
        self,
        recipient: CampaignRecipient,
        bounced_at: Optional[datetime] = None
    ) -> CampaignRecipient:
        """Mark email as bounced"""
        if bounced_at is None:
            bounced_at = datetime.utcnow()

        recipient.bounced_at = bounced_at
        recipient.status = RecipientStatus.BOUNCED
        return recipient


class CampaignAnalytics:
    """Campaign performance analytics"""

    @staticmethod
    def calculate_metrics(
        campaign: Campaign,
        recipients: List[CampaignRecipient]
    ) -> Dict[str, Any]:
        """Calculate campaign performance metrics"""

        total = len(recipients)
        if total == 0:
            return {
                'total_recipients': 0,
                'delivery_rate': 0.0,
                'open_rate': 0.0,
                'click_rate': 0.0,
                'reply_rate': 0.0,
                'unsubscribe_rate': 0.0,
                'bounce_rate': 0.0
            }

        sent = sum(1 for r in recipients if r.last_email_sent_at is not None)
        delivered = sum(1 for r in recipients if r.status in [
            RecipientStatus.DELIVERED,
            RecipientStatus.OPENED,
            RecipientStatus.CLICKED,
            RecipientStatus.REPLIED
        ])
        opened = sum(1 for r in recipients if r.last_opened_at is not None)
        clicked = sum(1 for r in recipients if r.last_clicked_at is not None)
        replied = sum(1 for r in recipients if r.status == RecipientStatus.REPLIED)
        unsubscribed = sum(1 for r in recipients if r.status == RecipientStatus.UNSUBSCRIBED)
        bounced = sum(1 for r in recipients if r.status == RecipientStatus.BOUNCED)

        return {
            'total_recipients': total,
            'sent': sent,
            'delivered': delivered,
            'opened': opened,
            'clicked': clicked,
            'replied': replied,
            'unsubscribed': unsubscribed,
            'bounced': bounced,
            'delivery_rate': delivered / sent if sent > 0 else 0.0,
            'open_rate': opened / delivered if delivered > 0 else 0.0,
            'click_rate': clicked / opened if opened > 0 else 0.0,
            'reply_rate': replied / delivered if delivered > 0 else 0.0,
            'unsubscribe_rate': unsubscribed / delivered if delivered > 0 else 0.0,
            'bounce_rate': bounced / sent if sent > 0 else 0.0
        }

    @staticmethod
    def get_step_metrics(
        campaign: Campaign,
        recipients: List[CampaignRecipient]
    ) -> List[Dict[str, Any]]:
        """Get metrics for each campaign step"""

        step_metrics = []

        for step in campaign.steps:
            step_recipients = [
                r for r in recipients
                if r.current_step >= step.step_number
            ]

            if not step_recipients:
                step_metrics.append({
                    'step_number': step.step_number,
                    'total': 0,
                    'open_rate': 0.0,
                    'click_rate': 0.0
                })
                continue

            total = len(step_recipients)
            opened = sum(1 for r in step_recipients if r.last_opened_at is not None)
            clicked = sum(1 for r in step_recipients if r.last_clicked_at is not None)

            step_metrics.append({
                'step_number': step.step_number,
                'total': total,
                'opened': opened,
                'clicked': clicked,
                'open_rate': opened / total if total > 0 else 0.0,
                'click_rate': clicked / opened if opened > 0 else 0.0
            })

        return step_metrics


# ===========================================================================
# PRE-BUILT CAMPAIGN TEMPLATES
# ===========================================================================

class CampaignTemplates:
    """Pre-built campaign templates for common scenarios"""

    @staticmethod
    def seller_outreach_sequence() -> List[Dict[str, Any]]:
        """3-step seller outreach campaign"""
        return [
            {
                'name': 'Initial Outreach',
                'delay_days': 0,
                'subject': 'Interested in {property_address}',
                'body_html': '''
                    <p>Hi {owner_name},</p>
                    <p>I noticed your property at {property_address} and wanted to reach out.</p>
                    <p>I work with buyers actively looking in your area, and I'd love to discuss if you've considered selling.</p>
                    <p>Would you be open to a quick conversation?</p>
                    <p>Best regards,<br>{agent_name}</p>
                '''
            },
            {
                'name': 'Follow-up (3 days)',
                'delay_days': 3,
                'subject': 'Following up on {property_address}',
                'body_html': '''
                    <p>Hi {owner_name},</p>
                    <p>I wanted to follow up on my previous email about {property_address}.</p>
                    <p>The market is strong right now, and I have buyers ready to make competitive offers.</p>
                    <p>Would you be interested in a free market analysis?</p>
                    <p>Best,<br>{agent_name}</p>
                '''
            },
            {
                'name': 'Final Touch (7 days)',
                'delay_days': 7,
                'subject': 'Last chance for {property_address}',
                'body_html': '''
                    <p>Hi {owner_name},</p>
                    <p>This is my last email about {property_address}.</p>
                    <p>If you're ever interested in selling or want to know what your home is worth, feel free to reach out.</p>
                    <p>Wishing you the best,<br>{agent_name}</p>
                '''
            }
        ]

    @staticmethod
    def buyer_nurture_sequence() -> List[Dict[str, Any]]:
        """Ongoing buyer nurture campaign"""
        return [
            {
                'name': 'Welcome Email',
                'delay_days': 0,
                'subject': 'Welcome to your property search!',
                'body_html': '''
                    <p>Hi {buyer_name},</p>
                    <p>Welcome! I'm excited to help you find your next home.</p>
                    <p>I'll be sending you curated property recommendations based on your criteria.</p>
                    <p>Let me know if you have any questions!</p>
                    <p>Best,<br>{agent_name}</p>
                '''
            },
            {
                'name': 'Weekly Market Update',
                'delay_days': 7,
                'subject': 'New properties matching your criteria',
                'body_html': '''
                    <p>Hi {buyer_name},</p>
                    <p>Here are some new listings that match what you're looking for:</p>
                    <p>{property_list_html}</p>
                    <p>Want to schedule showings?</p>
                    <p>Best,<br>{agent_name}</p>
                '''
            }
        ]
