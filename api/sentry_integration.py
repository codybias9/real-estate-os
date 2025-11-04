"""
Sentry Integration for Error Tracking and Performance Monitoring
"""

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
import os


def init_sentry():
    """
    Initialize Sentry SDK with FastAPI and SQLAlchemy integrations
    """
    sentry_dsn = os.getenv("SENTRY_DSN")
    environment = os.getenv("ENVIRONMENT", "development")

    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=environment,
            traces_sample_rate=0.1,  # 10% of transactions
            profiles_sample_rate=0.1,  # 10% of transactions
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration()
            ],
            before_send=before_send_handler,
            before_send_transaction=before_send_transaction_handler
        )

        return True
    return False


def before_send_handler(event, hint):
    """
    Filter or modify events before sending to Sentry
    """
    # Filter out certain error types
    if 'exc_info' in hint:
        exc_type, exc_value, tb = hint['exc_info']
        if isinstance(exc_value, KeyboardInterrupt):
            return None  # Don't send keyboard interrupts

    # Add custom context
    event.setdefault('tags', {})
    event['tags']['service'] = 'real-estate-os-api'

    return event


def before_send_transaction_handler(event, hint):
    """
    Filter or modify transaction events
    """
    # Only send slow transactions (>1s)
    if 'start_timestamp' in event and 'timestamp' in event:
        duration = event['timestamp'] - event['start_timestamp']
        if duration < 1.0:
            return None  # Drop fast transactions to reduce quota usage

    return event


def capture_test_event():
    """
    Capture a test event to verify Sentry integration
    """
    try:
        # Intentionally trigger an error
        1 / 0
    except Exception as e:
        sentry_sdk.capture_exception(e)

    # Capture a test message
    sentry_sdk.capture_message(
        "Sentry integration test - Real Estate OS",
        level="info"
    )


if __name__ == "__main__":
    # Test integration
    init_sentry()
    capture_test_event()
    print("Test events sent to Sentry")
