"""
Message Envelope - Required wrapper for all events/commands
Ensures idempotency, traceability, and versioning
"""

from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


T = TypeVar("T")


class Envelope(BaseModel, Generic[T]):
    """
    Canonical envelope for all messages in the system.

    Guarantees:
    - Idempotency via idempotency_key
    - Causality tracking via correlation_id + causation_id
    - Multi-tenancy via tenant_id
    - Schema evolution via schema_version
    """

    id: UUID = Field(default_factory=uuid4, description="Unique message ID")
    tenant_id: UUID = Field(..., description="Tenant isolation boundary")
    subject: str = Field(..., description="Event/command type (e.g., 'event.score.created')")
    schema_version: str = Field(default="1.0", description="Payload schema version")
    idempotency_key: str = Field(..., description="Deduplication key (source-specific)")
    correlation_id: UUID = Field(..., description="End-to-end flow identifier")
    causation_id: UUID = Field(..., description="Direct cause message ID")
    at: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp (ISO-8601)")
    payload: T = Field(..., description="Typed payload matching subject")

    class Config:
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat(),
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict with proper encoding"""
        return self.model_dump(mode="json")
