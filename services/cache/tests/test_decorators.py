"""
Tests for cache decorators
"""

import pytest
import fakeredis
from cache.decorators import (
    cached,
    cached_property_list,
    cached_property_detail,
    cached_property_score,
    cached_timeline,
    cache_aside,
    cache_through,
)
from cache.client import get_cache_client


@pytest.fixture
def mock_cache():
    """Mock cache client with fake Redis"""
    cache = get_cache_client()
    cache.client = fakeredis.FakeRedis(decode_responses=True)
    cache.available = True
    # Clear before each test
    cache.flush()
    return cache


class TestCachedDecorator:
    """Tests for @cached decorator"""

    def test_cached_basic(self, mock_cache):
        """Test basic caching"""
        call_count = {"count": 0}

        @cached()
        def expensive_function(x: int) -> int:
            call_count["count"] += 1
            return x * 2

        # First call - should execute
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count["count"] == 1

        # Second call - should use cache
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count["count"] == 1  # Not called again

    def test_cached_different_args(self, mock_cache):
        """Test caching with different arguments"""
        call_count = {"count": 0}

        @cached()
        def expensive_function(x: int) -> int:
            call_count["count"] += 1
            return x * 2

        # Call with different arguments
        result1 = expensive_function(5)
        result2 = expensive_function(10)

        assert result1 == 10
        assert result2 == 20
        assert call_count["count"] == 2  # Called twice for different args

        # Call again with same args
        result3 = expensive_function(5)
        result4 = expensive_function(10)

        assert result3 == 10
        assert result4 == 20
        assert call_count["count"] == 2  # Not called again

    def test_cached_with_ttl(self, mock_cache):
        """Test caching with custom TTL"""

        @cached(ttl=300)
        def expensive_function(x: int) -> int:
            return x * 2

        result = expensive_function(5)
        assert result == 10

        # Check TTL was set
        cache_key = expensive_function.cache_key(5)
        ttl = mock_cache.ttl(cache_key)
        assert ttl > 0 and ttl <= 300

    def test_cached_with_key_prefix(self, mock_cache):
        """Test caching with custom key prefix"""

        @cached(key_prefix="my_func")
        def expensive_function(x: int) -> int:
            return x * 2

        result = expensive_function(5)
        assert result == 10

        # Check key has custom prefix
        cache_key = expensive_function.cache_key(5)
        assert cache_key.startswith("my_func:")

    def test_cached_with_key_builder(self, mock_cache):
        """Test caching with custom key builder"""

        @cached(key_builder=lambda user_id, tenant_id: f"{tenant_id}:{user_id}")
        def get_user(user_id: str, tenant_id: str):
            return {"id": user_id, "tenant": tenant_id}

        result = get_user("user123", "tenant456")
        assert result == {"id": "user123", "tenant": "tenant456"}

        # Check key uses custom builder
        cache_key = get_user.cache_key("user123", "tenant456")
        assert cache_key == "tenant456:user123"

    def test_cached_cache_clear(self, mock_cache):
        """Test cache_clear method"""
        call_count = {"count": 0}

        @cached()
        def expensive_function(x: int) -> int:
            call_count["count"] += 1
            return x * 2

        # Call and cache
        expensive_function(5)
        expensive_function(10)
        assert call_count["count"] == 2

        # Clear cache
        expensive_function.cache_clear()

        # Call again - should execute
        expensive_function(5)
        expensive_function(10)
        assert call_count["count"] == 4

    def test_cached_with_kwargs(self, mock_cache):
        """Test caching with keyword arguments"""

        @cached()
        def expensive_function(x: int, multiplier: int = 2) -> int:
            return x * multiplier

        result1 = expensive_function(5, multiplier=3)
        result2 = expensive_function(5, multiplier=3)

        assert result1 == 15
        assert result2 == 15  # From cache

    def test_cached_complex_return(self, mock_cache):
        """Test caching complex return values"""

        @cached()
        def get_property(property_id: str):
            return {
                "id": property_id,
                "address": "123 Main St",
                "beds": 3,
                "baths": 2.5,
                "features": ["pool", "garage"],
            }

        result = get_property("prop123")
        assert result["id"] == "prop123"
        assert result["features"] == ["pool", "garage"]


class TestCacheKeyBuilders:
    """Tests for cache key builder functions"""

    def test_cached_property_list(self):
        """Test property list cache key"""
        key = cached_property_list("tenant123", {"state": "scored"})
        assert key.startswith("properties:list:tenant123:")
        assert len(key.split(":")) == 4  # prefix:type:tenant:hash

    def test_cached_property_list_no_filters(self):
        """Test property list cache key without filters"""
        key = cached_property_list("tenant123")
        assert key.startswith("properties:list:tenant123:")

    def test_cached_property_detail(self):
        """Test property detail cache key"""
        key = cached_property_detail("prop123")
        assert key == "property:detail:prop123"

    def test_cached_property_score(self):
        """Test property score cache key"""
        key = cached_property_score("prop123")
        assert key == "property:score:prop123"

    def test_cached_timeline(self):
        """Test timeline cache key"""
        key = cached_timeline("prop123")
        assert key == "property:timeline:prop123"


class TestCachePatterns:
    """Tests for cache-aside and cache-through patterns"""

    def test_cache_aside_hit(self, mock_cache):
        """Test cache-aside pattern with cache hit"""
        # Populate cache
        mock_cache.set("user:123", {"id": "123", "name": "Alice"})

        fetch_count = {"count": 0}

        def fetch_user():
            fetch_count["count"] += 1
            return {"id": "123", "name": "Alice"}

        result = cache_aside(
            cache_key="user:123",
            fetch_func=fetch_user,
            ttl=300,
        )

        assert result == {"id": "123", "name": "Alice"}
        assert fetch_count["count"] == 0  # Not fetched

    def test_cache_aside_miss(self, mock_cache):
        """Test cache-aside pattern with cache miss"""
        fetch_count = {"count": 0}

        def fetch_user():
            fetch_count["count"] += 1
            return {"id": "123", "name": "Alice"}

        result = cache_aside(
            cache_key="user:123",
            fetch_func=fetch_user,
            ttl=300,
        )

        assert result == {"id": "123", "name": "Alice"}
        assert fetch_count["count"] == 1  # Fetched

        # Check value was cached
        cached_value = mock_cache.get("user:123")
        assert cached_value == {"id": "123", "name": "Alice"}

    def test_cache_through(self, mock_cache):
        """Test cache-through (write-through) pattern"""
        persist_count = {"count": 0}

        def persist_user():
            persist_count["count"] += 1
            return {"id": "123", "name": "Alice", "email": "alice@example.com"}

        result = cache_through(
            cache_key="user:123",
            value={"id": "123", "name": "Alice"},
            persist_func=persist_user,
            ttl=300,
        )

        assert result == {"id": "123", "name": "Alice", "email": "alice@example.com"}
        assert persist_count["count"] == 1

        # Check value was cached
        cached_value = mock_cache.get("user:123")
        assert cached_value == {"id": "123", "name": "Alice", "email": "alice@example.com"}
