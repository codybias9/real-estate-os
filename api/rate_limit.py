"""
Rate limiting middleware using Redis sliding window algorithm.
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional, Callable
import logging
from functools import wraps

from api.config import settings
from api.redis_client import redis_client
from api.auth import TokenData, verify_token

logger = logging.getLogger(__name__)


# ========================================================================
# Exceptions
# ========================================================================

class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int = 60,
        limit: Optional[int] = None,
        window_seconds: Optional[int] = None,
        current_count: Optional[int] = None
    ):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=message
        )
        self.message = message
        self.retry_after = retry_after
        self.limit = limit
        self.window_seconds = window_seconds
        self.current_count = current_count

    def __str__(self):
        """Return just the message, not the status code."""
        return self.message


# ========================================================================
# Helper Functions
# ========================================================================

def generate_rate_limit_key(
    endpoint: str,
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None
) -> str:
    """
    Generate a unique rate limit key.

    Args:
        endpoint: API endpoint path
        tenant_id: Tenant ID (for authenticated users)
        user_id: User ID (for authenticated users)
        ip_address: IP address (for unauthenticated users)

    Returns:
        Rate limit key string
    """
    parts = []

    if tenant_id:
        parts.append(f"tenant:{tenant_id}")
    if user_id:
        parts.append(f"user:{user_id}")
    if ip_address:
        parts.append(f"ip:{ip_address}")

    parts.append(f"path:{endpoint}")

    return ":".join(parts)


# ========================================================================
# RateLimiter Class
# ========================================================================

class RateLimiter:
    """
    Rate limiter using Redis sliding window algorithm.

    Thin wrapper around redis_client.check_rate_limit for testing.
    """

    def __init__(self, redis_client=None):
        """
        Initialize rate limiter.

        Args:
            redis_client: Redis client instance (defaults to global instance)
        """
        from api.redis_client import redis_client as default_client
        self.redis_client = redis_client or default_client

    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int
    ) -> tuple[bool, int, int]:
        """
        Check if request is within rate limit.

        Args:
            key: Rate limit key
            limit: Maximum requests allowed
            window_seconds: Time window in seconds

        Returns:
            Tuple of (allowed, current_count, remaining)
        """
        return await self.redis_client.check_rate_limit(
            key=key,
            limit=limit,
            window_seconds=window_seconds
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce rate limits on API endpoints.

    Rate limits are applied per-tenant, per-user, per-endpoint using Redis.
    Uses sliding window algorithm for accurate rate limiting.
    """

    def __init__(self, app):
        super().__init__(app)
        self.enabled = settings.rate_limit_enabled

    async def dispatch(self, request: Request, call_next):
        """Process request and enforce rate limits."""

        if not self.enabled:
            return await call_next(request)

        # Skip rate limiting for health check and docs
        if request.url.path in ["/health", "/healthz", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Extract token and user info
        user_info = await self._extract_user_info(request)

        if not user_info:
            # No authentication - apply global rate limit
            client_host = request.client.host if request.client else "unknown"
            rate_limit_key = f"rate_limit:anonymous:{client_host}:{request.url.path}"
            limit = settings.rate_limit_default_per_minute
        else:
            # Authenticated - apply tenant+user rate limit
            tenant_id, user_id = user_info
            rate_limit_key = f"rate_limit:{tenant_id}:{user_id}:{request.url.path}"
            limit = self._get_endpoint_limit(request.url.path, request.method)

        # Check rate limit
        allowed, current_count, remaining = await redis_client.check_rate_limit(
            key=rate_limit_key,
            limit=limit,
            window_seconds=60  # 1 minute window
        )

        # Add rate limit headers
        ttl = await redis_client.get_rate_limit_ttl(rate_limit_key)

        headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(ttl),
        }

        if not allowed:
            # Rate limit exceeded
            logger.warning(
                f"Rate limit exceeded: {rate_limit_key} "
                f"(current: {current_count}, limit: {limit})"
            )

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "limit": limit,
                    "window": "60 seconds",
                    "retry_after": ttl
                },
                headers={
                    **headers,
                    "Retry-After": str(ttl)
                }
            )

        # Request allowed - proceed
        response = await call_next(request)

        # Add rate limit headers to response
        for key, value in headers.items():
            response.headers[key] = value

        return response

    async def _extract_user_info(self, request: Request) -> Optional[tuple[str, str]]:
        """
        Extract tenant_id and user_id from JWT token.

        Returns:
            Tuple of (tenant_id, user_id) or None if not authenticated
        """
        try:
            # Extract Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None

            # Extract and verify token
            token = auth_header.replace("Bearer ", "")
            token_data = await verify_token(token)

            return (token_data.tenant_id, token_data.sub)

        except Exception:
            # Token invalid or missing - not authenticated
            return None

    def _get_endpoint_limit(self, path: str, method: str) -> int:
        """
        Get rate limit for specific endpoint.

        Returns configured limit or default if not specified.
        """
        # Auth endpoints
        if "/auth/login" in path:
            return settings.rate_limit_auth_login
        if "/auth/register" in path:
            return settings.rate_limit_auth_register

        # Properties endpoints
        if "/properties" in path:
            if method == "GET":
                return settings.rate_limit_properties_list
            elif method in ["POST", "PUT", "PATCH"]:
                return settings.rate_limit_properties_create

        # ML endpoints
        if "/ml/" in path or "/valuation" in path:
            return settings.rate_limit_ml_valuation

        # Analytics endpoints
        if "/analytics" in path:
            return settings.rate_limit_analytics

        # Default
        return settings.rate_limit_default_per_minute


