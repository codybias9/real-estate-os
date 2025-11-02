"""
Redis client for rate limiting, caching, and session management.
"""
import redis.asyncio as redis
from typing import Optional, Any
import json
import logging
from datetime import timedelta

from api.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Async Redis client wrapper with utility methods."""

    def __init__(self):
        self._client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """Initialize Redis connection pool."""
        try:
            self._client = redis.from_url(
                settings.redis_url,
                password=settings.redis_password,
                max_connections=settings.redis_max_connections,
                encoding="utf-8",
                decode_responses=True,
            )
            # Test connection
            await self._client.ping()
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            logger.info("Redis disconnected")

    @property
    def client(self) -> redis.Redis:
        """Get Redis client (raises if not connected)."""
        if not self._client:
            raise RuntimeError("Redis client not initialized. Call connect() first.")
        return self._client

    # ========================================================================
    # Rate Limiting (Sliding Window Algorithm)
    # ========================================================================

    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60
    ) -> tuple[bool, int, int]:
        """
        Check if request is within rate limit using sliding window algorithm.

        Args:
            key: Redis key (e.g., "rate_limit:tenant_id:user_id:endpoint")
            limit: Maximum requests allowed in window
            window_seconds: Time window in seconds (default: 60)

        Returns:
            Tuple of (allowed, current_count, remaining)
            - allowed: True if request is within limit
            - current_count: Current number of requests in window
            - remaining: Requests remaining in current window

        Algorithm:
            Uses sorted set with timestamps as scores.
            1. Remove old entries outside the window
            2. Count entries in current window
            3. Add new entry if within limit
            4. Set expiration on key
        """
        import time

        now = time.time()
        window_start = now - window_seconds

        try:
            # Remove entries older than window
            await self.client.zremrangebyscore(key, 0, window_start)

            # Count current entries in window
            current_count = await self.client.zcard(key)

            if current_count < limit:
                # Within limit - add new entry
                await self.client.zadd(key, {str(now): now})
                await self.client.expire(key, window_seconds)
                remaining = limit - (current_count + 1)
                return True, current_count + 1, remaining
            else:
                # Exceeded limit
                return False, current_count, 0

        except Exception as e:
            logger.error(f"Rate limit check failed for {key}: {e}")
            # Fail open: allow request if Redis is down
            return True, 0, limit

    async def get_rate_limit_ttl(self, key: str) -> int:
        """
        Get TTL (time to live) for rate limit key.

        Returns:
            Seconds until rate limit window resets
        """
        try:
            ttl = await self.client.ttl(key)
            return max(0, ttl)
        except Exception:
            return 0

    # ========================================================================
    # Caching
    # ========================================================================

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        try:
            return await self.client.get(key)
        except Exception as e:
            logger.error(f"Redis GET failed for {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: str,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (optional)

        Returns:
            True if successful
        """
        try:
            if ttl:
                await self.client.setex(key, ttl, value)
            else:
                await self.client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Redis SET failed for {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE failed for {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            return await self.client.exists(key) > 0
        except Exception:
            return False

    # ========================================================================
    # JSON Caching (convenience methods)
    # ========================================================================

    async def get_json(self, key: str) -> Optional[Any]:
        """Get JSON value from cache."""
        try:
            value = await self.get(key)
            return json.loads(value) if value else None
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in cache for key: {key}")
            return None

    async def set_json(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set JSON value in cache."""
        try:
            json_str = json.dumps(value)
            return await self.set(key, json_str, ttl)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize JSON for {key}: {e}")
            return False

    # ========================================================================
    # Tenant-scoped caching
    # ========================================================================

    def tenant_key(self, tenant_id: str, key: str) -> str:
        """
        Generate tenant-scoped cache key.

        Args:
            tenant_id: Tenant UUID
            key: Base key

        Returns:
            Namespaced key (e.g., "tenant:abc123:properties:list")
        """
        return f"tenant:{tenant_id}:{key}"

    async def get_tenant_cache(
        self,
        tenant_id: str,
        key: str
    ) -> Optional[Any]:
        """Get tenant-scoped cached value (JSON)."""
        full_key = self.tenant_key(tenant_id, key)
        return await self.get_json(full_key)

    async def set_tenant_cache(
        self,
        tenant_id: str,
        key: str,
        value: Any,
        ttl: int = 300  # 5 minutes default
    ) -> bool:
        """Set tenant-scoped cached value (JSON)."""
        full_key = self.tenant_key(tenant_id, key)
        return await self.set_json(full_key, value, ttl)

    async def delete_tenant_cache(
        self,
        tenant_id: str,
        key: str
    ) -> bool:
        """Delete tenant-scoped cached value."""
        full_key = self.tenant_key(tenant_id, key)
        return await self.delete(full_key)

    async def clear_tenant_cache(self, tenant_id: str) -> int:
        """
        Clear all cache entries for a tenant.

        Returns:
            Number of keys deleted
        """
        try:
            pattern = f"tenant:{tenant_id}:*"
            cursor = 0
            deleted = 0

            while True:
                cursor, keys = await self.client.scan(
                    cursor,
                    match=pattern,
                    count=100
                )
                if keys:
                    deleted += await self.client.delete(*keys)

                if cursor == 0:
                    break

            logger.info(f"Cleared {deleted} cache keys for tenant {tenant_id}")
            return deleted

        except Exception as e:
            logger.error(f"Failed to clear tenant cache: {e}")
            return 0

    # ========================================================================
    # Session Management
    # ========================================================================

    async def set_session(
        self,
        session_id: str,
        data: dict,
        ttl: int = 3600  # 1 hour
    ) -> bool:
        """Store session data."""
        key = f"session:{session_id}"
        return await self.set_json(key, data, ttl)

    async def get_session(self, session_id: str) -> Optional[dict]:
        """Retrieve session data."""
        key = f"session:{session_id}"
        return await self.get_json(key)

    async def delete_session(self, session_id: str) -> bool:
        """Delete session."""
        key = f"session:{session_id}"
        return await self.delete(key)

    # ========================================================================
    # Health Check
    # ========================================================================

    async def health_check(self) -> dict[str, Any]:
        """
        Check Redis health.

        Returns:
            Dict with status and metrics
        """
        try:
            # Ping
            latency_start = await self.client.time()
            await self.client.ping()
            latency_end = await self.client.time()

            # Get info
            info = await self.client.info()

            return {
                "status": "healthy",
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "uptime_in_seconds": info.get("uptime_in_seconds", 0),
            }
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Global Redis client instance
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """
    Dependency for getting Redis client in FastAPI endpoints.

    Usage:
        @app.get("/properties")
        async def list_properties(redis: RedisClient = Depends(get_redis)):
            ...
    """
    return redis_client
