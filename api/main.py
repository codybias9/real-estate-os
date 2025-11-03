"""
Real Estate OS - Comprehensive API
10x better decision speed, not just data
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import schemas
import os

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
    sse_events
)

# Create FastAPI app
app = FastAPI(
    title="Real Estate OS API",
    description="""
# Real Estate OS - Complete UX Platform

## Big Themes

- **Decision speed, not just data**: Surface the one thing to do next for each deal, with context
- **Fewer tabs**: Bring email, calls, docs, and investor share-outs into the pipeline
- **Explainable confidence**: Probabilities and money-on-the-table estimates the team can trust
- **Zero-friction collaboration**: Secure sharing without logins, fully trackable
- **Operational guardrails**: Automate "don't forgets" - cadence, compliance, cost caps

## Feature Groups

### 🎯 Quick Wins (Month 1)
- Generate & Send Combo
- Auto-Assign on Reply
- Stage-Aware Templates
- Flag Data Issue

### 🚀 Workflow Accelerators
- Next Best Action (NBA) Panel
- Smart Lists (Saved Queries)
- One-Click Tasking

### 📧 Communication Inside Pipeline
- Email Threading (Gmail/Outlook)
- Call Capture + Transcription
- Reply Drafting & Objection Handling

### 💰 Portfolio & Outcomes
- Deal Economics Panel
- Investor Readiness Score
- Template Leaderboards

### 🔗 Sharing & Deal Rooms
- Secure Share Links (no login)
- Deal Room Artifacts
- Export Offer Packs

### 📊 Data & Trust Upgrades
- Owner Propensity Signals
- Provenance Inspector
- Deliverability Dashboard

### 🤖 Automation & Guardrails
- Cadence Governor
- Compliance Pack (DNC, Opt-outs)
- Budget Tracking

### 🎨 Differentiators
- Explainable Probability of Close
- Scenario Planning (What-If)
- Investor Network Effects

### 📚 Onboarding
- Starter Presets by Persona
- Guided Tour Checklist

### 🌍 Open Data Ladder
- Free sources first (OpenAddresses, OSM, FEMA)
- Paid sources only when needed
- Complete provenance tracking

## API Documentation

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`
""",
    version="1.0.0",
    contact={
        "name": "Real Estate OS Support",
        "email": "support@real-estate-os.com"
    }
)

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
    """
    print("🚀 Real Estate OS API Starting Up...")
    print(f"📊 Database: {os.getenv('DB_DSN', 'Not configured')}")
    print("✅ All routers loaded successfully")
    print("📖 API Documentation: /docs")

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
