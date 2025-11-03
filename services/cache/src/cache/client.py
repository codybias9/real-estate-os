"""
Redis cache client
"""

import os
import json
import hashlib
from typing import Any, Optional, Union
from datetime import timedelta

import redis
from redis import Redis


class CacheClient:
    """
    Redis cache client with automatic serialization/deserialization.

    Supports:
    - Automatic JSON serialization
    - TTL (time-to-live)
    - Pattern-based deletion
    - Connection pooling
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        default_ttl: int = 3600,
        key_prefix: str = "realestate:",
    ):
        """
        Initialize cache client.

        Args:
            redis_url: Redis connection URL (from env if not provided)
            default_ttl: Default TTL in seconds (1 hour)
            key_prefix: Prefix for all cache keys
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix

        # Initialize Redis connection
        try:
            self.client = Redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # Test connection
            self.client.ping()
            self.available = True
        except (redis.ConnectionError, redis.TimeoutError) as e:
            # Fallback mode when Redis is unavailable
            self.client = None
            self.available = False
            print(f"Warning: Redis unavailable ({e}), caching disabled")

    def _make_key(self, key: str) -> str:
        """
        Make full cache key with prefix.

        Args:
            key: Cache key

        Returns:
            Full key with prefix
        """
        return f"{self.key_prefix}{key}"

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache.

        Args:
            key: Cache key
            default: Default value if key not found

        Returns:
            Cached value or default
        """
        if not self.available:
            return default

        try:
            full_key = self._make_key(key)
            value = self.client.get(full_key)

            if value is None:
                return default

            # Deserialize JSON
            return json.loads(value)

        except Exception as e:
            print(f"Cache get error: {e}")
            return default

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: TTL in seconds (uses default if not provided)

        Returns:
            True if successful, False otherwise
        """
        if not self.available:
            return False

        try:
            full_key = self._make_key(key)
            ttl = ttl or self.default_ttl

            # Serialize to JSON
            serialized = json.dumps(value)

            # Set with TTL
            self.client.setex(full_key, ttl, serialized)
            return True

        except Exception as e:
            print(f"Cache set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False otherwise
        """
        if not self.available:
            return False

        try:
            full_key = self._make_key(key)
            self.client.delete(full_key)
            return True

        except Exception as e:
            print(f"Cache delete error: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.

        Args:
            pattern: Redis pattern (e.g., "property:*", "score:*")

        Returns:
            Number of keys deleted
        """
        if not self.available:
            return 0

        try:
            full_pattern = self._make_key(pattern)

            # Scan for matching keys
            deleted = 0
            cursor = 0
            while True:
                cursor, keys = self.client.scan(
                    cursor=cursor,
                    match=full_pattern,
                    count=100,
                )

                if keys:
                    self.client.delete(*keys)
                    deleted += len(keys)

                if cursor == 0:
                    break

            return deleted

        except Exception as e:
            print(f"Cache delete_pattern error: {e}")
            return 0

    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if exists, False otherwise
        """
        if not self.available:
            return False

        try:
            full_key = self._make_key(key)
            return bool(self.client.exists(full_key))

        except Exception as e:
            print(f"Cache exists error: {e}")
            return False

    def ttl(self, key: str) -> int:
        """
        Get TTL for key.

        Args:
            key: Cache key

        Returns:
            TTL in seconds (-1 if no expiry, -2 if key doesn't exist)
        """
        if not self.available:
            return -2

        try:
            full_key = self._make_key(key)
            return self.client.ttl(full_key)

        except Exception as e:
            print(f"Cache ttl error: {e}")
            return -2

    def incr(self, key: str, amount: int = 1) -> int:
        """
        Increment counter.

        Args:
            key: Cache key
            amount: Amount to increment by

        Returns:
            New value
        """
        if not self.available:
            return 0

        try:
            full_key = self._make_key(key)
            return self.client.incrby(full_key, amount)

        except Exception as e:
            print(f"Cache incr error: {e}")
            return 0

    def flush(self) -> bool:
        """
        Flush all keys with prefix (use with caution!).

        Returns:
            True if successful
        """
        if not self.available:
            return False

        try:
            # delete_pattern already adds prefix, so just use "*"
            self.delete_pattern("*")
            return True

        except Exception as e:
            print(f"Cache flush error: {e}")
            return False


# Global cache client instance
_cache_client: Optional[CacheClient] = None


def get_cache_client() -> CacheClient:
    """
    Get global cache client instance.

    Returns:
        CacheClient instance
    """
    global _cache_client

    if _cache_client is None:
        _cache_client = CacheClient()

    return _cache_client
