"""
Prometheus Metrics Endpoint
Exposes metrics in Prometheus format for observability
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
from fastapi.routing import APIRoute

# Define application metrics
http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds", "HTTP request latency", ["method", "endpoint"]
)

active_requests = Gauge("active_requests", "Number of active requests")

# Property-specific metrics
properties_discovered_total = Counter(
    "properties_discovered_total", "Total properties discovered", ["tenant_id"]
)

properties_scored_total = Counter(
    "properties_scored_total", "Total properties scored", ["tenant_id"]
)

enrichment_plugin_calls_total = Counter(
    "enrichment_plugin_calls_total",
    "Total enrichment plugin calls",
    ["plugin_name", "priority", "status"],
)

policy_decisions_total = Counter(
    "policy_decisions_total",
    "Total policy decisions",
    ["decision_type", "resource_type", "result"],
)

external_api_calls_total = Counter(
    "external_api_calls_total", "Total external API calls", ["provider", "status"]
)

external_api_cost_cents = Counter(
    "external_api_cost_cents", "Total external API costs in cents", ["provider"]
)


def metrics_endpoint() -> Response:
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus exposition format for scraping.
    Includes both framework metrics (HTTP requests, latency) and
    application-specific metrics (properties, enrichment, policy).
    """
    metrics_data = generate_latest()
    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)


__all__ = [
    "metrics_endpoint",
    "http_requests_total",
    "http_request_duration_seconds",
    "active_requests",
    "properties_discovered_total",
    "properties_scored_total",
    "enrichment_plugin_calls_total",
    "policy_decisions_total",
    "external_api_calls_total",
    "external_api_cost_cents",
]
