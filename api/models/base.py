"""Base model with common fields."""
from sqlalchemy import Column, Integer, DateTime, String
from sqlalchemy.sql import func
from ..database import Base


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""

    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(Integer, nullable=True)


class BaseModel(Base, TimestampMixin):
    """Abstract base model with timestamps."""

    __abstract__ = True
    id = Column(Integer, primary_key=True, index=True)
