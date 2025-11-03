"""
Security headers middleware

Adds security headers to all responses to protect against common attacks.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Protects against:
    - XSS attacks (X-XSS-Protection, Content-Security-Policy)
    - Clickjacking (X-Frame-Options)
    - MIME sniffing (X-Content-Type-Options)
    - Information leakage (X-Powered-By removal)
    - Downgrade attacks (Strict-Transport-Security)
    """

    def __init__(
        self,
        app,
        csp: str | None = None,
        hsts_max_age: int = 31536000,
        include_subdomains: bool = True,
    ):
        """
        Initialize security headers middleware.

        Args:
            app: ASGI application
            csp: Content-Security-Policy header value (default: restrictive)
            hsts_max_age: HSTS max-age in seconds (default: 1 year)
            include_subdomains: Include subdomains in HSTS (default: True)
        """
        super().__init__(app)
        self.csp = csp or (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        )
        self.hsts_max_age = hsts_max_age
        self.include_subdomains = include_subdomains

    async def dispatch(self, request: Request, call_next):
        """Add security headers to response"""
        response: Response = await call_next(request)

        # Content Security Policy (CSP)
        response.headers["Content-Security-Policy"] = self.csp

        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Enable XSS protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # HTTP Strict Transport Security (HTTPS only)
        # Only add HSTS if connection is HTTPS
        if request.url.scheme == "https":
            hsts_value = f"max-age={self.hsts_max_age}"
            if self.include_subdomains:
                hsts_value += "; includeSubDomains"
            response.headers["Strict-Transport-Security"] = hsts_value

        # Referrer Policy (control referer information)
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy (formerly Feature-Policy)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        # Remove X-Powered-By header if present
        if "X-Powered-By" in response.headers:
            del response.headers["X-Powered-By"]

        return response


def get_security_headers_config() -> dict:
    """
    Get current security headers configuration.

    Returns:
        Dictionary with security header settings
    """
    return {
        "Content-Security-Policy": "restrictive CSP enabled",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "enabled (HTTPS only)",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }
