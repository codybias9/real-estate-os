"""
Prometheus metrics instrumentation for FastAPI.
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging

logger = logging.getLogger(__name__)

# Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'Number of HTTP requests in progress',
    ['method', 'endpoint']
)

# Database metrics
db_connections_active = Gauge(
    'db_connections_active',
    'Number of active database connections'
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['query_type']
)

# Cache metrics
cache_hits_total = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_type']
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

# Rate limit metrics
rate_limit_exceeded_total = Counter(
    'rate_limit_exceeded_total',
    'Total rate limit exceeded events',
    ['endpoint']
)

# Data quality metrics
data_quality_checks_total = Counter(
    'data_quality_checks_total',
    'Total data quality checks',
    ['check_type', 'result']
)

# Provenance metrics
provenance_records_created_total = Counter(
    'provenance_records_created_total',
    'Total provenance records created'
)

trust_score_gauge = Gauge(
    'trust_score',
    'Trust score for data entities',
    ['entity_type']
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics."""

    async def dispatch(self, request: Request, call_next):
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        path = request.url.path

        # Track in-progress requests
        http_requests_in_progress.labels(method=method, endpoint=path).inc()

        # Start timer
        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)
            status_code = response.status_code

            # Record metrics
            http_requests_total.labels(
                method=method,
                endpoint=path,
                status=status_code
            ).inc()

            duration = time.time() - start_time
            http_request_duration_seconds.labels(
                method=method,
                endpoint=path
            ).observe(duration)

            return response

        except Exception as e:
            # Record error
            http_requests_total.labels(
                method=method,
                endpoint=path,
                status=500
            ).inc()

            duration = time.time() - start_time
            http_request_duration_seconds.labels(
                method=method,
                endpoint=path
            ).observe(duration)

            raise

        finally:
            # Decrement in-progress
            http_requests_in_progress.labels(method=method, endpoint=path).dec()


async def metrics_endpoint(request: Request):
    """Expose Prometheus metrics."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
