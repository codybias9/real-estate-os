"""
Structured logging configuration and middleware
"""

import sys
import time
import logging
from typing import Any, Dict
from contextvars import ContextVar

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variables for request-scoped logging
_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
_user_id_ctx: ContextVar[str] = ContextVar("user_id", default="")
_tenant_id_ctx: ContextVar[str] = ContextVar("tenant_id", default="")


def configure_logging(
    level: str = "INFO",
    json_logs: bool = True,
    include_timestamp: bool = True,
) -> None:
    """
    Configure structured logging with structlog.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: Output logs in JSON format
        include_timestamp: Include ISO timestamp in logs

    Example:
        configure_logging(level="INFO", json_logs=True)
    """
    # Set log level
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Configure structlog processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso") if include_timestamp else None,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Remove None processors
    processors = [p for p in processors if p is not None]

    if json_logs:
        # JSON output for production
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Console output for development
        processors.append(structlog.dev.ConsoleRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )


def get_logger(name: str = None) -> structlog.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Structured logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("processing_property", property_id="123", tenant_id="tenant-1")
    """
    logger = structlog.get_logger(name or __name__)

    # Add context variables
    request_id = _request_id_ctx.get()
    user_id = _user_id_ctx.get()
    tenant_id = _tenant_id_ctx.get()

    if request_id:
        logger = logger.bind(request_id=request_id)
    if user_id:
        logger = logger.bind(user_id=user_id)
    if tenant_id:
        logger = logger.bind(tenant_id=tenant_id)

    return logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request/response logging.

    Logs all HTTP requests with timing, status code, and request details.
    """

    def __init__(
        self,
        app,
        logger_name: str = "api",
        log_request_body: bool = False,
        log_response_body: bool = False,
    ):
        """
        Initialize logging middleware.

        Args:
            app: ASGI application
            logger_name: Logger name
            log_request_body: Log request body (be careful with sensitive data)
            log_response_body: Log response body (be careful with large responses)
        """
        super().__init__(app)
        self.logger = get_logger(logger_name)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body

    async def dispatch(self, request: Request, call_next):
        """Log request and response"""
        start_time = time.time()

        # Extract request metadata
        request_id = getattr(request.state, "request_id", "unknown")
        _request_id_ctx.set(request_id)

        # Extract user/tenant from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        tenant_id = getattr(request.state, "tenant_id", None)

        if user_id:
            _user_id_ctx.set(user_id)
        if tenant_id:
            _tenant_id_ctx.set(tenant_id)

        # Log request
        log_data = {
            "event": "http_request",
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        }

        if self.log_request_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                log_data["request_body"] = body.decode("utf-8")[:1000]  # Limit to 1KB
            except Exception:
                pass

        self.logger.info("request_received", **log_data)

        # Process request
        try:
            response: Response = await call_next(request)
            duration = time.time() - start_time

            # Log response
            self.logger.info(
                "request_completed",
                event="http_response",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
            )

            return response

        except Exception as e:
            duration = time.time() - start_time

            # Log error
            self.logger.error(
                "request_failed",
                event="http_error",
                method=request.method,
                path=request.url.path,
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=round(duration * 1000, 2),
                exc_info=True,
            )
            raise


def set_request_context(request_id: str = None, user_id: str = None, tenant_id: str = None):
    """
    Set request context for logging.

    Args:
        request_id: Request ID
        user_id: User ID
        tenant_id: Tenant ID
    """
    if request_id:
        _request_id_ctx.set(request_id)
    if user_id:
        _user_id_ctx.set(user_id)
    if tenant_id:
        _tenant_id_ctx.set(tenant_id)


def clear_request_context():
    """Clear request context"""
    _request_id_ctx.set("")
    _user_id_ctx.set("")
    _tenant_id_ctx.set("")
