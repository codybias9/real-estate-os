"""Prometheus metrics for Real Estate OS

Provides:
- HTTP request metrics (duration, status codes)
- Database query metrics
- Cache hit/miss rates
- Business metrics (properties created, campaigns sent, etc.)
"""

import time
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


# ============================================================================
# HTTP Metrics
# ============================================================================

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'HTTP requests currently in progress',
    ['method', 'endpoint']
)

# ============================================================================
# Database Metrics
# ============================================================================

db_queries_total = Counter(
    'db_queries_total',
    'Total database queries',
    ['operation', 'table']
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation', 'table'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)

db_connections_active = Gauge(
    'db_connections_active',
    'Active database connections'
)

# ============================================================================
# Cache Metrics
# ============================================================================

cache_operations_total = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['operation', 'result']  # operation: get/set/delete, result: hit/miss/success
)

cache_size_bytes = Gauge(
    'cache_size_bytes',
    'Cache size in bytes'
)

# ============================================================================
# Business Metrics
# ============================================================================

properties_total = Gauge(
    'properties_total',
    'Total number of properties',
    ['tenant_id']
)

campaigns_sent_total = Counter(
    'campaigns_sent_total',
    'Total campaigns sent',
    ['tenant_id', 'campaign_type']
)

api_keys_active = Gauge(
    'api_keys_active',
    'Number of active API keys',
    ['tenant_id']
)

auth_attempts_total = Counter(
    'auth_attempts_total',
    'Authentication attempts',
    ['method', 'result']  # method: jwt/api_key, result: success/failure
)

rate_limit_exceeded_total = Counter(
    'rate_limit_exceeded_total',
    'Rate limit exceeded events',
    ['limit_type']  # ip or tenant
)

# ============================================================================
# Middleware
# ============================================================================

class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP metrics"""

    async def dispatch(self, request: Request, call_next):
        # Skip metrics endpoint
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        endpoint = request.url.path

        # Track in-progress requests
        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()

        # Time the request
        start_time = time.time()

        try:
            response = await call_next(request)
            status = response.status_code
        except Exception as e:
            status = 500
            raise
        finally:
            # Record metrics
            duration = time.time() - start_time

            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status
            ).inc()

            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

            http_requests_in_progress.labels(
                method=method,
                endpoint=endpoint
            ).dec()

        return response


def setup_metrics(app):
    """Setup Prometheus metrics

    Adds middleware to collect HTTP metrics and exposes /metrics endpoint.

    Args:
        app: FastAPI application instance
    """
    # Add metrics middleware
    app.add_middleware(PrometheusMiddleware)

    # Add metrics endpoint
    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint"""
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )

    print("✅ Prometheus metrics enabled at /metrics")


def record_metric(metric_name: str, value: float = 1, labels: dict = None):
    """Record a custom metric

    Usage:
        record_metric("properties_created", labels={"tenant_id": "123"})
        record_metric("campaign_sent", labels={"tenant_id": "123", "type": "cold"})

    Args:
        metric_name: Name of the metric
        value: Value to record (default: 1)
        labels: Dictionary of labels
    """
    labels = labels or {}

    # Map metric names to actual metrics
    metrics_map = {
        "properties_created": properties_total,
        "campaign_sent": campaigns_sent_total,
        "auth_success": auth_attempts_total,
        "auth_failure": auth_attempts_total,
        "rate_limit_exceeded": rate_limit_exceeded_total,
    }

    metric = metrics_map.get(metric_name)
    if metric:
        if isinstance(metric, Counter):
            metric.labels(**labels).inc(value)
        elif isinstance(metric, Gauge):
            metric.labels(**labels).set(value)
