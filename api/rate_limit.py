"""
Rate Limiting Middleware
Per-user and per-IP rate limiting using Redis
"""
import os
import time
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import redis
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# REDIS CONNECTION
# ============================================================================

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    # Test connection
    redis_client.ping()
    logger.info("Rate limiting Redis connection established")
except Exception as e:
    logger.warning(f"Rate limiting disabled - Redis not available: {str(e)}")
    redis_client = None

# ============================================================================
# RATE LIMIT CONFIGURATION
# ============================================================================

# Default rate limits (can be overridden per endpoint)
DEFAULT_RATE_LIMITS = {
    "per_minute": int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
    "per_hour": int(os.getenv("RATE_LIMIT_PER_HOUR", "1000")),
    "per_day": int(os.getenv("RATE_LIMIT_PER_DAY", "10000"))
}

# Stricter limits for authentication endpoints
AUTH_RATE_LIMITS = {
    "per_minute": 5,
    "per_hour": 20,
    "per_day": 100
}

# Generous limits for authenticated API calls
API_RATE_LIMITS = {
    "per_minute": 100,
    "per_hour": 5000,
    "per_day": 50000
}

# ============================================================================
# RATE LIMITING FUNCTIONS
# ============================================================================

def get_rate_limit_key(identifier: str, window: str) -> str:
    """
    Generate Redis key for rate limiting

    Args:
        identifier: User ID, IP address, or other identifier
        window: Time window ('minute', 'hour', 'day')

    Returns:
        Redis key string
    """
    current_time = int(time.time())

    if window == "minute":
        # Bucket per minute
        bucket = current_time // 60
    elif window == "hour":
        # Bucket per hour
        bucket = current_time // 3600
    elif window == "day":
        # Bucket per day
        bucket = current_time // 86400
    else:
        bucket = current_time

    return f"rate_limit:{identifier}:{window}:{bucket}"


def check_rate_limit(
    identifier: str,
    limits: dict,
    redis_client: redis.Redis
) -> tuple[bool, Optional[dict]]:
    """
    Check if request is within rate limits

    Args:
        identifier: User ID, IP, or identifier
        limits: Dict with 'per_minute', 'per_hour', 'per_day' limits
        redis_client: Redis client

    Returns:
        Tuple of (allowed: bool, info: dict or None)
        If not allowed, info contains retry_after and limit details
    """
    if not redis_client:
        # Rate limiting disabled if Redis not available
        return True, None

    windows = {
        "minute": (60, limits.get("per_minute")),
        "hour": (3600, limits.get("per_hour")),
        "day": (86400, limits.get("per_day"))
    }

    for window_name, (ttl, limit) in windows.items():
        if limit is None:
            continue

        key = get_rate_limit_key(identifier, window_name)

        try:
            # Increment counter
            current = redis_client.incr(key)

            # Set expiry on first request
            if current == 1:
                redis_client.expire(key, ttl)

            # Check if limit exceeded
            if current > limit:
                retry_after = redis_client.ttl(key)

                return False, {
                    "retry_after": retry_after,
                    "limit": limit,
                    "window": window_name,
                    "current": current
                }

        except Exception as e:
            logger.error(f"Rate limit check failed: {str(e)}")
            # Fail open if Redis has issues
            return True, None

    return True, None


def get_identifier_from_request(request: Request, user_id: Optional[int] = None) -> str:
    """
    Get identifier for rate limiting from request

    Priority:
    1. Authenticated user ID (most accurate)
    2. IP address (fallback for unauthenticated requests)

    Args:
        request: FastAPI request
        user_id: Authenticated user ID (if available)

    Returns:
        Identifier string
    """
    if user_id:
        return f"user:{user_id}"

    # Get IP from headers (handle proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take first IP in chain
        ip = forwarded_for.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"

    return f"ip:{ip}"


# ============================================================================
# FASTAPI DEPENDENCIES
# ============================================================================

async def rate_limit_dependency(
    request: Request,
    limits: dict = DEFAULT_RATE_LIMITS,
    user_id: Optional[int] = None
):
    """
    FastAPI dependency for rate limiting

    Usage:
        @app.get("/endpoint")
        def my_endpoint(
            rate_limit: None = Depends(rate_limit_dependency)
        ):
            # Endpoint logic
            pass

    Args:
        request: FastAPI request
        limits: Rate limit configuration
        user_id: User ID (if authenticated)

    Raises:
        HTTPException: 429 Too Many Requests if rate limit exceeded
    """
    if not redis_client:
        # Rate limiting disabled
        return

    identifier = get_identifier_from_request(request, user_id)

    allowed, info = check_rate_limit(identifier, limits, redis_client)

    if not allowed:
        logger.warning(f"Rate limit exceeded for {identifier}: {info}")

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "retry_after": info["retry_after"],
                "limit": info["limit"],
                "window": info["window"]
            },
            headers={
                "Retry-After": str(info["retry_after"]),
                "X-RateLimit-Limit": str(info["limit"]),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time()) + info["retry_after"])
            }
        )


def rate_limit_auth(user_id: Optional[int] = None):
    """
    Rate limit dependency for authentication endpoints

    Stricter limits to prevent brute force attacks

    Usage:
        @app.post("/auth/login")
        def login(
            rate_limit: None = Depends(rate_limit_auth)
        ):
            pass
    """
    from functools import partial
    return partial(rate_limit_dependency, limits=AUTH_RATE_LIMITS, user_id=user_id)


def rate_limit_api(user_id: Optional[int] = None):
    """
    Rate limit dependency for authenticated API endpoints

    More generous limits for normal API usage

    Usage:
        @app.get("/properties")
        def list_properties(
            rate_limit: None = Depends(lambda: rate_limit_api(current_user.id)),
            current_user: User = Depends(get_current_user)
        ):
            pass
    """
    from functools import partial
    return partial(rate_limit_dependency, limits=API_RATE_LIMITS, user_id=user_id)


# ============================================================================
# MIDDLEWARE (Global Rate Limiting)
# ============================================================================

async def rate_limit_middleware(request: Request, call_next):
    """
    Global rate limiting middleware

    Applies default rate limits to all requests

    Add to FastAPI app:
        app.middleware("http")(rate_limit_middleware)
    """
    if not redis_client:
        # Rate limiting disabled
        return await call_next(request)

    # Skip rate limiting for health check endpoints
    if request.url.path in ["/health", "/ping", "/metrics"]:
        return await call_next(request)

    # Get identifier (IP-based for global middleware)
    identifier = get_identifier_from_request(request, user_id=None)

    # Check rate limit
    allowed, info = check_rate_limit(identifier, DEFAULT_RATE_LIMITS, redis_client)

    if not allowed:
        logger.warning(f"Rate limit exceeded (global) for {identifier}: {info}")

        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "retry_after": info["retry_after"],
                "limit": info["limit"],
                "window": info["window"]
            },
            headers={
                "Retry-After": str(info["retry_after"]),
                "X-RateLimit-Limit": str(info["limit"]),
                "X-RateLimit-Remaining": "0"
            }
        )

    # Process request
    response = await call_next(request)

    # Add rate limit headers to response
    try:
        minute_key = get_rate_limit_key(identifier, "minute")
        current = int(redis_client.get(minute_key) or 0)
        limit = DEFAULT_RATE_LIMITS["per_minute"]
        remaining = max(0, limit - current)

        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
    except Exception as e:
        logger.error(f"Failed to add rate limit headers: {str(e)}")

    return response


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def reset_rate_limit(identifier: str):
    """
    Reset rate limit for specific identifier

    Useful for testing or manual intervention

    Args:
        identifier: User ID or IP to reset
    """
    if not redis_client:
        return

    windows = ["minute", "hour", "day"]

    for window in windows:
        key = get_rate_limit_key(identifier, window)
        redis_client.delete(key)

    logger.info(f"Rate limit reset for {identifier}")


def get_current_rate_limit_status(identifier: str) -> dict:
    """
    Get current rate limit status for identifier

    Args:
        identifier: User ID or IP

    Returns:
        Dict with current counts and limits
    """
    if not redis_client:
        return {"enabled": False}

    status = {"enabled": True}

    windows = {
        "minute": DEFAULT_RATE_LIMITS["per_minute"],
        "hour": DEFAULT_RATE_LIMITS["per_hour"],
        "day": DEFAULT_RATE_LIMITS["per_day"]
    }

    for window, limit in windows.items():
        key = get_rate_limit_key(identifier, window)
        current = int(redis_client.get(key) or 0)
        ttl = redis_client.ttl(key)

        status[window] = {
            "current": current,
            "limit": limit,
            "remaining": max(0, limit - current),
            "reset_in": ttl if ttl > 0 else 0
        }

    return status
