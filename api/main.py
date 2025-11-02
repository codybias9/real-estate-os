from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
import os

from api.auth import get_current_user, get_tenant_id, require_role
from api.sentry_integration import init_sentry
from api.rate_limit import RateLimitMiddleware

# Initialize Sentry
init_sentry()

app = FastAPI(
    title="Real Estate OS API",
    version="1.0.0",
    description="Production API with JWT authentication and multi-tenant support"
)

# CORS Configuration - Explicit allowlist (no wildcards)
ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Explicit list, no wildcards
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Total-Count", "X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
    max_age=600  # Cache preflight requests for 10 minutes
)

# Rate Limiting Middleware
app.add_middleware(RateLimitMiddleware)


# Public endpoints (no authentication required)

@app.get("/healthz", tags=["health"])
def health():
    """Health check endpoint - publicly accessible"""
    return {"status": "ok"}


@app.get("/version", tags=["health"])
def version():
    """API version - publicly accessible"""
    return {
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development")
    }


# Protected endpoints (require JWT)

@app.get("/api/v1/me", tags=["auth"])
def get_me(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user info"""
    return current_user


@app.get("/ping", tags=["health"])
def ping(current_user: dict = Depends(get_current_user)):
    """Database ping - requires authentication"""
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
    return {
        "ping_count": count,
        "authenticated_as": current_user["username"],
        "tenant_id": current_user.get("tenant_id")
    }


@app.get("/api/v1/properties", tags=["properties"])
def list_properties(
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """
    List properties for authenticated tenant
    Filtered by tenant_id from JWT
    """
    # In production: query DB with tenant_id filter
    return {
        "tenant_id": tenant_id,
        "properties": [],
        "total": 0
    }


@app.get("/api/v1/properties/{property_id}", tags=["properties"])
def get_property(
    property_id: str,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """
    Get property by ID
    Enforces tenant ownership
    """
    # In production: query with WHERE property_id = ? AND tenant_id = ?
    # Return 404 if not found (not 403 to avoid information leak)
    return {
        "property_id": property_id,
        "tenant_id": tenant_id,
        "status": "active"
    }


@app.get("/api/v1/admin/stats", tags=["admin"], dependencies=[Depends(require_role(["admin"]))])
def admin_stats(current_user: dict = Depends(get_current_user)):
    """
    Admin-only endpoint
    Requires 'admin' role
    """
    return {
        "total_tenants": 10,
        "total_properties": 1247,
        "total_users": 45,
        "authenticated_as": current_user["username"],
        "roles": current_user["roles"]
    }


# For development/testing
@app.get("/internal/model-version", tags=["internal"])
def model_version():
    """Internal endpoint for canary testing"""
    return {
        "comp_critic": "v1",
        "dcf_engine": "v1",
        "regime_monitor": "v1"
    }
