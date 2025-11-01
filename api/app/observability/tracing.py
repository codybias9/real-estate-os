"""OpenTelemetry tracing setup

Provides distributed tracing for:
- HTTP requests
- Database queries
- External API calls
- Background tasks
"""

import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION


def setup_tracing(app):
    """Setup OpenTelemetry tracing

    Instruments FastAPI, SQLAlchemy, and Requests with automatic span creation.
    Exports traces to OTLP collector (typically Jaeger or Tempo).

    Args:
        app: FastAPI application instance
    """
    # Check if tracing is enabled
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not otlp_endpoint:
        print("⚠️  OpenTelemetry disabled (OTEL_EXPORTER_OTLP_ENDPOINT not set)")
        return

    # Create resource with service metadata
    resource = Resource.create({
        SERVICE_NAME: os.getenv("OTEL_SERVICE_NAME", "real-estate-os-api"),
        SERVICE_VERSION: os.getenv("APP_VERSION", "1.0.0"),
        "deployment.environment": os.getenv("ENVIRONMENT", "production"),
    })

    # Setup tracer provider
    provider = TracerProvider(resource=resource)

    # Setup OTLP exporter (exports to collector)
    otlp_exporter = OTLPSpanExporter(
        endpoint=otlp_endpoint,
        insecure=os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "false").lower() == "true"
    )

    # Add batch processor (buffers spans before export)
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # Set as global tracer provider
    trace.set_tracer_provider(provider)

    # Instrument frameworks
    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument()
    RequestsInstrumentor().instrument()

    print(f"✅ OpenTelemetry tracing enabled (endpoint: {otlp_endpoint})")


def get_tracer(name: str = __name__):
    """Get a tracer instance for custom spans

    Usage:
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("custom_operation"):
            # Your code here
            pass

    Args:
        name: Tracer name (typically __name__)

    Returns:
        Tracer instance
    """
    return trace.get_tracer(name)
