"""
Tests for Redis cache client
"""

import pytest
import fakeredis
from cache.client import CacheClient


class TestCacheClient:
    """Tests for cache client"""

    @pytest.fixture
    def cache(self):
        """Create cache client with fake Redis"""
        # Use fakeredis for testing
        client = CacheClient()
        # Replace Redis client with fake one
        client.client = fakeredis.FakeRedis(decode_responses=True)
        client.available = True
        return client

    def test_create_cache_client(self, cache):
        """Test creating cache client"""
        assert cache.available is True
        assert cache.key_prefix == "realestate:"
        assert cache.default_ttl == 3600

    def test_make_key(self, cache):
        """Test making cache key with prefix"""
        key = cache._make_key("test")
        assert key == "realestate:test"

    def test_get_nonexistent_key(self, cache):
        """Test getting nonexistent key returns default"""
        result = cache.get("nonexistent", default="default_value")
        assert result == "default_value"

    def test_set_and_get(self, cache):
        """Test setting and getting value"""
        cache.set("test_key", {"data": "value"})
        result = cache.get("test_key")
        assert result == {"data": "value"}

    def test_set_with_ttl(self, cache):
        """Test setting value with custom TTL"""
        cache.set("test_key", "value", ttl=300)
        result = cache.get("test_key")
        assert result == "value"

    def test_delete_key(self, cache):
        """Test deleting key"""
        cache.set("test_key", "value")
        assert cache.get("test_key") == "value"

        cache.delete("test_key")
        assert cache.get("test_key") is None

    def test_delete_pattern(self, cache):
        """Test deleting keys by pattern"""
        # Set multiple keys
        cache.set("property:1", "value1")
        cache.set("property:2", "value2")
        cache.set("property:3", "value3")
        cache.set("other:1", "other_value")

        # Delete property:* pattern
        deleted = cache.delete_pattern("property:*")
        assert deleted == 3

        # Check property keys are gone
        assert cache.get("property:1") is None
        assert cache.get("property:2") is None
        assert cache.get("property:3") is None

        # Check other key still exists
        assert cache.get("other:1") == "other_value"

    def test_exists(self, cache):
        """Test checking if key exists"""
        assert cache.exists("test_key") is False

        cache.set("test_key", "value")
        assert cache.exists("test_key") is True

        cache.delete("test_key")
        assert cache.exists("test_key") is False

    def test_ttl(self, cache):
        """Test getting TTL for key"""
        # Nonexistent key
        assert cache.ttl("nonexistent") == -2

        # Set key with TTL
        cache.set("test_key", "value", ttl=300)
        ttl = cache.ttl("test_key")
        assert ttl > 0 and ttl <= 300

    def test_incr(self, cache):
        """Test incrementing counter"""
        # First increment
        result = cache.incr("counter")
        assert result == 1

        # Second increment
        result = cache.incr("counter")
        assert result == 2

        # Increment by 5
        result = cache.incr("counter", amount=5)
        assert result == 7

    def test_flush(self, cache):
        """Test flushing all keys"""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        result = cache.flush()
        assert result is True

        # All keys should be gone
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None

    def test_json_serialization(self, cache):
        """Test automatic JSON serialization"""
        # Complex nested structure
        data = {
            "id": "123",
            "name": "Test Property",
            "metadata": {
                "beds": 3,
                "baths": 2.5,
                "features": ["pool", "garage", "fireplace"],
            },
        }

        cache.set("property", data)
        result = cache.get("property")

        assert result == data
        assert result["metadata"]["features"] == ["pool", "garage", "fireplace"]

    def test_unavailable_cache(self):
        """Test cache operations when Redis is unavailable"""
        cache = CacheClient()
        cache.available = False
        cache.client = None

        # All operations should gracefully degrade
        assert cache.get("key") is None
        assert cache.set("key", "value") is False
        assert cache.delete("key") is False
        assert cache.delete_pattern("*") == 0
        assert cache.exists("key") is False
        assert cache.ttl("key") == -2
        assert cache.incr("counter") == 0
        assert cache.flush() is False

    def test_error_handling(self, cache):
        """Test error handling"""
        # Force an error by setting client to None temporarily
        original_client = cache.client
        cache.client = None
        cache.available = True  # Still marked as available but client is None

        # Operations should handle errors gracefully
        result = cache.get("key")
        assert result is None

        # Restore client
        cache.client = original_client

    def test_get_cache_client_singleton(self):
        """Test global cache client singleton"""
        from cache.client import get_cache_client

        client1 = get_cache_client()
        client2 = get_cache_client()

        # Should be the same instance
        assert client1 is client2
