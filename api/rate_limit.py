"""
Rate Limiting Middleware

Implements per-tenant and per-token rate limiting with sliding window algorithm.
Uses Redis for distributed rate limiting in production.
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta
import time
import os
from collections import defaultdict, deque


class RateLimitExceeded(HTTPException):
    """Custom exception for rate limit exceeded"""

    def __init__(self, retry_after: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)}
        )
        self.retry_after = retry_after


class InMemoryRateLimiter:
    """
    In-memory rate limiter using sliding window algorithm
    For production, use RedisRateLimiter
    """

    def __init__(self):
        # Store for each key: deque of timestamps
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.cleanup_interval = 60  # Clean up old entries every 60 seconds
        self.last_cleanup = time.time()

    def is_allowed(self, key: str, limit: int, window_seconds: int) -> Tuple[bool, int]:
        """
        Check if request is allowed under rate limit

        Returns: (is_allowed, retry_after_seconds)
        """
        now = time.time()

        # Periodic cleanup
        if now - self.last_cleanup > self.cleanup_interval:
            self._cleanup()

        # Remove old timestamps outside the window
        window_start = now - window_seconds
        request_times = self.requests[key]

        while request_times and request_times[0] < window_start:
            request_times.popleft()

        # Check if under limit
        if len(request_times) < limit:
            request_times.append(now)
            return True, 0
        else:
            # Calculate when the oldest request will expire
            oldest_request = request_times[0]
            retry_after = int(oldest_request + window_seconds - now) + 1
            return False, retry_after

    def _cleanup(self):
        """Remove entries that are completely outside any reasonable window"""
        now = time.time()
        max_window = 3600  # 1 hour

        for key in list(self.requests.keys()):
            request_times = self.requests[key]
            # Remove timestamps older than max window
            while request_times and request_times[0] < now - max_window:
                request_times.popleft()

            # If empty, remove key
            if not request_times:
                del self.requests[key]

        self.last_cleanup = now


class RedisRateLimiter:
    """
    Redis-backed rate limiter for distributed systems
    Uses sorted sets with timestamp scores
    """

    def __init__(self, redis_url: str = None):
        try:
            import redis
            self.redis = redis.from_url(redis_url or os.getenv("REDIS_URL", "redis://localhost:6379"))
        except ImportError:
            raise ImportError("redis package required for RedisRateLimiter. Install with: pip install redis")

    def is_allowed(self, key: str, limit: int, window_seconds: int) -> Tuple[bool, int]:
        """
        Check if request is allowed using Redis sorted set
        """
        now = time.time()
        window_start = now - window_seconds

        pipe = self.redis.pipeline()

        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)

        # Count remaining entries
        pipe.zcard(key)

        # Add current request
        pipe.zadd(key, {str(now): now})

        # Set expiry on key
        pipe.expire(key, window_seconds + 10)

        results = pipe.execute()
        count = results[1]  # Result of zcard

        if count < limit:
            return True, 0
        else:
            # Get oldest timestamp in window
            oldest = self.redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                oldest_time = oldest[0][1]
                retry_after = int(oldest_time + window_seconds - now) + 1
                # Remove the request we just added since it's over limit
                self.redis.zrem(key, str(now))
                return False, retry_after
            else:
                return False, 1


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI

    Configuration via environment variables:
    - RATE_LIMIT_ENABLED: true/false (default: true)
    - RATE_LIMIT_BACKEND: memory/redis (default: memory)
    - RATE_LIMIT_DEFAULT: requests per minute (default: 60)
    """

    # Route-specific rate limits (requests per minute)
    ROUTE_LIMITS = {
        "/auth": (10, 60),  # 10 requests per minute for auth endpoints
        "/api/v1/properties": (30, 60),  # 30 req/min
        "/api/v1/search": (20, 60),  # 20 req/min (more expensive)
        "/api/v1/negotiation": (10, 60),  # 10 req/min (compliance)
        "/api/v1/admin": (100, 60),  # 100 req/min for admin
    }

    # Exempt routes (no rate limiting)
    EXEMPT_ROUTES = ["/healthz", "/version", "/docs", "/openapi.json", "/redoc"]

    def __init__(self, app):
        super().__init__(app)

        # Initialize rate limiter backend
        backend = os.getenv("RATE_LIMIT_BACKEND", "memory")
        if backend == "redis":
            try:
                self.limiter = RedisRateLimiter()
            except Exception as e:
                print(f"Failed to initialize Redis rate limiter: {e}")
                print("Falling back to in-memory rate limiter")
                self.limiter = InMemoryRateLimiter()
        else:
            self.limiter = InMemoryRateLimiter()

        self.enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
        self.default_limit = int(os.getenv("RATE_LIMIT_DEFAULT", "60"))

    def _get_rate_limit_for_path(self, path: str) -> Tuple[int, int]:
        """
        Get rate limit configuration for a path
        Returns: (limit, window_seconds)
        """
        # Check for exact match
        for route_prefix, (limit, window) in self.ROUTE_LIMITS.items():
            if path.startswith(route_prefix):
                return limit, window

        # Default limit
        return self.default_limit, 60

    def _get_rate_limit_key(self, request: Request) -> str:
        """
        Generate rate limit key from request
        Uses tenant_id and user_id if available, otherwise IP address
        """
        # Try to extract tenant and user from auth (if available)
        tenant_id = request.state.__dict__.get("tenant_id")
        user_id = request.state.__dict__.get("user_id")

        if tenant_id and user_id:
            return f"rl:tenant:{tenant_id}:user:{user_id}:{request.url.path}"
        elif user_id:
            return f"rl:user:{user_id}:{request.url.path}"
        else:
            # Fallback to IP-based rate limiting
            client_ip = request.client.host if request.client else "unknown"
            return f"rl:ip:{client_ip}:{request.url.path}"

    async def dispatch(self, request: Request, call_next):
        """
        Check rate limit before processing request
        """
        # Skip if rate limiting disabled
        if not self.enabled:
            return await call_next(request)

        # Check if route is exempt
        path = request.url.path
        if any(path.startswith(exempt) for exempt in self.EXEMPT_ROUTES):
            return await call_next(request)

        # Get rate limit for this path
        limit, window = self._get_rate_limit_for_path(path)

        # Generate rate limit key
        key = self._get_rate_limit_key(request)

        # Check rate limit
        allowed, retry_after = self.limiter.is_allowed(key, limit, window)

        if not allowed:
            # Rate limit exceeded
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded", "retry_after": retry_after},
                headers={"Retry-After": str(retry_after)}
            )

        # Add rate limit headers to response
        response = await call_next(request)

        # Get current usage
        current_count = len(self.limiter.requests.get(key, [])) if isinstance(self.limiter, InMemoryRateLimiter) else 0

        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - current_count))
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + window)

        return response
