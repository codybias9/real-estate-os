"""
Rate limiting middleware using slowapi and Redis
"""

import os
from typing import Optional, Callable
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from redis import Redis


class RateLimiter:
    """
    Rate limiter using slowapi and Redis backend.

    Provides per-route and global rate limiting to prevent abuse.
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        key_func: Optional[Callable] = None,
        default_limits: Optional[list[str]] = None,
    ):
        """
        Initialize rate limiter.

        Args:
            redis_url: Redis URL (from env if not provided)
            key_func: Function to extract key from request (default: IP address)
            default_limits: Default rate limits for all endpoints
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.key_func = key_func or get_remote_address
        self.default_limits = default_limits or ["1000/hour", "100/minute"]

        # Initialize Redis connection (if available)
        try:
            self.redis = Redis.from_url(self.redis_url, decode_responses=True)
            self.redis.ping()  # Test connection
            self.storage_uri = self.redis_url
        except Exception:
            # Fallback to in-memory storage if Redis not available
            self.redis = None
            self.storage_uri = "memory://"

        # Create limiter instance
        self.limiter = Limiter(
            key_func=self.key_func,
            storage_uri=self.storage_uri,
            default_limits=self.default_limits,
        )

    def get_limiter(self):
        """Get slowapi Limiter instance for FastAPI app"""
        return self.limiter

    def add_exception_handler(self, app):
        """Add rate limit exceeded exception handler to FastAPI app"""
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Global rate limiter instance
_rate_limiter = RateLimiter()


def rate_limit(limit: str):
    """
    Decorator for rate limiting specific endpoints.

    Usage:
        @app.get("/api/properties")
        @rate_limit("50/minute")
        def get_properties():
            return {"properties": []}

    Args:
        limit: Rate limit string (e.g., "10/minute", "100/hour")

    Returns:
        Decorator function
    """
    return _rate_limiter.limiter.limit(limit)


def get_rate_limiter():
    """Get global rate limiter instance"""
    return _rate_limiter
