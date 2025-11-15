"""Real Estate OS API - Main application."""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
import os
import sys

# Add project root to path
sys.path.insert(0, '/home/user/real-estate-os')

# Import routers
from api.routes import properties, enrichment, scoring, documents, campaigns, dashboard

# Create FastAPI app
app = FastAPI(
    title="Real Estate OS API",
    description="API for Real Estate investment automation platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(properties.router)
app.include_router(enrichment.router)
app.include_router(scoring.router)
app.include_router(documents.router)
app.include_router(campaigns.router)
app.include_router(dashboard.router)


# Root endpoint
@app.get("/")
def root():
    """API root endpoint."""
    return {
        "name": "Real Estate OS API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "properties": "/api/properties",
            "enrichment": "/api/properties/{id}/enrichment",
            "scoring": "/api/properties/{id}/score",
            "documents": "/api/properties/{id}/documents",
            "campaigns": "/api/campaigns",
            "dashboard": "/api/dashboard",
        },
    }


# Health endpoint
@app.get("/healthz")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


# Ping endpoint that uses DB_DSN
@app.get("/ping")
def ping():
    """Database connectivity test."""
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
