"""Rate limiting middleware

Implements:
- Per-IP rate limiting (default: 60 req/min)
- Per-tenant rate limiting (default: 100 req/min)
- Returns 429 Too Many Requests when exceeded
- Uses in-memory cache (for MVP; migrate to Redis for production)
"""

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter using sliding window"""

    def __init__(self, max_requests: int, window_seconds: int = 60):
        """
        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list[datetime]] = {}

    def is_allowed(self, key: str) -> Tuple[bool, int]:
        """Check if request is allowed

        Args:
            key: Unique identifier (IP or tenant_id)

        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)

        # Initialize or clean old requests
        if key not in self.requests:
            self.requests[key] = []
        else:
            # Remove requests outside window
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if req_time > window_start
            ]

        current_count = len(self.requests[key])

        if current_count >= self.max_requests:
            return False, 0

        # Allow request and record timestamp
        self.requests[key].append(now)
        remaining = self.max_requests - (current_count + 1)
        return True, remaining


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for FastAPI"""

    def __init__(self, app, per_ip_limit: int = 60, per_tenant_limit: int = 100):
        """
        Args:
            app: FastAPI application
            per_ip_limit: Max requests per IP per minute
            per_tenant_limit: Max requests per tenant per minute
        """
        super().__init__(app)
        self.ip_limiter = RateLimiter(max_requests=per_ip_limit, window_seconds=60)
        self.tenant_limiter = RateLimiter(max_requests=per_tenant_limit, window_seconds=60)

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""

        # Skip rate limiting for health checks
        if request.url.path in ["/healthz", "/ping"]:
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Check per-IP rate limit
        ip_allowed, ip_remaining = self.ip_limiter.is_allowed(client_ip)
        if not ip_allowed:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return Response(
                content='{"detail": "Rate limit exceeded. Please try again later."}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={
                    "X-RateLimit-Limit": str(self.ip_limiter.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(self.ip_limiter.window_seconds),
                    "Retry-After": str(self.ip_limiter.window_seconds),
                    "Content-Type": "application/json"
                }
            )

        # Try to extract tenant_id from token (if authenticated)
        tenant_id = None
        try:
            from ..auth.jwt_handler import verify_token
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                token_data = verify_token(token)
                tenant_id = token_data.tenant_id
        except Exception:
            # Not authenticated or invalid token - skip tenant rate limit
            pass

        # Check per-tenant rate limit (if authenticated)
        if tenant_id:
            tenant_allowed, tenant_remaining = self.tenant_limiter.is_allowed(tenant_id)
            if not tenant_allowed:
                logger.warning(f"Rate limit exceeded for tenant: {tenant_id}")
                return Response(
                    content='{"detail": "Tenant rate limit exceeded. Please try again later."}',
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    headers={
                        "X-RateLimit-Limit": str(self.tenant_limiter.max_requests),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(self.tenant_limiter.window_seconds),
                        "Retry-After": str(self.tenant_limiter.window_seconds),
                        "Content-Type": "application/json"
                    }
                )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit-IP"] = str(self.ip_limiter.max_requests)
        response.headers["X-RateLimit-Remaining-IP"] = str(ip_remaining)

        return response
