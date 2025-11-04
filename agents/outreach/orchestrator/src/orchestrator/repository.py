"""
Repository for outreach campaign persistence
"""

import os
from typing import Optional, List
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import create_engine, and_, text
from sqlalchemy.orm import sessionmaker, Session

from .models import Base, OutreachCampaignModel, OutreachEventModel, OutreachStatusEnum


class OutreachRepository:
    """
    Repository for outreach campaign operations.

    Provides campaign creation, status updates, and event logging.
    """

    def __init__(self, db_dsn: Optional[str] = None):
        """
        Initialize repository with database connection.

        Args:
            db_dsn: Database connection string. If None, reads from DB_DSN env var.
        """
        self.db_dsn = db_dsn or os.getenv("DB_DSN")
        if not self.db_dsn:
            raise ValueError("DB_DSN must be provided or set in environment")

        self.engine = create_engine(self.db_dsn)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Detect if we're using PostgreSQL (for RLS support)
        self.is_postgresql = "postgresql" in self.db_dsn.lower()

    def create_tables(self):
        """Create all tables (for testing only, use Alembic in production)"""
        Base.metadata.create_all(self.engine)

    def set_tenant_context(self, session: Session, tenant_id: str):
        """Set the current tenant context for RLS policies (PostgreSQL only)"""
        if self.is_postgresql:
            session.execute(text(f"SET app.current_tenant_id = '{tenant_id}';"))

    def reset_tenant_context(self, session: Session):
        """Reset the tenant context (PostgreSQL only)"""
        if self.is_postgresql:
            session.execute(text("RESET app.current_tenant_id;"))

    def create_campaign(
        self,
        tenant_id: str,
        property_id: str,
        owner_name: str,
        owner_email: str,
        subject: str,
        memo_url: Optional[str] = None,
        scheduled_at: Optional[datetime] = None,
        context: Optional[dict] = None,
    ) -> OutreachCampaignModel:
        """
        Create new outreach campaign.

        Args:
            tenant_id: Tenant UUID
            property_id: Property UUID
            owner_name: Property owner name
            owner_email: Property owner email
            subject: Email subject line
            memo_url: URL to property memo (PDF)
            scheduled_at: When to send email (default: now)
            context: Additional context data

        Returns:
            Created OutreachCampaignModel
        """
        with self.SessionLocal() as session:
            self.set_tenant_context(session, tenant_id)

            try:
                campaign = OutreachCampaignModel(
                    tenant_id=tenant_id,
                    property_id=property_id,
                    owner_name=owner_name,
                    owner_email=owner_email,
                    subject=subject,
                    memo_url=memo_url,
                    status=OutreachStatusEnum.SCHEDULED.value,
                    scheduled_at=scheduled_at or datetime.now(timezone.utc),
                    context=context or {},
                )

                session.add(campaign)
                session.commit()
                session.refresh(campaign)

                return campaign
            finally:
                self.reset_tenant_context(session)

    def get_campaign(self, campaign_id: str, tenant_id: str) -> Optional[OutreachCampaignModel]:
        """
        Get campaign by ID.

        Args:
            campaign_id: Campaign UUID
            tenant_id: Tenant UUID

        Returns:
            OutreachCampaignModel if found, None otherwise
        """
        with self.SessionLocal() as session:
            self.set_tenant_context(session, tenant_id)

            try:
                return (
                    session.query(OutreachCampaignModel)
                    .filter(
                        and_(
                            OutreachCampaignModel.id == campaign_id,
                            OutreachCampaignModel.tenant_id == tenant_id,
                        )
                    )
                    .first()
                )
            finally:
                self.reset_tenant_context(session)

    def get_campaign_by_property(
        self, property_id: str, tenant_id: str
    ) -> Optional[OutreachCampaignModel]:
        """
        Get campaign for a property.

        Args:
            property_id: Property UUID
            tenant_id: Tenant UUID

        Returns:
            OutreachCampaignModel if found, None otherwise
        """
        with self.SessionLocal() as session:
            self.set_tenant_context(session, tenant_id)

            try:
                return (
                    session.query(OutreachCampaignModel)
                    .filter(
                        and_(
                            OutreachCampaignModel.property_id == property_id,
                            OutreachCampaignModel.tenant_id == tenant_id,
                        )
                    )
                    .first()
                )
            finally:
                self.reset_tenant_context(session)

    def update_campaign_status(
        self,
        campaign_id: str,
        tenant_id: str,
        status: OutreachStatusEnum,
        sendgrid_message_id: Optional[str] = None,
        **timestamp_fields,
    ) -> OutreachCampaignModel:
        """
        Update campaign status and timestamps.

        Args:
            campaign_id: Campaign UUID
            tenant_id: Tenant UUID
            status: New status
            sendgrid_message_id: SendGrid message ID (for tracking)
            **timestamp_fields: sent_at, delivered_at, opened_at, clicked_at, responded_at

        Returns:
            Updated OutreachCampaignModel

        Raises:
            ValueError: If campaign not found
        """
        with self.SessionLocal() as session:
            self.set_tenant_context(session, tenant_id)

            try:
                campaign = (
                    session.query(OutreachCampaignModel)
                    .filter(
                        and_(
                            OutreachCampaignModel.id == campaign_id,
                            OutreachCampaignModel.tenant_id == tenant_id,
                        )
                    )
                    .first()
                )

                if not campaign:
                    raise ValueError(f"Campaign not found: {campaign_id}")

                # Update status
                campaign.status = status.value

                # Update SendGrid message ID
                if sendgrid_message_id:
                    campaign.sendgrid_message_id = sendgrid_message_id

                # Update timestamp fields
                for field, value in timestamp_fields.items():
                    if hasattr(campaign, field):
                        setattr(campaign, field, value)

                campaign.updated_at = datetime.now(timezone.utc)

                session.commit()
                session.refresh(campaign)

                return campaign
            finally:
                self.reset_tenant_context(session)

    def log_event(
        self,
        campaign_id: str,
        tenant_id: str,
        event_type: str,
        event_data: Optional[dict] = None,
    ) -> OutreachEventModel:
        """
        Log outreach event.

        Args:
            campaign_id: Campaign UUID
            tenant_id: Tenant UUID
            event_type: Event type (sent, delivered, opened, clicked, etc.)
            event_data: Event data (e.g., SendGrid webhook payload)

        Returns:
            Created OutreachEventModel
        """
        with self.SessionLocal() as session:
            self.set_tenant_context(session, tenant_id)

            try:
                event = OutreachEventModel(
                    campaign_id=campaign_id,
                    event_type=event_type,
                    event_data=event_data,
                    occurred_at=datetime.now(timezone.utc),
                )

                session.add(event)
                session.commit()
                session.refresh(event)

                return event
            finally:
                self.reset_tenant_context(session)

    def get_campaigns_by_status(
        self,
        status: OutreachStatusEnum,
        tenant_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[OutreachCampaignModel]:
        """
        Get campaigns by status.

        Args:
            status: Target status
            tenant_id: Tenant UUID
            limit: Maximum number of campaigns
            offset: Number of campaigns to skip

        Returns:
            List of OutreachCampaignModel
        """
        with self.SessionLocal() as session:
            self.set_tenant_context(session, tenant_id)

            try:
                return (
                    session.query(OutreachCampaignModel)
                    .filter(
                        and_(
                            OutreachCampaignModel.status == status.value,
                            OutreachCampaignModel.tenant_id == tenant_id,
                        )
                    )
                    .order_by(OutreachCampaignModel.scheduled_at.asc())
                    .limit(limit)
                    .offset(offset)
                    .all()
                )
            finally:
                self.reset_tenant_context(session)

    def count_by_status(self, tenant_id: str) -> dict[str, int]:
        """
        Count campaigns by status.

        Args:
            tenant_id: Tenant UUID

        Returns:
            Dict mapping status to count
        """
        with self.SessionLocal() as session:
            self.set_tenant_context(session, tenant_id)

            try:
                results = (
                    session.query(
                        OutreachCampaignModel.status,
                        OutreachCampaignModel.id,
                    )
                    .filter(OutreachCampaignModel.tenant_id == tenant_id)
                    .all()
                )

                counts = {}
                for status, _ in results:
                    counts[status] = counts.get(status, 0) + 1

                return counts
            finally:
                self.reset_tenant_context(session)