def rate_limit(
    requests_per_minute: int,
    scope: str = "endpoint"
):
    """
    Decorator to apply custom rate limit to specific endpoint.

    Usage:
        @app.get("/expensive-operation")
        @rate_limit(requests_per_minute=10, scope="endpoint")
        async def expensive_op(user: TokenData = Depends(get_current_user)):
            ...

    Args:
        requests_per_minute: Maximum requests per minute
        scope: Scope of rate limit ("endpoint", "tenant", "user")

    Returns:
        Decorator function
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request and user from kwargs
            request: Optional[Request] = kwargs.get('request')
            user: Optional[TokenData] = kwargs.get('user')

            if not request:
                # No request object - skip rate limiting
                logger.warning(f"Rate limit decorator on {func.__name__} but no request object")
                return await func(*args, **kwargs)

            # Build rate limit key based on scope
            if scope == "tenant" and user:
                key = f"rate_limit:{user.tenant_id}:{func.__name__}"
            elif scope == "user" and user:
                key = f"rate_limit:{user.tenant_id}:{user.sub}:{func.__name__}"
            else:
                # Endpoint scope
                key = f"rate_limit:endpoint:{func.__name__}"

            # Check rate limit
            allowed, current_count, remaining = await redis_client.check_rate_limit(
                key=key,
                limit=requests_per_minute,
                window_seconds=60
            )

            if not allowed:
                ttl = await redis_client.get_rate_limit_ttl(key)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "message": "Rate limit exceeded",
                        "limit": requests_per_minute,
                        "window": "60 seconds",
                        "retry_after": ttl
                    },
                    headers={"Retry-After": str(ttl)}
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# ============================================================================
# IP-based Rate Limiting (for unauthenticated endpoints)
# ============================================================================

async def check_ip_rate_limit(
    request: Request,
    limit: int = 20,
    window_seconds: int = 60
) -> None:
    """
    Check IP-based rate limit (for unauthenticated requests).

    Usage:
        @app.post("/public/contact")
        async def contact_form(request: Request):
            await check_ip_rate_limit(request, limit=5, window_seconds=60)
            ...

    Args:
        request: FastAPI request object
        limit: Maximum requests per window
        window_seconds: Time window in seconds

    Raises:
        HTTPException: If rate limit exceeded
    """
    if not settings.rate_limit_enabled:
        return

    ip = request.client.host
    key = f"rate_limit:ip:{ip}:{request.url.path}"

    allowed, current_count, remaining = await redis_client.check_rate_limit(
        key=key,
        limit=limit,
        window_seconds=window_seconds
    )

    if not allowed:
        ttl = await redis_client.get_rate_limit_ttl(key)
        logger.warning(f"IP rate limit exceeded: {ip} on {request.url.path}")

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": "Too many requests from your IP address",
                "limit": limit,
                "window": f"{window_seconds} seconds",
                "retry_after": ttl
            },
            headers={"Retry-After": str(ttl)}
        )


# ============================================================================
# Burst Protection
# ============================================================================

async def check_burst_limit(
    tenant_id: str,
    user_id: str,
    limit: int = 20,
    window_seconds: int = 10
) -> None:
    """
    Check burst rate limit (short time window).

    Prevents rapid-fire requests that might indicate abuse.

    Usage:
        @app.post("/properties/batch")
        async def batch_create(user: TokenData = Depends(get_current_user)):
            await check_burst_limit(user.tenant_id, user.sub, limit=10, window_seconds=5)
            ...

    Args:
        tenant_id: Tenant UUID
        user_id: User UUID
        limit: Maximum requests in burst window
        window_seconds: Burst window duration

    Raises:
        HTTPException: If burst limit exceeded
    """
    if not settings.rate_limit_enabled:
        return

    key = f"rate_limit:burst:{tenant_id}:{user_id}"

    allowed, current_count, remaining = await redis_client.check_rate_limit(
        key=key,
        limit=limit,
        window_seconds=window_seconds
    )

    if not allowed:
        ttl = await redis_client.get_rate_limit_ttl(key)
        logger.warning(
            f"Burst limit exceeded: tenant={tenant_id}, user={user_id} "
            f"({current_count} requests in {window_seconds}s)"
        )

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": "Too many requests in short time window (burst protection)",
                "limit": limit,
                "window": f"{window_seconds} seconds",
                "retry_after": ttl
            },
            headers={"Retry-After": str(ttl)}
        )
