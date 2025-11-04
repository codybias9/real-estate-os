# Observability Service

Structured logging, metrics collection, and error tracking for Real Estate OS.

## Features

1. **Structured Logging** - JSON logging with context variables
2. **Prometheus Metrics** - Custom business and HTTP metrics
3. **Error Tracking** - Exception capture with context
4. **Grafana Dashboards** - Pre-built dashboards for visualization
5. **Request Logging** - Automatic HTTP request/response logging

## Structured Logging

```python
from observability import get_logger

logger = get_logger(__name__)

# Log with structured data
logger.info("property_created",
    property_id="123",
    tenant_id="tenant-1",
    apn="203-656-44"
)
```

## Prometheus Metrics

### HTTP Metrics
- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request duration histogram
- `http_errors_total` - Total HTTP errors

### Business Metrics
- `property_operations_total` - Property operations
- `score_operations_total` - Scoring operations
- `outreach_operations_total` - Outreach operations
- `sse_events_sent_total` - SSE events sent
- `cache_operations_total` - Cache operations

### Infrastructure Metrics
- `db_query_duration_seconds` - DB query duration
- `db_connections_active` - Active DB connections
- `sse_connections_active` - Active SSE connections

## Recording Metrics

```python
from observability import (
    record_property_operation,
    record_score_operation,
    record_cache_operation,
)

# Record property operation
record_property_operation(operation="create", status="success")

# Record score operation
record_score_operation(status="success")

# Record cache operation
record_cache_operation(operation="get", status="hit")
```

## Error Tracking

```python
from observability import error_tracker

try:
    # Some operation
    pass
except Exception as e:
    error_tracker.capture_exception(
        e,
        context={"property_id": "123", "tenant_id": "tenant-1"}
    )
```

## Grafana Dashboards

Two pre-built dashboards:
1. **API Overview** - HTTP metrics, error rates, latency
2. **Business Metrics** - Property, scoring, outreach operations

Import from `dashboards/` directory.

## Middleware

Automatically adds logging and metrics to all requests:

```python
from observability import LoggingMiddleware, MetricsMiddleware

app.add_middleware(LoggingMiddleware)
app.add_middleware(MetricsMiddleware)
```

## Testing

```bash
cd services/observability
pytest -v --cov=src
```
