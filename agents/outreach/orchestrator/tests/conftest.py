"""
Pytest configuration for Outreach.Orchestrator tests
"""

import sys
from pathlib import Path

# Add src to path for imports
orchestrator_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(orchestrator_src))

# Add contracts to path
contracts_src = (
    Path(__file__).parent.parent.parent.parent / "packages" / "contracts" / "src"
)
sys.path.insert(0, str(contracts_src))

import pytest
from datetime import datetime, timezone
from uuid import uuid4


@pytest.fixture
def tenant_id():
    """Sample tenant UUID"""
    return str(uuid4())


@pytest.fixture
def property_id():
    """Sample property UUID"""
    return str(uuid4())


@pytest.fixture
def campaign_id():
    """Sample campaign UUID"""
    return str(uuid4())


@pytest.fixture
def sample_property(property_id):
    """Sample property record"""
    return {
        "id": property_id,
        "apn": "123-456-789",
        "address": {
            "line1": "123 Main St",
            "city": "Springfield",
            "state": "CA",
            "zip": "90210",
        },
        "owner": {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "type": "person",
        },
        "attrs": {
            "beds": 3,
            "baths": 2.0,
            "sqft": 1500,
            "year_built": 1985,
        },
    }


@pytest.fixture
def sample_score():
    """Sample score result"""
    return {
        "score": 78,
        "reasons": [
            {
                "feature": "price_sqft",
                "weight": 0.3,
                "direction": "positive",
                "note": "Price per sqft is 15% below market average",
                "raw_value": 250.0,
                "benchmark": 295.0,
            },
            {
                "feature": "days_on_market",
                "weight": 0.25,
                "direction": "positive",
                "note": "Property has been on market for 45 days",
                "raw_value": 45,
                "benchmark": 30,
            },
            {
                "feature": "cap_rate",
                "weight": 0.2,
                "direction": "positive",
                "note": "Estimated cap rate of 8.5% exceeds target",
                "raw_value": 8.5,
                "benchmark": 7.0,
            },
        ],
        "model_version": "deterministic-v1",
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def memo_url():
    """Sample memo URL"""
    return "https://s3.amazonaws.com/bucket/tenants/tenant-uuid/memos/abc123.pdf"
