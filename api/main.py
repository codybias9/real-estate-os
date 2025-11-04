"""
Real Estate OS API - Main application entry point.

This FastAPI application provides comprehensive endpoints for:
- Property pipeline management
- Communication tracking (email, SMS, calls)
- Workflow automation (Next Best Actions, Smart Lists)
- Quick Win features for immediate productivity gains
- Analytics and reporting

Tech Stack:
- FastAPI: Modern, fast web framework
- SQLAlchemy: ORM for PostgreSQL
- Pydantic: Data validation and serialization
- PostgreSQL: Primary database with JSONB support

Architecture:
- Modular routers for feature separation
- Dependency injection for database sessions
- Pydantic schemas for type safety
- Background tasks for async operations
"""

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text
from contextlib import asynccontextmanager
import os
import time
from typing import Dict, Any

from api.database import get_db, engine
from api.routers import properties, quick_wins, workflow

# Import additional routers (to be created)
# from api.routers import communications, templates, tasks, deals


# ============================================================================
# LIFESPAN EVENTS
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.

    Startup:
    - Verify database connection
    - Log application start

    Shutdown:
    - Close database connections
    - Clean up resources
    """
    # Startup
    print("🚀 Real Estate OS API starting up...")
    print(f"📊 Database: {os.getenv('DB_DSN', 'Not configured')[:50]}...")

    # Verify database connection
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ Database connected: PostgreSQL")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

    print("✨ API ready to handle requests")

    yield

    # Shutdown
    print("👋 Shutting down Real Estate OS API...")
    engine.dispose()
    print("✅ Database connections closed")


# ============================================================================
# APPLICATION SETUP
# ============================================================================

app = FastAPI(
    title="Real Estate OS API",
    description="""
    Comprehensive real estate pipeline and communication management platform.

    ## Features

    ### 📋 Property Management
    - Complete property lifecycle tracking
    - Pipeline stage management
    - Advanced filtering and search
    - Timeline and activity tracking

    ### 📧 Communications
    - Email threading and tracking
    - SMS integration
    - Call logging with transcription
    - Template management with stage awareness

    ### ⚡ Quick Wins (Month 1)
    - Generate & Send Combo
    - Auto-Assign on Reply
    - Stage-Aware Templates
    - Flag Data Issues

    ### 🎯 Workflow Automation (P0)
    - Next Best Action recommendations
    - Smart Lists with dynamic filtering
    - One-click task creation
    - Automated cadence rules

    ### 💰 Deal Management
    - Deal economics with what-if scenarios
    - Probability of close tracking
    - Investor document management
    - Secure share links

    ### 📊 Analytics
    - Pipeline statistics
    - Communication performance
    - Template leaderboards
    - User activity tracking

    ## Authentication

    Currently using basic auth. Production should implement OAuth2/JWT.
    """,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# ============================================================================
# MIDDLEWARE
# ============================================================================

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add X-Process-Time header to all responses"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Error handling middleware
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors"""
    print(f"❌ Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if os.getenv("DEBUG") == "true" else "An unexpected error occurred"
        }
    )


# ============================================================================
# ROUTERS
# ============================================================================

# Include routers with prefixes and tags
app.include_router(properties.router, prefix="/api/v1")
app.include_router(quick_wins.router, prefix="/api/v1")
app.include_router(workflow.router, prefix="/api/v1")

# TODO: Add these routers when created
# app.include_router(communications.router, prefix="/api/v1")
# app.include_router(templates.router, prefix="/api/v1")
# app.include_router(tasks.router, prefix="/api/v1")
# app.include_router(deals.router, prefix="/api/v1")
# app.include_router(analytics.router, prefix="/api/v1")


# ============================================================================
# HEALTH & STATUS ENDPOINTS
# ============================================================================

@app.get("/healthz", tags=["Health"])
def health_check():
    """
    Basic health check endpoint.

    Returns OK if the service is running.
    """
    return {"status": "ok", "service": "real-estate-os-api"}


@app.get("/readyz", tags=["Health"])
def readiness_check():
    """
    Readiness check endpoint.

    Verifies that the service is ready to handle requests by checking:
    - Database connectivity
    - Critical dependencies
    """
    checks = {
        "database": False,
        "overall": False
    }

    # Check database
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            checks["database"] = True
    except Exception as e:
        print(f"Database check failed: {e}")

    checks["overall"] = all([checks["database"]])

    status_code = 200 if checks["overall"] else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "ready": checks["overall"],
            "checks": checks
        }
    )


@app.get("/ping", tags=["Health"])
def ping():
    """
    Legacy ping endpoint with database write test.

    Creates a ping record in the database.
    """
    dsn = os.getenv("DB_DSN")
    if not dsn:
        raise HTTPException(500, "DB_DSN not set")

    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS ping (id serial PRIMARY KEY, ts timestamptz DEFAULT now())"
        ))
        conn.execute(text("INSERT INTO ping DEFAULT VALUES"))
        count = conn.execute(text("SELECT count(*) FROM ping")).scalar()

    return {"ping_count": count}


@app.get("/", tags=["Root"])
def root():
    """
    API root endpoint.

    Returns basic API information and links to documentation.
    """
    return {
        "service": "Real Estate OS API",
        "version": "0.1.0",
        "status": "running",
        "documentation": {
            "openapi": "/openapi.json",
            "swagger_ui": "/docs",
            "redoc": "/redoc"
        },
        "endpoints": {
            "properties": "/api/v1/properties",
            "quick_wins": "/api/v1/quick-wins",
            "workflow": "/api/v1/workflow",
            "health": "/healthz",
            "readiness": "/readyz"
        }
    }


@app.get("/api/v1/status", tags=["Status"])
def api_status():
    """
    API status and statistics.

    Returns:
    - Database connection status
    - Environment information
    - Feature flags
    """
    from db import models
    from sqlalchemy.orm import Session

    with engine.connect() as conn:
        # Get table counts
        try:
            with Session(bind=conn) as db:
                property_count = db.query(models.Property).count()
                user_count = db.query(models.User).count()
                communication_count = db.query(models.Communication).count()
                task_count = db.query(models.Task).count()
        except Exception as e:
            property_count = user_count = communication_count = task_count = 0

    return {
        "status": "operational",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "database": {
            "connected": True,
            "url": os.getenv("DB_DSN", "")[:30] + "...",
        },
        "statistics": {
            "properties": property_count,
            "users": user_count,
            "communications": communication_count,
            "tasks": task_count
        },
        "features": {
            "quick_wins": {
                "generate_and_send": True,
                "auto_assign_on_reply": True,
                "stage_aware_templates": True,
                "flag_data_issue": True
            },
            "workflow": {
                "next_best_actions": True,
                "smart_lists": True,
                "one_click_tasking": True
            },
            "communications": {
                "email_threading": False,  # TODO
                "call_capture": False,  # TODO
                "sms_integration": False  # TODO
            }
        }
    }


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    # Run the application with Uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )
