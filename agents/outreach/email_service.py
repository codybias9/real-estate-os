"""Simulated email outreach service for property campaigns."""

import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from db.models import Campaign, Property, PropertyScore, OutreachLog


class EmailService:
    """Service for managing email campaigns and outreach."""

    def __init__(self, db: Session):
        """
        Initialize the email service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def send_campaign(self, campaign_id: int, property_ids: Optional[List[int]] = None) -> Dict:
        """
        Execute a campaign by "sending" emails to property owners/investors.

        This is a simulated service that creates outreach logs without sending real emails.

        Args:
            campaign_id: ID of the campaign to execute
            property_ids: Optional list of specific property IDs to target

        Returns:
            Dictionary with campaign execution results
        """
        # Get campaign
        campaign = self.db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        # Determine target properties
        if property_ids:
            properties = self.db.query(Property).filter(Property.id.in_(property_ids)).all()
        else:
            # Default: Target high-scoring properties
            properties = (
                self.db.query(Property)
                .join(PropertyScore, Property.id == PropertyScore.property_id)
                .filter(
                    PropertyScore.total_score >= 70,  # Only high-quality properties
                    Property.status.in_(['scored', 'documented'])
                )
                .limit(100)  # Limit for demo
                .all()
            )

        if not properties:
            return {
                'campaign_id': campaign_id,
                'status': 'no_targets',
                'sent': 0,
                'message': 'No properties matched the campaign criteria'
            }

        # Simulate sending emails
        sent_count = 0
        for prop in properties:
            # Check if already contacted
            existing_log = self.db.query(OutreachLog).filter(
                OutreachLog.campaign_id == campaign_id,
                OutreachLog.property_id == prop.id
            ).first()

            if existing_log:
                continue  # Skip already contacted properties

            # Create outreach log
            log = self._create_outreach_log(campaign, prop)
            self.db.add(log)
            sent_count += 1

        # Update campaign counts
        campaign.sent_count = sent_count
        campaign.status = 'sent' if sent_count > 0 else campaign.status

        self.db.commit()

        return {
            'campaign_id': campaign_id,
            'status': 'completed',
            'sent': sent_count,
            'message': f'Successfully "sent" {sent_count} emails'
        }

    def simulate_engagement(self, campaign_id: int, engagement_rate: float = 0.3) -> Dict:
        """
        Simulate email engagement (opens, clicks, replies) for demo purposes.

        Args:
            campaign_id: ID of the campaign
            engagement_rate: Percentage of emails that get opened (0.0 - 1.0)

        Returns:
            Dictionary with engagement simulation results
        """
        # Get all outreach logs for this campaign
        logs = self.db.query(OutreachLog).filter(
            OutreachLog.campaign_id == campaign_id,
            OutreachLog.status == 'sent'
        ).all()

        opened = 0
        clicked = 0
        replied = 0

        for log in logs:
            # Simulate open
            if random.random() < engagement_rate:
                log.opened_at = datetime.utcnow() - timedelta(hours=random.randint(1, 48))
                opened += 1

                # If opened, might click
                if random.random() < 0.4:  # 40% of opens lead to clicks
                    log.clicked_at = log.opened_at + timedelta(minutes=random.randint(5, 120))
                    clicked += 1

                    # If clicked, might reply
                    if random.random() < 0.15:  # 15% of clicks lead to replies
                        log.replied_at = log.clicked_at + timedelta(hours=random.randint(1, 24))
                        log.status = 'replied'
                        replied += 1
                    else:
                        log.status = 'clicked'
                else:
                    log.status = 'opened'

        # Update campaign metrics
        campaign = self.db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if campaign:
            campaign.opened_count = opened
            campaign.clicked_count = clicked
            campaign.replied_count = replied

        self.db.commit()

        return {
            'campaign_id': campaign_id,
            'total_sent': len(logs),
            'opened': opened,
            'clicked': clicked,
            'replied': replied,
            'open_rate': (opened / len(logs) * 100) if logs else 0,
            'click_rate': (clicked / opened * 100) if opened else 0,
            'reply_rate': (replied / clicked * 100) if clicked else 0,
        }

    def _create_outreach_log(self, campaign: Campaign, property_obj: Property) -> OutreachLog:
        """Create an outreach log entry for a sent email."""
        # Generate simulated recipient email
        recipient_email = self._generate_recipient_email(property_obj)

        # Create log
        log = OutreachLog(
            campaign_id=campaign.id,
            property_id=property_obj.id,
            recipient_email=recipient_email,
            subject=f"Investment Opportunity: {property_obj.address}",
            status='sent',
            sent_at=datetime.utcnow(),
            template_used=campaign.template_type,
            metadata={
                'property_address': property_obj.address,
                'property_city': property_obj.city,
                'property_price': property_obj.price,
                'campaign_name': campaign.name,
            }
        )

        return log

    def _generate_recipient_email(self, property_obj: Property) -> str:
        """Generate a simulated recipient email address."""
        # Create email from property address
        address_slug = property_obj.address.lower().replace(' ', '.').replace(',', '')
        domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'icloud.com']
        domain = random.choice(domains)

        return f"owner.{address_slug[:20]}@{domain}"

    def get_campaign_logs(self, campaign_id: int) -> List[OutreachLog]:
        """Get all outreach logs for a campaign."""
        return self.db.query(OutreachLog).filter(
            OutreachLog.campaign_id == campaign_id
        ).order_by(OutreachLog.sent_at.desc()).all()

    def get_property_outreach_history(self, property_id: int) -> List[OutreachLog]:
        """Get outreach history for a specific property."""
        return self.db.query(OutreachLog).filter(
            OutreachLog.property_id == property_id
        ).order_by(OutreachLog.sent_at.desc()).all()


def send_campaign_emails(campaign_id: int, db: Session, simulate_engagement: bool = True) -> Dict:
    """
    Standalone function to send campaign emails.
    Used by DAGs and background tasks.

    Args:
        campaign_id: ID of the campaign to execute
        db: Database session
        simulate_engagement: Whether to simulate engagement after sending

    Returns:
        Campaign execution results
    """
    service = EmailService(db)

    # Send emails
    result = service.send_campaign(campaign_id)

    # Optionally simulate engagement for demo purposes
    if simulate_engagement and result['sent'] > 0:
        engagement = service.simulate_engagement(campaign_id, engagement_rate=0.35)
        result['engagement'] = engagement

    return result
