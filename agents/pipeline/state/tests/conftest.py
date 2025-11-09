"""
Pytest configuration for Pipeline.State tests
"""

import sys
from pathlib import Path

# Add src to path for imports
state_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(state_src))

import pytest
from uuid import uuid4
from datetime import datetime, timezone


@pytest.fixture
def tenant_id():
    """Sample tenant UUID"""
    return str(uuid4())


@pytest.fixture
def property_id():
    """Sample property UUID"""
    return str(uuid4())


@pytest.fixture
def event_id():
    """Sample event UUID"""
    return str(uuid4())


@pytest.fixture
def discovery_event(property_id, event_id):
    """Sample discovery event"""
    return {
        "event_id": event_id,
        "event_subject": "event.discovery.intake",
        "payload": {
            "property_id": property_id,
            "apn": "123-456-789",
            "status": "new",
        },
    }


@pytest.fixture
def enrichment_event(property_id):
    """Sample enrichment event"""
    return {
        "event_id": str(uuid4()),
        "event_subject": "event.enrichment.features",
        "payload": {
            "property_id": property_id,
            "features_added": ["owner", "tax_history"],
        },
    }


@pytest.fixture
def score_event(property_id):
    """Sample score event"""
    return {
        "event_id": str(uuid4()),
        "event_subject": "event.score.created",
        "payload": {
            "property_id": property_id,
            "score": 78,
        },
    }


@pytest.fixture
def memo_event(property_id):
    """Sample memo event"""
    return {
        "event_id": str(uuid4()),
        "event_subject": "event.docgen.memo",
        "payload": {
            "property_id": property_id,
            "pdf_url": "s3://bucket/memo.pdf",
        },
    }
