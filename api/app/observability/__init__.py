"""Observability module for Real Estate OS

Provides:
- OpenTelemetry instrumentation (traces, metrics)
- Prometheus metrics
- Sentry error tracking
- Audit logging
"""

from .tracing import setup_tracing, get_tracer
from .metrics import setup_metrics, record_metric
from .logging import setup_logging, audit_log
from .sentry import setup_sentry

__all__ = [
    'setup_tracing',
    'get_tracer',
    'setup_metrics',
    'record_metric',
    'setup_logging',
    'audit_log',
    'setup_sentry',
]
