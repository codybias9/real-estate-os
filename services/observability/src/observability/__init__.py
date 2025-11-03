"""
Observability Service

Provides structured logging, metrics collection, and monitoring.
"""

from .logging import configure_logging, get_logger, LoggingMiddleware
from .metrics import (
    metrics_registry,
    request_duration,
    request_count,
    error_count,
    record_request,
    record_error,
    MetricsMiddleware,
)
from .errors import ErrorTracker, error_handler

__all__ = [
    "configure_logging",
    "get_logger",
    "LoggingMiddleware",
    "metrics_registry",
    "request_duration",
    "request_count",
    "error_count",
    "record_request",
    "record_error",
    "MetricsMiddleware",
    "ErrorTracker",
    "error_handler",
]
