"""Data cleanup Celery tasks."""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from celery import Task

from .celery_app import celery_app
from ..database import SessionLocal
from ..models import IdempotencyKey, AuditLog, WebhookLog


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


@celery_app.task(base=DatabaseTask, bind=True)
def cleanup_idempotency_keys(self):
    """Clean up expired idempotency keys."""
    db = self.db

    try:
        now = datetime.utcnow()

        # Delete expired keys
        deleted_count = db.query(IdempotencyKey).filter(
            IdempotencyKey.expires_at < now
        ).delete()

        db.commit()

        return {
            "deleted_count": deleted_count,
            "timestamp": now.isoformat(),
        }

    except Exception as e:
        db.rollback()
        return {"error": str(e)}


@celery_app.task(base=DatabaseTask, bind=True)
def cleanup_audit_logs(self, days: int = 90):
    """
    Clean up old audit logs.

    Args:
        days: Number of days to keep logs (default: 90)
    """
    db = self.db

    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Delete old audit logs
        deleted_count = db.query(AuditLog).filter(
            AuditLog.created_at < cutoff_date
        ).delete()

        db.commit()

        return {
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
        }

    except Exception as e:
        db.rollback()
        return {"error": str(e)}


@celery_app.task(base=DatabaseTask, bind=True)
def cleanup_old_webhook_logs(self, days: int = 30):
    """
    Clean up old successful webhook logs.

    Args:
        days: Number of days to keep logs (default: 30)
    """
    db = self.db

    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Delete old successful webhooks only
        deleted_count = db.query(WebhookLog).filter(
            WebhookLog.created_at < cutoff_date,
            WebhookLog.success == True,
        ).delete()

        db.commit()

        return {
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
        }

    except Exception as e:
        db.rollback()
        return {"error": str(e)}


@celery_app.task(base=DatabaseTask, bind=True)
def cleanup_soft_deleted_records(self, days: int = 30):
    """
    Permanently delete soft-deleted records older than specified days.

    Args:
        days: Number of days to keep soft-deleted records (default: 30)
    """
    db = self.db

    try:
        from ..models import Property, Lead, Deal

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Permanently delete old soft-deleted properties
        properties_deleted = db.query(Property).filter(
            Property.deleted_at < cutoff_date,
            Property.deleted_at.isnot(None),
        ).delete()

        # Permanently delete old soft-deleted leads
        leads_deleted = db.query(Lead).filter(
            Lead.deleted_at < cutoff_date,
            Lead.deleted_at.isnot(None),
        ).delete()

        # Permanently delete old soft-deleted deals
        deals_deleted = db.query(Deal).filter(
            Deal.deleted_at < cutoff_date,
            Deal.deleted_at.isnot(None),
        ).delete()

        db.commit()

        return {
            "properties_deleted": properties_deleted,
            "leads_deleted": leads_deleted,
            "deals_deleted": deals_deleted,
            "cutoff_date": cutoff_date.isoformat(),
        }

    except Exception as e:
        db.rollback()
        return {"error": str(e)}


@celery_app.task(base=DatabaseTask, bind=True)
def vacuum_database(self):
    """Run database maintenance and optimization."""
    db = self.db

    try:
        # PostgreSQL VACUUM ANALYZE
        db.execute("VACUUM ANALYZE")
        db.commit()

        return {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        return {"error": str(e)}


@celery_app.task(base=DatabaseTask, bind=True)
def generate_backup_metadata(self):
    """Generate metadata for database backup."""
    db = self.db

    try:
        from ..models import Organization, User, Property, Lead, Deal, Campaign

        metadata = {
            "timestamp": datetime.utcnow().isoformat(),
            "organizations": db.query(Organization).count(),
            "users": db.query(User).count(),
            "properties": db.query(Property).count(),
            "leads": db.query(Lead).count(),
            "deals": db.query(Deal).count(),
            "campaigns": db.query(Campaign).count(),
        }

        return metadata

    except Exception as e:
        return {"error": str(e)}
