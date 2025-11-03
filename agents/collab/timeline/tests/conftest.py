"""
Pytest configuration for Collab.Timeline tests
"""

import sys
from pathlib import Path

# Add src to path for imports
timeline_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(timeline_src))

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
def user_id():
    """Sample user UUID"""
    return str(uuid4())


@pytest.fixture
def user_name():
    """Sample user name"""
    return "John Doe"


@pytest.fixture
def event_id():
    """Sample event UUID"""
    return str(uuid4())
