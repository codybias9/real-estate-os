"""ETag middleware for HTTP caching."""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
import hashlib


class ETagMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add ETag headers for HTTP caching.

    ETags allow clients to make conditional requests and reduce bandwidth
    by only downloading resources when they have changed.
    """

    def __init__(self, app):
        """Initialize ETag middleware."""
        super().__init__(app)
        self.cacheable_methods = {"GET", "HEAD"}

    async def dispatch(self, request: Request, call_next):
        """Process request with ETag support."""
        # Only apply to GET and HEAD requests
        if request.method not in self.cacheable_methods:
            return await call_next(request)

        # Get If-None-Match header from request
        if_none_match = request.headers.get("If-None-Match")

        # Process request
        response = await call_next(request)

        # Only add ETags to successful responses
        if response.status_code != 200:
            return response

        # Read response body
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk

        # Generate ETag from response body
        etag = self._generate_etag(response_body)

        # Check if client's ETag matches
        if if_none_match and if_none_match == etag:
            # Return 304 Not Modified
            return StarletteResponse(
                status_code=304,
                headers={
                    "ETag": etag,
                    "Cache-Control": "private, must-revalidate",
                },
            )

        # Return response with ETag header
        return Response(
            content=response_body,
            status_code=response.status_code,
            headers={
                **dict(response.headers),
                "ETag": etag,
                "Cache-Control": "private, must-revalidate",
            },
            media_type=response.media_type,
        )

    def _generate_etag(self, content: bytes) -> str:
        """
        Generate ETag from content.

        Args:
            content: Response body bytes

        Returns:
            ETag value (quoted hash)
        """
        hash_value = hashlib.sha256(content).hexdigest()[:32]
        return f'"{hash_value}"'
