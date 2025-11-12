"""
Real Estate OS - Data Processing and Automation Platform API
Main FastAPI application with comprehensive pipeline monitoring
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
import os

from .config import get_settings
from .routers import pipelines, scraping, enrichment, scoring, health, metrics

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="Real Estate OS API",
    description="Data Processing and Automation Platform - Pipeline Monitoring & Analytics",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api")
app.include_router(pipelines.router, prefix="/api")
app.include_router(scraping.router, prefix="/api")
app.include_router(enrichment.router, prefix="/api")
app.include_router(scoring.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")

# Root endpoint
@app.get("/")
def read_root():
    return {
        "service": "Real Estate OS API",
        "version": "1.0.0",
        "status": "running",
        "description": "Data Processing and Automation Platform",
        "docs": "/docs",
        "capabilities": [
            "Pipeline Monitoring (Airflow DAGs)",
            "Scraping Job Management",
            "Data Enrichment Tracking",
            "Property Scoring & ML",
            "System Health Monitoring",
            "Data Quality Metrics"
        ]
    }

# Legacy health endpoint
@app.get("/healthz")
def health():
    return {"status": "ok"}

# Legacy ping endpoint
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
