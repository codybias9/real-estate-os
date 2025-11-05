"""Real Estate OS API - FastAPI Application."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text

from .config import settings
from .database import init_db
from .routers import auth, properties, leads, campaigns, deals, users, analytics, sse
from . import health
from .middleware import (
    IdempotencyMiddleware,
    ETagMiddleware,
    RateLimitMiddleware,
    AuditLogMiddleware,
)
from .logging_config import setup_logging, LoggingMiddleware, logger
from .exception_handlers import register_exception_handlers


# Setup logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {'Development' if settings.DEBUG else 'Production'}")

    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    # Create logs directory
    os.makedirs("logs", exist_ok=True)
    logger.info("Logs directory created")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Comprehensive Real Estate Operating System API with Multi-tenancy, RBAC, Real-time Updates, and Background Task Processing",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Register exception handlers
register_exception_handlers(app)

# Add middleware (order matters - added in reverse order of execution)

# 1. CORS middleware (outermost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Logging middleware
app.add_middleware(LoggingMiddleware)

# 3. Rate limiting middleware
if not settings.DEBUG:  # Only enable in production
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=60,
        requests_per_hour=1000,
        requests_per_day=10000,
    )

# 4. ETag middleware for caching
app.add_middleware(ETagMiddleware)

# 5. Idempotency middleware
app.add_middleware(IdempotencyMiddleware, expire_hours=24)

# 6. Audit logging middleware (innermost)
app.add_middleware(AuditLogMiddleware, log_read_operations=False)

# Include routers
app.include_router(health.router, tags=["Health"])  # Health checks (no prefix)
app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
app.include_router(properties.router, prefix="/api/v1", tags=["Properties"])
app.include_router(leads.router, prefix="/api/v1", tags=["Leads"])
app.include_router(campaigns.router, prefix="/api/v1", tags=["Campaigns"])
app.include_router(deals.router, prefix="/api/v1", tags=["Deals"])
app.include_router(deals.portfolio_router, prefix="/api/v1", tags=["Portfolios"])
app.include_router(users.router, prefix="/api/v1", tags=["Users"])
app.include_router(users.roles_router, prefix="/api/v1", tags=["Roles"])
app.include_router(users.permissions_router, prefix="/api/v1", tags=["Permissions"])
app.include_router(analytics.router, prefix="/api/v1", tags=["Analytics"])
app.include_router(sse.router, prefix="/api/v1", tags=["Real-time"])


@app.get("/", tags=["Root"])
def root():
    """Root endpoint with API information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "Comprehensive Real Estate Operating System API",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "api_version": "v1",
        "endpoints": {
            "authentication": "/api/v1/auth",
            "properties": "/api/v1/properties",
            "leads": "/api/v1/leads",
            "campaigns": "/api/v1/campaigns",
            "deals": "/api/v1/deals",
            "portfolios": "/api/v1/portfolios",
            "users": "/api/v1/users",
            "analytics": "/api/v1/analytics",
            "real_time": "/api/v1/sse"
        }
    }
