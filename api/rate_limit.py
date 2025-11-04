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


# ============================================================================
# LOGIN LOCKOUT & AUTHENTICATION SECURITY
# ============================================================================

# Lockout configuration
MAX_LOGIN_ATTEMPTS = 5  # Lock after 5 failed attempts
LOCKOUT_DURATION_MINUTES = 15  # Lock for 15 minutes
PROGRESSIVE_BACKOFF = True  # Increase lockout duration with repeated failures


def get_login_attempts_key(identifier: str) -> str:
    """Get Redis key for login attempts counter"""
    return f"auth:login_attempts:{identifier}"


def get_lockout_key(identifier: str) -> str:
    """Get Redis key for lockout status"""
    return f"auth:lockout:{identifier}"


def get_lockout_count_key(identifier: str) -> str:
    """Get Redis key for total lockout count (for progressive backoff)"""
    return f"auth:lockout_count:{identifier}"


def is_locked_out(identifier: str) -> tuple[bool, Optional[int]]:
    """
    Check if identifier is currently locked out

    Args:
        identifier: Email or IP address

    Returns:
        Tuple of (is_locked, seconds_until_unlock)
    """
    if not redis_client:
        return False, None

    lockout_key = get_lockout_key(identifier)
    ttl = redis_client.ttl(lockout_key)

    if ttl > 0:
        return True, ttl

    return False, None


def record_failed_login(identifier: str):
    """
    Record a failed login attempt

    Implements progressive backoff:
    - First lockout: 15 minutes
    - Second lockout: 30 minutes
    - Third lockout: 1 hour
    - Fourth+ lockout: 4 hours

    Args:
        identifier: Email or IP address
    """
    if not redis_client:
        return

    attempts_key = get_login_attempts_key(identifier)
    lockout_key = get_lockout_key(identifier)
    lockout_count_key = get_lockout_count_key(identifier)

    # Increment failed attempts counter
    attempts = redis_client.incr(attempts_key)

    # Set expiry on attempts counter (reset after 15 minutes)
    if attempts == 1:
        redis_client.expire(attempts_key, 15 * 60)

    # Check if we should lock out
    if attempts >= MAX_LOGIN_ATTEMPTS:
        # Get total lockout count for progressive backoff
        lockout_count = int(redis_client.get(lockout_count_key) or 0)

        # Calculate lockout duration
        if PROGRESSIVE_BACKOFF:
            # Progressive backoff: 15min, 30min, 1hr, 4hr
            durations = [15, 30, 60, 240]  # minutes
            duration_minutes = durations[min(lockout_count, len(durations) - 1)]
        else:
            duration_minutes = LOCKOUT_DURATION_MINUTES

        # Set lockout
        redis_client.setex(lockout_key, duration_minutes * 60, "locked")

        # Increment lockout count (expires after 24 hours)
        redis_client.incr(lockout_count_key)
        redis_client.expire(lockout_count_key, 24 * 60 * 60)

        # Clear attempts counter (will start fresh after lockout)
        redis_client.delete(attempts_key)

        logger.warning(
            f"Account locked out: {identifier}",
            extra={
                "identifier": identifier,
                "attempts": attempts,
                "lockout_duration_minutes": duration_minutes,
                "lockout_number": lockout_count + 1
            }
        )


def record_successful_login(identifier: str):
    """
    Record a successful login

    Clears failed attempts counter but preserves lockout history
    (for progressive backoff)

    Args:
        identifier: Email or IP address
    """
    if not redis_client:
        return

    attempts_key = get_login_attempts_key(identifier)

    # Clear failed attempts
    redis_client.delete(attempts_key)

    logger.info(f"Successful login: {identifier}")


def get_remaining_attempts(identifier: str) -> int:
    """
    Get remaining login attempts before lockout

    Args:
        identifier: Email or IP address

    Returns:
        Number of remaining attempts (0 if locked out)
    """
    if not redis_client:
        return MAX_LOGIN_ATTEMPTS

    # Check if locked out
    locked, _ = is_locked_out(identifier)
    if locked:
        return 0

    # Get current attempts
    attempts_key = get_login_attempts_key(identifier)
    attempts = int(redis_client.get(attempts_key) or 0)

    return max(0, MAX_LOGIN_ATTEMPTS - attempts)


def reset_lockout(identifier: str):
    """
    Reset lockout for an identifier (admin action)

    Args:
        identifier: Email or IP address
    """
    if not redis_client:
        return

    attempts_key = get_login_attempts_key(identifier)
    lockout_key = get_lockout_key(identifier)
    lockout_count_key = get_lockout_count_key(identifier)

    redis_client.delete(attempts_key)
    redis_client.delete(lockout_key)
    redis_client.delete(lockout_count_key)

    logger.info(f"Lockout reset for {identifier}")


def get_lockout_status(identifier: str) -> dict:
    """
    Get detailed lockout status

    Args:
        identifier: Email or IP address

    Returns:
        Dict with lockout status details
    """
    if not redis_client:
        return {"enabled": False}

    locked, ttl = is_locked_out(identifier)
    attempts = int(redis_client.get(get_login_attempts_key(identifier)) or 0)
    lockout_count = int(redis_client.get(get_lockout_count_key(identifier)) or 0)

    return {
        "enabled": True,
        "locked_out": locked,
        "unlock_in_seconds": ttl if locked else 0,
        "failed_attempts": attempts,
        "remaining_attempts": get_remaining_attempts(identifier),
        "total_lockouts_today": lockout_count,
        "max_attempts": MAX_LOGIN_ATTEMPTS
    }
