"""
Real Estate OS - API Server
FastAPI application with health checks, metrics, and v1 API namespace
"""

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from api.v1 import router as v1_router
from api.metrics import metrics_endpoint

# FastAPI app with OpenAPI documentation
app = FastAPI(
    title="Real Estate OS API",
    description="""
    Real Estate Operating System API - Property discovery, enrichment, scoring, and outreach.

    ## Features

    * **Health Checks**: Process health and database connectivity verification
    * **Property Discovery**: Intake and normalization of property records
    * **Enrichment**: Plugin-based property data enrichment with provenance tracking
    * **Scoring**: Deterministic property scoring with explainability
    * **Outreach**: Multi-channel campaign orchestration
    * **Metrics**: Prometheus metrics for observability

    ## Architecture

    Event-driven microservices with:
    - Single-producer subjects (event.discovery.intake, event.enrichment.features, etc.)
    - Policy-first resource access via Policy Kernel
    - Per-field provenance tracking
    - Multi-tenant RLS
    """,
    version="0.1.0",
    openapi_tags=[
        {
            "name": "Health",
            "description": "Process health and database connectivity checks",
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
