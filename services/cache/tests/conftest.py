"""
Pytest configuration for cache tests
"""

import pytest


@pytest.fixture(autouse=True)
def reset_cache_singletons():
    """Reset global cache singletons before each test"""
    # Reset cache client singleton
    import cache.client
    cache.client._cache_client = None

    # Reset invalidator singleton
    import cache.invalidation
    cache.invalidation._invalidator = None
    cache.invalidation._event_invalidator = None

    yield

    # Clean up after test
    cache.client._cache_client = None
    cache.invalidation._invalidator = None
    cache.invalidation._event_invalidator = None
