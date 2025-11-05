"""Email notification Celery tasks."""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from celery import Task
import asyncio

from .celery_app import celery_app
from ..database import SessionLocal
from ..models import User, Lead, Property, Deal, Organization
from ..services.email import email_service


class DatabaseTask(Task):
    """Base task that provides database session."""

    _db = None

    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task
def send_welcome_email(user_email: str, user_name: str):
    """
    Send welcome email to new user.

    Args:
        user_email: User's email address
        user_name: User's name
    """
    subject = "Welcome to Real Estate OS!"
    body = f"""
    <h2>Welcome {user_name}!</h2>
    <p>Thank you for joining Real Estate OS. We're excited to have you on board!</p>
    <p>Here's what you can do next:</p>
    <ul>
        <li>Add your first property</li>
        <li>Import your leads</li>
        <li>Create your first campaign</li>
        <li>Set up your team</li>
    </ul>
    <p>If you need any help, our support team is here for you.</p>
    <p>Best regards,<br>The Real Estate OS Team</p>
    """

    success = asyncio.run(email_service.send_email(user_email, subject, body, html=True))
    return {"email": user_email, "success": success}


@celery_app.task(base=DatabaseTask, bind=True)
def send_lead_assignment_notification(self, lead_id: int, assigned_to_user_id: int):
    """
    Send notification when a lead is assigned.

    Args:
        lead_id: Lead ID
        assigned_to_user_id: User ID of assignee
    """
    db = self.db

    try:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        user = db.query(User).filter(User.id == assigned_to_user_id).first()

        if not lead or not user:
            return {"error": "Lead or user not found"}

        subject = f"New Lead Assigned: {lead.first_name} {lead.last_name}"
        body = f"""
        <h2>You have been assigned a new lead!</h2>
        <p><strong>Name:</strong> {lead.first_name} {lead.last_name}</p>
        <p><strong>Email:</strong> {lead.email}</p>
        <p><strong>Phone:</strong> {lead.phone}</p>
        <p><strong>Source:</strong> {lead.source.value}</p>
        <p><strong>Status:</strong> {lead.status.value}</p>
        <p><strong>Score:</strong> {lead.score}/100</p>
        {f"<p><strong>Notes:</strong> {lead.notes}</p>" if lead.notes else ""}
        <p><a href="http://localhost:3000/leads/{lead.id}">View Lead</a></p>
        <p>Please follow up as soon as possible!</p>
        """

        success = asyncio.run(email_service.send_email(user.email, subject, body, html=True))
        return {"lead_id": lead_id, "user_id": assigned_to_user_id, "success": success}

    except Exception as e:
        return {"error": str(e)}


@celery_app.task(base=DatabaseTask, bind=True)
def send_deal_update_notification(self, deal_id: int, stage: str):
    """
    Send notification when a deal stage changes.

    Args:
        deal_id: Deal ID
        stage: New stage
    """
    db = self.db

    try:
        deal = db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            return {"error": "Deal not found"}

        # Get users to notify (deal owner, assigned user, etc.)
        users_to_notify = []
        if deal.created_by:
            creator = db.query(User).filter(User.id == deal.created_by).first()
            if creator:
                users_to_notify.append(creator)

        if deal.assigned_to and deal.assigned_to != deal.created_by:
            assignee = db.query(User).filter(User.id == deal.assigned_to).first()
            if assignee:
                users_to_notify.append(assignee)

        subject = f"Deal Update: Stage Changed to {stage}"
        body = f"""
        <h2>Deal Stage Updated</h2>
        <p>A deal has been moved to <strong>{stage}</strong>.</p>
        <p><strong>Deal Value:</strong> ${deal.value:,.2f}</p>
        <p><strong>Deal Type:</strong> {deal.deal_type.value}</p>
        <p><strong>Expected Close:</strong> {deal.expected_close_date}</p>
        <p><a href="http://localhost:3000/deals/{deal.id}">View Deal</a></p>
        """

        results = []
        for user in users_to_notify:
            success = asyncio.run(email_service.send_email(user.email, subject, body, html=True))
            results.append({"user_id": user.id, "success": success})

        return {"deal_id": deal_id, "notifications": results}

    except Exception as e:
        return {"error": str(e)}


