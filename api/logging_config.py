"""Logging configuration for Real Estate OS API."""

import logging
import sys
from typing import Any, Dict
import json
from datetime import datetime

from loguru import logger
from .config import settings


class InterceptHandler(logging.Handler):
    """
    Intercept standard logging messages and redirect to loguru.
    """

    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def format_record(record: Dict[str, Any]) -> str:
    """
    Custom format for loguru loggers.
    Uses pformat for log any data like request/response body during debug.
    Works with logging if loguru is not installed.
    """
    format_string = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    format_string += "<level>{level: <8}</level> | "
    format_string += "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "

    # Add extra fields if present
    if record.get("extra"):
        extra = record["extra"]
        if "request_id" in extra:
            format_string += f"<magenta>request_id={extra['request_id']}</magenta> | "
        if "user_id" in extra:
            format_string += f"<blue>user_id={extra['user_id']}</blue> | "
        if "organization_id" in extra:
            format_string += f"<yellow>org_id={extra['organization_id']}</yellow> | "

    format_string += "<level>{message}</level>\n"

    if record.get("exception"):
        format_string += "{exception}\n"

    return format_string


class JSONFormatter:
    """
    JSON formatter for structured logging.
    """

    def __call__(self, record: Dict[str, Any]) -> str:
        """Format log record as JSON."""
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record["level"].name,
            "logger": record["name"],
            "function": record["function"],
            "line": record["line"],
            "message": record["message"],
        }

        # Add extra fields
        if record.get("extra"):
            extra = record["extra"]
            for key, value in extra.items():
                log_record[key] = value

        # Add exception if present
        if record.get("exception"):
            log_record["exception"] = {
                "type": record["exception"].type.__name__,
                "value": str(record["exception"].value),
                "traceback": record["exception"].traceback.format() if record["exception"].traceback else None,
            }

        return json.dumps(log_record) + "\n"


def setup_logging():
    """
    Configure logging for the application.
    """
    # Remove default loguru handler
    logger.remove()

    # Determine log level from settings
    log_level = "DEBUG" if settings.DEBUG else "INFO"

    # Add console handler with color formatting for development
    if settings.DEBUG:
        logger.add(
            sys.stdout,
            format=format_record,
            level=log_level,
            colorize=True,
            backtrace=True,
            diagnose=True,
        )
    else:
        # JSON formatting for production
        logger.add(
            sys.stdout,
            format=JSONFormatter(),
            level=log_level,
            serialize=False,
        )

    # Add file handler for errors
    logger.add(
        "logs/error.log",
        level="ERROR",
        format=format_record,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
    )

    # Add file handler for all logs
    logger.add(
        "logs/app.log",
        level=log_level,
        format=format_record if settings.DEBUG else JSONFormatter(),
        rotation="50 MB",
        retention="14 days",
        compression="zip",
    )

    # Intercept standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Set log levels for third-party loggers
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"]:
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]

    # Suppress noisy loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.INFO)

    logger.info(f"Logging configured (level={log_level}, debug={settings.DEBUG})")

    return logger


# Request logging middleware
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
import uuid


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log HTTP requests and responses.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Log request
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_host": request.client.host if request.client else None,
            }
        )

        # Process request
        start_time = time.time()
        try:
            response = await call_next(request)
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "process_time": f"{process_time:.3f}s",
                    "error": str(e),
                }
            )
            raise

        # Log response
        process_time = time.time() - start_time
        logger.info(
            f"Request completed: {request.method} {request.url.path} - {response.status_code}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "process_time": f"{process_time:.3f}s",
            }
        )

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response


# Utility functions for contextual logging
def get_logger_with_context(**context):
    """
    Get a logger with additional context.

    Example:
        log = get_logger_with_context(user_id=123, organization_id=456)
        log.info("User action performed")
    """
    return logger.bind(**context)


# Example usage in endpoints:
"""
from logging_config import get_logger_with_context

@router.post("/properties")
async def create_property(
    property_data: PropertyCreate,
    current_user: User = Depends(get_current_user)
):
    log = get_logger_with_context(
        user_id=current_user.id,
        organization_id=current_user.organization_id
    )

    log.info("Creating property", extra={"property_type": property_data.property_type})

    # ... business logic ...

    log.info("Property created successfully", extra={"property_id": property.id})
    return property
"""
