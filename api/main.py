"""
Real Estate OS - API Server
FastAPI application with health checks, metrics, and v1 API namespace
"""

import sys
import os
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

# Add services to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../services/security/src"))

from api.v1 import router as v1_router
from api.metrics import metrics_endpoint

# Import security middleware
from security import (
    configure_cors,
    SecurityHeadersMiddleware,
    RequestIDMiddleware,
    get_rate_limiter,
)

# FastAPI app with OpenAPI documentation
app = FastAPI(
    title="Real Estate OS API",
    description="""
    Real Estate Operating System API - Property discovery, enrichment, scoring, and outreach.

    ## Features

    * **Health Checks**: Process health and database connectivity verification
    * **Authentication**: JWT-based authentication with role-based access control
    * **Property Discovery**: Intake and normalization of property records
    * **Enrichment**: Plugin-based property data enrichment with provenance tracking
    * **Scoring**: Deterministic property scoring with explainability
    * **Outreach**: Multi-channel campaign orchestration
    * **Metrics**: Prometheus metrics for observability
    * **Security**: Rate limiting, CORS, security headers, request ID tracking

    ## Architecture

    Event-driven microservices with:
    - Single-producer subjects (event.discovery.intake, event.enrichment.features, etc.)
    - Policy-first resource access via Policy Kernel
    - Per-field provenance tracking
    - Multi-tenant RLS
    - JWT authentication with RBAC
    - Rate limiting and security headers
    """,
    version="0.1.0",
    openapi_tags=[
        {
            "name": "Health",
            "description": "Process health and database connectivity checks",
        },
        {
            "name": "Authentication",
            "description": "User authentication and authorization",
        },
        {
            "name": "Discovery",
            "description": "Property intake, normalization, and deduplication",
        },
        {
            "name": "Enrichment",
            "description": "Property data enrichment with plugin architecture",
        },
        {
            "name": "Scoring",
            "description": "Deterministic property scoring with explainability",
        },
        {
            "name": "Outreach",
            "description": "Multi-channel outreach orchestration",
        },
    ],
)

# Configure CORS for frontend
configure_cors(app)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add request ID tracking middleware
app.add_middleware(RequestIDMiddleware)

# Configure rate limiting
rate_limiter = get_rate_limiter()
app.state.limiter = rate_limiter.get_limiter()
rate_limiter.add_exception_handler(app)


# Root redirect to docs
@app.get("/", include_in_schema=False)
def root():
    """Redirect root to API documentation"""
    return RedirectResponse(url="/docs")


# Mount v1 API router
app.include_router(v1_router)


# Mount Prometheus metrics endpoint
@app.get("/metrics", include_in_schema=False)
def metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus exposition format.
    Not included in OpenAPI docs as it's for monitoring systems.
    """
    return metrics_endpoint()
