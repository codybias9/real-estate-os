"""Rate limiting middleware."""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from datetime import datetime, timedelta
import redis
from typing import Optional

from ..config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting API requests.

    Uses Redis to track request counts per user/IP address.
    Implements sliding window rate limiting.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        requests_per_day: int = 10000,
    ):
        """
        Initialize rate limit middleware.

        Args:
            app: FastAPI application
            requests_per_minute: Max requests per minute
            requests_per_hour: Max requests per hour
            requests_per_day: Max requests per day
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests_per_day = requests_per_day

        # Initialize Redis connection
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            self.redis_client.ping()
            self.enabled = True
        except Exception as e:
            print(f"Rate limiting disabled - Redis connection failed: {e}")
            self.enabled = False

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        if not self.enabled:
            return await call_next(request)

        # Get identifier (user ID or IP address)
        identifier = self._get_identifier(request)

        # Check rate limits
        is_allowed, retry_after = self._check_rate_limit(identifier)

        if not is_allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too many requests",
                    "message": "Rate limit exceeded. Please try again later.",
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                },
            )

        # Increment counters
        self._increment_counters(identifier)

        # Get remaining requests
        remaining = self._get_remaining_requests(identifier)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(datetime.utcnow().timestamp()) + 60)

        return response

    def _get_identifier(self, request: Request) -> str:
        """
        Get unique identifier for the request.

        Args:
            request: FastAPI request

        Returns:
            Identifier (user ID or IP address)
        """
        # Try to get user ID from request state
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        # Fall back to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ip = forwarded_for.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        return f"ip:{ip}"

    def _check_rate_limit(self, identifier: str) -> tuple[bool, Optional[int]]:
        """
        Check if request is within rate limits.

        Args:
            identifier: Request identifier

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        try:
            # Check per-minute limit
            minute_key = f"ratelimit:{identifier}:minute"
            minute_count = self.redis_client.get(minute_key)

            if minute_count and int(minute_count) >= self.requests_per_minute:
                ttl = self.redis_client.ttl(minute_key)
                return False, ttl if ttl > 0 else 60

            # Check per-hour limit
            hour_key = f"ratelimit:{identifier}:hour"
            hour_count = self.redis_client.get(hour_key)

            if hour_count and int(hour_count) >= self.requests_per_hour:
                ttl = self.redis_client.ttl(hour_key)
                return False, ttl if ttl > 0 else 3600

            # Check per-day limit
            day_key = f"ratelimit:{identifier}:day"
            day_count = self.redis_client.get(day_key)

            if day_count and int(day_count) >= self.requests_per_day:
                ttl = self.redis_client.ttl(day_key)
                return False, ttl if ttl > 0 else 86400

            return True, None

        except Exception as e:
            print(f"Rate limit check error: {e}")
            # Allow request on error
            return True, None

    def _increment_counters(self, identifier: str):
        """
        Increment rate limit counters.

        Args:
            identifier: Request identifier
        """
        try:
            # Increment per-minute counter
            minute_key = f"ratelimit:{identifier}:minute"
            pipe = self.redis_client.pipeline()
            pipe.incr(minute_key)
            pipe.expire(minute_key, 60)

            # Increment per-hour counter
            hour_key = f"ratelimit:{identifier}:hour"
            pipe.incr(hour_key)
            pipe.expire(hour_key, 3600)

            # Increment per-day counter
            day_key = f"ratelimit:{identifier}:day"
            pipe.incr(day_key)
            pipe.expire(day_key, 86400)

            pipe.execute()

        except Exception as e:
            print(f"Rate limit increment error: {e}")

    def _get_remaining_requests(self, identifier: str) -> int:
        """
        Get remaining requests for the current minute.

        Args:
            identifier: Request identifier

        Returns:
            Number of remaining requests
        """
        try:
            minute_key = f"ratelimit:{identifier}:minute"
            count = self.redis_client.get(minute_key)
            used = int(count) if count else 0
            return max(0, self.requests_per_minute - used)

        except Exception as e:
            print(f"Get remaining requests error: {e}")
            return self.requests_per_minute


def get_rate_limit_info(identifier: str, redis_client: redis.Redis) -> dict:
    """
    Get current rate limit information for an identifier.

    Args:
        identifier: Request identifier
        redis_client: Redis client

    Returns:
        Dictionary with rate limit information
    """
    try:
        minute_key = f"ratelimit:{identifier}:minute"
        hour_key = f"ratelimit:{identifier}:hour"
        day_key = f"ratelimit:{identifier}:day"

        minute_count = redis_client.get(minute_key) or 0
        hour_count = redis_client.get(hour_key) or 0
        day_count = redis_client.get(day_key) or 0

        return {
            "minute": {
                "used": int(minute_count),
                "limit": 60,
                "remaining": max(0, 60 - int(minute_count)),
            },
            "hour": {
                "used": int(hour_count),
                "limit": 1000,
                "remaining": max(0, 1000 - int(hour_count)),
            },
            "day": {
                "used": int(day_count),
                "limit": 10000,
                "remaining": max(0, 10000 - int(day_count)),
            },
        }

    except Exception as e:
        print(f"Get rate limit info error: {e}")
        return {}