@celery_app.task(base=DatabaseTask, bind=True)
def send_daily_analytics_report(self):
    """Send daily analytics report to organization admins."""
    db = self.db

    try:
        # Get all organizations
        organizations = db.query(Organization).all()

        results = []

        for org in organizations:
            # Get admin users for this organization
            admins = db.query(User).filter(
                User.organization_id == org.id,
                User.is_superuser == True,
                User.is_active == True,
            ).all()

            if not admins:
                continue

            # Calculate yesterday's metrics
            yesterday = datetime.utcnow() - timedelta(days=1)
            start_of_day = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)

            # Count new entities
            new_properties = db.query(Property).filter(
                Property.organization_id == org.id,
                Property.created_at >= start_of_day,
                Property.created_at <= end_of_day,
            ).count()

            new_leads = db.query(Lead).filter(
                Lead.organization_id == org.id,
                Lead.created_at >= start_of_day,
                Lead.created_at <= end_of_day,
            ).count()

            new_deals = db.query(Deal).filter(
                Deal.organization_id == org.id,
                Deal.created_at >= start_of_day,
                Deal.created_at <= end_of_day,
            ).count()

            subject = f"Daily Analytics Report - {yesterday.strftime('%B %d, %Y')}"
            body = f"""
            <h2>Daily Analytics Report</h2>
            <h3>{org.name}</h3>
            <p>Here's your daily summary for {yesterday.strftime('%B %d, %Y')}:</p>

            <h4>New Activity</h4>
            <ul>
                <li><strong>Properties Added:</strong> {new_properties}</li>
                <li><strong>New Leads:</strong> {new_leads}</li>
                <li><strong>New Deals:</strong> {new_deals}</li>
            </ul>

            <p><a href="http://localhost:3000/analytics">View Full Analytics Dashboard</a></p>

            <p>Best regards,<br>Real Estate OS</p>
            """

            # Send to all admins
            for admin in admins:
                success = asyncio.run(
                    email_service.send_email(admin.email, subject, body, html=True)
                )
                results.append({
                    "organization_id": org.id,
                    "user_id": admin.id,
                    "success": success,
                })

        return {"reports_sent": len(results), "results": results}

    except Exception as e:
        return {"error": str(e)}


@celery_app.task(base=DatabaseTask, bind=True)
def send_password_reset_email(self, user_email: str, reset_token: str):
    """
    Send password reset email.

    Args:
        user_email: User's email
        reset_token: Password reset token
    """
    success = asyncio.run(
        email_service.send_password_reset_email(user_email, reset_token)
    )
    return {"email": user_email, "success": success}


@celery_app.task(base=DatabaseTask, bind=True)
def send_verification_email(self, user_email: str, verification_token: str):
    """
    Send email verification.

    Args:
        user_email: User's email
        verification_token: Verification token
    """
    success = asyncio.run(
        email_service.send_verification_email(user_email, verification_token)
    )
    return {"email": user_email, "success": success}


@celery_app.task(base=DatabaseTask, bind=True)
def send_bulk_notification(self, user_ids: list, subject: str, body: str):
    """
    Send bulk notification to multiple users.

    Args:
        user_ids: List of user IDs
        subject: Email subject
        body: Email body (HTML)
    """
    db = self.db

    try:
        users = db.query(User).filter(User.id.in_(user_ids)).all()

        results = []
        for user in users:
            success = asyncio.run(
                email_service.send_email(user.email, subject, body, html=True)
            )
            results.append({"user_id": user.id, "success": success})

        return {
            "total": len(user_ids),
            "sent": sum(1 for r in results if r["success"]),
            "results": results,
        }

    except Exception as e:
        return {"error": str(e)}
