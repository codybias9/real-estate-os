"""Real Estate OS API - FastAPI Application."""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
import os

from .config import settings
from .database import init_db
from .routers import auth, properties, leads, campaigns, deals, users, analytics, sse
from .middleware import (
    IdempotencyMiddleware,
    ETagMiddleware,
    RateLimitMiddleware,
    AuditLogMiddleware,
)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Comprehensive Real Estate Operating System API",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add middleware (order matters - added in reverse order of execution)

# 1. CORS middleware (outermost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Rate limiting middleware
if not settings.DEBUG:  # Only enable in production
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=60,
        requests_per_hour=1000,
        requests_per_day=10000,
    )

# 3. ETag middleware for caching
app.add_middleware(ETagMiddleware)

# 4. Idempotency middleware
app.add_middleware(IdempotencyMiddleware, expire_hours=24)

# 5. Audit logging middleware (innermost)
app.add_middleware(AuditLogMiddleware, log_read_operations=False)

# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(properties.router, prefix="/api/v1")
app.include_router(leads.router, prefix="/api/v1")
app.include_router(campaigns.router, prefix="/api/v1")
app.include_router(deals.router, prefix="/api/v1")
app.include_router(deals.portfolio_router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(users.roles_router, prefix="/api/v1")
app.include_router(users.permissions_router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(sse.router, prefix="/api/v1")


@app.on_event("startup")
def startup_event():
    """Initialize database on startup."""
    init_db()


# Health endpoint
@app.get("/healthz")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


# Ping endpoint that uses DB_DSN
@app.get("/ping")
def ping():
    """Ping database endpoint."""
    dsn = os.getenv("DB_DSN")
    if not dsn:
        return {"error": "DB_DSN not set"}

    try:
        engine = create_engine(dsn)
        with engine.begin() as conn:
            conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS ping (id serial PRIMARY KEY, ts timestamptz DEFAULT now())"
                )
            )
            conn.execute(text("INSERT INTO ping DEFAULT VALUES"))
            count = conn.execute(text("SELECT count(*) FROM ping")).scalar()
        return {"ping_count": count}
    except Exception as e:
        return {"error": str(e)}


@app.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/healthz",
    }
