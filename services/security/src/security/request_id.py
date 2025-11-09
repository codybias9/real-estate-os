"""
Request ID middleware for request tracking and correlation
"""

import uuid
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable for request ID (thread-safe)
_request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to generate and track request IDs.

    Adds a unique request ID to each request for tracking and debugging.
    If client provides X-Request-ID header, it is preserved.
    """

    def __init__(self, app, header_name: str = "X-Request-ID"):
        """
        Initialize request ID middleware.

        Args:
            app: ASGI application
            header_name: Header name for request ID (default: X-Request-ID)
        """
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next):
        """Generate or extract request ID and add to response"""
        # Get request ID from header or generate new one
        request_id = request.headers.get(self.header_name) or str(uuid.uuid4())

        # Set in context variable
        _request_id_ctx_var.set(request_id)

        # Store in request state for access in endpoints
        request.state.request_id = request_id

        # Call next middleware/endpoint
        response: Response = await call_next(request)

        # Add request ID to response headers
        response.headers[self.header_name] = request_id

        return response


def get_request_id() -> str:
    """
    Get current request ID from context.

    Returns:
        Request ID string (UUID)

    Example:
        @app.get("/properties")
        def get_properties():
            request_id = get_request_id()
            logger.info(f"Request {request_id}: Fetching properties")
            return {"properties": []}
    """
    return _request_id_ctx_var.get()


def get_correlation_id(request: Request) -> str:
    """
    Get correlation ID from request headers or generate new one.

    Correlation IDs are used to track a request across multiple services.

    Args:
        request: FastAPI/Starlette request object

    Returns:
        Correlation ID string
    """
    return request.headers.get("X-Correlation-ID") or get_request_id()
