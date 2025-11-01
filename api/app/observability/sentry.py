"""Sentry error tracking

Captures:
- Unhandled exceptions
- Performance issues
- Custom error events
"""

import os
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration


def setup_sentry(app):
    """Setup Sentry error tracking

    Captures exceptions, performance data, and custom events.

    Args:
        app: FastAPI application instance
    """
    sentry_dsn = os.getenv("SENTRY_DSN")

    if not sentry_dsn:
        print("⚠️  Sentry disabled (SENTRY_DSN not set)")
        return

    environment = os.getenv("ENVIRONMENT", "production")
    release = os.getenv("APP_VERSION", "1.0.0")

    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=environment,
        release=release,

        # Performance monitoring
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),

        # Integrations
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
            RedisIntegration(),
        ],

        # Additional configuration
        send_default_pii=False,  # Don't send PII by default
        attach_stacktrace=True,
        max_breadcrumbs=50,

        # Filter out health check endpoints
        before_send=before_send_filter,
    )

    print(f"✅ Sentry enabled (environment: {environment}, release: {release})")


def before_send_filter(event, hint):
    """Filter events before sending to Sentry

    Filters out:
    - Health check requests
    - Expected errors (404, 401)
    """
    # Filter health checks
    if event.get("request", {}).get("url", "").endswith("/healthz"):
        return None

    # Filter expected HTTP errors
    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]
        if "404" in str(exc_value) or "401" in str(exc_value):
            return None

    return event
