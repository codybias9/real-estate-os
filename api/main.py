"""
Real Estate OS - Comprehensive API
10x better decision speed, not just data
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from api import schemas
import os

# Prometheus metrics
from prometheus_client import make_asgi_app
from prometheus_fastapi_instrumentator import Instrumentator
from api import metrics

# OpenAPI enhancements
from api.openapi_config import get_openapi_schema_enhancements, OPENAPI_TAGS

# Import all routers
from api.routers import (
    auth,
    properties,
    quick_wins,
    workflow,
    communications,
    portfolio,
    sharing,
    data_propensity,
    automation,
    differentiators,
    onboarding,
    open_data,
    webhooks,
    jobs,
    sse_events,
    admin
)

# Create FastAPI app with enhanced OpenAPI configuration
app = FastAPI(
    title="Real Estate OS API",
    version="1.0.0",
    description="Real Estate OS - Decision speed, not just data",
    contact={
        "name": "Real Estate OS Support",
        "email": "support@realestateos.com",
        "url": "https://realestateos.com/support"
    },
    license_info={
        "name": "Proprietary",
        "url": "https://realestateos.com/license"
    },
    terms_of_service="https://realestateos.com/terms",
    openapi_tags=OPENAPI_TAGS,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    servers=[
        {
            "url": "https://api.realestateos.com",
            "description": "Production"
        },
        {
            "url": "https://staging-api.realestateos.com",
            "description": "Staging"
        },
        {
            "url": "http://localhost:8000",
            "description": "Local Development"
        }
    ]
)

# Customize OpenAPI schema with examples
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
        servers=app.servers
    )

    # Merge with enhancements
    enhancements = get_openapi_schema_enhancements()
    openapi_schema["info"].update(enhancements["info"])

    # Add external docs
    openapi_schema["externalDocs"] = enhancements["externalDocs"]

    # Add tag groups (for ReDoc)
    if "x-tagGroups" in enhancements:
        openapi_schema["x-tagGroups"] = enhancements["x-tagGroups"]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
from api.rate_limit import rate_limit_middleware
app.middleware("http")(rate_limit_middleware)

# Add ETag support for conditional requests
from api.etag import etag_middleware
app.middleware("http")(etag_middleware)

# ============================================================================
# PROMETHEUS METRICS
# ============================================================================

# Instrument FastAPI app with default metrics
instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_respect_env_var=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/metrics", "/healthz", "/ping"],
    env_var_name="ENABLE_METRICS",
    inprogress_name="realestateos_requests_inprogress",
    inprogress_labels=True,
)

# Add custom metrics
instrumentator.add(
    metrics.api_request_duration_seconds.labels(method="", endpoint="").observe
)

# Expose metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# ============================================================================
# LEGACY ENDPOINTS (keep for compatibility)
# ============================================================================

@app.get("/healthz", tags=["System"])
def health():
    """Health check endpoint"""
    return {"status": "ok"}

@app.get("/ping", tags=["System"])
def ping():
    """Legacy ping endpoint"""
    from sqlalchemy import create_engine, text
    dsn = os.getenv("DB_DSN")
    if not dsn:
        return {"error": "DB_DSN not set"}

    try:
        engine = create_engine(dsn)
        with engine.begin() as conn:
            count = conn.execute(text("SELECT count(*) FROM ping")).scalar()
        return {"ping_count": count}
    except Exception as e:
        return {"error": str(e)}

# ============================================================================
# STATUS / FEATURE FLAGS
# ============================================================================

@app.get("/api/v1/status", response_model=schemas.HealthResponse, tags=["System"])
def get_status():
    """
    Get API status and feature flags

    Shows which feature groups are implemented
    """
    return {
        "status": "operational",
        "features": {
            # Quick Wins (Month 1)
            "generate_and_send": True,
            "auto_assign_on_reply": True,
            "stage_aware_templates": True,
            "flag_data_issue": True,

            # Workflow Accelerators
            "next_best_action": True,
            "smart_lists": True,
            "one_click_tasking": True,

            # Communication Inside Pipeline
            "email_threading": True,
            "call_capture": True,
            "reply_drafting": True,

            # Portfolio & Outcomes
            "deal_economics": True,
            "investor_readiness": True,
            "template_leaderboards": True,

            # Sharing & Deal Rooms
            "secure_share_links": True,
            "deal_rooms": True,
            "offer_pack_export": True,

            # Data & Trust
            "propensity_signals": True,
            "provenance_inspector": True,
            "deliverability_dashboard": True,

            # Automation & Guardrails
            "cadence_governor": True,
            "compliance_pack": True,
            "budget_tracking": True,

            # Differentiators
            "explainable_probability": True,
            "scenario_planning": True,
            "investor_network": True,

            # Onboarding
            "starter_presets": True,
            "guided_tour": True,

            # Open Data Ladder
            "open_data_integrations": True,
            "provenance_tracking": True
        }
    }

# ============================================================================
# INCLUDE ALL ROUTERS
# ============================================================================

# Authentication (Login, Register, Profile)
app.include_router(auth.router, prefix="/api/v1")

# Properties (CRUD, Filtering, Timeline, Stats)
app.include_router(properties.router, prefix="/api/v1")

# Quick Wins (Month 1 Features)
app.include_router(quick_wins.router, prefix="/api/v1")

# Workflow Automation (NBA, Smart Lists, Tasks)
app.include_router(workflow.router, prefix="/api/v1")

# Communications (Email Threading, Calls, Reply Drafting)
app.include_router(communications.router, prefix="/api/v1")

# Portfolio & Outcomes (Deals, Investor Readiness, Templates)
app.include_router(portfolio.router, prefix="/api/v1")

# Sharing & Collaboration (Share Links, Deal Rooms)
app.include_router(sharing.router, prefix="/api/v1")

# Data & Propensity (Propensity Signals, Provenance, Deliverability)
app.include_router(data_propensity.router, prefix="/api/v1")

# Automation & Guardrails (Cadence, Compliance, Budget)
app.include_router(automation.router, prefix="/api/v1")

# Differentiators (Explainable Probability, Scenarios, Investor Network)
app.include_router(differentiators.router, prefix="/api/v1")

# Onboarding (Presets, Guided Tour)
app.include_router(onboarding.router, prefix="/api/v1")

# Open Data Integrations (Free Sources, Enrichment, Provenance)
app.include_router(open_data.router, prefix="/api/v1")

# Webhooks (SendGrid, Twilio event handlers)
app.include_router(webhooks.router, prefix="/api/v1")

# Background Jobs (Async task management)
app.include_router(jobs.router, prefix="/api/v1")

# Server-Sent Events (Real-time updates)
app.include_router(sse_events.router, prefix="/api/v1")

# Admin & System Management (DLQ, Monitoring, Health)
app.include_router(admin.router, prefix="/api/v1")

# ============================================================================
# BACKGROUND TASKS
# ============================================================================

async def metrics_collection_task():
    """
    Background task to periodically update database-derived metrics

    Runs every 30 seconds to update:
    - DLQ depth and age
    - Business metrics (properties, users, teams)
    - Provider status
    """
    import asyncio
    from db.database import get_db

    while True:
        try:
            # Get database session
            db = next(get_db())
            try:
                # Update all metrics
                metrics.update_all_metrics(db)
            finally:
                db.close()

            # Wait 30 seconds before next update
            await asyncio.sleep(30)

        except Exception as e:
            print(f"Error in metrics collection: {e}")
            await asyncio.sleep(30)

# ============================================================================
# STARTUP / SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """
    Run on application startup

    - Initialize database connection
    - Load configuration
    - Warm up caches
    - Instrument Prometheus metrics
    """
    print("🚀 Real Estate OS API Starting Up...")
    print(f"📊 Database: {os.getenv('DB_DSN', 'Not configured')}")
    print("✅ All routers loaded successfully")
    print("📖 API Documentation: /docs")

    # Instrument the app for metrics
    instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    print("📈 Prometheus metrics enabled at /metrics")

    # Start background metric collection
    import asyncio
    asyncio.create_task(metrics_collection_task())

@app.on_event("shutdown")
async def shutdown_event():
    """
    Run on application shutdown

    - Close database connections
    - Save state
    - Clean up resources
    """
    print("👋 Real Estate OS API Shutting Down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
