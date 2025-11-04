"""Base model mixins and utilities."""
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, Boolean, func


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def soft_delete(self):
        """Mark record as deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()

    def restore(self):
        """Restore a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None
