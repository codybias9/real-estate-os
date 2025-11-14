from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
import os

# Import routers
from api.routers import (
    auth,
    analytics,
    properties,
    leads,
    deals,
    pipelines,
    system,
    workflow,
    templates,
    communications,
    automation,
    sharing,
    portfolio,
    data_propensity,
    jobs,
    sse_events,
    status,
    quick_wins
)

app = FastAPI(
    title="Real Estate OS API",
    description="Hybrid Sales Ops & Data Processing Platform for Real Estate Intelligence",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with /api/v1 prefix to match frontend expectations
# Authentication & User Management
app.include_router(auth.router, prefix="/api/v1")

# Analytics & Metrics
app.include_router(analytics.router, prefix="/api/v1")

# Data Management (CRM features)
app.include_router(properties.router, prefix="/api/v1")
app.include_router(leads.router, prefix="/api/v1")
app.include_router(deals.router, prefix="/api/v1")

# Sales Ops - Core Features
app.include_router(workflow.router, prefix="/api/v1")
app.include_router(templates.router, prefix="/api/v1")
app.include_router(communications.router, prefix="/api/v1")
app.include_router(quick_wins.router, prefix="/api/v1")

# Sales Ops - Automation & Compliance
app.include_router(automation.router, prefix="/api/v1")

# Sales Ops - Collaboration & Portfolio
app.include_router(sharing.router, prefix="/api/v1")
app.include_router(portfolio.router, prefix="/api/v1")

# Data Enrichment & Signals
app.include_router(data_propensity.router, prefix="/api/v1")

# Observability & Monitoring
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(sse_events.router, prefix="/api/v1")
app.include_router(status.router, prefix="/api/v1")

# Technical Platform Features
app.include_router(pipelines.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")

# Health endpoint
@app.get("/healthz")
def health():
    return {"status": "ok"}

# Ping endpoint that uses DB_DSN
@app.get("/ping")
def ping():
    dsn = os.getenv("DB_DSN")
    if not dsn:
        raise HTTPException(500, "DB_DSN not set")
    engine = create_engine(dsn)
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS ping (id serial PRIMARY KEY, ts timestamptz DEFAULT now())"
        ))
        conn.execute(text("INSERT INTO ping DEFAULT VALUES"))
        count = conn.execute(text("SELECT count(*) FROM ping")).scalar()
    return {"ping_count": count}
