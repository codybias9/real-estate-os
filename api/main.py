"""
Real Estate OS API - Main FastAPI Application
Complete API with JWT/OIDC auth, RLS integration, rate limiting, and observability.
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import logging
import sys
from datetime import datetime

from api.config import settings
from api.database import init_db, close_db
from api.redis_client import redis_client
from api.rate_limit import RateLimitMiddleware
from api.models import HealthCheckResponse, ServiceHealth, ErrorResponse

# Import routers
from api.routers import (
    auth, properties, prospects, offers, ml, analytics,
    leases, ownership, documents, hazards, graph
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


# ============================================================================
# Lifespan Events (Startup/Shutdown)
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")

    try:
        # Initialize database
        if settings.environment == "development":
            await init_db()
            logger.info("Database initialized")

        # Connect to Redis
        await redis_client.connect()
        logger.info("Redis connected")

        # Initialize observability
        if settings.sentry_dsn:
            import sentry_sdk
            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                environment=settings.sentry_environment or settings.environment,
                traces_sample_rate=settings.sentry_traces_sample_rate,
                integrations=[
                    # Add FastAPI integration if available
                ]
            )
            logger.info("Sentry initialized")

        logger.info("API startup complete")

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down API")

    try:
        await close_db()
        await redis_client.disconnect()
        logger.info("Cleanup complete")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    Real Estate OS API - Complete platform for real estate investment analysis,
    deal pipeline management, and portfolio optimization.

    Features:
    - Multi-tenant isolation with Row-Level Security (RLS)
    - JWT/OIDC authentication via Keycloak
    - Role-based access control (RBAC)
    - Rate limiting per tenant/user/endpoint
    - ML-powered property valuation
    - Spatial queries with PostGIS
    - Complete audit trail

    Authentication:
    All endpoints (except /health and /docs) require a valid JWT Bearer token.
    Get a token by calling POST /api/v1/auth/login.
    """,
    docs_url="/docs" if settings.enable_swagger else None,
    redoc_url="/redoc" if settings.enable_redoc else None,
    openapi_url="/openapi.json",
    lifespan=lifespan
)


# ============================================================================
# Middleware
# ============================================================================

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Rate Limiting
if settings.rate_limit_enabled:
    app.add_middleware(RateLimitMiddleware)
    logger.info("Rate limiting enabled")


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    logger.warning(f"Validation error: {errors}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Request validation failed",
            "errors": errors,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    # Don't leak internal errors in production
    detail = str(exc) if settings.debug else "Internal server error"

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": detail,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# ============================================================================
# Health Check
# ============================================================================

@app.get(
    "/health",
    response_model=HealthCheckResponse,
    tags=["System"],
    summary="Health check",
    description="Check API and service health status"
)
async def health_check() -> HealthCheckResponse:
    """
    Health check endpoint for load balancers and monitoring.

    Checks:
    - API status
    - Database connectivity
    - Redis connectivity
    - Overall system health
    """
    services = []

    # Check Redis
    redis_health = await redis_client.health_check()
    services.append(ServiceHealth(
        name="redis",
        status=redis_health.get("status", "unknown"),
        error=redis_health.get("error")
    ))

    # Check Database
    try:
        from api.database import engine
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        services.append(ServiceHealth(
            name="database",
            status="healthy"
        ))
    except Exception as e:
        services.append(ServiceHealth(
            name="database",
            status="unhealthy",
            error=str(e)
        ))

    # Overall status
    all_healthy = all(s.status == "healthy" for s in services)
    overall_status = "healthy" if all_healthy else "degraded"

    return HealthCheckResponse(
        status=overall_status,
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.utcnow(),
        services=services
    )


@app.get(
    "/",
    tags=["System"],
    summary="API info"
)
async def root():
    """API root - returns basic information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "docs": "/docs" if settings.enable_swagger else None,
        "health": "/health"
    }


# ============================================================================
# Include Routers
# ============================================================================

app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(properties.router, prefix=settings.api_prefix)
app.include_router(prospects.router, prefix=settings.api_prefix)
app.include_router(offers.router, prefix=settings.api_prefix)
app.include_router(leases.router, prefix=settings.api_prefix)
app.include_router(ownership.router, prefix=settings.api_prefix)
app.include_router(documents.router, prefix=settings.api_prefix)
app.include_router(hazards.router, prefix=settings.api_prefix)
app.include_router(graph.router, prefix=settings.api_prefix)
app.include_router(ml.router, prefix=settings.api_prefix)
app.include_router(analytics.router, prefix=settings.api_prefix)


# ============================================================================
# Request Logging Middleware
# ============================================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests for monitoring."""
    start_time = datetime.utcnow()

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

    # Log
    logger.info(
        f"{request.method} {request.url.path} "
        f"status={response.status_code} "
        f"duration={duration_ms:.2f}ms "
        f"client={request.client.host if request.client else 'unknown'}"
    )

    # Add custom headers
    response.headers["X-Request-ID"] = str(id(request))
    response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

    return response


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers if settings.environment != "development" else 1,
        log_level=settings.log_level.lower(),
        reload=settings.debug,
        access_log=True
    )
