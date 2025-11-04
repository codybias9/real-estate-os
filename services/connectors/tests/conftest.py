"""
Pytest configuration for connectors tests
"""

import pytest


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset global singletons before each test"""
    # Reset connector manager singleton
    import connectors.manager

    connectors.manager._connector_manager = None

    yield

    # Clean up after test
    connectors.manager._connector_manager = None
