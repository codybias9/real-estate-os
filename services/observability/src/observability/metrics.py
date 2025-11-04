"""
Prometheus metrics collection and middleware
"""

import time
from typing import Callable
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Create custom registry to avoid conflicts
metrics_registry = CollectorRegistry()

# HTTP request metrics
request_count = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
    registry=metrics_registry,
)

request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    registry=metrics_registry,
)

# Error metrics
error_count = Counter(
    "http_errors_total",
    "Total HTTP errors",
    ["method", "endpoint", "error_type"],
    registry=metrics_registry,
)

# Business metrics
property_operations = Counter(
    "property_operations_total",
    "Total property operations",
    ["operation", "status"],
    registry=metrics_registry,
)

score_operations = Counter(
    "score_operations_total",
    "Total scoring operations",
    ["status"],
    registry=metrics_registry,
)

outreach_operations = Counter(
    "outreach_operations_total",
    "Total outreach operations",
    ["operation", "status"],
    registry=metrics_registry,
)

# Database metrics
db_query_duration = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["query_type"],
    registry=metrics_registry,
)

db_connections = Gauge(
    "db_connections_active",
    "Number of active database connections",
    registry=metrics_registry,
)

# Cache metrics
cache_operations = Counter(
    "cache_operations_total",
    "Total cache operations",
    ["operation", "status"],
    registry=metrics_registry,
)

# SSE metrics
sse_connections = Gauge(
    "sse_connections_active",
    "Number of active SSE connections",
    registry=metrics_registry,
)

sse_events_sent = Counter(
    "sse_events_sent_total",
    "Total SSE events sent",
    ["event_type"],
    registry=metrics_registry,
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect HTTP metrics.

    Records request count, duration, and errors.
    """

    def __init__(self, app):
        """Initialize metrics middleware"""
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        """Record metrics for each request"""
        start_time = time.time()

        # Get endpoint path (without query params)
        endpoint = request.url.path
        method = request.method

        try:
            response: Response = await call_next(request)
            duration = time.time() - start_time

            # Record metrics
            request_count.labels(
                method=method,
                endpoint=endpoint,
                status_code=response.status_code,
            ).inc()

            request_duration.labels(
                method=method,
                endpoint=endpoint,
            ).observe(duration)

            return response

        except Exception as e:
            duration = time.time() - start_time

            # Record error metrics
            error_count.labels(
                method=method,
                endpoint=endpoint,
                error_type=type(e).__name__,
            ).inc()

            request_duration.labels(
                method=method,
                endpoint=endpoint,
            ).observe(duration)

            raise


def record_request(method: str, endpoint: str, status_code: int, duration: float):
    """
    Manually record request metrics.

    Args:
        method: HTTP method
        endpoint: Endpoint path
        status_code: HTTP status code
        duration: Request duration in seconds
    """
    request_count.labels(
        method=method,
        endpoint=endpoint,
        status_code=status_code,
    ).inc()

    request_duration.labels(
        method=method,
        endpoint=endpoint,
    ).observe(duration)


def record_error(method: str, endpoint: str, error_type: str):
    """
    Manually record error metrics.

    Args:
        method: HTTP method
        endpoint: Endpoint path
        error_type: Error type (exception name)
    """
    error_count.labels(
        method=method,
        endpoint=endpoint,
        error_type=error_type,
    ).inc()


def record_property_operation(operation: str, status: str):
    """
    Record property operation metric.

    Args:
        operation: Operation type (create, update, delete, etc.)
        status: Operation status (success, failure)
    """
    property_operations.labels(
        operation=operation,
        status=status,
    ).inc()


def record_score_operation(status: str):
    """
    Record scoring operation metric.

    Args:
        status: Operation status (success, failure)
    """
    score_operations.labels(status=status).inc()


def record_outreach_operation(operation: str, status: str):
    """
    Record outreach operation metric.

    Args:
        operation: Operation type (send, track, etc.)
        status: Operation status (success, failure)
    """
    outreach_operations.labels(
        operation=operation,
        status=status,
    ).inc()


def record_db_query(query_type: str, duration: float):
    """
    Record database query metric.

    Args:
        query_type: Query type (select, insert, update, delete)
        duration: Query duration in seconds
    """
    db_query_duration.labels(query_type=query_type).observe(duration)


def record_cache_operation(operation: str, status: str):
    """
    Record cache operation metric.

    Args:
        operation: Operation type (get, set, delete)
        status: Operation status (hit, miss, success, failure)
    """
    cache_operations.labels(
        operation=operation,
        status=status,
    ).inc()


def record_sse_event(event_type: str):
    """
    Record SSE event metric.

    Args:
        event_type: Event type (timeline-event, state-change, etc.)
    """
    sse_events_sent.labels(event_type=event_type).inc()


def get_metrics() -> bytes:
    """
    Get Prometheus metrics in exposition format.

    Returns:
        Metrics in Prometheus text format
    """
    return generate_latest(metrics_registry)
