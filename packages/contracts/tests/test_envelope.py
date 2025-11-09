"""Tests for message envelope"""

from datetime import datetime
from uuid import UUID, uuid4
import pytest
from pydantic import ValidationError

from contracts import Envelope


def test_envelope_creation():
    """Test basic envelope creation"""
    tenant_id = uuid4()
    correlation_id = uuid4()
    causation_id = uuid4()

    envelope = Envelope(
        tenant_id=tenant_id,
        subject="event.test.created",
        idempotency_key="test-123",
        correlation_id=correlation_id,
        causation_id=causation_id,
        payload={"test": "data"}
    )

    assert isinstance(envelope.id, UUID)
    assert envelope.tenant_id == tenant_id
    assert envelope.subject == "event.test.created"
    assert envelope.schema_version == "1.0"
    assert envelope.idempotency_key == "test-123"
    assert isinstance(envelope.at, datetime)
    assert envelope.payload == {"test": "data"}


def test_envelope_requires_fields():
    """Test that required fields are enforced"""
    with pytest.raises(ValidationError):
        Envelope(payload={"test": "data"})


def test_envelope_serialization():
    """Test envelope can be serialized to dict"""
    envelope = Envelope(
        tenant_id=uuid4(),
        subject="event.test.created",
        idempotency_key="test-123",
        correlation_id=uuid4(),
        causation_id=uuid4(),
        payload={"test": "data"}
    )

    data = envelope.to_dict()

    assert isinstance(data["id"], str)
    assert isinstance(data["tenant_id"], str)
    assert isinstance(data["at"], str)
    assert data["subject"] == "event.test.created"
    assert data["payload"] == {"test": "data"}
