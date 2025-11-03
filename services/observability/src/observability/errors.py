"""
Error tracking and handling
"""

import sys
import traceback
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .logging import get_logger
from .metrics import record_error

logger = get_logger(__name__)


class ErrorTracker:
    """
    Track and report errors with context.

    In production, this would integrate with services like Sentry, Rollbar, etc.
    """

    def __init__(self, service_name: str = "realestate-api"):
        """
        Initialize error tracker.

        Args:
            service_name: Name of the service for error reporting
        """
        self.service_name = service_name

    def capture_exception(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        level: str = "error",
    ):
        """
        Capture and report exception.

        Args:
            exception: Exception to capture
            context: Additional context (request_id, user_id, etc.)
            level: Error level (error, warning, critical)
        """
        error_data = {
            "event": "exception_captured",
            "error_type": type(exception).__name__,
            "error_message": str(exception),
            "service": self.service_name,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Add context
        if context:
            error_data.update(context)

        # Add traceback
        tb = traceback.format_exception(type(exception), exception, exception.__traceback__)
        error_data["traceback"] = "".join(tb)

        # Log error
        log_func = getattr(logger, level, logger.error)
        log_func("exception_occurred", **error_data)

        # In production, send to error tracking service
        # sentry_sdk.capture_exception(exception)

    def capture_message(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        level: str = "warning",
    ):
        """
        Capture custom message.

        Args:
            message: Message to capture
            context: Additional context
            level: Message level
        """
        error_data = {
            "event": "message_captured",
            "message": message,
            "service": self.service_name,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if context:
            error_data.update(context)

        log_func = getattr(logger, level, logger.warning)
        log_func("custom_message", **error_data)


# Global error tracker instance
error_tracker = ErrorTracker()


async def error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for FastAPI.

    Handles all unhandled exceptions and returns consistent error responses.

    Args:
        request: FastAPI request
        exc: Exception that occurred

    Returns:
        JSON error response
    """
    # Get request context
    request_id = getattr(request.state, "request_id", "unknown")
    context = {
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
    }

    # Handle different exception types
    if isinstance(exc, StarletteHTTPException):
        # HTTP exceptions (404, 403, etc.)
        status_code = exc.status_code
        detail = exc.detail

        logger.warning(
            "http_exception",
            status_code=status_code,
            detail=detail,
            **context,
        )

    elif isinstance(exc, RequestValidationError):
        # Validation errors
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        detail = "Validation error"

        logger.warning(
            "validation_error",
            errors=exc.errors(),
            **context,
        )

        # Record metrics
        record_error(
            method=request.method,
            endpoint=request.url.path,
            error_type="ValidationError",
        )

        return JSONResponse(
            status_code=status_code,
            content={
                "error": detail,
                "request_id": request_id,
                "errors": exc.errors(),
            },
        )

    else:
        # Unhandled exceptions
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        detail = "Internal server error"

        # Capture exception
        error_tracker.capture_exception(exc, context=context)

        # Record metrics
        record_error(
            method=request.method,
            endpoint=request.url.path,
            error_type=type(exc).__name__,
        )

    return JSONResponse(
        status_code=status_code,
        content={
            "error": detail,
            "request_id": request_id,
        },
    )


def setup_error_handlers(app):
    """
    Set up global error handlers for FastAPI app.

    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(Exception, error_handler)
    app.add_exception_handler(StarletteHTTPException, error_handler)
    app.add_exception_handler(RequestValidationError, error_handler)
